"""Build the five feeder packages of the boundary example from model/, and check them.

Usage: python build.py [--zip]      (needs cim-tables installed)

Writes packages/<feeder>/ (the unpacked package), catalog.jsonld and data.json. With --zip it also
writes dist/<feeder>.zip. Output is deterministic: the same model/ gives the same bytes.

The metadata is written three ways from the same facts:
- manifest.jsonld and catalog.jsonld in the Grid Kitchen layout (DCAT-US 3.0 with the gk: vocabulary);
- manifest.xml and the dcat:Dataset header of each RDF XML file in the ENTSO-E layout (Metadata for
  Dataset and Distribution Specification v2.4.0);
- data.json in the Project Open Data layout.
"""
import hashlib
import json
import re
import shutil
import sys
import types
import uuid
import zipfile
from xml.sax.saxutils import escape, quoteattr
from pathlib import Path

import cimtables
from cimgraph.utils import write_json_ld, write_xml
from cimgraph.utils.write_xml import write_graph_xml
from cimprofiles.jsonld import profile_jsonld

HERE = Path(__file__).parent
MODEL = HERE / 'model'
PACKAGES = HERE / 'packages'
PROFILE = 'cim18v17'
AUTHORITY = 'https://github.com/PNNL-CIM-Tools/CIMTBL-Models'
SCOPE = 'boundary_example'
HOME = AUTHORITY + '/tree/main/distribution/boundary_example'
ISSUED = '2026-11-16T00:00:00Z'
VERSION = '1.0.0'
LICENSE = 'https://spdx.org/licenses/BSD-3-Clause.html'
PUBLISHER = 'Pacific Northwest National Laboratory'
CONTACT = 'mailto:example@example.org'  # placeholder
GK_VOCABULARY = '0.1.0'
PUBLISHER_ID = 'https://www.pnnl.gov/'
PROFILE_DOCS = profile_jsonld(PROFILE)
GK_CONTEXT = json.loads((HERE / 'gk-context.jsonld').read_text(encoding='utf-8'))['@context']
# Prefixes, for the RDF XML form. dcterms is Dublin Core's own namespace, with no '#'.
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dcat': 'http://www.w3.org/ns/dcat#',
    'dcterms': 'http://purl.org/dc/terms/',
    'adms': 'http://www.w3.org/ns/adms#',
    'prov': 'http://www.w3.org/ns/prov#',
    'spdx': 'http://spdx.org/rdf/terms#',
    'foaf': 'http://xmlns.com/foaf/0.1/',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'md': 'http://iec.ch/TC57/61970-552/ModelDescription/1#',
    'cim': 'http://cim.ucaiug.io/cim101/draft#',
    'gk': GK_CONTEXT['gk'],
}
# A manifest's JSON-LD context: the profile's (cim, dcat, dct, md), Grid Kitchen's, and the terms used here.
# FrameModel and BoundaryModel are the draft grid-model metadata classes (cim18v17.metadata in CIM-Profiles).
CONTEXT = [PROFILE_DOCS['context'], GK_CONTEXT, {
    'cim:FrameModel.perimeter': {'@type': '@id', '@container': '@set'},
    'dct:requires': {'@type': '@id', '@container': '@set'},
    'dct:conformsTo': {'@type': '@id', '@container': '@set'},
    'dct:license': {'@type': '@id'},
    'dct:spatial': {'@type': '@id'},
    'dcat:isVersionOf': {'@type': '@id'},
    'spdx:algorithm': {'@type': '@id'},
}]
# Properties whose value is a resource, not text
RESOURCES = {'cim:FrameModel.perimeter', 'dct:requires', 'dct:conformsTo', 'dct:license', 'dct:spatial',
             'dcat:isVersionOf', 'spdx:algorithm', 'dcat:accessURL', 'dcat:mediaType'}
RESOURCES |= {key for key, value in GK_CONTEXT.items() if isinstance(value, dict) and value.get('@type') == '@id'}
FEEDERS = {'s1_f1': 's1', 's1_f2': 's1', 's1_f3': 's1', 's2_f1': 's2', 's2_f2': 's2'}
MEDIA = {'.cimtbl': 'text/plain', '.xml': 'application/rdf+xml', '.jsonld': 'application/ld+json'}


def dataset_id(name: str) -> str:
    """A dataset's persistent identifier: the same name gives the same id in every package."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{AUTHORITY}/{SCOPE}/{name}'))


# Datasets that more than one package carries. Their files are byte-identical in each.
SHARED = {
    'reference': dict(
        title='Boundary example: reference data',
        description='Base voltages, the line impedance and the as-built ConnectedArea objects that every '
                    'feeder of the example points at.',
        area='area_d_example', files=['catalog.cimtbl', 'areas.cimtbl'], requires=[]),
    'boundary': dict(
        title='Boundary example: boundary model',
        description='The connectivity nodes either side of each tie between feeders, and nothing else. Each '
                    'names as its container the smallest ConnectedArea that contains both feeders.',
        types=['cim:BoundaryModel'], area='area_d_example',
        files=['boundary.cimtbl', 'boundary.xml', 'boundary.jsonld'], requires=['reference']),
    'ties': dict(
        title='Boundary example: ties between feeders',
        description='The normally-open switches between feeders. Each belongs to the smallest ConnectedArea '
                    'that contains both feeders. Loaded only where both sides of a tie are present.',
        types=['cim:FrameModel'], perimeter=['boundary'], area='area_d_example',
        files=['ties.cimtbl'], requires=['reference', 'boundary']),
}
for _sub in sorted(set(FEEDERS.values())):
    SHARED[f'substation_{_sub}'] = dict(
        title=f'Boundary example: substation {_sub}',
        description=f'Substation {_sub} and its source, repeated in the package of each of its feeders so that '
                    'each solves alone.',
        types=['cim:FrameModel'], area=f'area_ss_{_sub}',
        files=[f'substation_{_sub}.cimtbl'], requires=['reference'])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def header(name: str, spec: dict, areas: dict) -> dict:
    """The dcat:Dataset description of one dataset, as it opens a data file and as a manifest lists it."""
    ident = dataset_id(name)
    out = {
        '@id': 'urn:uuid:' + ident,
        '@type': ['dcat:Dataset'] + spec.get('types', []),
        'dct:identifier': ident,
        'dct:title': spec['title'],
        'dct:description': spec['description'],
        'dct:issued': ISSUED,
        'dcat:version': VERSION,
        'adms:versionNotes': 'First release.',
        'dcat:isVersionOf': f'{HOME}#{name}',
        'md:Model.modelingAuthoritySet': AUTHORITY,
        'dct:license': LICENSE,
        'dct:accessRights': 'public',
        'dct:publisher': {'@id': PUBLISHER_ID, '@type': 'foaf:Organization', 'foaf:name': PUBLISHER},
        'prov:wasGeneratedBy': {'@type': 'prov:Activity', 'rdfs:label': 'CIMTBL-Models boundary_example build.py'},
        # The as-built area the dataset covers: the ConnectedArea object itself
        'dct:spatial': areas[spec['area']],
    }
    if 'cim:BoundaryModel' not in out['@type']:
        # ENTSO-E: a boundary dataset states no conformance
        out['dct:conformsTo'] = PROFILE_DOCS['conventions'][PROFILE_DOCS['default']]
    if spec.get('perimeter'):
        out['cim:FrameModel.perimeter'] = ['urn:uuid:' + dataset_id(n) for n in spec['perimeter']]
    if spec.get('requires'):
        out['dct:requires'] = ['urn:uuid:' + dataset_id(n) for n in spec['requires']]
    out.update(spec.get('facts', {}))
    return out


def expand(value: str) -> str:
    prefix, _, rest = value.partition(':')
    return NS[prefix] + rest if prefix in NS and not rest.startswith('//') else value


def rdf_xml(node: dict, indent: str = '') -> list[str]:
    """One JSON-LD node as RDF XML: text as literals, RESOURCES as rdf:resource, nested nodes inline."""
    types = node['@type'] if isinstance(node['@type'], list) else [node['@type']]
    tag = types[0].replace('dct:', 'dcterms:')
    about = f' rdf:about={quoteattr(node["@id"])}' if '@id' in node else ''
    lines = [f'{indent}<{tag}{about}>']
    lines += [f'{indent}  <rdf:type rdf:resource={quoteattr(expand(extra))}/>' for extra in types[1:]]
    for key, value in node.items():
        if key.startswith('@'):
            continue
        prop = key.replace('dct:', 'dcterms:')
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, dict) and '@type' in item and key not in ('dcat:dataset', 'dcat:distribution'):
                lines += [f'{indent}  <{prop}>'] + rdf_xml(item, indent + '    ') + [f'{indent}  </{prop}>']
            elif isinstance(item, dict):
                lines.append(f'{indent}  <{prop} rdf:resource={quoteattr(item["@id"])}/>')
            elif key in RESOURCES:
                lines.append(f'{indent}  <{prop} rdf:resource={quoteattr(expand(item))}/>')
            elif isinstance(item, bool):
                lines.append(f'{indent}  <{prop}>{str(item).lower()}</{prop}>')
            else:
                lines.append(f'{indent}  <{prop}>{escape(str(item))}</{prop}>')
    return lines + [f'{indent}</{tag}>']


def xmlns() -> str:
    return ' '.join(f'xmlns:{prefix}="{uri}"' for prefix, uri in NS.items())


def stamp_header(path: Path, head: dict) -> None:
    """Replace cim-graph's per-export header (random id, time of writing) with the dataset's own.

    RDF XML: the md:FullModel block becomes a dcat:Dataset block, as ENTSO-E's metadata specification has it.
    JSON-LD: the md:FullModel node becomes the same dcat:Dataset node, as Grid Kitchen's data files have it.
    """
    if path.suffix == '.xml':
        text = path.read_text(encoding='utf-8')
        block = '\n'.join(rdf_xml(head))
        text, n = re.subn(r'<md:FullModel .*?</md:FullModel>', lambda _: block, text, flags=re.S)
        root, m = re.subn(r'<rdf:RDF [^>]*>', f'<rdf:RDF {xmlns()} xmlns:eu="http://iec.ch/TC57/CIM100-European#" '
                          'xmlns:gad="http://gridappsd.org/CIM/extension#" xmlns:nc="http://entsoe.eu/ns/nc#">', text)
        assert n == 1 and m == 1, path
        path.write_text(root, encoding='utf-8')
        return
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['@graph'] = [head] + [node for node in doc['@graph'] if node.get('@type') != 'md:FullModel']
    doc['@context'] = CONTEXT
    path.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')


def write_rdf(network, stem: Path, head: dict) -> None:
    write_xml(network, f'{stem}.xml')
    write_json_ld(network, f'{stem}.jsonld')
    for suffix in ('.xml', '.jsonld'):
        stamp_header(stem.with_suffix(suffix), head)


def write_boundary_rdf(directory: Path, areas: dict) -> None:
    """The boundary model on its own in RDF: only its connectivity nodes, pointing at their areas."""
    scratch = directory / '_boundary.cimtbl'
    scratch.write_text(f'Profile = {PROFILE}\nAuthority = {AUTHORITY}\nModel = {SCOPE}\n\n'
                       'Import areas.cimtbl\nImport boundary.cimtbl\n', encoding='utf-8')
    network = cimtables.load_model(str(scratch))
    scratch.unlink()
    nodes = {network.cim.ConnectivityNode: network.graph[network.cim.ConnectivityNode]}
    write_graph_xml(nodes, str(directory / 'boundary.xml'))
    write_json_ld(types.SimpleNamespace(graph=nodes), str(directory / 'boundary.jsonld'))
    for suffix in ('.xml', '.jsonld'):
        stamp_header(directory / f'boundary{suffix}', header('boundary', SHARED['boundary'], areas))


def area_uris() -> dict:
    """mRID -> URI of every ConnectedArea: what a dataset's dct:spatial points at."""
    scratch = MODEL / '_areas.cimtbl'
    scratch.write_text(f'Profile = {PROFILE}\nAuthority = {AUTHORITY}\nModel = {SCOPE}\n\nImport areas.cimtbl\n',
                       encoding='utf-8')
    network = cimtables.load_model(str(scratch))
    scratch.unlink()
    return {area.mRID: 'urn:uuid:' + area.uri().removeprefix('urn:uuid:')
            for area in network.graph[network.cim.ConnectedArea].values()}


def facts(network, feeder: str) -> dict:
    """The Grid Kitchen facts that can be computed from the feeder's own objects.

    Left out: state, setting and climate (a made-up model has no place), the quality measurements (it has
    no source data), and secondary modeling.
    """
    cim = network.cim
    head = network.find_by_mRID(f'sw_{feeder}')
    primary = head.BaseVoltage.nominalVoltage.to('kV')
    lines = [line for line in network.graph.get(cim.ACLineSegment, {}).values() if line.BaseVoltage is head.BaseVoltage]
    return {
        'gk:vocabularyVersion': GK_VOCABULARY,
        'gk:modelClass': 'gk:ModelClass.Generic',
        'gk:useCase': 'gk:UseCase.Representative',
        'gk:primaryVoltage': round(float(primary), 3),
        'gk:voltageClass': 15,
        'gk:mvConnection': 'gk:Connection.WyeGrounded',
        'gk:feederLength': round(float(sum(line.length.to('km') for line in lines)), 2),
        'gk:loadCount': len(network.graph.get(cim.EnergyConsumer, {})),
        'gk:dgCount': 0,
        'gk:fuseCount': len(network.graph.get(cim.Fuse, {})),
        'gk:recloserCount': len(network.graph.get(cim.Recloser, {})),
        'gk:sectionalizerCount': len(network.graph.get(cim.Sectionaliser, {})),
        'gk:substationLTC': False,
        'gk:regulatorCount': 0,  # the step-down units have no tap changer, so they are not regulators
        'gk:capacitorCount': len(network.graph.get(cim.LinearShuntCompensator, {})),
        'gk:lowVoltageNetwork': False,
        'gk:geographicSpecificity': 'gk:GeographicSpecificity.None',
        'gk:multiFeederCompatible': True,
        'gk:siblingGroup': f'{SCOPE}/{FEEDERS[feeder]}',
    }


def distribution(root: Path, path: Path) -> dict:
    relative = path.relative_to(root).as_posix()
    out = {
        '@id': 'urn:uuid:' + str(uuid.uuid5(uuid.NAMESPACE_URL, f'{AUTHORITY}/{SCOPE}/file/{sha256(path)}/{relative}')),
        '@type': 'dcat:Distribution',
        'dcat:accessURL': relative,
        'dcat:mediaType': MEDIA[path.suffix],
        'dcat:byteSize': path.stat().st_size,
        'spdx:checksum': {'@type': 'spdx:Checksum', 'spdx:algorithm': 'spdx:checksumAlgorithm_sha256',
                          'spdx:checksumValue': sha256(path)},
    }
    if path.suffix == '.cimtbl':
        # A .cimtbl file conforms to the same profile context its JSON-LD twin names in @context
        out['dct:conformsTo'] = [PROFILE_DOCS['context']]
    elif path.suffix == '.jsonld':
        out['dct:conformsTo'] = PROFILE_DOCS['conventions'][PROFILE_DOCS['default']]
    return out


def dataset(root: Path, name: str, spec: dict, files: list[Path], areas: dict) -> dict:
    out = header(name, spec, areas)
    out['dcat:distribution'] = [distribution(root, f) for f in files]
    return out


def manifest_xml(manifest: dict) -> str:
    """The manifest as ENTSO-E's specification lays it out: a dcat:Catalog header, then each dcat:Dataset
    and dcat:Distribution as its own resource, linked by reference. File locations are file:// and media
    types are IANA resources. Nested lists (none here) are not written."""
    def flat(node: dict) -> dict:
        out = dict(node)
        if 'dcat:accessURL' in out:
            out['dcat:accessURL'] = 'file://' + out['dcat:accessURL']
            out['dcat:mediaType'] = 'https://www.iana.org/assignments/media-types/' + out['dcat:mediaType']
        return out
    datasets = manifest['dcat:dataset']
    catalog = {k: v for k, v in manifest.items() if k != '@context'}
    catalog['dcat:dataset'] = [{'@id': ds['@id']} for ds in datasets]
    lines = ['<?xml version="1.0" encoding="utf-8"?>', f'<rdf:RDF {xmlns()}>'] + rdf_xml(catalog)
    for ds in datasets:
        node = dict(ds, **{'dcat:distribution': [{'@id': d['@id']} for d in ds['dcat:distribution']]})
        lines += rdf_xml(node)
        for dist in ds['dcat:distribution']:
            lines += rdf_xml(flat(dist))
    return '\n'.join(lines + ['</rdf:RDF>']) + '\n'


def feeder_spec(feeder: str) -> dict:
    sub = FEEDERS[feeder]
    has_tie = feeder in (MODEL / 'ties.cimtbl').read_text(encoding='utf-8')
    return dict(
        area=f'area_f_{feeder}',
        title=f'Boundary example: feeder {feeder}',
        description=f'Feeder {feeder} of substation {sub}: self-contained, with its substation and source.',
        types=['cim:FrameModel'], perimeter=['boundary'] if has_tie else [],
        requires=['reference', 'boundary', f'substation_{sub}'])


def build_package(feeder: str, areas: dict) -> dict:
    sub = FEEDERS[feeder]
    root = PACKAGES / feeder
    tbl = root / 'cimtbl'
    tbl.mkdir(parents=True)
    shared = ['reference', 'boundary', f'substation_{sub}', 'ties']
    for name in shared:
        for file in SHARED[name]['files']:
            if file.endswith('.cimtbl'):
                shutil.copyfile(MODEL / file, tbl / file)
    shutil.copyfile(MODEL / f'feeder_{feeder}.cimtbl', tbl / f'feeder_{feeder}.cimtbl')
    master = tbl / f'{feeder}.cimtbl'
    master.write_text(
        f'# Feeder {feeder}, self-contained: its shared files, its substation, then its own objects.\n'
        '# ties.cimtbl is in this package but is not imported: the far side of each tie is in another package.\n\n'
        f'Profile = {PROFILE}\nAuthority = {AUTHORITY}\nModel = {SCOPE}\n\n'
        'Import catalog.cimtbl\nImport areas.cimtbl\nImport boundary.cimtbl\n\n'
        f'Import substation_{sub}.cimtbl\nImport feeder_{feeder}.cimtbl\n', encoding='utf-8')
    write_boundary_rdf(tbl, areas)
    for suffix in ('.xml', '.jsonld'):
        (tbl / f'boundary{suffix}').replace(root / f'boundary{suffix}')

    network = cimtables.load_model(str(master))
    spec = feeder_spec(feeder)
    spec['facts'] = facts(network, feeder)
    write_rdf(network, root / feeder, header(feeder, spec, areas))

    def located(file: str) -> Path:
        return tbl / file if file.endswith('.cimtbl') else root / file

    datasets = [dataset(root, feeder, spec, [master, tbl / f'feeder_{feeder}.cimtbl',
                                             root / f'{feeder}.xml', root / f'{feeder}.jsonld'], areas)]
    datasets += [dataset(root, name, SHARED[name], [located(f) for f in SHARED[name]['files']], areas) for name in shared]
    manifest = {
        '@context': CONTEXT,
        '@id': 'urn:uuid:' + dataset_id(f'package/{feeder}'),
        '@type': 'dcat:Catalog',
        'dct:identifier': dataset_id(f'package/{feeder}'),
        'dct:title': f'Boundary example: package {feeder} v{VERSION}',
        'dct:issued': ISSUED,
        'dct:modified': ISSUED,
        'dcat:version': VERSION,
        'dcat:dataset': datasets,
    }
    (root / 'manifest.jsonld').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (root / 'manifest.xml').write_text(manifest_xml(manifest), encoding='utf-8')
    return {'feeder': feeder, 'network': network, 'manifest': manifest, 'spec': spec}


def check(built: list[dict], areas: dict) -> None:
    """The properties the example exists to show. Raises on the first that does not hold."""
    # 1. Every boundary node keeps the container boundary.cimtbl gives it, in every package and assembled
    assembled = cimtables.load_model(str(MODEL / 'boundary_example.cimtbl'))
    expected = {node.mRID: node.ConnectivityNodeContainer.mRID
                for node in assembled.graph[assembled.cim.ConnectivityNode].values()
                if isinstance(node.ConnectivityNodeContainer, assembled.cim.ConnectedArea)}
    assert expected == {'s1_f1_end': 'area_ss_s1', 's1_f2_end': 'area_ss_s1',
                        's1_f3_end': 'area_d_example', 's2_f1_end': 'area_d_example'}, expected
    for item in built:
        for mrid, area in expected.items():
            node = item['network'].find_by_mRID(mrid)
            assert node.ConnectivityNodeContainer.mRID == area, (item['feeder'], mrid)
    # 2. An object two packages declare has one identity
    for mrid in ('area_d_example', 's1_f3_end', 's2_f1_end', 'bv_12p47kv'):
        ids = {item['network'].find_by_mRID(mrid).uri() for item in built} | {assembled.find_by_mRID(mrid).uri()}
        assert len(ids) == 1, (mrid, ids)
    # 3. A shared file has one checksum, and a shared dataset one identifier, wherever it appears
    seen: dict[str, set] = {}
    for item in built:
        for ds in item['manifest']['dcat:dataset'][1:]:
            sums = tuple(d['spdx:checksum']['spdx:checksumValue'] for d in ds['dcat:distribution'])
            seen.setdefault(ds['@id'], set()).add(sums)
    assert all(len(sums) == 1 for sums in seen.values()), seen
    # 4. Assembled, each tie joins its two boundary nodes, and the operating state binds on top
    for tie, ends in (('sw_tie_s1_f1_s1_f2', ['s1_f1_end', 's1_f2_end']), ('sw_tie_s1_f3_s2_f1', ['s1_f3_end', 's2_f1_end'])):
        switch = assembled.find_by_mRID(tie)
        assert [t.ConnectivityNode.mRID for t in switch.Terminals] == ends and switch.open is None, tie
    write_rdf(assembled, HERE / 'boundary_example', header('assembled', dict(
        title='Boundary example: assembled', description='All five feeders, their substations and the ties.',
        types=['cim:GridAssembly'], area='area_d_example'), areas))
    cimtables.load(str(MODEL / 'situation.cimtbl'), assembled)
    assert assembled.find_by_mRID('sw_tie_s1_f1_s1_f2').open is False
    assert assembled.find_by_mRID('sw_s1_f2').open is True
    print(f'ok: {len(built)} packages, {len(seen)} shared datasets, '
          f'{sum(len(v) for v in assembled.graph.values())} objects assembled')


def write_catalogs(built: list[dict], areas: dict) -> None:
    """The public entries: a catalog in the Grid Kitchen layout (DCAT-US 3.0 terms and the gk: vocabulary),
    and a Project Open Data data.json for site indexing."""
    def us3(spec: dict, name: str) -> dict:
        ident = dataset_id(name)
        out = {
            '@type': ['Dataset'] + spec.get('types', []), '@id': 'urn:uuid:' + ident, 'identifier': ident,
            'title': f'{spec["title"]} v{VERSION}', 'description': spec['description'],
            'contactPoint': {'@type': 'Kind', 'fn': 'CIMTBL-Models', 'hasEmail': CONTACT},
            'publisher': {'@type': 'Organization', 'name': PUBLISHER},
            'issued': ISSUED, 'modified': ISSUED, 'version': VERSION,
            'dcat:isVersionOf': f'{HOME}#{name}',
            'keyword': ['CIM', 'distribution feeder', 'boundary model', 'ConnectedArea'], 'theme': ['Energy'],
            'license': LICENSE, 'accessRights': 'public',
            'conformsTo': [{'@type': 'Standard', 'identifier': PROFILE_DOCS['conventions'][PROFILE_DOCS['default']][0],
                            'title': f'CIM-Profiles {PROFILE} SI units'}],
            'dct:spatial': areas[spec['area']],
        }
        if spec.get('perimeter'):
            out['cim:FrameModel.perimeter'] = ['urn:uuid:' + dataset_id(n) for n in spec['perimeter']]
        if spec.get('requires'):
            out['dct:requires'] = ['urn:uuid:' + dataset_id(n) for n in spec['requires']]
        return out

    entries, pod = [], []
    for item in built:
        feeder, spec = item['feeder'], item['spec']
        page = f'{HOME}/packages/{feeder}'
        entry = us3(spec, feeder)
        entry['landingPage'] = {'@type': 'Document', '@id': page, 'title': f'{feeder} version {VERSION}'}
        entry['distribution'] = [{'@type': 'Distribution', 'title': 'CIM .cimtbl, RDF XML and JSON-LD package',
                                  'accessURL': page, 'packageFormat': 'application/zip'}]
        entry.update(spec['facts'])
        entries.append(entry)
        pod.append({
            '@type': 'dcat:Dataset', 'identifier': dataset_id(feeder), 'title': spec['title'],
            'description': spec['description'], 'keyword': ['CIM', 'distribution feeder', 'boundary model'],
            'modified': ISSUED[:10], 'issued': ISSUED[:10], 'accessLevel': 'public', 'license': LICENSE,
            'publisher': {'@type': 'org:Organization', 'name': PUBLISHER},
            'contactPoint': {'@type': 'vcard:Contact', 'fn': 'CIMTBL-Models', 'hasEmail': CONTACT},
            'landingPage': page,
            'distribution': [{'@type': 'dcat:Distribution', 'accessURL': page, 'title': f'Package {feeder}'}],
        })
    entries += [us3(spec, name) for name, spec in SHARED.items()]
    catalog = {
        '@context': ['https://gridkitchen.pnnl.gov/ns/dcat-us/3.0.0/context.jsonld',
                     f'https://gridkitchen.pnnl.gov/ns/gk/{GK_VOCABULARY}/context.jsonld',
                     {'cim': NS['cim'], 'dct': NS['dcterms'],
                      'cim:FrameModel.perimeter': {'@type': '@id', '@container': '@set'},
                      'dct:requires': {'@type': '@id', '@container': '@set'}, 'dct:spatial': {'@type': '@id'}}],
        '@type': 'Catalog', '@id': f'{HOME}/catalog.jsonld',
        'title': 'Boundary example', 'description': 'Five feeder packages joined by boundary nodes.',
        'publisher': {'@type': 'Organization', 'name': PUBLISHER}, 'modified': ISSUED, 'dataset': entries}
    (HERE / 'catalog.jsonld').write_text(json.dumps(catalog, indent=2) + '\n', encoding='utf-8')
    data = {'@context': 'https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld', '@type': 'dcat:Catalog',
            'conformsTo': 'https://project-open-data.cio.gov/v1.1/schema',
            'describedBy': 'https://project-open-data.cio.gov/v1.1/schema/catalog.json', 'dataset': pod}
    (HERE / 'data.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def write_zip(feeder: str) -> None:
    """A zip with manifest.jsonld at its root, with fixed timestamps so the bytes repeat."""
    root = PACKAGES / feeder
    (HERE / 'dist').mkdir(exist_ok=True)
    files = sorted(p for p in root.rglob('*') if p.is_file())
    files.sort(key=lambda p: not p.name.startswith('manifest.'))  # the manifests first
    with zipfile.ZipFile(HERE / 'dist' / f'{feeder}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 11, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def main() -> None:
    if PACKAGES.exists():
        shutil.rmtree(PACKAGES)
    areas = area_uris()
    built = [build_package(feeder, areas) for feeder in FEEDERS]
    check(built, areas)
    write_catalogs(built, areas)
    if '--zip' in sys.argv:
        for feeder in FEEDERS:
            write_zip(feeder)


main()

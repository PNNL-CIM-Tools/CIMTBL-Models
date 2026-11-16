"""Build the five feeder packages of the boundary example from model/, and check them.

Usage: python build.py [--zip]      (needs cim-tables installed)

Writes packages/<feeder>/ (the unpacked package), catalog.jsonld and data.json. With --zip it also
writes dist/<feeder>.zip. Output is deterministic: the same model/ gives the same bytes.
"""
import hashlib
import json
import re
import shutil
import sys
import types
import uuid
import zipfile
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
# The draft grid-model metadata classes (cim18v17.metadata in CIM-Profiles) are in the CIM namespace
CONTEXT = {
    'dcat': 'http://www.w3.org/ns/dcat#',
    'dct': 'http://purl.org/dc/terms/',
    'spdx': 'http://spdx.org/rdf/terms#',
    'foaf': 'http://xmlns.com/foaf/0.1/',
    'cim': 'http://cim.ucaiug.io/cim101/draft#',
    'cim:FrameModel.perimeter': {'@type': '@id', '@container': '@set'},
    'dct:requires': {'@type': '@id', '@container': '@set'},
    'dct:conformsTo': {'@type': '@id', '@container': '@set'},
    'dct:license': {'@type': '@id'},
}
FEEDERS = {'s1_f1': 's1', 's1_f2': 's1', 's1_f3': 's1', 's2_f1': 's2', 's2_f2': 's2'}
PROFILE_DOCS = profile_jsonld(PROFILE)
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
        files=['catalog.cimtbl', 'areas.cimtbl'], requires=[]),
    'boundary': dict(
        title='Boundary example: boundary model',
        description='The connectivity nodes either side of each tie between feeders, and nothing else. Each '
                    'names as its container the smallest ConnectedArea that contains both feeders.',
        types=['cim:BoundaryModel'],
        files=['boundary.cimtbl', 'boundary.xml', 'boundary.jsonld'], requires=['reference']),
    'ties': dict(
        title='Boundary example: ties between feeders',
        description='The normally-open switches between feeders. Each belongs to the smallest ConnectedArea '
                    'that contains both feeders. Loaded only where both sides of a tie are present.',
        types=['cim:FrameModel'], perimeter=['boundary'],
        files=['ties.cimtbl'], requires=['reference', 'boundary']),
}
for _sub in sorted(set(FEEDERS.values())):
    SHARED[f'substation_{_sub}'] = dict(
        title=f'Boundary example: substation {_sub}',
        description=f'Substation {_sub} and its source, repeated in the package of each of its feeders so that '
                    'each solves alone.',
        types=['cim:FrameModel'],
        files=[f'substation_{_sub}.cimtbl'], requires=['reference'])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp_header(path: Path, name: str, title: str) -> None:
    """Replace cim-graph's per-export header (random id, time of writing) with the dataset's own."""
    ident = dataset_id(name)
    if path.suffix == '.xml':
        text = path.read_text(encoding='utf-8')
        text, n_id = re.subn(r'(<md:FullModel rdf:about="urn:uuid:)[0-9a-f-]+', r'\g<1>' + ident, text)
        text, n_at = re.subn(r'(<md:Model\.created>)[^<]+', r'\g<1>' + ISSUED, text)
        assert n_id == 1 and n_at == 1, path
        path.write_text(text, encoding='utf-8')
        return
    doc = json.loads(path.read_text(encoding='utf-8'))
    header = {
        '@id': 'urn:uuid:' + ident,
        '@type': 'dcat:Dataset',
        'dct:identifier': ident,
        'dct:title': title,
        'dct:issued': ISSUED,
        'dcat:version': VERSION,
        'dct:conformsTo': PROFILE_DOCS['conventions'][PROFILE_DOCS['default']],
    }
    doc['@graph'] = [header] + [node for node in doc['@graph'] if node.get('@type') != 'md:FullModel']
    doc['@context'] = [PROFILE_DOCS['context'], {'dcat': CONTEXT['dcat'], 'dct': CONTEXT['dct']}]
    path.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')


def write_rdf(network, stem: Path, name: str, title: str) -> None:
    write_xml(network, f'{stem}.xml')
    write_json_ld(network, f'{stem}.jsonld')
    for suffix in ('.xml', '.jsonld'):
        stamp_header(stem.with_suffix(suffix), name, title)


def write_boundary_rdf(directory: Path) -> None:
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
        stamp_header(directory / f'boundary{suffix}', 'boundary', SHARED['boundary']['title'])


def distribution(root: Path, path: Path) -> dict:
    out = {
        '@type': 'dcat:Distribution',
        'dcat:accessURL': path.relative_to(root).as_posix(),
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


def dataset(root: Path, name: str, spec: dict, files: list[Path]) -> dict:
    out = {
        '@id': 'urn:uuid:' + dataset_id(name),
        '@type': ['dcat:Dataset'] + spec.get('types', []),
        'dct:identifier': dataset_id(name),
        'dct:title': spec['title'],
        'dct:description': spec['description'],
        'dct:issued': ISSUED,
        'dcat:version': VERSION,
        'dct:license': LICENSE,
        'dct:publisher': {'@type': 'foaf:Organization', 'foaf:name': PUBLISHER},
    }
    if spec.get('perimeter'):
        out['cim:FrameModel.perimeter'] = ['urn:uuid:' + dataset_id(n) for n in spec['perimeter']]
    if spec.get('requires'):
        out['dct:requires'] = ['urn:uuid:' + dataset_id(n) for n in spec['requires']]
    out['dcat:distribution'] = [distribution(root, f) for f in files]
    return out


def feeder_spec(feeder: str) -> dict:
    sub = FEEDERS[feeder]
    has_tie = feeder in (MODEL / 'ties.cimtbl').read_text(encoding='utf-8')
    return dict(
        title=f'Boundary example: feeder {feeder}',
        description=f'Feeder {feeder} of substation {sub}: self-contained, with its substation and source.',
        types=['cim:FrameModel'], perimeter=['boundary'] if has_tie else [],
        requires=['reference', 'boundary', f'substation_{sub}'])


def build_package(feeder: str) -> dict:
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
    write_boundary_rdf(tbl)
    for suffix in ('.xml', '.jsonld'):
        (tbl / f'boundary{suffix}').replace(root / f'boundary{suffix}')

    network = cimtables.load_model(str(master))
    spec = feeder_spec(feeder)
    write_rdf(network, root / feeder, feeder, spec['title'])

    def located(file: str) -> Path:
        return tbl / file if file.endswith('.cimtbl') else root / file

    datasets = [dataset(root, feeder, spec, [master, tbl / f'feeder_{feeder}.cimtbl',
                                             root / f'{feeder}.xml', root / f'{feeder}.jsonld'])]
    datasets += [dataset(root, name, SHARED[name], [located(f) for f in SHARED[name]['files']]) for name in shared]
    manifest = {
        '@context': CONTEXT,
        '@id': 'urn:uuid:' + dataset_id(f'package/{feeder}'),
        '@type': 'dcat:Catalog',
        'dct:title': f'Boundary example: package {feeder} v{VERSION}',
        'dct:issued': ISSUED,
        'dcat:dataset': datasets,
    }
    (root / 'manifest.jsonld').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return {'feeder': feeder, 'network': network, 'manifest': manifest, 'spec': spec}


def check(built: list[dict]) -> None:
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
    write_rdf(assembled, HERE / 'boundary_example', 'assembled', 'Boundary example: assembled')
    cimtables.load(str(MODEL / 'situation.cimtbl'), assembled)
    assert assembled.find_by_mRID('sw_tie_s1_f1_s1_f2').open is False
    assert assembled.find_by_mRID('sw_s1_f2').open is True
    print(f'ok: {len(built)} packages, {len(seen)} shared datasets, '
          f'{sum(len(v) for v in assembled.graph.values())} objects assembled')


def write_catalogs(built: list[dict]) -> None:
    """The public entries: a DCAT catalog, and a Project Open Data data.json for site indexing."""
    entries, pod = [], []
    for item in built:
        feeder, spec = item['feeder'], item['spec']
        page = f'{HOME}/packages/{feeder}'
        entries.append({
            '@id': 'urn:uuid:' + dataset_id(feeder), '@type': ['dcat:Dataset'] + spec['types'],
            'dct:identifier': dataset_id(feeder), 'dct:title': spec['title'], 'dct:description': spec['description'],
            'dct:issued': ISSUED, 'dcat:version': VERSION, 'dct:license': LICENSE,
            'dct:publisher': {'@type': 'foaf:Organization', 'foaf:name': PUBLISHER},
            'cim:FrameModel.perimeter': ['urn:uuid:' + dataset_id(n) for n in spec['perimeter']],
            'dct:requires': ['urn:uuid:' + dataset_id(n) for n in spec['requires']],
            'dcat:distribution': [{'@type': 'dcat:Distribution', 'dcat:accessURL': page,
                                   'dct:title': f'Package {feeder}', 'dcat:packageFormat': 'application/zip'}],
        })
        pod.append({
            '@type': 'dcat:Dataset', 'identifier': dataset_id(feeder), 'title': spec['title'],
            'description': spec['description'], 'keyword': ['CIM', 'distribution feeder', 'boundary model'],
            'modified': ISSUED[:10], 'issued': ISSUED[:10], 'accessLevel': 'public', 'license': LICENSE,
            'publisher': {'@type': 'org:Organization', 'name': PUBLISHER},
            'contactPoint': {'@type': 'vcard:Contact', 'fn': 'CIMTBL-Models', 'hasEmail': CONTACT},
            'landingPage': page,
            'distribution': [{'@type': 'dcat:Distribution', 'accessURL': page, 'title': f'Package {feeder}'}],
        })
    for name, spec in SHARED.items():
        entry = {'@id': 'urn:uuid:' + dataset_id(name), '@type': ['dcat:Dataset'] + spec.get('types', []),
                 'dct:identifier': dataset_id(name), 'dct:title': spec['title'], 'dct:description': spec['description']}
        if spec.get('perimeter'):
            entry['cim:FrameModel.perimeter'] = ['urn:uuid:' + dataset_id(n) for n in spec['perimeter']]
        entries.append(entry)
    catalog = {'@context': CONTEXT, '@id': f'{HOME}/catalog.jsonld', '@type': 'dcat:Catalog',
               'dct:title': 'Boundary example', 'dct:modified': ISSUED, 'dcat:dataset': entries}
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
    files.sort(key=lambda p: p.name != 'manifest.jsonld')  # the manifest first
    with zipfile.ZipFile(HERE / 'dist' / f'{feeder}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 11, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def main() -> None:
    if PACKAGES.exists():
        shutil.rmtree(PACKAGES)
    built = [build_package(feeder) for feeder in FEEDERS]
    check(built)
    write_catalogs(built)
    if '--zip' in sys.argv:
        for feeder in FEEDERS:
            write_zip(feeder)


main()

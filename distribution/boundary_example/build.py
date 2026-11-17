"""Build the boundary example from model/ as frames and boundaries, and check it.

Usage: python build.py [--zip]      (needs cim-tables installed)

The organisation is that of the GB Grid Code Planning Code, PC.G.3 (modification GC0139): each
substation and each feeder is a Frame; a Boundary joins each set of frames whose systems connect and
its boundary model holds only connectivity nodes; every object is in exactly one model. The metadata
uses the draft grid-model classes of IEC 61970-55x (cim18v17.metadata in CIM-Profiles) and the ENTSO-E
Metadata for Dataset and Distribution Specification v2.4.0.

Writes:
- framework.jsonld, framework.xml: the framework edition, its frames and its boundaries;
- merged_assembly.xml, .jsonld: the whole assembly in one file of each;
- packages/<feeder>/: one feeder's package, unpacked, with manifest.jsonld and manifest.xml. Its cimtbl/,
  xml/ and jsonld/ hold each dataset in that format, instance data only (no header). A steady state
  hypothesis (SSH) states only the attributes it sets, as a CGMES SSH file does;
- with --zip, dist/<feeder>.zip.

Output is deterministic: the same model/ gives the same bytes.
"""
import hashlib
import json
import re
import shutil
import sys
import tempfile
import types
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import cimtables
from cimgraph.utils import write_json_ld
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
VERSION = '2.0.0'
VERSION_NOTES = 'Reorganised as frames and boundaries after GB Grid Code Planning Code PC.G.3 (GC0139).'
LICENSE = 'https://spdx.org/licenses/BSD-3-Clause.html'
PUBLISHER = {'@id': 'https://www.pnnl.gov/', '@type': 'foaf:Organization',
             'foaf:name': 'Pacific Northwest National Laboratory'}
PROFILE_DOCS = profile_jsonld(PROFILE)
UNITS = PROFILE_DOCS['conventions'][PROFILE_DOCS['default']]
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dcat': 'http://www.w3.org/ns/dcat#',
    'dcterms': 'http://purl.org/dc/terms/',
    'adms': 'http://www.w3.org/ns/adms#',
    'spdx': 'http://spdx.org/rdf/terms#',
    'foaf': 'http://xmlns.com/foaf/0.1/',
    'md': 'http://iec.ch/TC57/61970-552/ModelDescription/1#',
    'cim': 'http://cim.ucaiug.io/cim101/draft#',
}
LISTS = ['cim:FrameModel.perimeter', 'cim:GridModel.usedIn', 'cim:Boundary.separates',
         'cim:Frame.connectsTo', 'cim:Frame.includedIn', 'dct:requires', 'dct:conformsTo']
LINKS = LISTS + ['cim:FrameModel.represents', 'dct:license', 'dct:spatial', 'dcat:isVersionOf',
                 'spdx:algorithm', 'dcat:mediaType']
CONTEXT = [PROFILE_DOCS['context'], {
    'adms': NS['adms'], 'spdx': NS['spdx'], 'foaf': NS['foaf'],
    **{term: {'@type': '@id', '@container': '@set'} if term in LISTS else {'@type': '@id'} for term in LINKS},
}]
MEDIA = {'.cimtbl': 'text/plain', '.xml': 'application/rdf+xml', '.jsonld': 'application/ld+json'}
# The serialisation standard a file conforms to, as ENTSO-E's metadata specification names it
SYNTAX = {'.xml': 'urn:iso:std:iec:61970-552:2016', '.jsonld': 'urn:iso:std:iec:61970-553:draft:ed-1'}

SUBSTATIONS = ['s1', 's2']
FEEDERS = {'s1_f1': 's1', 's1_f2': 's1', 's1_f3': 's1', 's2_f1': 's2', 's2_f2': 's2'}
FRAMES = SUBSTATIONS + list(FEEDERS)
# A boundary is named for its frames, sorted and joined by '-': model/boundary_<set>.cimtbl
BOUNDARIES = {path.stem.removeprefix('boundary_'): path.stem.removeprefix('boundary_').split('-')
              for path in sorted(MODEL.glob('boundary_*-*.cimtbl'))}


def label(name: str) -> str:
    return name.replace('_', '-')


def perimeter(frame: str) -> list[str]:
    return [f'boundary_{name}' for name, frames in BOUNDARIES.items() if frame in frames]


def identifier(kind: str, name: str) -> str:
    """A persistent identifier: the same kind and name give the same UUID wherever they appear."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{AUTHORITY}/{SCOPE}/{kind}/{name}'))


def iri(kind: str, name: str) -> str:
    return 'urn:uuid:' + identifier(kind, name)


def dataset_iri(name: str) -> str:
    return iri('dataset', name)


def frame_file(frame: str) -> str:
    return f'substation_{frame}' if frame in SUBSTATIONS else f'feeder_{frame}'


# Every dataset of the example: its kind, its frame or boundary, what it requires, and its text.
DATASETS = {
    'catalog': dict(kind='reference', requires=[], title='Reference data: catalogue',
                    description='Base voltages and the line impedance that every frame points at.'),
    'containers': dict(kind='reference', requires=[], title='Reference data: containers',
                       description='The containers that more than one frame names: the as-built '
                                   'ConnectedArea objects, nested by ContainedWithin, and the Substations.'),
}
for _name, _frames in BOUNDARIES.items():
    DATASETS[f'boundary_{_name}'] = dict(
        kind='boundary', boundary=_name, requires=['containers'],
        title=f'Boundary model {" | ".join(label(f) for f in _frames)}',
        description='The connectivity nodes where frames ' + ', '.join(label(f) for f in _frames) + ' join, '
                    'and nothing else.')
for _frame in FRAMES:
    _what = f'substation {_frame}: its source' if _frame in SUBSTATIONS else f'feeder {label(_frame)}'
    DATASETS[frame_file(_frame)] = dict(
        kind='frame', frame=_frame, requires=['catalog', 'containers'] + perimeter(_frame),
        title=f'Frame model {label(_frame)}', description=f'The structural model of {_what}.')
for _feeder in FEEDERS:
    DATASETS[f'ssh_{_feeder}'] = dict(
        kind='ssh', frame=_feeder, requires=[f'feeder_{_feeder}'],
        title=f'Steady state hypothesis {label(_feeder)}',
        description=f'The p and q of the loads and the positions of the switches of frame {label(_feeder)}, '
                    'in normal operation.')
# The datasets a model may reference besides its own objects
ALLOWED = {name: (['catalog'] if name == 'containers' else []) +
           (spec['requires'] if spec['kind'] in ('boundary', 'frame') else [])
           for name, spec in DATASETS.items() if spec['kind'] != 'ssh'}


def header(name: str) -> dict:
    """The dcat:Dataset description of a dataset, as a package manifest lists it."""
    spec = DATASETS[name]
    extra_types = {'reference': [], 'boundary': ['cim:BoundaryModel'], 'frame': ['cim:FrameModel'],
                   'ssh': ['cim:FrameModel'], 'assembly': ['cim:GridAssembly']}[spec['kind']]
    out = {
        '@id': dataset_iri(name),
        '@type': ['dcat:Dataset'] + extra_types,
        'dct:identifier': identifier('dataset', name),
        'dct:title': spec['title'],
        'dct:description': spec['description'],
        'dct:issued': ISSUED,
        'dcat:version': VERSION,
        'adms:versionNotes': VERSION_NOTES,
        'dcat:isVersionOf': f'{HOME}#{name}',
        'md:Model.modelingAuthoritySet': AUTHORITY,
        'dct:publisher': PUBLISHER,
        'dct:license': LICENSE,
    }
    if spec['kind'] == 'boundary':
        # ENTSO-E R:MD:ALL:NA:BoundaryIdentification: dct:spatial names the boundary, and no conformance is stated
        out['dct:spatial'] = iri('boundary', spec['boundary'])
    else:
        out['dct:conformsTo'] = UNITS + [PROFILE_DOCS['context']]
    if spec['kind'] in ('frame', 'ssh'):
        out['dct:spatial'] = iri('frame', spec['frame'])
        out['cim:FrameModel.represents'] = iri('frame', spec['frame'])
    if spec['kind'] == 'frame':
        out['cim:FrameModel.perimeter'] = [dataset_iri(b) for b in perimeter(spec['frame'])]
    if spec['requires']:
        out['dct:requires'] = [dataset_iri(n) for n in spec['requires']]
    return out


def framework_nodes(frames: list[str], boundaries: list[str]) -> list[dict]:
    """The cim:Frame and cim:Boundary resources that datasets point at with dct:spatial.

    Each of `frames` is described with the boundaries it connects to. Any other frame that one of
    `boundaries` separates is named only, so that the nodes leave no frame undescribed."""
    named = [f for f in FRAMES if f not in frames and any(f in BOUNDARIES[b] for b in boundaries)]
    nodes = [{'@id': iri('frame', f), '@type': 'cim:Frame', 'dct:title': f'Frame {label(f)}',
              'cim:Frame.connectsTo': [iri('boundary', b.removeprefix('boundary_')) for b in perimeter(f)]}
             for f in frames]
    nodes += [{'@id': iri('frame', f), '@type': 'cim:Frame', 'dct:title': f'Frame {label(f)}'} for f in named]
    nodes += [{'@id': iri('boundary', b), '@type': 'cim:Boundary',
               'dct:title': f'Boundary {" | ".join(label(f) for f in BOUNDARIES[b])}',
               'cim:Boundary.separates': [iri('frame', f) for f in BOUNDARIES[b]]} for b in boundaries]
    return nodes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expand(value: str) -> str:
    prefix, _, rest = value.partition(':')
    prefix = 'dcterms' if prefix == 'dct' else prefix
    return NS[prefix] + rest if prefix in NS and not rest.startswith('//') else value


def rdf_xml(node: dict, indent: str = '') -> list[str]:
    """One JSON-LD node as RDF XML: links as rdf:resource, nested nodes inline, the rest as literals."""
    node_types = node['@type'] if isinstance(node['@type'], list) else [node['@type']]
    tag = node_types[0].replace('dct:', 'dcterms:')
    about = f' rdf:about={quoteattr(node["@id"])}' if '@id' in node else ''
    lines = [f'{indent}<{tag}{about}>']
    lines += [f'{indent}  <rdf:type rdf:resource={quoteattr(expand(extra))}/>' for extra in node_types[1:]]
    for key, value in node.items():
        if key.startswith('@'):
            continue
        prop = key.replace('dct:', 'dcterms:')
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, dict) and set(item) == {'@id'}:
                lines.append(f'{indent}  <{prop} rdf:resource={quoteattr(item["@id"])}/>')
            elif isinstance(item, dict):
                lines += [f'{indent}  <{prop}>'] + rdf_xml(item, indent + '    ') + [f'{indent}  </{prop}>']
            elif key in LINKS or key == 'dcat:accessURL':
                lines.append(f'{indent}  <{prop} rdf:resource={quoteattr(expand(item))}/>')
            else:
                lines.append(f'{indent}  <{prop}>{escape(str(item))}</{prop}>')
    return lines + [f'{indent}</{tag}>']


def rdf_open() -> str:
    return '<rdf:RDF ' + ' '.join(f'xmlns:{p}="{u}"' for p, u in NS.items()) + '>'


def is_kept(prop: str, keep: set[str] | None) -> bool:
    return keep is None or prop.rsplit('.', 1)[-1] in keep


def write_rdf(graph: dict, cim, stem: Path, keep: set[str] | None = None) -> None:
    """A graph's RDF XML and JSON-LD, instance data only: the package manifest is the one place a
    dataset is described, so neither file has a header.

    JSON-LD with no header is read in the profile's default units, which are the units it is written in.
    keep: write only these attributes of each object, as an SSH file states only its own.
    """
    write_graph_xml(graph, f'{stem}.xml', write_model_header=False)
    text = stem.with_suffix('.xml').read_text(encoding='utf-8')
    text = '\n'.join(line for line in text.split('\n')
                     if not (prop := re.match(r'  <(\w+:\w+\.\w+)[ >]', line)) or is_kept(prop.group(1), keep))
    stem.with_suffix('.xml').write_text(text, encoding='utf-8')

    write_json_ld(types.SimpleNamespace(graph=graph, cim=cim), f'{stem}.jsonld')
    doc = json.loads(stem.with_suffix('.jsonld').read_text(encoding='utf-8'))
    assert doc['dcat:distribution']['dct:conformsTo'] == UNITS, doc['dcat:distribution']
    nodes = [{k: v for k, v in node.items() if k.startswith('@') or is_kept(k, keep)} for node in doc['@graph']]
    out = {'@context': doc['@context'], '@graph': nodes}
    stem.with_suffix('.jsonld').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')


def load_by_dataset() -> tuple[object, dict]:
    """Load model/ one file at a time in assembly order, noting which file declares each object."""
    order = ['containers'] + [f'boundary_{b}' for b in BOUNDARIES] + [frame_file(f) for f in FRAMES]
    scratch = MODEL / '_catalog.cimtbl'
    scratch.write_text(master_text('scratch', ['catalog']), encoding='utf-8')
    network = cimtables.load_model(str(scratch))
    scratch.unlink()
    owned = {'catalog': {cls: dict(objs) for cls, objs in network.graph.items()}}
    for name in order:
        before = {(cls, key) for cls, objs in network.graph.items() for key in objs}
        cimtables.load(str(MODEL / f'{name}.cimtbl'), network)
        new = {}
        for cls, objs in network.graph.items():
            for key, obj in objs.items():
                if (cls, key) not in before:
                    new.setdefault(cls, {})[key] = obj
        owned[name] = new
    return network, owned


def write_datasets(network, owned: dict, staging: Path) -> None:
    for name, graph in owned.items():
        write_rdf(graph, network.cim, staging / name)
    edition = {'@id': iri('framework', 'edition-1'), '@type': 'cim:FrameworkEdition',
               'dct:title': 'Boundary example framework, edition 1', 'dct:issued': ISSUED}
    nodes = framework_nodes(FRAMES, list(BOUNDARIES))
    for node in nodes[:len(FRAMES)]:
        node['cim:Frame.includedIn'] = [edition['@id']]
    framework = {'@context': CONTEXT, '@graph': [edition] + nodes}
    (HERE / 'framework.jsonld').write_text(json.dumps(framework, indent=2) + '\n', encoding='utf-8')
    lines = ['<?xml version="1.0" encoding="utf-8"?>', rdf_open()]
    for node in [edition] + nodes:
        lines += rdf_xml(node)
    (HERE / 'framework.xml').write_text('\n'.join(lines + ['</rdf:RDF>']) + '\n', encoding='utf-8')


def apply_ssh(network, staging: Path) -> None:
    """Load each frame's SSH onto the structural model, and write its RDF: each object it updates, with
    only the attributes it sets."""
    for feeder in FEEDERS:
        name = f'ssh_{feeder}'
        records, _ = cimtables.parse_file(MODEL / f'{name}.cimtbl')
        attributes = {field for record in records for field in record.fields if field != 'mRID'}
        mrids = {record.fields['mRID'] for record in records}
        cimtables.load(str(MODEL / f'{name}.cimtbl'), network)
        graph = {}
        for cls, objs in network.graph.items():
            for key, obj in objs.items():
                if getattr(obj, 'mRID', None) in mrids:
                    graph.setdefault(cls, {})[key] = obj
        write_rdf(graph, network.cim, staging / name, keep=attributes)


def master_text(comment: str, imports: list[str]) -> str:
    return (f'# {comment}\n\nProfile = {PROFILE}\nAuthority = {AUTHORITY}\nModel = {SCOPE}\n\n'
            + ''.join(f'Import {name}.cimtbl\n' for name in imports))


def distribution(root: Path, path: Path) -> dict:
    relative = path.relative_to(root).as_posix()
    return {
        '@id': iri('file', f'{sha256(path)}/{relative}'),
        '@type': 'dcat:Distribution',
        'dcat:accessURL': relative,
        'dcat:mediaType': 'https://www.iana.org/assignments/media-types/' + MEDIA[path.suffix],
        'dcat:byteSize': path.stat().st_size,
        'spdx:checksum': {'@type': 'spdx:Checksum', 'spdx:algorithm': 'spdx:checksumAlgorithm_sha256',
                          'spdx:checksumValue': sha256(path)},
        'dct:conformsTo': ([SYNTAX[path.suffix]] if path.suffix in SYNTAX else [])
                          + (UNITS if path.suffix == '.jsonld' else []) + [PROFILE_DOCS['context']],
    }


def manifest_xml(manifest: dict) -> str:
    """The manifest as ENTSO-E's specification lays it out: a dcat:Catalog, then each dcat:Dataset and
    dcat:Distribution as its own resource, linked by reference, with file:// locations."""
    catalog, *framework = manifest['@graph']
    datasets = catalog['dcat:dataset']
    lines = ['<?xml version="1.0" encoding="utf-8"?>', rdf_open()]
    lines += rdf_xml(dict(catalog, **{'dcat:dataset': [{'@id': ds['@id']} for ds in datasets]}))
    for ds in datasets:
        lines += rdf_xml(dict(ds, **{'dcat:distribution': [{'@id': d['@id']} for d in ds['dcat:distribution']]}))
        for dist in ds['dcat:distribution']:
            lines += rdf_xml(dict(dist, **{'dcat:accessURL': 'file://' + dist['dcat:accessURL']}))
    for node in framework:
        lines += rdf_xml(node)
    return '\n'.join(lines + ['</rdf:RDF>']) + '\n'


def package_datasets(feeder: str) -> list[str]:
    substation = FEEDERS[feeder]
    boundaries = sorted(set(perimeter(feeder)) | set(perimeter(substation)))
    return ['catalog', 'containers'] + boundaries + [frame_file(substation), f'feeder_{feeder}', f'ssh_{feeder}']


def build_package(feeder: str, staging: Path) -> dict:
    """One feeder's package: an assembly of its frame, its substation's frame, the boundary models on
    either's perimeter and the reference data, so that it loads and solves on its own."""
    root = PACKAGES / feeder
    for folder in ('cimtbl', 'xml', 'jsonld'):
        (root / folder).mkdir(parents=True)
    names = package_datasets(feeder)
    files = {}
    for name in names:
        files[name] = [root / 'cimtbl' / f'{name}.cimtbl']
        shutil.copyfile(MODEL / f'{name}.cimtbl', files[name][0])
        for folder in ('xml', 'jsonld'):
            shutil.copyfile(staging / f'{name}.{folder}', root / folder / f'{name}.{folder}')
            files[name].append(root / folder / f'{name}.{folder}')
    master = root / 'cimtbl' / f'{feeder}.cimtbl'
    master.write_text(master_text(
        f'Package {label(feeder)}: the reference data, the boundary models, the frames of substation '
        f'{FEEDERS[feeder]} and feeder {label(feeder)},\n# then the feeder\'s steady state hypothesis.', names),
        encoding='utf-8')

    assembly = f'package_{feeder}'
    DATASETS[assembly] = dict(
        kind='assembly', requires=[], title=f'Package {label(feeder)}',
        description=f'Feeder {label(feeder)} with its substation, ready to load and solve on its own: an '
                    'assembly of two frame models, the boundary models on their perimeters, the reference '
                    'data, and the steady state hypothesis of the feeder.')
    datasets = [dict(header(assembly), **{'dcat:distribution': [distribution(root, master)]})]
    for name in names:
        dataset = header(name)
        if DATASETS[name]['kind'] != 'reference':
            dataset['cim:GridModel.usedIn'] = [dataset_iri(assembly)]
        datasets.append(dict(dataset, **{'dcat:distribution': [distribution(root, f) for f in files[name]]}))
    frames = [FEEDERS[feeder], feeder]
    boundaries = [n.removeprefix('boundary_') for n in names if n.startswith('boundary_')]
    manifest = {'@context': CONTEXT, '@graph': [{
        '@id': iri('manifest', feeder),
        '@type': 'dcat:Catalog',
        'dct:identifier': identifier('manifest', feeder),
        'dct:title': f'Boundary example: package {label(feeder)} v{VERSION}',
        'dct:issued': ISSUED,
        'dcat:version': VERSION,
        'dcat:dataset': datasets,
    }] + framework_nodes(frames, boundaries)}
    (root / 'manifest.jsonld').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (root / 'manifest.xml').write_text(manifest_xml(manifest), encoding='utf-8')
    return {'feeder': feeder, 'names': names, 'manifest': manifest, 'master': master}


def references(node) -> set[str]:
    """Every urn:uuid an object of a JSON-LD @graph points at."""
    found = set()
    for key, value in node.items():
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, str) and item.startswith('urn:uuid:') and key != '@id':
                found.add(item)
            elif isinstance(item, dict):
                found |= references(item)
    return found


def described(node) -> set[str]:
    """Every @id a JSON-LD node, or a node nested in it, describes rather than only names."""
    found = {node['@id']} if '@id' in node and len(node) > 1 else set()
    for value in node.values():
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, dict):
                found |= described(item)
    return found


def undescribed(graph: list[dict]) -> set[str]:
    return set().union(*(references(n) for n in graph)) - set().union(*(described(n) for n in graph))


def graph_of(name: str) -> list[dict]:
    """A dataset's JSON-LD objects, from the first package that carries it (check 6 makes every copy identical)."""
    path = sorted(PACKAGES.glob(f'*/jsonld/{name}.jsonld'))[0]
    return json.loads(path.read_text(encoding='utf-8'))['@graph']


def ids_of(name: str) -> set[str]:
    return {node['@id'] for node in graph_of(name)}


def check(network, owned: dict, built: list[dict]) -> None:
    """The rules the example exists to show. Raises on the first that does not hold."""
    # 1. Each object is declared in exactly one file
    declared = {}
    for name in list(owned) + [f'ssh_{f}' for f in FEEDERS]:
        records, _ = cimtables.parse_file(MODEL / f'{name}.cimtbl')
        for record in records:
            mrid = record.fields['mRID']
            if record.form == 'Update':
                assert name.startswith('ssh_') and declared[mrid] == f'feeder_{name.removeprefix("ssh_")}', (name, mrid)
            else:
                assert mrid not in declared, (mrid, name, declared.get(mrid))
                declared[mrid] = name
    # 2. A boundary model holds only connectivity nodes, of two or more frames
    for name, frames in BOUNDARIES.items():
        assert set(owned[f'boundary_{name}']) == {network.cim.ConnectivityNode}, name
        assert len(frames) >= 2 and frames == sorted(frames) and set(frames) <= set(FRAMES), name
    # 3. A model references only its own objects, its perimeter's boundary nodes and the reference data
    for name, allowed in ALLOWED.items():
        reach = ids_of(name).union(*(ids_of(n) for n in allowed))
        stray = set().union(*(references(node) for node in graph_of(name))) - reach
        assert not stray, (name, sorted(stray)[:3])
    # An SSH states attributes of its own frame's objects only
    for feeder in FEEDERS:
        assert ids_of(f'ssh_{feeder}') <= ids_of(f'feeder_{feeder}'), feeder
        assert not set().union(*(references(node) for node in graph_of(f'ssh_{feeder}'))), feeder
    # 4. A boundary node is referenced by exactly the frames of its boundary
    for name, frames in BOUNDARIES.items():
        for node in ids_of(f'boundary_{name}'):
            users = sorted(f for f in FRAMES
                           if any(node in references(obj) for obj in graph_of(frame_file(f))))
            assert users == frames, (name, node, users)
    # 5. Every package loads on its own, keeps every boundary node's container, and has no dangling reference
    # in its RDF files or its manifest
    containers = {node.mRID: node.ConnectivityNodeContainer.mRID
                  for name, graph in owned.items() if name.startswith('boundary_')
                  for node in graph[network.cim.ConnectivityNode].values()}
    for item in built:
        alone = cimtables.load_model(str(item['master']))
        for name in item['names']:
            if name.startswith('boundary_'):
                for node in owned[name][network.cim.ConnectivityNode].values():
                    assert alone.find_by_mRID(node.mRID).ConnectivityNodeContainer.mRID == containers[node.mRID]
        names = item['names']
        stray = set().union(*(references(o) for n in names for o in graph_of(n))) - set().union(*(ids_of(n) for n in names))
        assert not stray, (item['feeder'], sorted(stray)[:3])
        assert not undescribed(item['manifest']['@graph']), (item['feeder'], undescribed(item['manifest']['@graph']))
        assert all(load.p is not None for load in alone.graph[alone.cim.EnergyConsumer].values()), item['feeder']
    framework = json.loads((HERE / 'framework.jsonld').read_text(encoding='utf-8'))['@graph']
    assert not undescribed(framework), undescribed(framework)
    # 6. A shared dataset has one identifier and one set of checksums wherever it appears
    seen: dict[str, set] = {}
    for item in built:
        for ds in item['manifest']['@graph'][0]['dcat:dataset']:
            seen.setdefault(ds['@id'], set()).add(
                tuple(d['spdx:checksum']['spdx:checksumValue'] for d in ds['dcat:distribution']))
    assert all(len(sums) == 1 for sums in seen.values()), seen
    # 7. Assembled, each tie runs from its owner's node to a boundary node, and every SSH binds
    assembled = cimtables.load_model(str(MODEL / 'merged_assembly.cimtbl'))
    for tie, owner, ends in (('sw_tie_s1_f1_s1_f2', 'feeder_s1_f1', ['s1_f1_end', 's1_f2_end']),
                             ('sw_tie_s1_f3_s2_f1', 'feeder_s1_f3', ['s1_f3_end', 's2_f1_end'])):
        switch = assembled.find_by_mRID(tie)
        assert declared[tie] == owner and declared[ends[1]].startswith('boundary_'), tie
        assert [t.ConnectivityNode.mRID for t in switch.Terminals] == ends and switch.normalOpen, tie
        assert switch.open is True, tie
    assert all(assembled.find_by_mRID(f'sw_{feeder}').open is False for feeder in FEEDERS)
    assert all(load.p is not None for load in assembled.graph[assembled.cim.EnergyConsumer].values())
    total = sum(len(v) for v in assembled.graph.values())
    assert total == sum(len(objs) for graph in owned.values() for objs in graph.values()), total
    print(f'ok: {len(built)} packages, {len(FRAMES)} frames, {len(BOUNDARIES)} boundaries, '
          f'{len(seen)} datasets, {total} objects assembled')


def write_assembly(network) -> None:
    write_rdf(network.graph, network.cim, HERE / 'merged_assembly')


def write_zip(feeder: str) -> None:
    """A zip with the manifests first, with fixed timestamps so the bytes repeat."""
    root = PACKAGES / feeder
    (HERE / 'dist').mkdir(exist_ok=True)
    files = sorted(p for p in root.rglob('*') if p.is_file())
    files.sort(key=lambda p: not p.name.startswith('manifest.'))
    with zipfile.ZipFile(HERE / 'dist' / f'{feeder}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 11, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def main() -> None:
    if PACKAGES.exists():
        shutil.rmtree(PACKAGES)
    network, owned = load_by_dataset()
    with tempfile.TemporaryDirectory() as staging:
        write_datasets(network, owned, Path(staging))
        apply_ssh(network, Path(staging))
        built = [build_package(feeder, Path(staging)) for feeder in FEEDERS]
    check(network, owned, built)
    write_assembly(network)
    if '--zip' in sys.argv:
        for feeder in FEEDERS:
            write_zip(feeder)


main()

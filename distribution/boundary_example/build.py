"""Build the boundary example from model/ as frames and boundaries, and check it.

Usage: python build.py [--zip]      (needs cim-tables installed)

The organisation is that of the GB Grid Code Planning Code, PC.G.3 (modification GC0139), as the Grid
Kitchen publishing contract 0.4.0 applies it: each substation and each feeder is a Frame; one Boundary
joins every frame of the distribution area, and its one boundary model holds the nodes where frames meet
and the tie switches between them; every object is in exactly one model. The metadata uses the draft
grid-model classes of IEC 61970-55x (cim18v17.metadata in CIM-Profiles).

Writes:
- framework.xml: the framework edition, its frames and its boundary;
- merged_assembly.xml, .jsonld: the whole assembly in one file of each;
- packages/<feeder>/: one feeder's package, unpacked, with manifest.jsonld (DCAT: every model and file,
  with checksums) and assembly.xml (grid model: how the models fit together as frames and boundary). Its
  cimtbl/, jsonld/ and xml/ hold each model in that format, instance data only (no header). A steady
  state hypothesis (SSH) states only the attributes it sets, as a CGMES SSH file does;
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
# Stands for the utility code of the contract's identifiers, and is the model scope of every file
CODE = 'boundary_example'
NAMESPACE = uuid.UUID('f2acde89-6756-4b1a-8817-efd5597eb830')
ISSUED = '2026-11-18T00:00:00Z'
VERSION = '3.0.0'
LICENSE = 'https://spdx.org/licenses/BSD-3-Clause.html'
PROFILE_DOCS = profile_jsonld(PROFILE)
CONTEXT = PROFILE_DOCS['context']
UNITS = PROFILE_DOCS['conventions'][PROFILE_DOCS['default']]
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'cim': 'http://cim.ucaiug.io/cim101/draft#',
    'md': 'http://iec.ch/TC57/61970-552/ModelDescription/1#',
    'dct': 'http://purl.org/dc/terms/',
    'dcat': 'http://www.w3.org/ns/dcat#',
}
MEDIA = {'.cimtbl': 'text/plain', '.xml': 'application/rdf+xml', '.jsonld': 'application/ld+json'}
RDF_552 = 'urn:iso:std:iec:61970-552:2016'
JSONLD_553 = 'urn:iso:std:iec:61970-553:draft:ed-1'
CONFORMS = {'.cimtbl': [CONTEXT], '.xml': [RDF_552, CONTEXT], '.jsonld': [JSONLD_553, CONTEXT] + UNITS}

SUBSTATIONS = ['s1', 's2']
FEEDERS = {'s1_f1': 's1', 's1_f2': 's1', 's1_f3': 's1', 's2_f1': 's2', 's2_f2': 's2'}
FRAMES = SUBSTATIONS + list(FEEDERS)
AREA = 'area_d_example'
REFERENCE = ['catalog', 'containers']
STRUCTURE = REFERENCE + ['boundary']


def label(name: str) -> str:
    return name.replace('_', '-')


def frame_file(frame: str) -> str:
    return f'substation_{frame}' if frame in SUBSTATIONS else f'feeder_{frame}'


def uuid_of(text: str) -> str:
    return str(uuid.uuid5(NAMESPACE, text))


# Every model of the example: its kind, its title, the frame it represents and the models it requires.
MODELS = {
    'catalog': dict(kind='reference', title='Catalogue data', requires=[]),
    'containers': dict(kind='reference', title='Containers', requires=['catalog']),
    'boundary': dict(kind='boundary', title='Boundary', requires=REFERENCE),
    'ssh_boundary': dict(kind='boundary-ssh', title='Boundary situation', requires=['boundary']),
}
for _frame in FRAMES:
    _what = 'Substation' if _frame in SUBSTATIONS else 'Feeder'
    MODELS[frame_file(_frame)] = dict(kind='frame', title=f'{_what} frame', frame=_frame, requires=STRUCTURE)
    MODELS[f'ssh_{_frame}'] = dict(kind='ssh', title=f'{_what} situation', frame=_frame,
                                   requires=[frame_file(_frame)])
# The structural model each SSH updates
UPDATES = {name: spec['requires'][0] for name, spec in MODELS.items() if spec['kind'] in ('ssh', 'boundary-ssh')}
# The models a structural model may reference besides its own objects
ALLOWED = {name: spec['requires'] for name, spec in MODELS.items() if name not in UPDATES}


def identifiers(network) -> dict:
    """The contract's identifiers (section 2): model, frame and boundary IRIs, keyed by name.

    Shared models are keyed by the UUID of the object they belong to, feeder models by
    <model_id>@<version>, so a shared model has one identifier in every package that carries it."""
    area = str(network.find_by_mRID(AREA).identifier)
    keys = {'catalog': f'catalog/{CODE}', 'containers': f'containers/{area}', 'boundary': f'boundary/{area}',
            'ssh_boundary': f'ssh-boundary/{area}'}
    for sub in SUBSTATIONS:
        station = str(network.find_by_mRID(f'sub_{sub}').identifier)
        keys[f'substation_{sub}'] = f'substation/{station}'
        keys[f'ssh_{sub}'] = f'ssh-substation/{station}'
    for feeder in FEEDERS:
        keys[f'feeder_{feeder}'] = f'feeder/{feeder}@{VERSION}'
        keys[f'ssh_{feeder}'] = f'ssh-feeder/{feeder}@{VERSION}'
    out = {name: 'urn:uuid:' + uuid_of(f'{CODE}/{key}') for name, key in keys.items()}
    out |= {f'frame:{f}': 'urn:uuid:' + uuid_of(f'{CODE}/frame/{f}') for f in FRAMES}
    out['area-boundary'] = 'urn:uuid:' + uuid_of(f'{CODE}/area-boundary/{area}')
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rdf_xml(nodes: list[dict]) -> str:
    """Grid-model nodes as RDF XML: a urn:uuid value is a resource, anything else a literal."""
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<rdf:RDF ' + '\n    '.join(f'xmlns:{p}="{u}"' for p, u in NS.items()) + '>']
    for node in nodes:
        lines.append(f'  <{node["@type"]} rdf:about={quoteattr(node["@id"])}>')
        for key, value in node.items():
            if key.startswith('@'):
                continue
            for item in value if isinstance(value, list) else [value]:
                if item.startswith('urn:uuid:'):
                    lines.append(f'    <{key} rdf:resource={quoteattr(item)}/>')
                else:
                    lines.append(f'    <{key}>{escape(item)}</{key}>')
        lines.append(f'  </{node["@type"]}>')
    return '\n'.join(lines + ['</rdf:RDF>']) + '\n'


def frame_nodes(ids: dict, frames: list[str]) -> list[dict]:
    """The cim:Frame resources and the one cim:Boundary. Each of `frames` is described with the boundary
    it connects to; every other frame of the area is named only, so no reference is left undescribed."""
    nodes = [{'@id': ids[f'frame:{f}'], '@type': 'cim:Frame', 'dct:title': label(f),
              'cim:Frame.connectsTo': ids['area-boundary']} for f in frames]
    nodes += [{'@id': ids[f'frame:{f}'], '@type': 'cim:Frame', 'dct:title': label(f)}
              for f in sorted(FRAMES) if f not in frames]
    nodes.append({'@id': ids['area-boundary'], '@type': 'cim:Boundary', 'dct:title': 'Distribution area boundary',
                  'cim:Boundary.separates': [ids[f'frame:{f}'] for f in sorted(FRAMES)]})
    return nodes


def model_node(ids: dict, name: str, assembly: str) -> dict:
    """A model as assembly.xml describes it (contract 5.3)."""
    spec = MODELS[name]
    node_type = {'reference': 'cim:GridModel', 'boundary': 'cim:BoundaryModel', 'boundary-ssh': 'cim:BoundaryModel',
                 'frame': 'cim:FrameModel', 'ssh': 'cim:FrameModel'}[spec['kind']]
    node = {'@id': ids[name], '@type': node_type, 'dct:title': spec['title'], 'cim:GridModel.usedIn': assembly,
            'dct:requires': [ids[n] for n in spec['requires']]}
    if spec['kind'] in ('boundary', 'boundary-ssh'):
        node['dct:spatial'] = ids['area-boundary']
    if 'frame' in spec:
        node['cim:FrameModel.represents'] = ids[f'frame:{spec["frame"]}']
        node['dct:spatial'] = ids[f'frame:{spec["frame"]}']
    if spec['kind'] == 'frame':
        node['cim:FrameModel.perimeter'] = ids['boundary']
    return node


def is_kept(prop: str, keep: set[str] | None) -> bool:
    return keep is None or prop.rsplit('.', 1)[-1] in keep


def write_rdf(graph: dict, cim, stem: Path, keep: set[str] | None = None) -> None:
    """A graph's RDF XML and JSON-LD, instance data only: the package metadata is the one place a model
    is described, so neither file has a header.

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


def new_objects(network, before: set) -> dict:
    new = {}
    for cls, objs in network.graph.items():
        for key, obj in objs.items():
            if (cls, key) not in before:
                new.setdefault(cls, {})[key] = obj
    return new


def load_by_model() -> tuple[object, dict]:
    """Load the structural models one file at a time in assembly order, noting which file declares
    each object."""
    scratch = MODEL / '_catalog.cimtbl'
    scratch.write_text(master_text('scratch', ['catalog']), encoding='utf-8')
    network = cimtables.load_model(str(scratch))
    scratch.unlink()
    owned = {'catalog': new_objects(network, set())}
    for name in ['containers', 'boundary'] + [frame_file(f) for f in FRAMES]:
        before = {(cls, key) for cls, objs in network.graph.items() for key in objs}
        cimtables.load(str(MODEL / f'{name}.cimtbl'), network)
        owned[name] = new_objects(network, before)
    return network, owned


def write_framework(ids: dict) -> None:
    edition = {'@id': 'urn:uuid:' + uuid_of(f'{CODE}/framework/edition-1'), '@type': 'cim:FrameworkEdition',
               'dct:title': 'Boundary example framework, edition 1', 'dct:issued': ISSUED}
    nodes = frame_nodes(ids, FRAMES)
    for node in nodes[:len(FRAMES)]:
        node['cim:Frame.includedIn'] = edition['@id']
    (HERE / 'framework.xml').write_text(rdf_xml([edition] + nodes), encoding='utf-8')


def apply_ssh(network, staging: Path) -> None:
    """Load each SSH onto the structural model, and write its RDF: each object it updates, with only the
    attributes it sets."""
    for name in UPDATES:
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
    return (f'# {comment}\n\nProfile = {PROFILE}\nAuthority = {AUTHORITY}\nModel = {CODE}\n\n'
            + ''.join(f'Import {name}.cimtbl\n' for name in imports))


def distribution(root: Path, path: Path) -> dict:
    conforms = [RDF_552] if path.name == 'assembly.xml' else CONFORMS[path.suffix]
    return {
        '@type': 'dcat:Distribution',
        'dcat:accessURL': path.relative_to(root).as_posix(),
        'dcat:mediaType': {'@id': 'https://www.iana.org/assignments/media-types/' + MEDIA[path.suffix]},
        'dcat:byteSize': path.stat().st_size,
        'spdx:checksum': {'@type': 'spdx:Checksum', 'spdx:algorithm': {'@id': 'spdx:checksumAlgorithm_sha256'},
                          'spdx:checksumValue': sha256(path)},
        'dct:conformsTo': [{'@id': c} for c in conforms],
    }


def package_models(feeder: str) -> list[str]:
    """A package's models, in the master's import order (contract 3.5)."""
    substation = FEEDERS[feeder]
    return STRUCTURE + [frame_file(substation), frame_file(feeder), 'ssh_boundary', f'ssh_{substation}',
                        f'ssh_{feeder}']


def build_package(feeder: str, staging: Path, ids: dict) -> dict:
    """One feeder's package: its frame, its substation's frame, the boundary model, the reference data and
    their SSHs, so that it loads and solves on its own."""
    root = PACKAGES / feeder
    for folder in ('cimtbl', 'jsonld', 'xml'):
        (root / folder).mkdir(parents=True)
    names = package_models(feeder)
    files = {}
    for name in names:
        files[name] = [root / 'cimtbl' / f'{name}.cimtbl']
        shutil.copyfile(MODEL / f'{name}.cimtbl', files[name][0])
        for folder in ('jsonld', 'xml'):
            shutil.copyfile(staging / f'{name}.{folder}', root / folder / f'{name}.{folder}')
            files[name].append(root / folder / f'{name}.{folder}')
    master = root / 'cimtbl' / f'{feeder}.cimtbl'
    master.write_text(master_text(
        f'Package {label(feeder)}: the reference data, the boundary model, the frames of substation '
        f'{FEEDERS[feeder]} and feeder {label(feeder)},\n# then the steady state hypotheses of the boundary '
        'and of both frames.', names), encoding='utf-8')

    title = f'Boundary example package {label(feeder)} v{VERSION}'
    assembly_id = 'urn:uuid:' + uuid_of(f'{feeder}@{VERSION}')
    assembly = [{'@id': assembly_id, '@type': 'cim:GridAssembly', 'dct:title': title, 'dcat:version': VERSION,
                 'md:Model.modelingAuthoritySet': AUTHORITY}]
    assembly += [model_node(ids, name, assembly_id) for name in names]
    assembly += frame_nodes(ids, [FEEDERS[feeder], feeder])
    (root / 'assembly.xml').write_text(rdf_xml(assembly), encoding='utf-8')

    package = {'@id': assembly_id, '@type': 'dcat:Dataset', 'dct:identifier': assembly_id.removeprefix('urn:uuid:'),
               'dct:title': label(feeder), 'dct:issued': ISSUED, 'dcat:version': VERSION,
               'dct:license': {'@id': LICENSE},
               'dcat:distribution': [distribution(root, master), distribution(root, root / 'assembly.xml')]}
    datasets = [package] + [{'@id': ids[name], '@type': 'dcat:Dataset', 'dct:title': MODELS[name]['title'],
                             'dcat:distribution': [distribution(root, f) for f in files[name]]} for name in names]
    manifest = {
        '@context': [CONTEXT, {'spdx': 'http://spdx.org/rdf/terms#'}],
        '@id': 'urn:uuid:' + uuid_of(f'{feeder}@{VERSION}/manifest'),
        '@type': 'dcat:Catalog',
        'dct:title': title,
        'dct:issued': ISSUED,
        'dcat:dataset': datasets,
    }
    (root / 'manifest.jsonld').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return {'feeder': feeder, 'names': names, 'manifest': manifest, 'assembly': assembly, 'master': master}


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


def undescribed(graph: list[dict]) -> set[str]:
    return set().union(*(references(n) for n in graph)) - {n['@id'] for n in graph if len(n) > 1}


def graph_of(name: str) -> list[dict]:
    """A model's JSON-LD objects, from the first package that carries it (check 6 makes every copy identical)."""
    path = sorted(PACKAGES.glob(f'*/jsonld/{name}.jsonld'))[0]
    return json.loads(path.read_text(encoding='utf-8'))['@graph']


def ids_of(name: str) -> set[str]:
    return {node['@id'] for node in graph_of(name)}


def check(network, owned: dict, built: list[dict]) -> None:
    """The rules the example exists to show. Raises on the first that does not hold."""
    cim = network.cim
    owner = {obj.mRID: name for name, graph in owned.items() for objs in graph.values() for obj in objs.values()}
    # 1. Each object is declared in exactly one file. An Update in an SSH changes an object of the model
    # it updates; one in a structural model, an object of that model (a terminal its equipment created)
    declared = {}
    for name in list(owned) + list(UPDATES):
        records, _ = cimtables.parse_file(MODEL / f'{name}.cimtbl')
        for record in records:
            mrid = record.fields['mRID']
            if record.form == 'Update':
                assert owner[mrid] == UPDATES.get(name, name), (name, mrid, owner[mrid])
            else:
                assert mrid not in declared, (mrid, name, declared.get(mrid))
                declared[mrid] = name
    # 2. The boundary model holds the nodes where frames meet and the switches between them, nothing else,
    # and each of its switches has both terminals on its own nodes
    boundary = owned['boundary']
    assert all(cls in (cim.ConnectivityNode, cim.Terminal) or issubclass(cls, cim.Switch) for cls in boundary)
    switches = [s for cls, objs in boundary.items() if issubclass(cls, cim.Switch) for s in objs.values()]
    nodes = {node.mRID for node in boundary[cim.ConnectivityNode].values()}
    assert all({t.ConnectivityNode.mRID for t in s.Terminals} <= nodes for s in switches)
    # 3. A model references only its own objects, the boundary and the reference data; an SSH states
    # attributes of its own model's objects only
    for name, allowed in ALLOWED.items():
        reach = ids_of(name).union(*(ids_of(n) for n in allowed))
        stray = set().union(*(references(node) for node in graph_of(name))) - reach
        assert not stray, (name, sorted(stray)[:3])
    for name, model in UPDATES.items():
        assert ids_of(name) <= ids_of(model), name
        assert not set().union(*(references(node) for node in graph_of(name))), name
    # 4. A feeder head node joins its substation and its feeder. A tie node is one feeder's, and a tie
    # joins two feeders
    users = {}
    for node in boundary[cim.ConnectivityNode].values():
        iri = f'urn:uuid:{node.identifier}'
        users[node.mRID] = sorted(f for f in FRAMES if any(iri in references(o) for o in graph_of(frame_file(f))))
    tie_nodes = {t.ConnectivityNode.mRID for s in switches for t in s.Terminals}
    for mrid, frames in users.items():
        if mrid in tie_nodes:
            assert len(frames) == 1 and frames[0] in FEEDERS, (mrid, frames)
        else:
            feeder = mrid.removesuffix('_head')
            assert frames == sorted([FEEDERS[feeder], feeder]), (mrid, frames)
    for switch in switches:
        assert len({users[t.ConnectivityNode.mRID][0] for t in switch.Terminals}) == 2, switch.mRID
    # 5. Every package loads on its own, keeps every boundary node's container, has no dangling reference
    # across its RDF files, and its assembly.xml describes every resource it references
    containers = {node.mRID: node.ConnectivityNodeContainer.mRID for node in boundary[cim.ConnectivityNode].values()}
    for item in built:
        alone = cimtables.load_model(str(item['master']))
        for mrid, container in containers.items():
            assert alone.find_by_mRID(mrid).ConnectivityNodeContainer.mRID == container, (item['feeder'], mrid)
        names = item['names']
        stray = set().union(*(references(o) for n in names for o in graph_of(n))) - set().union(*(ids_of(n) for n in names))
        assert not stray, (item['feeder'], sorted(stray)[:3])
        assert not undescribed(item['assembly']), (item['feeder'], undescribed(item['assembly']))
        assert all(load.p is not None for load in alone.graph[alone.cim.EnergyConsumer].values()), item['feeder']
        assert all(s.open is not None for cls, objs in alone.graph.items() if issubclass(cls, alone.cim.Switch)
                   for s in objs.values()), item['feeder']
    # 6. A shared model has one identifier and one set of checksums wherever it appears
    seen: dict[str, set] = {}
    for item in built:
        for ds in item['manifest']['dcat:dataset'][1:]:
            seen.setdefault(ds['@id'], set()).add(
                tuple(d['spdx:checksum']['spdx:checksumValue'] for d in ds['dcat:distribution']))
    assert all(len(sums) == 1 for sums in seen.values()), seen
    # 7. Assembled, the ties are open, the breakers closed and every load has its p
    assembled = cimtables.load_model(str(MODEL / 'merged_assembly.cimtbl'))
    for switch in switches:
        tie = assembled.find_by_mRID(switch.mRID)
        assert tie.normalOpen and tie.open is True, switch.mRID
    assert all(assembled.find_by_mRID(f'brk_{feeder}').open is False for feeder in FEEDERS)
    assert all(load.p is not None for load in assembled.graph[assembled.cim.EnergyConsumer].values())
    total = sum(len(v) for v in assembled.graph.values())
    assert total == sum(len(objs) for graph in owned.values() for objs in graph.values()), total
    print(f'ok: {len(built)} packages, {len(FRAMES)} frames, 1 boundary with {len(switches)} ties, '
          f'{len(seen)} models, {total} objects assembled')


def write_zip(feeder: str) -> None:
    """A zip with the metadata first, with fixed timestamps so the bytes repeat."""
    root = PACKAGES / feeder
    (HERE / 'dist').mkdir(exist_ok=True)
    files = sorted(p for p in root.rglob('*') if p.is_file())
    files.sort(key=lambda p: p.parent != root)
    with zipfile.ZipFile(HERE / 'dist' / f'{feeder}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 11, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def main() -> None:
    if PACKAGES.exists():
        shutil.rmtree(PACKAGES)
    network, owned = load_by_model()
    ids = identifiers(network)
    write_framework(ids)
    with tempfile.TemporaryDirectory() as staging:
        for name, graph in owned.items():
            write_rdf(graph, network.cim, Path(staging) / name)
        apply_ssh(network, Path(staging))
        built = [build_package(feeder, Path(staging), ids) for feeder in FEEDERS]
    check(network, owned, built)
    write_rdf(network.graph, network.cim, HERE / 'merged_assembly')
    if '--zip' in sys.argv:
        for feeder in FEEDERS:
            write_zip(feeder)


main()

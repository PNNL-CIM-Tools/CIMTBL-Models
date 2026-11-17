# Boundary example: frames and boundaries for distribution feeders

A small made-up model, two substations and five feeders joined by two ties. It is organised as frames and
boundaries in the way the GB Grid Code Planning Code describes them (PC.G.3, from modification GC0139), and
it is described with the draft grid-model metadata classes of IEC 61970-55x (`cim18v17.metadata` in
CIM-Profiles). Each feeder is published as its own package, and the five packages join into one model with
no object declared twice. The electrical values are illustrative.

Version 2.0.0 (2026-11-16). This version is for review: the questions at the end are the points where we
are least sure we have read PC.G.3 and the 55x drafts correctly.

## The system

```
  boundary s1 | s1-f1 | s1-f2 | s1-f3                boundary s2 | s2-f1 | s2-f2
         ◆ s1_bus  12.47 kV                                 ◆ s2_bus  13.2 kV
  src_s1 ┤ (frame s1)                                src_s2 ┤ (frame s2)
         ├─R─ frame s1-f1 ──── s1_f1_end ─T1─┐              ├─R─ frame s2-f2
         │                                   ◆ s1_f2_end    │
         ├─R─ frame s1-f2 ───────────────────┘              └─R─ frame s2-f1 ── step-down ──┐
         │                     (boundary s1-f1 | s1-f2)              13.2 to 12.47 kV       │
         └─R─ frame s1-f3 ──── s1_f3_end ─T2────────────────────────────────────────────────◆ s2_f1_end
                                                                    (boundary s1-f3 | s2-f1)

  R       feeder-head recloser, in its feeder's frame
  T1, T2  normally-open ties: T1 in frame s1-f1, T2 in frame s1-f3
  ◆       boundary node
```

## How the GC0139 concepts map

| PC.G.3 concept | Here |
|---|---|
| Profile | Structural data: the frame, boundary and reference models. Situation data: one steady state hypothesis (SSH) per feeder frame. No solution models |
| Frame | Each substation (`s1`, `s2`) and each feeder (`s1-f1` … `s2-f2`): seven frames |
| Boundary | One for each set of frames whose systems connect: four boundaries, two of them multilateral |
| PSM Interface Node | A boundary node: a `ConnectivityNode` in a boundary model |
| Model | One `.cimtbl` file, with its RDF XML and JSON-LD twins: a frame model, a boundary model, an SSH, or reference data |
| Assembly | A feeder package, and the whole example (`model/merged_assembly.cimtbl`) |

| Frame | Holds | Perimeter |
|---|---|---|
| `s1`, `s2` | The source standing for the grid behind the bus | The substation's bus boundary |
| `s1-f1` | Head recloser, lines, loads, tie T1 | `s1` bus boundary; `s1-f1 \| s1-f2` |
| `s1-f2` | Head recloser, lines, loads | `s1` bus boundary; `s1-f1 \| s1-f2` |
| `s1-f3` | Head recloser, lines, loads, tie T2 | `s1` bus boundary; `s1-f3 \| s2-f1` |
| `s2-f1` | Head recloser, lines, loads, the step-down autotransformers | `s2` bus boundary; `s1-f3 \| s2-f1` |
| `s2-f2` | Head recloser, lines, loads | `s2` bus boundary |

| Boundary | Node | Node's container |
|---|---|---|
| `s1 \| s1-f1 \| s1-f2 \| s1-f3` | `s1_bus` | `area_ss_s1` |
| `s2 \| s2-f1 \| s2-f2` | `s2_bus` | `area_ss_s2` |
| `s1-f1 \| s1-f2` | `s1_f2_end`, the far side of T1 | `area_ss_s1` |
| `s1-f3 \| s2-f1` | `s2_f1_end`, the far side of T2 | `area_d_example` |

## The rules

1. **Every object is declared in exactly one model.** An object that several frames name is either a
   boundary node or reference data. Two files never repeat a row.
2. **A boundary model holds connectivity nodes and nothing else** (PC.G.3.4.1, Figure 11). There is one
   boundary for each set of frames whose systems connect, and "all connections between the equipment of one
   Frame and that of another Frame (or set of Frames) are defined using a single Boundary" (PC.G.3.2). So a
   node belongs to the boundary of exactly the frames whose equipment connects to it.
3. **A frame model references only its own objects, the boundary models on its perimeter and the reference
   data.** It never references an object of another frame. This is the `BoundaryModel` rule of the 55x draft
   ("frame models must have associations only with the boundary objects and not with any adjacent frame model
   objects") and the PC.G.3.4.2 rule that Structural Frame Model objects point at PSM Interface Nodes in
   Structural Boundary Models. An SSH states attributes of its own frame's objects only.
4. **The substation bus is a boundary node.** The source is in the substation's frame. Each feeder-head
   recloser is in its feeder's frame, with its bus-side terminal on the bus node. This follows Figure 11, where
   the busbars of Substation B are PSM Interface Nodes and each bay is in the frame of the party it serves,
   and PC.G.1.3.2.1 ("each busbar designated as a PSM Interface Node").
5. **A tie switch is in exactly one frame, its owner's.** The owner is the feeder the source assigns the
   device to, else the one whose name sorts first. One terminal is on the owner's own node, the other on the
   boundary node, where the other feeder's line ends. This is the DNO2–DNO3 coupling of Figure 11: DNO2's
   disconnector, the interface node, then DNO3's breaker.
6. **Containers that several frames name are reference data.** `containers.cimtbl` holds the `Substation`s
   (container of the source and of the feeder-head reclosers) and the as-built `ConnectedArea`s (container of
   the boundary nodes and the ties). They change with construction, never with switching. `catalog.cimtbl`
   holds the base voltages and the line impedance.
7. **A boundary node's container is the smallest `ConnectedArea` that contains every frame of its boundary**,
   and its boundary model is loaded after the containers and before any equipment. (cimtables gives a node
   with no container the container of the first equipment that touches it.)
8. **The SSH is per frame and holds only situation data:** the `p` and `q` of the loads and `Switch.open`.
   Boundaries have none, as PC.G.3.3 expects. `Switch.normalOpen` is structural. Here every SSH describes
   normal operation; another case, such as s1-f2 rolled over onto s1-f1, would be another set of SSH models
   and would move no frame, boundary or container.
9. **A package is an assembly that loads and solves on its own:** the feeder's frame, its substation's frame,
   the boundary models on either perimeter, the reference data and the feeder's SSH. It has no dangling
   references. This departs on purpose from a Solved PSM (PC.G.3.4.2), which keeps only the sender's frame
   and its boundaries. A feeder alone has no source, so the package carries its substation's frame too.
10. **A voltage step sits inside a frame, not at a boundary.** Feeder s2-f1 runs at 13.2 kV and steps down
    through three single-phase autotransformers one span before T2, so both sides of the boundary node are
    12.47 kV.
11. `Switch.areaBoundary = true` on every feeder-head recloser and every tie. `Terminal.BoundedConnectedArea`
    is left to a topology processor and is not written.

## Files

| Path | What it is |
|---|---|
| `model/` | Every model as written, each once. `merged_assembly.cimtbl` assembles them all |
| `framework.jsonld`, `framework.xml` | The framework edition: its seven frames and four boundaries |
| `merged_assembly.xml`, `.jsonld` | The whole assembly in one file of each format |
| `packages/<feeder>/` | One feeder's package, unpacked, as a user would download it |
| `build.py` | Writes everything outside `model/`, and checks it |

A package, for feeder s1-f3:

```
packages/s1_f3/
  manifest.jsonld, manifest.xml     a dcat:Catalog of everything below, with checksums
  cimtbl/
    s1_f3.cimtbl                    the package master: Profile, Authority, Model and Imports only
    catalog.cimtbl                  reference data
    containers.cimtbl               reference data
    boundary_s1-s1_f1-s1_f2-s1_f3.cimtbl   boundary model: s1_bus
    boundary_s1_f3-s2_f1.cimtbl     boundary model: s2_f1_end
    substation_s1.cimtbl            frame model s1
    feeder_s1_f3.cimtbl             frame model s1-f3
    ssh_s1_f3.cimtbl                steady state hypothesis of s1-f3
  xml/                              the same models in RDF XML, one file per model, instance data only
  jsonld/                           the same models in JSON-LD, one file per model, instance data only
```

The master imports reference data, boundary models, frame models, then the SSH. A model that more than one
package carries is byte-identical in each, so a reader joining two packages loads it once and can tell by
checksum that it is the same.

An SSH's RDF names each object it updates by `rdf:about` and states only the attributes it sets, as a CGMES
SSH file does. The frame models' RDF has no `p`, `q` or `Switch.open`.

## The metadata

Each package's `manifest.jsonld` (and `manifest.xml`, the same graph laid out as the ENTSO-E Metadata for
Dataset and Distribution Specification v2.4.0 has it) is a `dcat:Catalog` of these datasets:

| Dataset | `@type` | Links |
|---|---|---|
| The package | `dcat:Dataset`, `cim:GridAssembly` | Its distribution is the master |
| Catalogue, containers | `dcat:Dataset` | — (cim18v17 has no reference-model class, though Frameworks v4 describes a `ReferenceModel`) |
| Each boundary model | `dcat:Dataset`, `cim:BoundaryModel` | `dct:spatial` its `cim:Boundary`; `dct:requires` the containers; `cim:GridModel.usedIn` the package; no `dct:conformsTo` |
| Each frame model | `dcat:Dataset`, `cim:FrameModel` | `cim:FrameModel.represents` and `dct:spatial` its `cim:Frame`; `cim:FrameModel.perimeter` its boundary models; `dct:requires` the reference data and its boundary models; `cim:GridModel.usedIn` the package |
| The SSH | `dcat:Dataset`, `cim:FrameModel` | `represents` and `dct:spatial` the feeder's `cim:Frame`; `dct:requires` the feeder's frame model; `cim:GridModel.usedIn` the package |

After the datasets, the manifest lists the `cim:Frame` and `cim:Boundary` resources they point at. Each
boundary has `cim:Boundary.separates` for its frames. The package's two frames are listed with
`cim:Frame.connectsTo` their boundaries. Any other frame that a listed boundary separates (a sibling feeder, or
the feeder across a tie) is named by its title only. The manifest therefore has no undescribed reference, and the
build checks this. `framework.jsonld` lists every frame, each with `cim:Frame.includedIn` the one
`cim:FrameworkEdition`, and every boundary.

The links are written in the direction cim18v17 serialises them: `GridModel.usedIn`, `Frame.includedIn` and
`Frame.connectsTo`, not their inverses `GridAssembly.contains` and `FrameworkEdition.includes`. One consequence
is that cim18v17 gives no way to place a `Boundary` in a framework edition: `FrameworkEdition.includes` takes
frames only, and `Boundary` has no `includedIn`.

- **`dct:spatial` names the frame or boundary**, as ENTSO-E's R:MD:ALL:NA:BoundaryIdentification has it for a
  boundary and its `dcterms:spatial` definition has it for any model ("the responsibility area … also
  referred to frame").
- **A boundary dataset states no `dct:conformsTo`** (ENTSO-E C:MD:ALL:Dataset.conformsTo:cardinality). Every
  other dataset names the profile's units vocabulary and JSON-LD context.
- Every file is one `dcat:Distribution` with `dcat:accessURL` (relative in JSON-LD, `file://` in RDF XML),
  an IANA `dcat:mediaType`, `dcat:byteSize` and an SPDX SHA-256 checksum.
- A distribution's `dct:conformsTo` names its serialisation standard, as in ENTSO-E's example:
  `urn:iso:std:iec:61970-552:2016` for RDF XML and `urn:iso:std:iec:61970-553:draft:ed-1` for JSON-LD. It also
  names the profile context, as every Grid Kitchen package does, and for JSON-LD the units vocabulary. A
  `.cimtbl` file names only the profile context, because its format has no standard.
- Two terms follow the Grid Kitchen publishing contract rather than ENTSO-E. `md:Model.modelingAuthoritySet` is
  kept, because CIM-Graph writes and reads the authority there. ENTSO-E's R:MD:ALL:NA:previousHeader asks new
  profiles not to use it, but ENTSO-E's own transition example still does. Dependencies are given as
  `dct:requires`, where ENTSO-E replaces `md:Model.DependentOn` with `dct:references`.
- **The manifest is the only place a dataset is described.** A data file holds instance data and nothing
  else: no `md:FullModel`, and no `dcat:Dataset` header. This follows the 55x metadata drafts: one metadata
  file per message, in place of the 61970-552 file headers. ENTSO-E's specification also repeats the dataset
  header in each data file; we do not. A JSON-LD file with no header is read in the profile's default units
  (SI), which are the units it is written in.
- Identifiers are UUID v5 of the dataset's name in this example's namespace, so a model has the same
  identifier in every package that carries it. All files use one `Authority` and `Model`, so a shared object
  has one UUID everywhere.
- `dcterms` is `http://purl.org/dc/terms/`, Dublin Core's own namespace.

## Rebuild and check

```bash
uv run --no-project --prerelease=allow --with cim-tables python distribution/boundary_example/build.py [--zip]
```

The build raises unless:

1. every object is declared in exactly one file, and an SSH updates only its own frame's objects;
2. every boundary model holds only connectivity nodes, of two or more frames;
3. every model's RDF references only its own objects, the boundary models on its perimeter and the reference
   data, and an SSH only its frame's objects;
4. every boundary node is referenced by exactly the frames of its boundary;
5. every package loads on its own, keeps each boundary node's container, gives every load its `p`, and has
   no dangling reference across its RDF files. Its manifest, and `framework.jsonld`, describe every resource
   they reference;
6. a model carried by several packages has one identifier and one set of checksums;
7. assembled, each tie runs from its owner's node to a boundary node and is open, and every head recloser is
   closed.

`--zip` also writes `dist/<feeder>.zip`, manifests first. The output is deterministic.

## Questions for review

1. **Multilateral bus boundaries.** The bus boundary of a substation includes every one of its feeders.
   Adding a feeder changes that boundary, so every sibling's frame has a new perimeter, and under the 55x
   draft "a new Frame object is required if any of its perimeter boundaries are different". Is that the
   intended consequence, or should each feeder bay meet the substation at its own node in a bilateral
   boundary (the draft's "recommended practice")?
2. **Containers as reference data.** Feeder-head reclosers are contained by the `Substation`, and boundary
   nodes and ties by `ConnectedArea`s, all in reference data so that no frame points into another. Is that
   how GB models handle a bay that one party owns inside another party's substation?
3. **Tie containment.** A tie is in its owner's frame, but its container is the smallest area that contains
   both feeders, not the owner's `Feeder`. Does that matter for frame ownership?
4. **Boundary identity.** Frameworks v4 says "a BoundaryModel associates to the Boundary it defines". In
   cim18v17, `BoundaryModel.defines` has an `EquivalentModel` as its target, and its description is that of an
   equivalent. That looks like an error in the draft profile. Until it is fixed, `dct:spatial` carries the link,
   as ENTSO-E's R:MD:ALL:NA:BoundaryIdentification has it. Is `defines` meant to point at the `Boundary`?
5. **Frame and as-built area.** Nothing in cim18v17 or the draft links a `Frame`, `Feeder` or `Substation` to
   its `ConnectedArea`; here they are tied by name only.
6. **Substation situation data.** The source's voltage set point stays in the structural model, so the
   substation frames have no SSH. CGMES would put it in SSH.
7. **Profile keywords.** No `dcat:keyword` (EQ, SSH, …) is set, because a `.cimtbl` model is not split by
   CGMES profile.
8. **Not shown:** solution models, edge models and equivalents.

## Changes from 1.0.0

- Substations and feeders are frames. Each substation bus is a boundary node, and the substation frame holds
  only the source.
- One boundary model per set of connected frames replaces the single `boundary.cimtbl`, and holds one node
  per tie, the far side, instead of both sides.
- Each tie is in its owner's frame. `ties.cimtbl`, a frame that no master loaded, is gone.
- `areas.cimtbl` becomes `containers.cimtbl` and also holds the `Substation`s.
- One SSH per feeder frame, holding the loads' `p` and `q` and the switch positions, replaces the
  assembly-wide `situation.cimtbl`. The rollover case is no longer shipped.
- Each model has its own RDF, and each package's manifest lists one dataset per model plus the frames and
  boundaries they point at. `dct:spatial` names a frame or boundary, not a `ConnectedArea`.
- The Grid Kitchen catalog, `data.json` and `gk:` facts are removed: they belong to a publishing pipeline,
  not to the frame and boundary structure.
- `Terminal.BoundedConnectedArea` is no longer written by hand.
- Data files carry no header. Each package's manifest describes its datasets, once.

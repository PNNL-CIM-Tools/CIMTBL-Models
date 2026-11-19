# Boundary example: frames and boundaries for distribution feeders

A small made-up model, two substations and five feeders joined by two ties. It is organised as frames and
boundaries in the way the GB Grid Code Planning Code describes them (PC.G.3, from modification GC0139), as
the Grid Kitchen publishing contract 0.4.0 applies them, and it is described with the draft grid-model
metadata classes of IEC 61970-55x (`cim18v17.metadata` in CIM-Profiles). Each feeder is published as its own
package, and the five packages join into one model with no object declared twice. The electrical values are
illustrative.

Version 3.0.0 (2026-11-18). This version is for review: the questions at the end are the points where we
are least sure we have read PC.G.3 and the 55x drafts correctly.

## The system

```
  frame s1                                               frame s2
  src_s1 ── s1_bus  12.47 kV                             src_s2 ── s2_bus  13.2 kV
              ├─B─ ◆ s1_f1_head ── frame s1-f1 ── ◆ s1_f1_end ┐           ├─B─ ◆ s2_f2_head ── frame s2-f2
              │                                              T1           │
              ├─B─ ◆ s1_f2_head ── frame s1-f2 ── ◆ s1_f2_end ┘           └─B─ ◆ s2_f1_head ── frame s2-f1 ── step-down ─┐
              │                                                                                13.2 to 12.47 kV    │
              └─B─ ◆ s1_f3_head ── frame s1-f3 ── ◆ s1_f3_end ── T2 ──────────────────────────────────────── ◆ s2_f1_end

  B       a feeder breaker, in its substation's frame
  T1, T2  the normally-open ties, in the boundary model with the nodes on both of their sides
  ◆       a boundary node
```

## How the GC0139 concepts map

| PC.G.3 concept | Here |
|---|---|
| Profile | Structural data: the frame models, the boundary model and the reference data. Situation data: one steady state hypothesis (SSH) for each frame and one for the boundary. No solution models |
| Frame | Each substation (`s1`, `s2`) and each feeder (`s1-f1` … `s2-f2`): seven frames |
| Boundary | One for the distribution area, the set of feeders joined by ties: it separates all seven frames |
| PSM Interface Node | A boundary node: a `ConnectivityNode` in the boundary model |
| Model | One `.cimtbl` file, with its JSON-LD and RDF XML twins |
| Assembly | A feeder package, and the whole example (`model/merged_assembly.cimtbl`) |

| Frame | Holds | Its boundary nodes |
|---|---|---|
| `s1`, `s2` | The source standing for the grid behind the station, the bus, and one breaker per feeder | Its feeders' head nodes |
| `s1-f1`, `s1-f2`, `s1-f3` | Lines and loads | Its head node and its side of its tie |
| `s2-f1` | Lines, loads, and the step-down autotransformers | Its head node and its side of tie T2 |
| `s2-f2` | Lines and loads | Its head node |

| Boundary node | Where | Container |
|---|---|---|
| `s1_f1_head`, `s1_f2_head`, `s1_f3_head` | Between a breaker of `s1` and its feeder's first span | `area_ss_s1` |
| `s2_f1_head`, `s2_f2_head` | Between a breaker of `s2` and its feeder's first span | `area_ss_s2` |
| `s1_f1_end`, `s1_f2_end` | The two sides of tie T1 | `area_ss_s1` |
| `s1_f3_end`, `s2_f1_end` | The two sides of tie T2 | `area_d_example` |

## The rules

1. **Every object is declared in exactly one model.** An object that several frames name is a boundary
   object or reference data. Two files never repeat a row.
2. **The boundary model holds the nodes where frames meet, and the tie switches between them.** Every
   boundary object of the distribution area is in the one `boundary.cimtbl`, so it is the same file in
   every package of the area. "All connections between the equipment of one Frame and that of another
   Frame (or set of Frames) are defined using a single Boundary" (PC.G.3.2).
3. **A frame model references only its own objects, the boundary model and the reference data.** It never
   references an object of another frame. This is the `BoundaryModel` rule of the 55x draft ("frame models
   must have associations only with the boundary objects and not with any adjacent frame model objects")
   and the PC.G.3.4.2 rule that Structural Frame Model objects point at PSM Interface Nodes in Structural
   Boundary Models. An SSH states attributes of its own model's objects only.
4. **The substation frame** is laid out as CIM-Builder lays out a primitive single bus: the source, the bus
   (a `BusbarSection` on the bus node), and one `Breaker` per feeder from the bus to that feeder's **head
   node**. Each head node is a boundary node, so each joint between the substation and a feeder is
   bilateral. The bus node is the substation frame's own. The station's equipment is contained by the
   `Substation`, which is reference data.
5. **The feeder frame** starts at its head node. `Feeder.NormalEnergizingSubstation` is the `Substation`,
   and `Feeder.NormalHeadTerminal` is the terminal of the first span on the head node.
6. **A tie belongs to neither feeder.** Each feeder's own equipment ends on its own side of the tie, and both
   sides are boundary nodes. The switch joins them in the boundary model, so neither feeder's frame has to
   be chosen as the tie's owner, and every package of the area has the whole switch. The tie and its two
   nodes are contained by the smallest `ConnectedArea` that contains both feeders.
7. **Containers that several frames name are reference data.** `containers.cimtbl` holds the
   `Substation`s and the as-built `ConnectedArea`s, nested by `ContainedWithin`. They change with
   construction, never with switching. `catalog.cimtbl` holds the base voltages and the line impedance.
8. **A boundary node's container is the smallest `ConnectedArea` that contains every frame that meets
   there**, and the boundary model is loaded after the containers and before any frame. (cimtables gives a
   node with no container the container of the first equipment that touches it.)
9. **Each frame, and the boundary, has one SSH holding only situation data:** the `p` and `q` of the loads,
   the source's `voltageMagnitude` and `voltageAngle`, and `Switch.open`. `Switch.normalOpen` is
   structural. Each SSH row is an `Update` of an object of its own model, and the structural models' RDF
   has none of these attributes. Every SSH describes normal operation; another case, such as s1-f2 rolled
   over onto s1-f1, would be another set of SSHs and would move no frame, boundary or container.
10. **A package is an assembly that loads and solves on its own:** the feeder's frame, its substation's
    frame, the boundary model, the reference data and the three SSHs. It has no dangling references. This
    departs on purpose from a Solved PSM (PC.G.3.4.2), which keeps only the sender's frame and its
    boundaries. A feeder alone has no source, so the package carries its substation's frame too. The
    sibling feeders' head nodes, and the far sides of the area's ties, are then dead ends, and readers
    ignore them.
11. **A voltage step sits inside a frame, not at a boundary.** Feeder s2-f1 runs at 13.2 kV and steps down
    through three single-phase autotransformers one span before T2, so both sides of T2 are 12.47 kV.
12. `Switch.areaBoundary = true` on every feeder breaker and every tie. `Terminal.BoundedConnectedArea` is
    left to a topology processor and is not written.

## Files

| Path | What it is |
|---|---|
| `model/` | Every model as written, each once. `merged_assembly.cimtbl` assembles them all |
| `framework.xml` | The framework edition: its seven frames and its boundary |
| `merged_assembly.xml`, `.jsonld` | The whole assembly in one file of each format |
| `packages/<feeder>/` | One feeder's package, unpacked, as a user would download it |
| `build.py` | Writes everything outside `model/`, and checks it |

A package, for feeder s1-f3:

```
packages/s1_f3/
  manifest.jsonld          DCAT: every model and file below, with checksums
  assembly.xml             grid model: the assembly, its models, its two frames and the boundary
  cimtbl/
    s1_f3.cimtbl           the package master: Profile, Authority, Model and Imports only
    catalog.cimtbl         reference data
    containers.cimtbl      reference data
    boundary.cimtbl        the boundary model: head nodes, tie nodes and ties
    substation_s1.cimtbl   frame model s1
    feeder_s1_f3.cimtbl    frame model s1-f3
    ssh_boundary.cimtbl    SSH of the boundary: the tie positions
    ssh_s1.cimtbl          SSH of s1: the source's set point and the breaker positions
    ssh_s1_f3.cimtbl       SSH of s1-f3: the loads
  jsonld/                  the same models in JSON-LD, one file per model, instance data only
  xml/                     the same models in RDF XML, one file per model, instance data only
```

The master imports reference data, the boundary model, the frame models, then the SSHs. A model that more
than one package carries is byte-identical in each, so a reader joining two packages loads it once and can
tell by checksum that it is the same.

An SSH's RDF names each object it updates by `rdf:about` and states only the attributes it sets, as a CGMES
SSH file does.

## The metadata

The metadata is split in two, as contract 0.4.0 (5.3) has it.

**`manifest.jsonld`** is the DCAT description of what is in the package: a `dcat:Catalog` whose
`dcat:dataset` lists the package (its distributions are the master and `assembly.xml`) and then one
`dcat:Dataset` per model, titled "Catalogue data", "Containers", "Boundary", "Substation frame", "Feeder
frame", "Boundary situation", "Substation situation" or "Feeder situation". Each file is one
`dcat:Distribution` with:

- `dcat:accessURL`, the relative path;
- an IANA `dcat:mediaType`, `dcat:byteSize` and an SPDX SHA-256 checksum;
- `dct:conformsTo`. For JSON-LD: `urn:iso:std:iec:61970-553:draft:ed-1`, the profile context and its units
  vocabulary. For RDF XML: `urn:iso:std:iec:61970-552:2016` and the profile context. For `.cimtbl`: the
  profile context, since the format has no standard. For `assembly.xml`: 61970-552.

**`assembly.xml`** is the grid-model description: how the models fit together as frames and a boundary.

| Resource | Links |
|---|---|
| `cim:GridAssembly`, the package | `dcat:version`, `md:Model.modelingAuthoritySet` |
| Catalogue, containers: `cim:GridModel` | `cim:GridModel.usedIn` the assembly; `dct:requires` (containers need the catalogue). cim18v17 has no reference-model class, though Frameworks v4 describes a `ReferenceModel` |
| The boundary model and its SSH: `cim:BoundaryModel` | `dct:spatial` the `cim:Boundary`; `cim:GridModel.usedIn`; `dct:requires`; no `dct:conformsTo` |
| Each frame model: `cim:FrameModel` | `cim:FrameModel.represents` and `dct:spatial` its `cim:Frame`; `cim:FrameModel.perimeter` the boundary model; `dct:requires` the reference data and the boundary model |
| Each frame SSH: `cim:FrameModel` | `represents` and `dct:spatial` its `cim:Frame`; `dct:requires` its frame model |
| The package's two `cim:Frame`s | `dct:title`; `cim:Frame.connectsTo` the boundary |
| The `cim:Boundary` | `cim:Boundary.separates` all seven frames. The five outside the package are named by title only, so the file has no undescribed reference, and the build checks this |

`framework.xml` lists every frame, each with `cim:Frame.includedIn` the one `cim:FrameworkEdition`, and the
boundary.

- **The links are written in the direction cim18v17 serialises them:** `GridModel.usedIn`,
  `Frame.includedIn` and `Frame.connectsTo`, not their inverses `GridAssembly.contains` and
  `FrameworkEdition.includes`. One consequence is that cim18v17 gives no way to place a `Boundary` in a
  framework edition: `FrameworkEdition.includes` takes frames only, and `Boundary` has no `includedIn`.
- **`dct:spatial` names the frame or boundary**, as ENTSO-E's R:MD:ALL:NA:BoundaryIdentification has it
  for a boundary and its `dcterms:spatial` definition has it for any model.
- **Data files carry no header.** A data file holds instance data and nothing else: no `md:FullModel` and no
  `dcat:Dataset`. This follows the 55x metadata drafts: one metadata file per message, in place of the
  61970-552 file headers. A JSON-LD file with no header is read in the profile's default units (SI), which
  are the units it is written in.
- **Identifiers follow the contract (section 2):** UUID v5, in the contract's namespace, of
  `<code>/<role>/<key>`, with `boundary_example` as the code. Shared models are keyed by the UUID of their
  distribution area or `Substation`, feeder models by `<feeder>@<version>`, so a shared model has the same
  identifier in every package. All files use one `Authority` and `Model`, so a shared object has one UUID
  everywhere.
- `md:Model.modelingAuthoritySet` and `dct:requires` follow the Grid Kitchen contract rather than ENTSO-E,
  which asks new profiles not to use the first and replaces `md:Model.DependentOn` with `dct:references`.
  CIM-Graph writes and reads the authority there.

## Rebuild and check

```bash
uv run --no-project --prerelease=allow --with cim-tables python distribution/boundary_example/build.py [--zip]
```

The build raises unless:

1. every object is declared in exactly one file, and every `Update` changes an object of its own model;
2. the boundary model holds only connectivity nodes, switches and their terminals, and each switch has
   both terminals on boundary nodes;
3. every model's RDF references only its own objects, the boundary model and the reference data, and an
   SSH only its own model's objects;
4. each head node is referenced by exactly its substation's frame and its feeder's frame, each tie node by
   exactly one feeder frame, and each tie joins two feeders;
5. every package loads on its own, keeps each boundary node's container, gives every load its `p` and
   every switch its `open`, and has no dangling reference across its RDF files. Its `assembly.xml`
   describes every resource it references;
6. a model carried by several packages has one identifier and one set of checksums;
7. assembled, the ties are open, the breakers closed and every load has its `p`.

`--zip` also writes `dist/<feeder>.zip`, metadata first. The output is deterministic.

## Questions for review

1. **Ties in the boundary model.** PC.G.3.4.1 and Figure 11 have a boundary model hold PSM Interface Nodes
   only. Here it also holds each tie switch, with the nodes on both of its sides, so that neither feeder is
   chosen as the tie's owner and its position is in the boundary's SSH. Figure 11's DNO2–DNO3 coupling
   instead gives each party its own switch on either side of one interface node. Is a switch that belongs
   to no single frame acceptable in a boundary model, or should it be a frame of its own?
2. **One boundary per distribution area.** The one boundary separates every frame of the area, so adding
   a feeder anywhere in the area changes it, and under the 55x draft "a new Frame object is required if any
   of its perimeter boundaries are different". The joints themselves are all bilateral (a head node joins
   two frames, a tie two). Should each joint be its own boundary instead?
3. **Containers as reference data.** The station equipment is contained by the `Substation`, and boundary
   nodes and ties by `ConnectedArea`s, all in reference data so that no frame points into another. Is that
   how GB models handle a bay that one party owns inside another party's substation?
4. **Boundary identity.** Frameworks v4 says "a BoundaryModel associates to the Boundary it defines". In
   cim18v17, `BoundaryModel.defines` has an `EquivalentModel` as its target, and its description is that of
   an equivalent. That looks like an error in the draft profile. Until it is fixed, `dct:spatial` carries the
   link, as ENTSO-E's R:MD:ALL:NA:BoundaryIdentification has it. Is `defines` meant to point at the
   `Boundary`?
5. **Boundary SSH.** PC.G.3.3 gives a boundary no situation data. A tie in the boundary has a position, so
   the boundary here has an SSH, typed `cim:BoundaryModel`. Is there a better class for it?
6. **Frame and as-built area.** Nothing in cim18v17 or the draft links a `Frame`, `Feeder` or `Substation` to
   its `ConnectedArea`; here they are tied by name only.
7. **Profile keywords.** No `dcat:keyword` (EQ, SSH, …) is set, because a `.cimtbl` model is not split by
   CGMES profile.
8. **Not shown:** solution models, edge models and equivalents.

## Changes from 2.0.0

- Laid out as Grid Kitchen contract 0.4.0 has a package: one area-wide `boundary.cimtbl` replaces the four
  per-set boundary models, and the metadata is split into `manifest.jsonld` (DCAT) and `assembly.xml` (grid
  model), which replace `manifest.jsonld` and `manifest.xml`. `framework.jsonld` is gone; `framework.xml`
  remains. Identifiers follow the contract.
- The substation frame has a bus and one breaker per feeder, as CIM-Builder lays out a primitive single bus.
  The feeder-head reclosers become those breakers. Each head node is a boundary node, so the joints
  between substation and feeders are bilateral, and the substation bus is no longer a boundary node.
- Each tie and the nodes on both of its sides are in the boundary model, instead of the tie being in its
  owner's frame with only its far side a boundary node. This departs from contract 0.4.0 (3.5 rules 2 and
  6), which keeps a boundary model to connectivity nodes and puts each tie in one feeder's frame.
- The substations and the boundary have SSHs: the source's set point and the breaker positions, and the
  tie positions. A feeder SSH holds only its loads.
- `Feeder.NormalHeadTerminal` is set.

# Boundary example: frames and boundaries for distribution feeders

A small made-up model, two substations and five feeders joined by two ties. It is organised as frames and
boundaries along the lines of J. Britton's Frameworks note (v5) and the GB Grid Code Planning Code (PC.G.3,
from modification GC0139), as the Grid Kitchen publishing contract 0.5.0 applies them, and it is described
with the draft grid-model metadata classes of IEC 61970-55x (`cim18v17.metadata` in CIM-Profiles). Each
feeder is published as its own assembly, which loads and solves on its own; any two or more of the five
snap together into one model. The electrical values are illustrative.

Version 4.1.0 (2026-11-19). This version is for review: the questions at the end are the points where we
are least sure we have read the drafts correctly, or where we depart from them on purpose.

## The system

```
  frame s1                                                frame s2
  src_s1 ── s1_bus  12.47 kV                              src_s2 ── s2_bus  13.2 kV
              ├─B─ ◆ s1_f1_head ── frame s1-f1 ── ◆ s1_f1_bnd ┐           ├─B─ ◆ s2_f2_head ── frame s2-f2
              │                                               T1          │
              ├─B─ ◆ s1_f2_head ── frame s1-f2 ── ◆ s1_f2_bnd ┘           └─B─ ◆ s2_f1_head ── frame s2-f1 ── step-down ─┐
              │                                                                                13.2 to 12.47 kV    │
              └─B─ ◆ s1_f3_head ── frame s1-f3 ── ◆ s1_f3_bnd ── T2 ──────────────────────────────────────── ◆ s2_f1_bnd

  B       a feeder breaker, in its substation's frame
  T1, T2  the normally-open ties, in the frame of the distribution area (s1-s2 area)
  ◆       a boundary node: each joins exactly two frames
```

Feeders s1-f2 and s1-f3 leave the station on one double-circuit structure: their first spans share an
`XYSpacing` and its neutral, and are tied by a `MultiCircuitGroup`. The spacing is not a template, so each
phase names its wire (`OverheadWireInfo` 397 ACSR). Both feeders declare the spacing, and the later restates
it.

## How the concepts map

| Concept | Here |
|---|---|
| Profile | Structural data: the frame models and the boundary model. Situation data: one steady state hypothesis (SSH) for each feeder frame. No solution models |
| Frame | The distribution area (`s1-s2 area`), each substation (`s1`, `s2`) and each feeder (`s1-f1` … `s2-f2`): eight frames |
| Boundary | One for the distribution area: it separates all eight frames |
| Boundary node (PSM Interface Node) | A `ConnectivityNode` in the boundary model |
| Model | One `.cimtbl` file, with its JSON-LD and RDF XML twins |
| Assembly | A feeder assembly (`packages/<feeder>/`), any set of them loaded together, and the whole example (`model/merged_assembly.cimtbl`) |

| Frame | File | Holds | Its boundary nodes |
|---|---|---|---|
| `s1-s2 area` | `dso_area.cimtbl` | The service areas, the five `Feeder`s, and the two ties | The four tie nodes |
| `s1`, `s2` | `substation_s1/s2.cimtbl` | The `Substation`, the source standing for the grid behind the station, the bus, and one breaker per feeder | Its feeders' head nodes |
| `s1-f1`, `s1-f2`, `s1-f3` | `feeder_*.cimtbl` | Lines and loads | Its head node and its side of its tie |
| `s2-f1` | `feeder_s2_f1.cimtbl` | Lines, loads, and the step-down autotransformers | Its head node and its side of tie T2 |
| `s2-f2` | `feeder_s2_f2.cimtbl` | Lines and loads | Its head node |

| Boundary node | Joins | Container |
|---|---|---|
| `s1_f1_head`, `s1_f2_head`, `s1_f3_head` | A breaker of `s1` and its feeder's first span | `sub_s1_service_area` |
| `s2_f1_head`, `s2_f2_head` | A breaker of `s2` and its feeder's first span | `sub_s2_service_area` |
| `s1_f1_bnd`, `s1_f2_bnd` | Tie T1 and a feeder's last span | `sub_s1_service_area` |
| `s1_f3_bnd`, `s2_f1_bnd` | Tie T2 and a feeder's last span | `s1_s2_dist_area` |

## The rules

1. **Each file declares what it uses, and every declaration of an object agrees.** A feeder's file
   declares the base voltages, line impedances, wires and spacings it uses, so each feeder assembly is
   self-contained and no separate reference model is needed. When a later file declares the same object
   again it restates it: cimtables accepts an identical restatement and raises on any difference. Each
   model's RDF carries every object its file declares, restated ones included, under the one identity it
   has everywhere. Only reference data and containers are restated, never equipment.
2. **The boundary model holds the nodes where frames meet, and nothing else.** Each node joins exactly two
   frames, so every joint is bilateral (Frameworks v5, "Simple Connectivity Node Boundaries"). The one
   `boundary.cimtbl` is the same file in every assembly.
3. **A frame model references only its own objects, the boundary model and the distribution-area frame.**
   It never references a substation or feeder frame other than its own. The area's frame holds what every
   frame of the area names: the service areas that contain the boundary nodes, and the `Feeder`s that
   contain each feeder's equipment. An SSH states attributes of its own model's objects only.
4. **The distribution area is a frame.** It holds its as-built `ConnectedArea`s (nested by
   `ContainedWithin`), its `Feeder`s with their `NormalEnergizingSubstation`, and its ties. It restates the
   two `Substation`s its Feeders name. Every assembly of the area carries it.
5. **A tie belongs to the distribution-area frame, not to either feeder.** Each feeder's last span ends on
   its own side of the tie, and both sides are boundary nodes, so neither feeder is chosen as the tie's
   owner and the joint between the area's frame and each feeder is bilateral. A tie is contained by the
   smallest `ConnectedArea` that contains both of its feeders.
6. **The substation frame** is laid out as CIM-Builder lays out a primitive single bus: the source, the bus
   (a `BusbarSection` on the bus node), and one `Breaker` per feeder from the bus to that feeder's **head
   node**, the feeder's exit from the station. The source stands for the 46 kV sub-transmission network,
   which will be a frame of its own and is out of scope for now.
7. **The feeder frame** starts at its head node. Its equipment is contained by its `Feeder`, in the
   area's frame, and its first span's terminal on the head node is the Feeder's `NormalHeadTerminal`
   (written from the terminal's side, `Terminal.NormalHeadFeeder`, the side cim18v17 serializes).
8. **A boundary node's container is the smallest `ConnectedArea` that contains both frames that meet
   there.** `ConnectedArea` is how an as-built area contains a node that belongs to no one substation or
   line, without an artificial `Substation` or `Line`. The boundary model is loaded after the area's frame
   and before any other frame (cimtables gives a node with no container the container of the first
   equipment that touches it).
9. **Each feeder frame has one SSH: the `p` and `q` of its loads.** `Switch.normalOpen` and `Switch.open`
   of the breakers and ties are in the structural models for now. Every SSH describes normal operation;
   another case, such as s1-f2 rolled over onto s1-f1, would be another set of SSHs and would move no frame,
   boundary or container.
10. **A feeder assembly loads and solves on its own:** the area's frame, the boundary model, the feeder's
    frame, its substation's frame and the feeder's SSH. It has no dangling references. A feeder alone has
    no source, so the assembly carries its substation's frame too. The sibling feeders' head nodes, and the
    far sides of the area's ties, are then dead ends: the ties are open, and readers ignore them.
11. **Feeder assemblies snap together.** Loading the masters of any two or more of them into one model
    gives exactly the union of their objects: the area's frame, the boundary model and a shared substation
    frame restate, and nothing is declared twice with different values.
12. **A voltage step sits inside a frame, not at a boundary.** Feeder s2-f1 runs at 13.2 kV and steps down
    through three single-phase autotransformers one span before T2, so both sides of T2 are 12.47 kV.
13. `Switch.areaBoundary = true` on every feeder breaker and every tie. `Terminal.BoundedConnectedArea` is
    left to a topology processor and is not written.

## Files

| Path | What it is |
|---|---|
| `model/` | Every model as written. `merged_assembly.cimtbl` assembles them all |
| `framework.xml` | The framework edition: its eight frames and its boundary |
| `merged_assembly.xml`, `.jsonld` | The whole assembly in one file of each format |
| `packages/<feeder>/` | One feeder assembly, unpacked, as a user would download it |
| `build.py` | Writes everything outside `model/`, and checks it |

A feeder assembly, for feeder s1-f3:

```
packages/s1_f3/
  manifest.jsonld          DCAT: every model and file below, with checksums
  assembly.xml             grid model: the assembly, its models, its three frames and the boundary
  cimtbl/
    s1_f3.cimtbl           the master: Profile, Authority, Model and Imports only
    dso_area.cimtbl        frame model s1-s2 area: service areas, Feeders, ties
    boundary.cimtbl        the boundary model: head nodes and tie nodes
    substation_s1.cimtbl   frame model s1
    feeder_s1_f3.cimtbl    frame model s1-f3
    ssh_s1_f3.cimtbl       SSH of s1-f3: the loads
  jsonld/                  the same models in JSON-LD, one file per model, instance data only
  xml/                     the same models in RDF XML, one file per model, instance data only
```

The master imports the area's frame, the boundary model, the substation and feeder frames, then the SSH. A
model that more than one assembly carries is byte-identical in each, so a reader joining two assemblies
can tell by checksum that it is the same; loading it twice only restates it.

An SSH's RDF names each object it updates by `rdf:about` and states only the attributes it sets, as a CGMES
SSH file does.

## The metadata

The metadata is split in two, as Grid Kitchen contract 0.5.0 (5.3) has it, and each feeder assembly is
identified as a Grid Kitchen package would be (contract section 2), so its metadata can be read by the
portal as it is.

| Feeder | `model_id` | Substation's sibling group | Area's group |
|---|---|---|---|
| s1-f1 | `XX-6ff8fc3330` | `XX-3db0e703a8` (s1) | `XX-31208a45a0` |
| s1-f2 | `XX-83f72e3bb3` | `XX-3db0e703a8` (s1) | `XX-31208a45a0` |
| s1-f3 | `XX-3cf8687e9a` | `XX-3db0e703a8` (s1) | `XX-31208a45a0` |
| s2-f1 | `XX-7a0c44bb82` | `XX-e036f0aad6` (s2) | `XX-31208a45a0` |
| s2-f2 | `XX-2b4028a34f` | `XX-e036f0aad6` (s2) | `XX-31208a45a0` |

The contract takes HMAC-SHA256 of the source names with a secret key. A made-up model has no secret, so
the example takes SHA-256 of `boundary_example/<substation>/<feeder>`, `boundary_example/<substation>`
and `boundary_example/area/<area>`, and `XX` stands for the state code.

**`manifest.jsonld`** is the DCAT description of what is in the assembly: a `dcat:Catalog`, titled
"Grid Kitchen package `<model_id>` v`<version>`", whose `dcat:dataset` lists:

1. **The package**, `@id` the version identifier, with `dct:identifier`, `dct:title` (the `model_id`),
   `dct:issued`, `dcat:version`, `dcat:isVersionOf` (`https://gridkitchen.pnnl.gov/models/<model_id>`),
   `dcat:landingPage` (`…/models/<model_id>/<version>`), `dcat:inSeries` and `dct:license`. Its
   distributions are the master and `assembly.xml`.
2. **One dataset per model**, titled "Distribution area frame", "Boundary", "Substation frame",
   "Feeder frame" or "Feeder situation", whose distributions are its three files.

`dcat:inSeries` names two `dcat:DatasetSeries`, described inline with their titles: the feeders of the
feeder's substation (`https://gridkitchen.pnnl.gov/series/<sibling group>`, "Grid Kitchen substation
…") and the feeders of its distribution area (`…/series/<area group>`, "Grid Kitchen distribution
area …"). A landing page lists the other feeders of either from the catalog. The ties themselves are
in the area's frame model, which every package ships.

Each file is one `dcat:Distribution` with:

- `dcat:accessURL`, the relative path;
- an IANA `dcat:mediaType`, `dcat:byteSize` and an SPDX SHA-256 checksum;
- `dct:conformsTo`. For JSON-LD: `urn:iso:std:iec:61970-553:draft:ed-1`, the profile context and its units
  vocabulary. For RDF XML: `urn:iso:std:iec:61970-552:2016` and the profile context. For `.cimtbl`: the
  profile context, since the format has no standard. For `assembly.xml`: 61970-552.

**`assembly.xml`** is the grid-model description: how the models fit together as frames and a boundary.

| Resource | Links |
|---|---|
| `cim:GridAssembly`, the feeder assembly | `rdf:about` the version identifier, the manifest's package; `dct:title` the manifest's; `dcat:version`, `md:Model.modelingAuthoritySet` |
| The boundary model: `cim:BoundaryModel` | `dct:spatial` the `cim:Boundary`; `cim:GridModel.usedIn`; `dct:requires` the area's frame model; no `dct:conformsTo` |
| The area's frame model: `cim:FrameModel` | `cim:FrameModel.represents` and `dct:spatial` its `cim:Frame`; `cim:FrameModel.perimeter` the boundary model; `dct:requires` the boundary model |
| Each substation frame model: `cim:FrameModel` | As the area's; `dct:requires` the boundary model |
| Each feeder frame model: `cim:FrameModel` | As the area's; `dct:requires` the area's frame model and the boundary model |
| The feeder's SSH: `cim:FrameModel` | `represents` and `dct:spatial` its `cim:Frame`; `dct:requires` its frame model |
| The assembly's three `cim:Frame`s | `dct:title` the area's group, the sibling group or the `model_id`; `cim:Frame.connectsTo` the boundary |
| The `cim:Boundary` | `cim:Boundary.separates` all eight frames: the area's frame first, then the other seven by title. The five outside the assembly are named by title only, so the file has no undescribed reference, and the build checks this |

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
  `<code>/<role>/<key>`, with `boundary_example` as the code. The area's frame and boundary models are
  keyed by the UUID of the distribution area, a substation's by the UUID of its `Substation`, feeder models
  by `<model_id>@<version>`, so a shared model has the same identifier in every assembly. A frame is keyed
  by its title. The package, the `cim:GridAssembly`, is `<model_id>@<version>`, and the manifest
  `<model_id>@<version>/manifest`. All files use one
  `Authority` and `Model`, so a shared or restated object has one UUID everywhere.
- `md:Model.modelingAuthoritySet` and `dct:requires` follow the Grid Kitchen contract rather than ENTSO-E,
  which asks new profiles not to use the first and replaces `md:Model.DependentOn` with `dct:references`.
  CIM-Graph writes and reads the authority there.

## Rebuild and check

```bash
uv run --no-project --prerelease=allow --with cim-tables --with rdflib python distribution/boundary_example/build.py [--zip]
```

The model needs a cim-tables that accepts restated objects, which is not yet released; until it is, run
against a local checkout (`--with-editable ../CIM-Tables` and its sibling CIM-Graph and CIM-Profiles).

The build raises unless:

1. no equipment is declared in more than one file, and every `Update` changes an object of its own model;
2. the boundary model holds only connectivity nodes;
3. every model's RDF references only its own objects and the models it requires, and an SSH only its own
   model's objects;
4. each head node is referenced by exactly its substation's frame and its feeder's frame, each tie node by
   exactly the area's frame and one feeder frame, and each tie joins two feeders;
5. every feeder assembly loads on its own, keeps each boundary node's container, gives every load its `p`
   and every switch its `open`, and has no dangling reference across its RDF files. Its `assembly.xml`
   describes every resource it references;
6. a model carried by several assemblies has one identifier and one set of checksums;
7. every combination of two to five feeder assemblies, their masters loaded into one model, holds exactly
   the objects of their RDF files;
8. assembled, the ties are open, the breakers closed and every load has its `p`;
9. each assembly's `manifest.jsonld` and `assembly.xml` parse with rdflib, every manifest key expanding
   to an IRI (the profile context is read from cim-profiles' cache, so the check runs offline); the
   manifest's datasets are exactly the assembly and the models of `assembly.xml`, each model used in the
   assembly; and no data file carries a header.

`--zip` also writes `dist/<feeder>.zip`, metadata first. The output is deterministic.

## Questions for review

1. **Frames per feeder.** Frameworks v5 ("LV Frameworks") and J. Britton's review argue against one frame
   per feeder: open points move, so equipment moves between frames, and a feeder study is better assembled
   by tracing from its source. Frames would then follow distribution divisions. Here each feeder stays a
   frame because each feeder assembly is shipped on its own, to be exported and solved in OpenDSS by
   itself or with any of the area's other feeders. Is there a way to keep that with division-sized frames,
   for example a feeder assembly that is a traced extract of a division frame?
2. **References to the area's frame.** Frameworks v5 and the 55x draft have frame models reference only
   boundary and reference models. Here every feeder frame references the area's frame (its `Feeder`), and
   the area's frame and the boundary model require each other (the ties end on boundary nodes, and the
   boundary nodes are contained by the area's `ConnectedArea`s). Should the area's frame be described as a
   reference model instead, even though it holds the ties?
3. **Restated reference data.** Frameworks v5 puts objects such as base voltages in reference models. Here
   each file declares the reference data it uses, and an object several models declare appears in each
   one's RDF, identical, under one identity. Is a restated object acceptable in a frame model, or must each
   object be in exactly one grid model?
4. **Ties in the area's frame.** Frameworks v5 ("2-Party Station Boundaries") puts a switch between two
   parties in the frame responsible for its state. Here that is the area's frame, which keeps both feeders
   free of it. Is that a fair reading, given that the area's frame is in every assembly?
5. **One boundary per distribution area.** The one boundary separates every frame of the area, so adding
   a feeder anywhere in the area changes it, and under the 55x draft "a new Frame object is required if any
   of its perimeter boundaries are different". The joints themselves are all bilateral. Should each joint
   be its own boundary instead?
6. **Containers.** Frameworks v5 recommends artificial `Substation` or `Line` containers for boundary
   nodes. Here the boundary nodes are contained by the as-built `ConnectedArea`s, which exist for that
   purpose. Is that acceptable?
7. **Switch positions.** `Switch.open` of the breakers and ties is in the structural models, with
   `normalOpen`, and only the loads are in the SSHs. Frameworks v5 has situation models plug into frame
   models one to one. Should the area's frame and the substation frames each have an SSH holding their
   switch positions?
8. **The substation and the sub-transmission frame.** J. Britton prefers the whole substation in the
   higher-voltage frame, with distribution frames connecting to transmission frames rather than to an
   infinite source. The 46 kV sub-transmission network is out of scope for now, so each substation is its
   own frame and its source stands for the network behind it.
9. **Boundary identity.** Frameworks v5 says "a BoundaryModel associates to the Boundary it defines". In
   cim18v17, `BoundaryModel.defines` has an `EquivalentModel` as its target, and its description is that of
   an equivalent. That looks like an error in the draft profile. Until it is fixed, `dct:spatial` carries the
   link, as ENTSO-E's R:MD:ALL:NA:BoundaryIdentification has it. cim18v17 also has no `ReferenceModel`,
   `Reference` or `GridFile`, which Frameworks v5 describes.
10. **Frame and as-built area.** Nothing in cim18v17 or the draft links a `Frame`, `Feeder` or `Substation`
    to its `ConnectedArea`; here they are tied by name only.
11. **Profile keywords.** No `dcat:keyword` (EQ, SSH, …) is set, because a `.cimtbl` model is not split by
    CGMES profile.
12. **Not shown:** solution models, edge models, equivalents and tie flows.

## Departures from Grid Kitchen contract 0.5.0

Contract 0.5.0 adopts this example's 4.1.0 layout and metadata: the distribution area as a frame holding
its `ConnectedArea`s, `Feeder`s and ties; reference data restated in each file, with no catalog or
containers models; one SSH per feeder; the area's group and distribution-area series; and the model
titles and identifier roles used here. What remains is example-only:

1. **File names** are readable: `dso_area.cimtbl` (the contract's `area.cimtbl`), `substation_s1`,
   `feeder_s1_f1`, `ssh_s1_f1` and the master `s1_f1.cimtbl`, not the sibling group or `model_id`.
2. **Identifiers** of section 2 are SHA-256 of the readable names, not HMAC with `GK_MODEL_ID_KEY`, and
   the state code is `XX`.
3. **The code and authority** are `boundary_example` and `https://github.com/PNNL-CIM-Tools/CIMTBL-Models`,
   not a utility code. Changing them would change every UUID in the data files.
4. **The package's distributions** are the master and `assembly.xml` only: the publisher writes
   `README.md`, `notebook.ipynb`, `LICENSE.txt` and `DISCLAIMER.txt`.
5. **The version** is the example's (4.1.0), not a first publish (1.0.0).

## Changes from 4.0.0

- Each feeder assembly has a Grid Kitchen identity: a `model_id`, its substation's sibling group and its
  area's group. The package's `dct:title`, the frames' titles and the feeder model and frame identifiers
  are keyed by them.
- The manifest's package has `dcat:isVersionOf`, `dcat:landingPage` and `dcat:inSeries` (its substation
  and its distribution area), and the manifest and `cim:GridAssembly` the contract's titles.
- `cim:Boundary.separates` lists the area's frame first, then the other frames by title.
- The build parses the metadata with rdflib (check 9).

## Changes from 3.0.0

- The distribution area is a frame (`dso_area.cimtbl`). It holds the service areas, the `Feeder`s and the
  ties, which move out of the boundary model. The boundary model holds only connectivity nodes, each
  joining exactly two frames.
- There is no reference data model: `catalog.cimtbl` and `containers.cimtbl` are gone. Each file declares
  the base voltages, line impedances, wires and spacings it uses, and each substation frame declares its
  `Substation`, which the area's frame restates.
- Only the feeder frames have SSHs. The boundary and substation SSHs are gone, and the switch positions are
  in the structural models.
- A "package" is called a feeder assembly. The build checks that every combination of feeder assemblies
  snaps together.

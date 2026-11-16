# Boundary example: two substations, five feeders, two ties

A small made-up model that shows how a boundary is defined together with `ConnectedArea`, and how
five feeders published as five separate packages still join into one model. The electrical values
are illustrative.

```
                    area_d_example (distributionArea)
  ┌──────────────────────────────────────┐   ┌───────────────────────────────────┐
  │ area_ss_s1 (substationServiceArea)   │   │ area_ss_s2                        │
  │                                      │   │                                   │
  │ src_s1 ── s1_bus, 12.47 kV           │   │ src_s2 ── s2_bus, 13.2 kV         │
  │   ├─ R ─ feeder s1-f1 ── s1_f1_end ●─┐   │   ├─ R ─ feeder s2-f2             │
  │   │                    tie 1 (open) ─┤   │   │                               │
  │   ├─ R ─ feeder s1-f2 ── s1_f2_end ●─┘   │   └─ R ─ feeder s2-f1             │
  │   │                                  │   │            │ 13.2 kV              │
  │   └─ R ─ feeder s1-f3 ── s1_f3_end ●─┼───┼─● s2_f1_end ── autotransformer    │
  │                           tie 2 (open, 12.47 kV both sides)                   │
  └──────────────────────────────────────┘   └───────────────────────────────────┘

  R  feeder-head recloser, areaBoundary = true        ●  boundary node
```

## What it shows

**`ConnectedArea` is as built.** The eight areas in `model/areas.cimtbl` nest by `ContainedWithin`:
one distribution area, two substation service areas, five feeder areas. They change only with
construction. Switch positions are as operated and are kept apart, in `model/situation.cimtbl`.

**A boundary node is the node two models share.** It is not an ownership or operating boundary. The
nodes either side of each tie are the boundary nodes, and `model/boundary.cimtbl` holds those four
nodes and nothing else. A feeder names its boundary node in a `node` column and does not declare it.

**The container rule.** A switch between two areas, and each of its boundary nodes, belongs to the
smallest area that contains both:

| Object | Between | Belongs to |
|---|---|---|
| Feeder-head recloser `sw_s1_f1` | Feeder s1-f1 and the bus | Substation `sub_s1` |
| Tie 1 `sw_tie_s1_f1_s1_f2` and its nodes | Two feeders of substation 1 | `area_ss_s1` |
| Tie 2 `sw_tie_s1_f3_s2_f1` and its nodes | Feeders of two substations | `area_d_example` |

`Switch.areaBoundary = true` is the input, set by a person or from GIS. `Terminal.BoundedConnectedArea`
is what a topology processor computes from it; it is written by hand here.

**The voltage step is inside the feeder, not at the tie.** Feeder s2-f1 runs at 13.2 kV and steps
down to 12.47 kV through three single-phase `AutoTransformer` units one span before tie 2. Each unit
has one `AutoTransformerEnd` at 13.2 kV and one at 12.47 kV, so both sides of the tie have the same
`BaseVoltage`.

**Operating state does not move a boundary.** `model/situation.cimtbl` rolls feeder s1-f2 over onto
s1-f1: its head recloser opens and tie 1 closes. No area, boundary node or container changes.

## Files

| Path | What it is |
|---|---|
| `model/` | The model as written, each file once |
| `model/boundary_example.cimtbl` | The assembled model: every shared file once, every feeder, then the ties |
| `boundary_example.xml`, `.jsonld` | The assembled model in RDF |
| `packages/<feeder>/` | One feeder's package, unpacked, as a user would download it |
| `catalog.jsonld` | The public DCAT catalog entry for the five packages |
| `data.json` | The same entries in the Project Open Data layout, for site indexing |
| `build.py` | Writes everything outside `model/` and checks it |

## A package

```
packages/s1_f3/
  manifest.jsonld              a dcat:Catalog of everything below, with checksums
  s1_f3.xml, s1_f3.jsonld      the feeder in RDF
  boundary.xml, boundary.jsonld  the boundary model on its own in RDF
  cimtbl/
    s1_f3.cimtbl               master: Profile, Authority, Model and Imports only
    catalog.cimtbl             shared
    areas.cimtbl               shared
    boundary.cimtbl            shared
    substation_s1.cimtbl       shared with s1-f1 and s1-f2
    feeder_s1_f3.cimtbl        the feeder's own objects
    ties.cimtbl                shared; not imported by the master
```

Each package loads and stands alone: it repeats its substation and source. An object that more than
one package declares is in a shared file, which is byte-identical wherever it appears, so a reader
joining two packages loads it once.

The master imports `areas.cimtbl`, then `boundary.cimtbl`, before any equipment. The order matters:
`cimtables` gives a node with no container the container of the first equipment that touches it, so
a boundary node declared late, or not at all, would land in whichever feeder loaded first.

`ties.cimtbl` is in every package but no feeder's master imports it, because the far side of each
tie is in another package. A feeder package also holds the far-side boundary nodes with nothing
connected to them.

## The metadata

`manifest.jsonld` lists five datasets. Four of them have the same identifier and the same checksums
in every package that carries them, which is how five separate downloads point back at the same
areas and boundary:

| Dataset | Type | Files | Same across |
|---|---|---|---|
| The feeder | `FrameModel` | master, feeder file, RDF | — |
| Reference data | — | `catalog.cimtbl`, `areas.cimtbl` | All five |
| Boundary model | `BoundaryModel` | `boundary.cimtbl`, `boundary.xml`, `boundary.jsonld` | All five |
| Substation | `FrameModel` | `substation_<s>.cimtbl` | Its feeders |
| Ties | `FrameModel` | `ties.cimtbl` | All five |

- `FrameModel.perimeter` points a feeder with a tie, and the ties dataset, at the boundary model.
  `FrameModel` and `BoundaryModel` are the draft grid-model metadata classes (the `cim18v17.metadata`
  profile of CIM-Profiles).
- `dct:requires` records what must be loaded first.
- A `.cimtbl` file carries only `Profile`, `Authority` and `Model`. Its `dct:conformsTo` is the
  profile's JSON-LD context, the document its JSON-LD twin names in `@context`.
- The JSON-LD files open with a `dcat:Dataset` header whose identifier is the dataset's in the
  manifest. The RDF XML files keep the `md:FullModel` header with the same identifier.
- All five packages use one `Authority` and `Model`, so a shared object has one UUID everywhere.

## Rebuild and check

```bash
uv run --no-project --prerelease=allow --with cim-tables python distribution/boundary_example/build.py [--zip]
```

The build raises unless: every boundary node has its declared container in every package and in the
assembled model; shared objects have one UUID across packages; every shared dataset has one set of
checksums; each tie joins its two boundary nodes; and the operating state binds onto the assembled
model. `--zip` also writes `dist/<feeder>.zip`, with `manifest.jsonld` first. The output is
deterministic.

## Open points

- **No link from `Feeder` or `Substation` to its `ConnectedArea`.** cim18v17 has none, so `fdr_s1_f1`
  and `area_f_s1_f1` are tied by name only. Equipment keeps its `Feeder` or `Substation` as
  `EquipmentContainer`; only the ties, which belong to no feeder, are contained by an area.
- **Reference data has no metadata class.** The draft has no reference-model class, so that dataset
  is a plain `dcat:Dataset`.
- **Boundary RDF points outside itself.** Each boundary node references its `ConnectedArea`, which is
  in the reference data, not in the boundary model.
- **No Open Packaging parts.** The zip has `manifest.jsonld` at its root and no `[Content_Types].xml`
  or `_rels`.
- **Placeholders.** The contact address in `data.json` is a placeholder, and the catalog entries
  point at the package folders in this repository, not at downloadable zips.

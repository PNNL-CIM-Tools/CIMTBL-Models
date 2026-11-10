---
name: cimtbl-transformer-template
description: Turn a picture of a transformer winding/connection diagram (IEEE C57.12.70 or IEC 60076 vector diagram, nameplate schematic, phasor diagram, utility construction standard) into a reusable TransformerTankConfiguration or TransformerBankConfiguration .cimtbl template - wye-wye, delta-wye, wye-delta, delta-delta, single-phase, center-tap, three-winding, open wye - open delta banks. Use when the user pastes or points to a transformer connection picture and wants a cimtbl template, or asks for a template of a given vector group.
---

# Transformer template from a winding diagram

Output: one file `distribution/templates/<name>.cimtbl` holding a
`TransformerTankConfiguration` that instances reuse through
`TransformerTank.TankConfiguration=` (like an OpenDSS XfmrCode), or for a bank of tanks a
`TransformerBankConfiguration` with one tank configuration per tank position. It follows the repo's
general conventions (`cimtbl-translate` skill): `Profile = cim18v17`, no `Authority` /
`Model` (a template is imported by many models), values transcribed with their unit in
the header.

**Worked examples, read them first:**
- `distribution/templates/padmount_3ph_500kva_dyn1.cimtbl`: three-phase, delta-wye, Dyn1.
- `distribution/templates/padmount_1ph_250kva.cimtbl` (instance: `distribution/padmount_example.cimtbl`):
  single-phase, center-tapped secondary.
- `distribution/templates/polemount_1ph_50kva_7200_12470y{,_1bushing}.cimtbl`: single-phase
  pole-mount, with two primary bushings and with one (SRP 7-33-1, 7-34-1).
- `distribution/templates/bank_oyod_50_50_7200_12470y.cimtbl` (instance:
  `distribution/open_wye_open_delta_example.cimtbl`): open wye - open delta bank (SRP 7-35-1).

## The template is the tank; the phases are the instance's

A template says how the tank is built, never which phases it is connected to: the same
tank goes phase to neutral on A, phase to phase on B-C, or into a bank, and CYME and
OpenDSS likewise template only the tank. So:

- **Template:** lugs, windings, impedances, core. No `TransformerPhaseEnd`, no phases.
- **Each lug's `sequenceNumber` is the conductor it lands on**, numbered over the
  transformer's (or bank's) terminals: end 1's conductors first, then end 2's. Lugs that
  are tied together share a number (H2 and X2 on a common neutral). A lug that lands on
  nothing (an open-delta T tank's center tap) has none.
- **Instance:** one `TransformerPhaseEnd` per numbered conductor, with the same
  `sequenceNumber`, the real `phase`, `phaseNeutralU`, `grounded`, and `Terminal` = its
  PowerTransformerEnd's generated terminal (`<xf>_T1`). A tank's lug lands on the phase
  end with its number among the phase ends on its PowerTransformer's terminals.

## 1. Read the picture, and say what you read

Before writing rows, list what the picture shows and put it in your reply, so the user
can check it against the picture:

- **Bushings / lugs**, with their designations as printed: `H1 H2 H3 H0`, `X1 X2 X3 X0`,
  `Y1...` (tertiary), loop-feed `H1A H1B`, IEC `1U 1V 1W 1N`, `2U 2V 2W 2N`.
- **Coils:** each coil as the two bushings (or internal junctions) it runs between,
  From = the polarity-marked (dotted) end.
- **Legs:** which high-side coil shares a core leg with which low-side coil. Coils drawn
  parallel in the connection diagram, or on the same leg, or parallel in the phasor
  diagram, are on one leg.
- **Vector group and angular displacement** if printed (`Dyn1`, "X1 lags H1 by 30°").
- **Nameplate numbers:** kVA, each side's voltage designation (`12470`, `480Y/277`,
  `120/240`), percent impedance, losses, X/R, core form.

Numbers the picture doesn't give: ask the user. Don't invent them. If the user asks
for "typical" values, use them and say so in the file header ("illustrative, not from a
datasheet").

## 2. Map it to rows

In this order (each table only references rows above it):

| Row | One per | mRID | Columns |
|---|---|---|---|
| `TransformerBankConfiguration` (banks only) | bank design | `xb_<name>` | `name` |
| `TransformerTankConfiguration` | tank design (in a bank: tank position) | `xc_<name>` (in a bank: `<xb>_<position>`, `_l`, `_t`) | `percentImpedance`, `loadLoss (W)`, `noLoadLoss (W)`, `percentMagnetizingCurrent` as on the nameplate; `BankConfiguration` in a bank |
| `TransformerCore` (if the form is known) | tank | `<xc>_core` | `form` = `coreForm` / `shellForm` |
| `TransformerLug` | bushing | `<xc>_lug_<designation>` (lowercase: `_lug_h1`) | `designation` as printed, `sequenceNumber` (the conductor) |
| `TransformerWinding` | coil | `<xc>_wdg_<from><to>` (`_wdg_h1h3`) | `ratedU`, `baseU`, `ratedS`, `baseS`, `FromTransformerLug`, `ToTransformerLug` |
| `TransformerMeshImpedance` | coil pair on one leg | `<xc>_mesh_<leg>` (`_mesh_a`) | `FromWinding` (high side), `ToWinding`, `r (percent)`, `x (percent)` |

Every row but the bank and the mesh carries `TankConfiguration=<xc>` (as a header
default in a one-tank file, see the examples).

- **Conductor numbering** (`sequenceNumber`): the conductors of the transformer's
  terminals in terminal order: end 1, then end 2 (then 3), each in phase order then its
  neutral (A B C N; s1 s2 N). Delta-wye: `H1 H2 H3` = 1-3, `X1 X2 X3 X0` = 4-7; wye-wye adds
  `H0` = 4; center-tap: `H1` = 1, `H2` = 2, `X1` = 3, `X3` = 4, `X2` = 5 (or `H2` shares the
  secondary N where the source ties the primary to it, as OpenDSS's node 0 does). For a
  bank, the bank terminals' conductors: open wye - open delta is 1, 2 = the two primary
  phases, 3 = N, 4, 5, 6 = a, b, c (c the power leg), 7 = N. Say the numbering in the file
  header.
- **Banks of single-phase tanks** (open delta, open wye, three cans): one tank
  configuration per tank position, even when the tanks are the same design, because
  their lugs land on different conductors. Each points at the bank
  (`BankConfiguration=`). A tank used on its own keeps its own one-tank template.
- **Name** a template `<mounting>_<phases>_<kVA>_<rating>` with the rating as the IEEE
  C57.12.00 Table 7 nameplate marking, lowercase, `/` as `_`: `12470GrdY/7200` ->
  `12470grdy_7200`, `7200/12470Y` -> `7200_12470y` (E/E1Y, fully insulated: a different
  winding from E1GrdY/E). Sources print ratings other ways (SRP: `12000/20780GrdY` for
  `20780GrdY/12000`); write the IEEE marking in the header and note how the source prints
  it. Variants get a suffix (`_1bushing`).
- **Source:** cite the drawing (document, page, URL) in the file header.
- **Internal ends:** a coil end with no bushing (a single-bushing unit's H2, tied to the
  tank inside) has no lug; the winding's lug cell stays blank and a comment says where
  it ends.
- **Bonds to the tank** (a ground symbol on X2, an internal H2) have no attribute on a
  lug: say so in a comment, and the instance sets `grounded=true` on that phase end.
- **Windings** run From the polarity-marked end. The link to the lugs is written on the
  winding (`FromTransformerLug` / `ToTransformerLug`); in cim18v17 the lug side is
  `serialize=False`. A bank's polarity (like or opposite, which secondary lug lands on
  which conductor) follows the drawing; check the secondary voltages with phasors and
  put the result in the header (open delta: 240 V on every side, 207.8 V power leg).
- **Instance phase ends** (not in the template): `phase` A/B/C/N, center-tap `s1`/`s2`;
  `phaseNeutralU` = the conductor's nominal voltage to neutral: wye side line-to-neutral
  (`277`), delta side or phase-to-phase coil line-to-line / sqrt(3) (`7199.56` for
  12470), neutral `0`, center-tap halves `120`, open-delta power leg `207.8`.

### Ratings: one rule for every winding

- `ratedU` = that side's nameplate designation, phase to phase (`12470`, `480`, `240`).
- `baseU` = the voltage across this coil: line-to-line on a delta, line-to-neutral on a
  wye (`277`), half the secondary on a center-tap half (`120`).
- `ratedS` = the winding's rating: on a balanced three-phase tank the three-phase basis
  (the tank kVA, `500` on every coil of a 500 kVA tank); on a single-phase tank the
  coil's own kVA, per phase on a split-phase secondary (`125` on each half of a 250 kVA
  center-tap).
- `baseS` = the per-coil kVA base shared by every coil on the leg: `ratedS / 3` on a
  three-phase tank, the tank kVA on a single-phase tank (so a center-tap half has
  `baseS = 2 * ratedS`; = OpenDSS `kvas`).

Percent impedances convert on the From winding's `baseU^2 / baseS` (cimtables), so with
this rule the nameplate percent values go on every leg unchanged.

### Coil pairs for the common vector groups

ANSI labels (H1/X1 = phase A, the standard labelling the checker assumes). From is listed first. Use the table to check your reading,
not instead of it: the picture wins, and `check_vector_group.py` says whether it agrees.

| Group | High-side coils (legs a, b, c) | Low-side coils (same legs) |
|---|---|---|
| YNyn0 (wye-wye) | H1H0, H2H0, H3H0 | X1X0, X2X0, X3X0 |
| Dd0 (delta-delta) | H1H2, H2H3, H3H1 | X1X2, X2X3, X3X1 |
| Dyn1 (ANSI delta-wye, X lags 30°) | H1H3, H2H1, H3H2 | X1X0, X2X0, X3X0 |
| Dyn11 (X leads 30°) | H1H2, H2H3, H3H1 | X1X0, X2X0, X3X0 |
| YNd1 (ANSI wye-delta, X lags 30°) | H1H0, H2H0, H3H0 | X1X2, X2X3, X3X1 |
| YNd11 (X leads 30°) | H1H0, H2H0, H3H0 | X1X3, X2X1, X3X2 |

Groups 6/5/7 (180° more) are the same coils with the low side's From and To swapped.

### Impedance

- One mesh per leg, between the leg's high-side and low-side coils, on the high-side
  (From) coil's base.
- From losses: `R % = loadLoss / kVA * 100`; `X % = sqrt(percentImpedance^2 - R^2)`.
  From X/R: `R = Z / sqrt(1 + XR^2)`, `X = R * XR`. Put the derivation in a comment
  above the table.
- **Three-winding** (H, X, Y): three meshes per leg, H-X, H-Y, X-Y, each from the
  nameplate's pairwise impedance, converted to the From coil's base if it is given on
  another kVA.
- **Center-tap:** the half-winding impedances aren't on the nameplate. Derive them as
  `padmount_1ph_250kva.cimtbl` does (H to each half = 1.5R + j1.2X, half to half =
  2.0R + j0.8X) and say that the values are inferred.
- Zero sequence (`r0`, `x0`) only if the nameplate gives it.

### Not a single template

- **Autotransformers and step-voltage regulators:** `VoltageRegulator` +
  `AutoTransformerEnd`s, per `distribution/regulator_example.cimtbl`.
- **Zigzag (Z, Zn) and other split coils:** each half coil needs an internal junction
  that isn't a bushing. Stop and ask the user how to represent it.

## 3. Check it

With `cim-tables` from PyPI (or `python -I` in any environment that has it installed):

```bash
P="uv run --no-project --prerelease=allow --with cim-tables python -I"
$P .claude/skills/cimtbl-translate/check_cimtbl.py distribution/templates/<name>.cimtbl
$P .claude/skills/cimtbl-transformer-template/check_vector_group.py distribution/templates/<name>.cimtbl
```

`check_cimtbl.py` loads the template (also load an instance that imports it, like the
examples, to see the conductor numbers meet real phase ends). `check_vector_group.py`
reads a three-phase tank's coil pairs back as a vector group, taking each lug's phase
from its designation (H1/X1 = A, ...), e.g. `vector group Dyn1`; it must match the
picture's label or angular displacement. `FAIL` means a coil pair, a From/To polarity or
a lug is misread: go back to step 1. It skips single-phase and center-tap tanks, so
check those, and bank connections, with phasors by hand.

In your reply, list the bushings, coils and leg pairs you read, the vector group the
checker reports, and every number you derived or assumed.

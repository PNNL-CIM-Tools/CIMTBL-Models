# IEEE 13 node feeder (OCHRE variant)

Translated by hand from `CIMHub_2_0/test_data/models/feeders/OpenDSS/IEEE/IEEE13_OCHRE/`
(`Master.dss` and the files it redirects) to `.cimtbl` (profile `cim18v17`, model
`IEEE13_OCHRE`). Load the master; it imports the rest in dependency order:

| file | OpenDSS source | CIM |
|---|---|---|
| `IEEE13_OCHRE.cimtbl` | Master.dss, VSource.dss (circuit), voltagebases, batchedit model=5 | Substation, Feeder, BaseVoltage, LoadResponseCharacteristic, EnergySource |
| `linecodes.cimtbl` | LineCodes.dss, TpxLineCodes.dss | PerLengthPhaseImpedance + PhaseImpedanceData (matrices as written) |
| `xfmrcodes.cimtbl` | Transformers.dss (`xfcode_*`) | TransformerTankConfiguration (+ lugs, windings, mesh) |
| `transformers.cimtbl` | VSource.dss (`source_650`), Transformers.dss (instances) | PowerTransformer + ends + mesh, or PowerTransformer + TransformerTank + ends + TransformerPhaseEnd |
| `regulators.cimtbl` | Regulators.dss | VoltageRegulator + AutoTransformerEnd + TransformerLug + TransformerWinding + RatioTapChanger + TapChangerControl |
| `switches.cimtbl` | VSource.dss (`trunk`), Switches.dss, Jumpers.dss | LoadBreakSwitch |
| `lines.cimtbl` | OverheadLines.dss, UndergroundLines.dss | ACLineSegment |
| `triplex_lines.cimtbl` (added) | TriplexLines.dss | ACLineSegment (phases `s1s2N`) |
| `capacitors.cimtbl` | Capacitors.dss, CapControls.dss | LinearShuntCompensator + RegulatingControl |
| `loads.cimtbl` | TpxLoads.dss | EnergyConsumer |

The split follows the worked example (CDPSM) per element family. The one addition
is `triplex_lines.cimtbl`, because the triplex lines are a separate family from the
overhead and underground lines. Jumpers are in `switches.cimtbl` (switch lines).
Underground lines are in `lines.cimtbl` (same class as overhead).

Check output (`check_cimtbl.py`, from `CIMTBL-Models`):

```
942 objects (50 Identity-only, keyed by identifier)
profile cim18v17, model 'IEEE13_OCHRE', container 'fdr_ieee13ochre'
   51  ACLineSegment        (11 overhead/underground + 40 triplex)
  156  ACLineSegmentPhase
    6  AutoTransformerEnd
    4  BaseVoltage
   74  ConnectivityNode
   40  EnergyConsumer       (+ 80 EnergyConsumerPhase)
    1  EnergySource         (+ 3 EnergySourcePhase)
    1  Feeder, 1 Substation
    2  LinearShuntCompensator (+ 6 LinearShuntCompensatorPhase)
    4  LoadBreakSwitch      (+ 12 SwitchPhase)
    1  LoadResponseCharacteristic
    8  PerLengthPhaseImpedance
   50  PhaseImpedanceData
   17  PowerTransformer
   34  PowerTransformerEnd
    3  RatioTapChanger, 3 TapChangerControl
    2  RegulatingControl
   47  TransformerLug
   22  TransformerMeshImpedance
   68  TransformerPhaseEnd
   16  TransformerTank
    7  TransformerTankConfiguration
   27  TransformerWinding
  193  Terminal
    3  VoltageRegulator
```

## Element counts: source vs output

| OpenDSS element | source | output |
|---|---|---|
| `circuit` (VSource.dss) | 1 | 1 EnergySource (`src_ieee13ochre`) |
| `line.trunk` (switch=yes) | 1 | 1 LoadBreakSwitch (`sw_trunk`) |
| `energymeter.feeder` | 1 | not translated (see below) |
| `transformer.source_650` | 1 | 1 PowerTransformer (`xf_source_650`) |
| `capacitor` | 2 | 2 LinearShuntCompensator |
| `capcontrol` | 2 | 2 RegulatingControl (`cap_capN_ctrl`) |
| `line.671-692` (switch=y) | 1 | 1 LoadBreakSwitch (`sw_671-692`) |
| `linecode` (LineCodes.dss) | 7 | 7 PerLengthPhaseImpedance |
| `linecode` (TpxLineCodes.dss) | 1 | 1 PerLengthPhaseImpedance |
| overhead `line` (OverheadLines.dss) | 9 | 9 ACLineSegment |
| underground `line` (UndergroundLines.dss) | 2 | 2 ACLineSegment |
| triplex `line` (TriplexLines.dss) | 40 | 40 ACLineSegment |
| `line.j1`, `line.j2` (Jumpers.dss, switch=yes) | 2 | 2 LoadBreakSwitch |
| `xfmrcode` (Transformers.dss) | 7 | 7 TransformerTankConfiguration (6 center-tap `xfcode_*_config*` codes + `xfcode_OBJECT_151`) |
| `transformer` (Transformers.dss) | 16 | 16 PowerTransformer + TransformerTank (15 center-tap units and `transformer_633-634`) |
| `transformer` (Regulators.dss) | 3 | 3 VoltageRegulator |
| `regcontrol` | 3 | 3 TapChangerControl + 3 RatioTapChanger |
| `load` (TpxLoads.dss) | 40 | 40 EnergyConsumer |
| `buscoords`, `AddBusMarker`, `set mark*` | - | not represented (display only) |
| `set voltagebases`, `calcv`, `solve`, `earthmodel`, `!export` / `!uuids` | - | BaseVoltage rows only; the rest is solver, export, or display state |

There is no `Loads.dss` in the deck: the 40 triplex loads are the only loads, and
there are no DER elements.

## Translation conventions

Same as the CDPSM worked example, except where noted below.

- **mRIDs** = prefix from the `cimtbl-translate` table + OpenDSS name lowercased
  (`ln_632-645`, `sw_671-692`, `xf_source_650`, `lc_object_14`, `cap_cap1_ctrl`,
  `ld_tl_house_1_240v`, `vr_object_162_a`). No new prefixes were introduced. Child rows
  extend their parent's mRID (`vr_object_162_a_2`, `vr_object_162_a_tap`, `lc_object_14_21`,
  `xc_xfcode_as_config_wdg2`); the regulator's generated Terminal is `vr_object_162_a_T2`.
- **Bus names are the OpenDSS bus names as written**, including the `node_` prefix that
  this deck uses (`node_650`, `node_632`, `node_6321`). They are not stripped to `650` as in the
  CDPSM deck. Also `sourcebus`, `rootbus`, `CAP1`, `CAP2`, `trip_node1..15`, `tl_house_1..40`.
- **Connectivity**: `node` / `node1` / `node2` = the bus name. `phases` = the node suffix in
  written order (`.2.3` -> `BC`, `.1.3` -> `AC`, `.1.2.3.4` -> `ABCN`). `N` is written when
  the deck's line or code carries a neutral (see 1 and 3).
- **Units** go in the header as written in OpenDSS: `length (ft)`, `r (ohm/mile)`, `p (kW)`,
  `q (kVAr)`, `nomQ (kVAr)`, `nomU (kV)`, `ratedU (kV)`, `ratedS (kVA)`, `nominalVoltage (kV)`,
  `phaseNeutralU (kV)`, `targetValue (V)`. Values are not pre-converted: the deck is in kV
  (the phase ends' `phaseNeutralU` is each code's wdg kv; 633-634's is kV / sqrt(3)).
- **Load model**: `batchedit load..* model=5` (Master.dss) applies to every load, so all 40 loads
  are `zip_constant_i`. Only that LoadResponseCharacteristic is defined.
- **Sign**: all loads are consumers with positive `p`, `q`.
- **Percent impedances**: on a direct PowerTransformer (`source_650`), `%loadloss` on the end's
  ratedU²/ratedS and mesh `x (percent)` on the From end; on a template, winding `r` and mesh `x`
  on the (From) winding's baseU²/baseS (see transformers).

## Judgment calls and deviations

### 1. Line codes: no Kron reduction (`kron=yes` not applied; 4-wire as written)

The deck's codes with a neutral (`OBJECT_14`, `OBJECT_15` as 4x4 with neutral=4;
`OBJECT_16`, `OBJECT_17` as 3x3 with neutral=3; `OBJECT_18`, `OBJECT_22` as 2x2 with neutral=2;
`triplex_line_configuration_1` as 3x3 with neutral=3) are written **as the deck's matrices**,
in the deck's conductor order (neutral last). `conductorCount` = nphases as written (4, 4, 3, 3,
2, 3, 2, 3). `OBJECT_21` has no neutral (3x3). The reduction is left to the converter.

Lines on these codes carry the neutral in `phases`, in the matrix's conductor order:

| line | code | phases | conductors (row order) |
|---|---|---|---|
| 630-632, 632-6321, 6321-671, 671-680, 632-633 | OBJECT_14 / OBJECT_15 | `ABCN` | A, B, C, N |
| 671-684 (nodes .1 .3) | OBJECT_17 | `ACN` | row 1 = A, row 2 = C, row 3 = N |
| 632-645, 645-646 (nodes .2 .3) | OBJECT_16 | `BCN` | row 1 = B, row 2 = C, row 3 = N |
| 684-611 (node .3) | OBJECT_18 | `CN` | row 1 = C, row 2 = N |
| 684-652 (node .1) | OBJECT_22 | `AN` | row 1 = A, row 2 = N |
| 692-675 | OBJECT_21 | `ABC` | no neutral |
| triplex 110-149 | triplex_line_configuration_1 | `s1s2N` | s1, s2, N |

The deck gives no neutral node or neutral ground: the N terminal lands on the bus's own
ConnectivityNode (as the CDPSM `s1s2N` secondary does), and no neutral is grounded here.
OpenDSS's kron reduction would eliminate N, and grounding is not stated.

Values: `PhaseImpedanceData` rows are the deck's `rmatrix` / `xmatrix` lower triangles, identifier
`<code>_<row><col>`. `calculatedFrequency` = 60 Hz, the OpenDSS default (`basefreq` is not in the
deck). No `b` column (no `cmatrix` in the deck).

### 2. Overhead and underground lines

Both are `ACLineSegment` and are in `lines.cimtbl`. The 6321 and 630 buses are as written in the
deck. No OpenDSS normamps, so no OperationalLimitSet / CurrentLimit rows.

### 3. Triplex lines and triplex loads

- The triplex cable has 3 conductors (s1, s2, N), `neutral=3`, and is written as the matrix.
  The lines carry **`phases = s1s2N`**, so N continues from each center-tap secondary (`trip_nodeK`,
  whose N is the tap's center, see 4) to each triplex load bus.
- Triplex loads: `phases = s1s2`, `phaseConnection = Y`, `grounded = true` (the CDPSM `ld_house`
  precedent). The deck's load has two terminals (s1, s2) and no neutral node, so the load stays `s1s2`.
  `p = 5.840 kW`, `q = 1.589 kVAr` as written, per load.
- Triplex lines: `length = 1.0 ft` as written.
- BaseVoltage `bv_240v` (240 V) for the triplex secondary, the CDPSM precedent. The deck's
  `voltagebases` lists `0.208`. The `0.208` kV is OpenDSS's line-to-line base for the 120/240 V
  split-phase loads, which give 120 V legs, so it is not a BaseVoltage. This is the one value in
  `IEEE13_OCHRE.cimtbl` that is not the deck's entry.

### 4. Center-tapped service transformers (15 units)

Each `transformer_center_tap_N` is a single-phase 3-winding unit, built as
`distribution/padmount_example.cimtbl` builds its padmount on
`distribution/templates/padmount_1ph_250kva.cimtbl`:
- one tank-only `TransformerTankConfiguration` per deck `xfcode_*` (1:1, 6 codes): lugs,
  windings, mesh, no phases;
- lugs as the CDPSM ct5: `sequenceNumber` = the conductor, in terminal order, H1 = 1, X1 = 2 (s1),
  X3 = 3 (s2), and H2 and X2 share 4 (N). H2 shares 4 because the deck's primary returns to node 0,
  the center tap's ground (`buses=[node.1 trip_node.1.0 trip_node.0.2]`);
- the phase letter in the code name is the primary phase the deck uses it on (`AS` = A, `BS` = B,
  `CS` = C); the tanks are identical and carry no phase. Each instance's primary bus is the same
  phase (for example `transformer_center_tap_9`: `node_652.1`, AS, phase A);
- three `TransformerWinding`s, lug to lug: wdg1 H1 -> H2, wdg2 X1 -> X2, wdg3 X2 -> X3 (template
  polarity: s1 -> N -> s2);
- mesh `x (percent)` from `xhl`, `xht`, `xlt` (1.632, 1.632, 1.088) on wdg1, wdg1, wdg2;
  winding `r (percent)` from the deck's `%R` (0.300 primary, 0.600 each half);
- instance = PowerTransformer + `TransformerTank` + two ends: end 1 = primary on the deck bus and
  phase, `Y`, grounded; end 2 = `trip_nodeN`, `s1s2N`, connectionKind `I`, grounded (the CDPSM
  `tpoletop` center-tap precedent);
- plus four `TransformerPhaseEnd`s with the lugs' sequenceNumbers and the real phases: 1 = the
  primary phase (`phaseNeutralU` 2401 V on the 4.16 kV codes, 277 V on the `_634` codes),
  2 = s1 and 3 = s2 (120 V), 4 = N (0 V, grounded).

Winding ratings, per the template's rules (`ratedU` = nameplate phase-to-phase designation,
`baseU` = coil voltage = OpenDSS `kvs`, `ratedS` = the winding's own rating, `baseS` = tank kVA):

| code | winding | ratedU (kV) designation | baseU (kV) = kvs | ratedS (kVA) | baseS (kVA) |
|---|---|---|---|---|---|
| `_config` (AS, BS, CS) | wdg1 primary | **4.160** (4.16 kV system) | 2.401 | 75 | 75 |
| `_config` | wdg2, wdg3 halves | **0.240** (240 V split phase) | 0.120 | 37.5 | 75 |
| `_config_634` (AS, BS, CS) | wdg1 primary | **0.480** (480 V system) | 0.277 | 75 | 75 |
| `_config_634` | wdg2, wdg3 halves | **0.240** | 0.120 | 37.5 | 75 |

Designations chosen:
- the `_config` primary is designated for the 4.16 kV system, the phase-to-phase voltage
  whose line-to-neutral is `kv = 2.401` (the deck's wdg1 kV, across the winding);
- the `_config_634` primary is designated for the 480 V system (`kv = 0.277` across the winding);
- the halves are designated 240 V, the split-phase nameplate (template: 240 / 120).

Ratings and percent bases:
- `ratedS` halves = 37.5 kVA each, half of the 75 kVA tank (template: 125 of 250). The deck gives
  `kva=75` on every winding; for the halves I read that as the tank total (the CDPSM ct5 rule,
  2.5 of 5). The primary keeps 75.
- `baseS = 75` (OpenDSS `kvas`), the base for the percent values of all three windings. This matches
  the deck's per-winding `%R` and `xhl` bases, since each winding has `kva=75`.
- Percent conversions use `baseU²/baseS` of the From winding (template comment).

Not written: `percentImpedance`, `%noloadloss`, `%imag` (not in the deck). The template's
`percentImpedance` and mesh `r` come from a Hopkinson derivation of loadLoss, which the deck does
not need: its `%R` per winding and `xhl/xht/xlt` are transcribed directly (the CDPSM ct5 style).

### 5. Single 3-phase transformer on a 3-phase template

`transformer_633-634` uses `xfcode_OBJECT_151` (3-phase, 2 winding, 500 kVA each), used by this
one unit only. The code is a tank-only YNyn0 template, `xc_xfcode_object_151`, as IEEE13_assets
writes FdrXfmr:
- 8 lugs in terminal order: end 1 H1 H2 H3 H0 = 1-4, end 2 X1 X2 X3 X0 = 5-8;
- 6 coils, one per phase per side (H1-H0 / X1-X0 on leg a, and so on): `ratedU` = the side's kV
  (4.160, 0.480), `baseU` = the coil, line to neutral (2.40178, 0.27713 kV), `ratedS = 500`
  (three-phase basis), `baseS = 500 / 3 = 166.6667` per coil;
- `r (percent) = 0.55` per coil: the deck's `%loadloss = 1.100` split evenly (the CDPSM `xfm1`
  convention); mesh `x (percent) = 2.0` on each leg (deck `xhl = 2.0`). On the coil base these are
  the deck's three-phase percent values unchanged;
- no `noLoadLoss` or `percentMagnetizingCurrent`: the deck code sets no `%noloadloss` or `%imag`.

The instance is a PowerTransformer + `TransformerTank` on the template + two ends: end 1 `node_633`,
end 2 `node_634`, both `ABCN`, `Yn`, grounded, `BaseVoltage` `bv_4p16kv` / `bv_480v`. The deck's
buses are `node_633.1.2.3` / `node_634.1.2.3` (neutral to ground, OpenDSS default); the terminals
carry N for the grounded neutrals. Eight `TransformerPhaseEnd`s carry the lugs' sequenceNumbers and
the real phases (`phaseNeutralU` 2401.78 / 277.13 V, N grounded at 0 V). `vectorGroup = YNyn0`
(derived from the wye-wye grounded connections; the CDPSM `xfm1` value).

### 6. Substation transformer `source_650` (in VSource.dss)

115 kV to 4.16 kV, 100000 kVA per winding, OpenDSS default wye on both windings. Written as a
direct PowerTransformer, as with `xfm1`. Its values are essentially zero impedance:
- `r (percent) = 0.00005` per end (`%loadloss = 0.0001` split evenly);
- mesh `x (percent) = 0.0001` (`xhl`);
- `%noloadloss` and `%imag` are dropped: a direct PowerTransformer has no field for them. They
  belong on a TransformerTankConfiguration, and this unit has none.
- `connectionKind Yn`, grounded, and `vectorGroup YNyn0`: the deck gives no connection
  (OpenDSS default wye), so this is the CDPSM `xfm1` precedent (see the open question on grounding).

### 7. Regulators (Regulators.dss)

Three single-phase regulators, each its own VoltageRegulator (the CDPSM model), on node_650
phase N to node_630 phase N, 2.4 kV, `kva = 100000` per winding as written.
- Two `AutoTransformerEnd`s per regulator: end 1 = S on `node_650`, end 2 = L on `node_630`,
  phase `AN` / `BN` / `CN`, `baseU = 2.4 kV`, `ratedS = 100000 kVA` (the through rating, as written).
- Lugs S, L, SL and one `TransformerWinding` S -> SL with the tap at L. Its `ratedS = 10000 kVA`
  is the buck/boost rating, derived as 10 % of the through rating as written. An `Update` row then
  sets `VoltageRegulator.AutoTransformerWinding`. `construction` (type A/B) is unset: the deck
  doesn't say.
- No `%R`, `%loadloss` or `xhl` in the deck, so no TransformerMeshImpedance. This is an
  ideal-transformer assumption, not the CDPSM near-ideal 0.01 % values.
- `TapChangerControl`: `mode voltage`, `discrete true`, `enabled true`, `monitoredPhase` = the
  phase; `targetValue (V) = 2400` (vreg 2400 × ptratio 1); `targetDeadband (V) = 80` (band 80 × 1).
- `lineDropCompensation = false`, no R/X: the deck has no `R`/`X` (OpenDSS defaults 0).
- `RatioTapChanger` on end 2 (`winding=2`): `lowStep -16`, `highStep 16` (`numtaps=32`), `stepVoltageIncrement 0.625`
  percent (OpenDSS default), `ltcFlag true`, `neutralU (kV) = 2.4` (the regulator winding kV),
  `ptRatio = 1`, `initialDelay (s) = 0` (`delay=0.0`), `subsequentDelay (s) = 2`
  (OpenDSS default `tapdelay`, not in the deck).
- **Taps: `step = normalStep = 0`.** The deck has no solved tap positions (it sets no `tap=` and no
  solution script is in the deck), so `step` takes `normalStep` (0, neutral), per the skill rule.
  The OpenDSS solve moves the taps; the solved positions are not in this translation.
- `Bank=vreg1` is not represented (no bank class in the format).

### 8. Switches

All four are `LoadBreakSwitch`. The deck has no Relay, Recloser or Fuse, so there is no protection
element to set a subclass (CDPSM rule: none -> LoadBreakSwitch). The stand-in r1=1e-4 impedance is
dropped.
- `sw_trunk` (`trunk`, sourcebus to rootbus): `bv_115kv`.
- `sw_671-692`: `bv_4p16kv`.
- `sw_j1`, `sw_j2` (Jumpers.dss): `CAP1`/`CAP2` to `node_675`, `bv_4p16kv`.
- `EquipmentContainer = fdr_ieee13ochre` for all switches (the CDPSM breakers' container).

### 9. Capacitors and capacitor controls

- `nomU (kV) = 4.160`, `nomQ (kVAr) = 900` / `750` as written, `bPerSection (S) = nomQ / nomU^2`
  for one section (0.0520063 and 0.0433386). `sections = normalSections = maximumSections = 1`.
- Wye: `phaseConnection Y`, grounded (the CDPSM precedent). Both banks are 3-phase.
- `CapControl` -> `RegulatingControl` (`cap_capN_ctrl`), voltage mode, on the capacitor
  (`ShuntCompensator.RegulatingControl`), as in IEEE13_assets:
  - `targetValue = (on + off) / 2`, `targetDeadband = off - on`, volts, `ptratio = 1`:
    CAP1 on 1950, off 2500 -> **2225 V / 550 V**; CAP2 on 2050, off 2600 -> **2325 V / 550 V**.
    (Derived. The deck gives on/off in volts, and ptratio is 1, so no scaling.)
  - `monitoredPhase = A`: `ptphase=1`, the element's first conductor (CAP1.1 / CAP2.1).
  - `enabled = true`, `discrete = true`; capacitors `controlEnabled = true` (no `set controlmode=off`).
  - `Terminal = sw_j1_T1` / `sw_j2_T1`. The CapControl monitors the capacitor's terminal 1. Its own
    generated terminal (`cap_capN_T1`) exists only after the capacitor binds, but the capacitor must
    reference its control, so the control cannot point at it. The jumper's terminal 1 sits on the
    same ConnectivityNode (`CAP1` / `CAP2`), so the monitored voltage is the same.
  - `aVRDelay (s)`: CAP2 `delay=300` -> 300 on `cap_cap2`. CAP1 `delay=0.0` -> 0 on `cap_cap1`.
- **Not represented** (no cim18v17 attribute): `delayoff` (0.0 both) and `deadtime` (0 both). The
  on/off thresholds are represented only as target/deadband, the CIM setpoint model.

### 10. Not translated

- **`energymeter.feeder`** (VSource.dss): a measurement object, not a network element. The format
  has no meter class.
- **`buscoords`** (Buscoords1.csv), **`AddBusMarker`**, **`set mark*`**: display only.
- **`!export cim100 ...`, `!uuids`**: commented out in the deck (`!`). The `sub=IEEE13`,
  `geo=IEEE` names in them are not used.
- **`set earthmodel=carson`, `calcv`, `solve`, `set DaisySize`**: solver state.
- **`batchedit load..* model=5`**: applied as `zip_constant_i` (not a translation of a field).
- **Jumper impedance**: none in the deck (switch lines).
- **Normamps / limits**: no `normamps` in the deck, so no OperationalLimitSet / CurrentLimit.

### 11. Other decisions

- **Substation / feeder**: `sub_ieee13ochre` and `fdr_ieee13ochre`, named from the circuit
  (`ieee13ochre`). The export directive's names (`IEEE13`, commented out) are not used.
- **Source (EnergySource)**: `basekv=115`, `pu` default 1.0, `angle` default 0 (`voltageMagnitude = 115 kV`,
  `voltageAngle = 0 deg`). `MVAsc3 = 50000`: `Z1 = 115² / 50000 = 0.2645 ohm`, `X1/R1 = 4`
  (OpenDSS default), so `r = 0.064151 ohm`, `x = 0.256603 ohm`.
  **Zero-sequence impedance is not transcribed.** The deck sets only `MVAsc3`, and the default
  `MVAsc1` could not be verified here (no OpenDSS install, no web access). The CDPSM values
  came from an explicit `MVAsc1 = 21000`. Add `r0`, `x0` once the default is confirmed.
- **`voltagebases` 0.48**: `bv_480v` (0.48 kV). **115** and **4.16** as written.
- **Feeder/substation container**: equipment in the feeder, source and `source_650` in the substation.
- **Overhead/underground** use the same `ACLineSegment`; `triplex_lines.cimtbl` added.
- **Terminal and phase children**: generated by the loader. No hand-written Terminal rows.

## Open questions

- **Neutral conductors on the 4-wire feeder**: the N terminals are carried but not grounded
  (the deck gives no neutral ground; OpenDSS's kron eliminated N, so grounding was implicit there).
  A converter should decide how to treat N.
- **Source-transformer grounding**: OpenDSS's default for an unspecified wye winding (ungrounded
  vs solidly grounded) is not confirmed here. The CDPSM `xfm1` precedent (`Yn`, grounded) is used
  for `source_650`, `transformer_633-634` and the center-tap primaries (`Y`, grounded). If OpenDSS
  leaves them ungrounded, change `grounded` on these ends.
- **`MVAsc1`**: see Source above.
- **Regulator `neutralU` / `subsequentDelay`**: derived (regulator kV; OpenDSS default tapdelay),
  not in the deck.
- **Triplex base**: `bv_240v` = 240 V (CDPSM precedent), not the deck's `0.208` kV.
- **Solved tap positions**: not in the deck; `step = normalStep = 0` is the starting state, not a
  solution.
- **Capacitor control Terminal**: the jumper's terminal stands in for the capacitor's own terminal
  (same ConnectivityNode). If the format later allows a control to reference a capacitor's
  generated terminal, switch to `cap_capN_T1`.

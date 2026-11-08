# IEEE 13 node feeder (CYME 9.4 study file)

Translated by hand from `CIMHub_2_0/cimhub_cyme/tests/test_models/IEEE_13_node_test_feeder.sxst`
(Eaton's QA validation case, companion `IEEE_13_node_test_feeder.pdf`) to `.cimtbl`
(profile `cim18v17`). The goal is what this file contains, not the textbook IEEE 13
feeder. Where the file and the standard IEEE 13 / the OpenDSS CDPSM model disagree, the
file wins and the difference is listed under "Differences from the OpenDSS IEEE 13".

Load the master; it imports the rest in dependency order:

| file | CYME | CIM |
|---|---|---|
| `IEEE13_CYME.cimtbl` | Network 650, Source SUB650WYE-S2, load model 1, base voltages | Substation, Feeder, BaseVoltage (kV), LoadResponseCharacteristic, EnergySource |
| `linecodes.cimtbl` | OverheadLineUnbalanced equipment LINE606, LINE607 (user-defined impedances) | PerLengthPhaseImpedance + PhaseImpedanceData |
| `wireinfos.cimtbl` | ConductorDB 556_500, 4/0, 1/0 | OverheadWireInfo x3 |
| `linespacings.cimtbl` | OverheadSpacingOfConductorDB 500, 505, 510 | XYSpacing x3 + XYConductorPosition x9 |
| `linegeometries.cimtbl` | conductors at each position of the spacings, per line | WireConfiguration x4 + WireSequenceConfiguration x13 |
| `transformer_db.cimtbl` | TransformerDB XFM1_XFO | TransformerTankConfiguration (tank-only template) + TransformerCore + TransformerLug x8 + TransformerWinding x6 + TransformerMeshImpedance x3 |
| `transformers.cimtbl` | Transformer XFM1_XFO on section L633_634_XFM_1 | PowerTransformer + TransformerTank + 2 PowerTransformerEnd + TransformerPhaseEnd x8 |
| `regulators.cimtbl` | Regulator 650REG (3 single-phase units, FixedTap) | 3 VoltageRegulator + AutoTransformerEnd + TransformerLug + TransformerWinding + RatioTapChanger + TapChangerControl |
| `switches.cimtbl` | Switch 296, Switch L671_692_SW-1 | LoadBreakSwitch x2 |
| `lines.cimtbl` | 10 overhead sections, 632-671 split at 670 (11 ACLineSegment) | ACLineSegment, OperationalLimitSet + CurrentLimit |
| `loads.cimtbl` | 8 SpotLoad sections + the distributed load of L632_671, lumped at 670 | EnergyConsumer x15 |
| `capacitors.cimtbl` | ShuntCapacitor L675CAP, L611CAP | LinearShuntCompensator x2 |

Check (from `CIMTBL-Models`):

```
uv run --project /home/ande188/CIM-Tables python -I .claude/skills/cimtbl-translate/check_cimtbl.py distribution/IEEE/IEEE13_CYME/IEEE13_CYME.cimtbl
```

Output: 290 objects (7 Identity-only PhaseImpedanceData): ACLineSegment 11,
ACLineSegmentPhase 35, AutoTransformerEnd 6, BaseVoltage 2, ConnectivityNode 16, CurrentLimit 11,
EnergyConsumer 15, EnergyConsumerPhase 17, EnergySource 1, EnergySourcePhase 3, Feeder 1,
LinearShuntCompensator 2, LinearShuntCompensatorPhase 4, LoadBreakSwitch 2,
LoadResponseCharacteristic 1, OperationalLimitSet 11, OverheadWireInfo 3, PerLengthPhaseImpedance 2,
PhaseImpedanceData 7, PowerTransformer 1, PowerTransformerEnd 2, RatioTapChanger 3, Substation 1,
SwitchPhase 6, TapChangerControl 3, Terminal 52, TransformerCore 1, TransformerLug 17,
TransformerMeshImpedance 3, TransformerPhaseEnd 8, TransformerTank 1, TransformerTankConfiguration 1,
TransformerWinding 9, VoltageRegulator 3, WireConfiguration 4, WireSequenceConfiguration 13,
XYConductorPosition 9, XYSpacing 3.

## CYME units (determined from the file)

| quantity | CYME unit | evidence |
|---|---|---|
| section Length, spacing positions | m | 152.4 = 500 ft, 609.6 = 2000 ft, 243.84 = 800 ft; 2.1336 = 7 ft |
| line impedance (LINE606/607) | ohm/km | LINE607 self R 0.834191 ohm/km = 1.3425 ohm/mile, the OpenDSS mtx607 value |
| line shunt susceptance | uS/km | LINE607 55.296553 uS/km = 88.99 uS/mile, OpenDSS mtx607 88.97 uS/mile |
| conductor resistance (ResistanceAC1/AC2) | ohm/km | 4/0 0.367852 ohm/km = 0.11212 ohm/kft |
| conductor GMR, OutsideDiameter | cm | 4/0 GMR 0.248107 cm = 0.09768 in; OD 1.43002 cm = 0.563 in |
| conductor rating (NominalRating) | A | 730 / 340 / 230 A |
| transformer | kVA, kV, % impedance on the nameplate base, X/R | `TransfoVoltageUnit=KVLL`, `PositiveSequenceImpedancePercent` 2.2825 with `XRRatio` 1.8181 |
| regulator set point and bandwidth | V on the 120 V base | `VoltageTargetUnit=120V`; PT ratio 20 converts to primary |
| regulator/shunt kV | kV, line-to-neutral per unit | `RatedKVLN` 2.401780; source `KVLL` 4.160000 |
| BaseVoltage | kV, phase-to-phase | 4.16 kV and 0.48 kV (`nominalVoltage (kV)`) |
| source impedance | ohm | `ImpedanceUnit=Ohms` |
| loads, shunts | kW, kvar per phase | `KW`, `KVAR` per CustomerLoadValue |

## Source -> CIM mapping

**Source**. `SourceID SUB650WYE` on node 650, `KVLL 4.16`, `OperatingAngle1 0 deg`, `Yg`.
`EnergySource` on node 650 (not a 115 kV bus). Impedance: `FirstLevelR1/X1 = R0/X0`
= 0.001731 + j0.013844 ohm. Zero-sequence equals positive-sequence (CYME gives no
separate R0/X0).

**Sections** (24 sections, 25 devices):

| CYME device | count | CIM | notes |
|---|---|---|---|
| OverheadByPhase (8): L650_632, L632_633, L632_671, L671_680, L671_684, L684_611, L645_646, L632_645 | 8 | ACLineSegment + WireConfiguration | conductors and spacing from the file; no impedance in the file (see below). L632_671 becomes two segments |
| OverheadLineUnbalanced (2): L692_675 (LINE606), L684_652 (LINE607) | 2 | ACLineSegment + PerLengthPhaseImpedance | user-defined impedance, ohm/km and uS/km |
| SpotLoad (8): LOAD611, LOAD646, LOAD634, LOAD692, LOAD671, LOAD645, LOAD652, LOAD675 | 8 | EnergyConsumer x12 | 634 and 675 split per phase |
| DistributedLoad (1): L632_671-1 (on section L632_671) | 1 | EnergyConsumer x3 at node 670 | lumped, see TODO below |
| ShuntCapacitor (2): L675CAP, L611CAP | 2 | LinearShuntCompensator | |
| Switch (2): 296, L671_692_SW-1 | 2 | LoadBreakSwitch | generic CYME Switch, no protection |
| Transformer (1): L633_634_XFM_1 (XFM1_XFO) | 1 | PowerTransformer + TransformerTank | on the XFM1_XFO template |
| Regulator (1): 650REG (section 7 -> RG60) | 1 | 3 VoltageRegulator (one per unit) | |
| Source (1): SUB650WYE-S2 | 1 | EnergySource | |

Nodes: 25 CYME nodes. 15 are real buses (`650 7 RG60 632 633 634 645 646 671 680 684 611 652 692 675`),
which become the ConnectivityNodes, plus the added node `670` (the distributed-load node), for 16. The other 10 are
section end points used only to hang a device (`LOAD611`, `L675CAP`, `L611CAP`, and so on);
loads and shunts attach to their real bus directly, as in CDPSM.

**mRIDs** follow the cimtbl-translate prefix table: `ln_`, `sw_`, `ld_`, `cap_`, `xf_`, `vr_`,
`xc_`, `lc_`, `wire_`, `spc_`, `wc_`, `src_`; buses use the bare CYME name in lower case (`rg60`);
`name` is the CYME device name. Child rows extend their parent (`_1`/`_2` ends, `_lug_s`, `_wdg`,
`_tap`, `_ctrl` on a regulator; `_lug_h1`, `_wdg_h1h0`, `_mesh_a`, `_core` on the template; `_tank`,
`_1_a` phase ends; `_limits`, `_normal`, `_<n>` for wire sequences and positions). The
regulator's generated Terminal is `vr_650reg_a_T2`. Substation
`sub_sub650wye`, feeder `fdr_650` (the CYME network ID 650). The two split segments of
632-671 are `ln_l632_671a` (632-670) and `ln_l632_671b` (670-671).

## Conductors, spacing, and the phase-to-position mapping

**Wires** (`wireinfos.cimtbl`, OverheadWireInfo, `wire_<name>`): one per CYME conductor used,
with CYME's values as written: `NominalRating` -> `ratedCurrent (A)`, `ResistanceAC1/AC2`
-> `rAC25` / `rAC50 (ohm/km)`, `GMR (cm)`, and `MaterialID` (COPPER) -> `material`.
`radius (cm)` = OutsideDiameter / 2. That is derived, as in the assets worked example, and
the file gives only the diameter.

**Spacings** (`linespacings.cimtbl`, XYSpacing `spc_<id>`, isTemplate, plus XYConductorPosition
`spc_<id>_<n>`): positions in metres as written, with the position number from CYME's
`PositionOfConductor1..n` (phase conductors first, neutral last) and `kind` phase / neutral.

**Line geometry** (`linegeometries.cimtbl`): one WireConfiguration per distinct (spacing,
conductor at each position). Each WireSequenceConfiguration `<wc>_<n>` carries
`sequenceNumber = n`, the position number.

**CYME ConductorPosition -> position numbers.** Each OverheadByPhase section has a
`ConductorPosition` string, such as `PositionBAC`. Read it as the phase at each position,
left to right, so `BAC` means position 1 = B, position 2 = A, position 3 = C. The
neutral is the last position of the spacing. The check: the phase conductors named by
`PhaseConductorIDA/B/C` sit exactly at those positions (for example, L671_684 `PositionAC`,
A and C = 1/0).

| line | section phase | ConductorPosition (1, 2, 3) | spacing | WireConfiguration | phases token order |
|---|---|---|---|---|---|
| L650_632 | ABC | B, A, C | 500 | wc_500_556_500 | `BACN` |
| L632_671 (split: `ln_l632_671a`, `ln_l632_671b`) | ABC | B, A, C | 500 | wc_500_556_500 | `BACN` (each part) |
| L671_680 | ABC | B, A, C | 500 | wc_500_556_500 | `BACN` |
| L632_633 | ABC | C, A, B | 500 | wc_500_4/0 | `CABN` |
| L671_684 | AC | A, C | 505 | wc_505 | `ACN` |
| L645_646 | BC | C, B | 505 | wc_505 | `CBN` |
| L632_645 | BC | C, B | 505 | wc_505 | `CBN` |
| L684_611 | C | C, (neutral) | 510 | wc_510 | `CN` |

Conductor per position (from the phase conductor IDs, which match the positions):
- 500 with 556_500 phases and 4/0 neutral: positions 1-3 = 556_500, position 4 (neutral) = 4/0 (`wc_500_556_500`).
- 500 with 4/0 phases and 4/0 neutral: `wc_500_4/0`.
- 505 with 1/0 phases and 1/0 neutral: `wc_505`.
- 510 with 1/0 phase and 1/0 neutral: `wc_510`.

**Phase order in `phases`.** Token k = the conductor at position k, so
`ACLineSegmentPhase.sequenceNumber` = k and the matching WireSequenceConfiguration
`sequenceNumber` = k. The `phases` column therefore follows the CYME position order
(`BACN`), not the section's ABC node order. Terminals still get the canonical PhaseCode
(`ABCN`). This follows the cimtbl-translate rule "token k is conductor k".

**Neutral.** Every OverheadByPhase line has a real neutral conductor in CYME
(`NeutralConductorID1`), so each `phases` ends in `N`.

**Impedance.** These lines carry geometry and conductors only. CYME computes the
impedance from them (Carson, earth resistivity 100 ohm.m, 60 Hz), and the file has no result.
They have no PerLengthPhaseImpedance and no Kron reduction here; the converter does that.

## Distributed load on 632-671: lumped at node 670

CYME `DistributedLoad` `L632_671-1` on section L632_671, per-phase totals A 17 + j10, B 66 + j38,
C 117 + j68 kW/kvar. It is lumped at a new node `670` (as OpenDSS IEEE 13 does), with the
section split at 667 ft from 632:
- `ln_l632_671a`: 632-670, 203.3016 m (667 ft).
- `ln_l632_671b`: 670-671, 406.2986 m. 1333 ft is 406.2984 m; the 0.0002 m difference
  keeps the CYME total of 609.6002 m.
- `ld_l632_671-1_a/_b/_c`: three EnergyConsumers at node 670 (one per phase, as the per-phase
  values differ), total 200 kW, 116 kvar, the same totals as the distributed load.

TODO (CIM18 gap): CIM 18 has no distributed load along a line segment, so the load is lumped at
an added node. See `distribution/CIM18_GAPS.md`.

## Deviations and judgment calls

1. **Source at 4.16 kV on bus 650** (CYME), not a 115 kV source behind a 115/4.16 kV
   substation transformer. No `sub3`, no 13.2 kV tertiary, no `sourcebus`.
2. **Source impedance**: 0.001731 + j0.013844 ohm (4.16 kV side), R0 = R1, X0 = X1. Equivalent
   short-circuit level 4.16^2 / |Z| = 1240 MVA. The `SubstationDB` 5 MVA rating is not
   transcribed (it is a rating, not an impedance). The source angle is 0 deg (CDPSM 30 deg).
3. **Regulator 650REG is one device with per-phase taps** (`SettingOption FixedTap`,
   `ControlStatus ABC`). One VoltageRegulator per unit, as CDPSM does: two AutoTransformerEnds
   (end 1 = S on node 7, end 2 = L on rg60, phase `AN` / `BN` / `CN`, baseU 2.40178 kV), lugs S, L, SL, one
   TransformerWinding S -> SL with the tap at L, and an `Update` row that sets
   `VoltageRegulator.AutoTransformerWinding`. Each unit has its own tap changer, on end 2;
   the control is kept but disabled (`enabled=false`, `controlEnabled=false`), matching
   FixedTap. The PDF says results used fixed taps too. `construction = typeA`
   (RegulatorDB REG650-632 `ConstructionType A`: the tap changer on the L lug, end 2).
4. **Tap sign.** `TapPositionA/B/C` = 10 / 8 / 11 is written as `step`, read as steps above
   neutral (+10, +8, +11 of 0.625 %). The file does not state the sign. This is inferred
   from the CDPSM taps (1.0625, 1.05, 1.06875 are +10, +8, +11 steps), not from CYME.
5. **Regulator step size and range.** `NumberOfTaps 32`, `BoostPercent/BuckPercent 10`:
   lowStep -16, highStep +16, stepVoltageIncrement 0.625. Derived from those values.
   `neutralStep = normalStep = 0` (not in the file).
6. **Regulator targets.** CYME `SetVoltage 116.19` on the 120 V base, times PT ratio 20,
   gives `targetValue = 2323.8 V` (primary). Bandwidth 2 V times 20 = `targetDeadband 40 V`.
   `lineDropCompensation=false`: CYME LDC R and X are both 0 (volts), so no LDC.
7. **Regulator rating: 150 kVA is the buck/boost rating.** A step regulator's nameplate kVA
   is its buck/boost (series winding) rating, the regulation range times the through rating.
   So `RatedKVA 150` is the TransformerWinding `ratedS`, and the through rating is
   150 / 10 % = 1500 kVA (derived), the AutoTransformerEnd `ratedS`. That is 625 A at
   2.40178 kV, which fits the 700 A CT primary (MaxRatingCurrent is 1000 A). CDPSM uses
   1666 kVA through, 166.6 kVA buck/boost.
8. **Regulator impedance: none.** The file gives no series impedance; no mesh and no `r` are
   written (CDPSM uses 0.01 %). `ctRatio` (CT secondary) is not in the file, so it is omitted.
9. **Regulator delays**: `initialDelay 30 s` (LTC `ActivationDelayFirstTap`) and
   `subsequentDelay 2 s` (`TimeBetweenTaps`). These do not matter for FixedTap.
10. **XFM1 as a template and an instance.** TransformerDB XFM1_XFO is a tank-only
    TransformerTankConfiguration `xc_xfm1_xfo` in `transformer_db.cimtbl`: `TransformerCore`
    `form=shellForm` (`WindingType ShellForm`), 8 lugs (H1 H2 H3 H0 = 1-4, X1 X2 X3 X0 = 5-8),
    6 coils (`ratedU` = the side's kV LL, `baseU` = line to neutral 2.40178 / 0.27713 kV,
    `ratedS` 500.00102, `baseS` = kVA / 3 = 166.66701) and 3 meshes, one per leg.
    Impedance: CYME gives Z = 2.2825 % and X/R = 1.8181 (`PositiveSequenceImpedancePercent`,
    `XRRatio`), the same in zero sequence. Derived R = 1.10 % and X = 2.00 %. CYME's impedance
    is the primary-secondary pair, so it goes whole on each leg's mesh (r 1.10, x 2.00,
    r0 1.10, x0 2.00 %) and the coils carry no r. The ZeroSequenceImpedancePrimSec / PrimMag /
    SecMag entries (8, 20, 30 %) are not carried. The instance (`transformers.cimtbl`) is a
    PowerTransformer + TransformerTank on the template + two ends, 633 and 634, `ABCN`, `Yn`,
    grounded, `rground`/`xground` 0 (grounding 0 ohm both sides), + 8 TransformerPhaseEnds with
    the real phases and a grounded N on each side. The transformer sits directly between 633
    and 634, with no fuse node. Ratings: 500 kVA (`500.00102` kVA as written), 4.16 / 0.48 kV,
    Yg-Yg (`YNyn0`).
11. **Wire radius is derived**: `radius (cm)` = OutsideDiameter / 2 (CYME gives the diameter).
12. **Line ratings.** `NominalRatingA/B/C = 0` on the sections, so the equipment rating applies:
    LINE606/607 `1000 A`. OverheadByPhase: the phase conductor's `NominalRating`
    (556_500 730 A, 4/0 340 A, 1/0 230 A). Split segments share the 730 A limit.
13. **Phase order for line impedances.** LINE606 row 1 = A, row 2 = B, row 3 = C (the
    `ABC` section order; LINE606 has no neutral). Off-diagonal b blank (the file has no
    mutual shunt).
14. **Lengths** are kept in metres as written (`length (m)`), e.g. 609.6002 for the 2000 ft
    632-671 section, and 91.440002 for 684-611.
15. **Load model.** All loads use `LoadModelID 1` (`DEFAULT`), which the file does not
    define. Assumed constant PQ (`zip_constant_pq`) for every load.
16. **Delta loads.** `p/q` are totals. A single-value delta load takes its branch from the
    CYME label: `Phase=B` on section BC is branch BC, and `Phase=C` on section AC is branch
    CA (CDPSM convention). LOAD671 (D, A/B/C 385 + j220 each) is one consumer with
    p = 1155 kW, q = 660 kvar.
17. **Capacitors.** `nomQ` is the bank total (600 kVAr = 3 x 200 kVAr at 675; 100 kVAr at 611).
    `nomU` = 4.16 kV line-to-line for the 675 bank: CYME's `RatedVoltageKVLN` is 2.40178 kV
    per unit, and 2.40178 x sqrt(3) = 4.16. `nomU` for the single-phase 611 unit is its own
    2.40178 kV. `bPerSection` = nomQ / nomU^2 (computed, as in CDPSM).
18. **Switches.** CYME's generic Switch has no protection element, so both are LoadBreakSwitch.
    No Breaker, Recloser, Fuse, or Sectionaliser exists in the file.
19. **Not transcribed**: section `Position` (graphics), tags and colours, the earth
    resistivity (100 ohm.m; CIM 18 has an `EarthResistivity` class, but its `rho` is a
    Resistance and the unit does not fit, so it is left out), `Temperature` (25 C), CYME `EquivalentLoad` (0),
    the source's `NominalCapacity` (150 MVA), LTC `Delay`, `MechanismDelay`, and reverse-flow
    settings, and CT secondary.
20. **Lines in the file are all overhead.** The PDF says the underground lines were modelled
    as overhead lines (unbalanced) to get matrix impedances. LINE606 (692-675) and LINE607
    (684-652) are the cables.

## Differences from the OpenDSS IEEE 13 (`IEEE13_CDPSM`)

Concrete value and topology differences between `IEEE_13_node_test_feeder.sxst` and
`CIMTBL-Models/distribution/IEEE/IEEE13_CDPSM` (OpenDSS `IEEE13_CDPSM.dss`).

| item | CYME (this file) | OpenDSS CDPSM |
|---|---|---|
| source | 4.16 kV at bus 650, angle 0 | 115 kV `Vsource` at `sourcebus`, angle 30 deg, through `sub3` (5 MVA 115/4.16 kV Dyn1, 13.2 kV tertiary) |
| source impedance | Z1 = 0.001731 + j0.013844 ohm at 4.16 kV (|Z| = 0.01395 ohm, 1240 MVA). Z0 = Z1 | Z1 = 0.160377 + j0.641507 ohm at 115 kV (20000 MVA, about 0.000865 ohm at 4.16 kV); Z0 = 0.179604 + j0.538811 ohm |
| substation transformer | none | `sub3`, 5 MVA 115/4.16 kV Dyn1 with R 1 %, X 8 % nameplate (tertiary X 10 % / 4 % assumed) |
| 650 -> regulator | switch 296 (650 -> 7, LoadBreakSwitch), then regulator 7 -> RG60 | breaker `brkr1` (650 -> brkr), then regulators brkr -> RG60 |
| regulator control | FixedTap, taps 10 / 8 / 11, no regulation | regulating, vreg 122 V, same taps 10 / 8 / 11 |
| regulator set point | 116.19 V on the 120 V base (targetValue 2323.8 V primary) | 122 V (targetValue 2440 V) |
| regulator LDC | R = X = 0 (none) | R = 3, X = 9 volts (0.085714 / 0.257143 ohm primary) |
| regulator rating | 150 kVA buck/boost per unit, 1500 kVA through (derived) | 1666 kVA through per unit, 166.6 kVA buck/boost (derived) |
| regulator impedance | none in the file | one mesh, r 0.01 % and x 0.01 % (near-ideal) |
| XFM1 (633 -> 634) | direct 633 -> 634, a tank on the XFM1_XFO template, same values: 500 kVA, 4.16/0.48, Z 2.2825 %, X/R 1.8181 | fuse `fuse1` (633 -> xf1), then XFM1 xf1 -> 634, a per-end PowerTransformer, same R 1.1 % and X 2 % |
| protection | Switch 296 and Switch 671-692 only | Breaker `brkr1`, Recloser `rec1` (632 -> mid), Fuse `fuse1`, Sectionaliser `sect1` (684 -> tap), LoadBreakSwitch 671-692 |
| 632-671 line | one 2000 ft section, with the distributed load (17+j10, 66+j38, 117+j68 kW/kvar); lumped at 670 here | two segments, 632-670 (667 ft) and 670-671 (1333 ft), load lumped at 670 (3 consumers): the same as here |
| lines | 11 ACLineSegments (10 sections, 632-671 split at 670) | 11 ACLineSegments |
| 692-675 (LINE606, mtx606) | user matrix, ohm/km: self R 0.495978 / 0.490324 / 0.495978 (0.798 / 0.789 / 0.798 ohm/mi); self X 0.277318 / 0.251096 / 0.277318 (0.446 / 0.404 / 0.446 ohm/mi); mutual R 0.191258 (0.308 ohm/mi), mutual X 0.010625 (0.017 ohm/mi); shunt 60.2 uS/km (96.9 uS/mi), per phase; unbalanced (B differs) | mtx606: R11 0.791721, X11 0.438352 ohm/mi; R21 0.318476, X21 0.0276838 ohm/mi; 144.745 uS/mi shunt. CYME is 0.8 % high on R11, 1.8 % high on X11, 3 % low on mutual R, 38 % low on mutual X, and 33 % low on shunt |
| 684-652 (LINE607, mtx607) | R 0.834191 ohm/km = 1.3425 ohm/mi; X 0.318390 ohm/km = 0.5124 ohm/mi; shunt 55.297 uS/km = 88.99 uS/mi | mtx607: 1.3425 ohm/mi, 0.5124 ohm/mi, 88.9699 uS/mi. Matches (shunt within 0.03 %) |
| OverheadByPhase lines (8) | conductor + spacing + position (WireConfiguration), impedance computed by CYME (not in file) | explicit 3x3 / 2x2 / 1x1 matrices mtx601-605 with zero shunt |
| loads | same P and Q values at every bus, and the distributed load (now lumped at 670) | same (671 1155 + j660; 645 170 + j125; 646 230 + j132; 692 170 + j151; 675 485/68/290 kW; 611 170 + j80; 652 128 + j86; 634 160/120/120 kW; 670 17/66/117 kW) |
| load models | all `LoadModelID 1` (assumed PQ) | 611 and 692 constant I (`zip_constant_i`); 646 and 652 constant Z (`zip_constant_z`); 645, 671, 675, 634 constant PQ |
| shunt capacitors | 675: 200 kVAr per phase (600 kVAr); 611: 100 kVAr on C | same |
| in-line / extension equipment | none | `xfmrcodes` ct5 and the 1-phase tank `tpoletop` on 670 with `house` (5 kW, 0.85 pf), PV `school` and battery `storage` (CDPSM additions) |
| feeder | network 650, feeder `fdr_650` | `fdr_ieee13nodeckt` |
| bus 650 | the source node, 4.16 kV | downstream of `sub3`, 4.16 kV |
| mRIDs | `ln_l650_632`, `ld_load611`, `sw_296`, `vr_650reg_a`, ... | `ln_650632`, `ld_611`, `brkr1`, `vr_reg1`, ... |

Note on the PDF: the PDF's own comparison tables (CYMDIST vs IEEE published) are in
`IEEE_13_node_test_feeder.pdf` and were not used as input. The `.sxst` is the source.

## TODO (CIM18 gap)

- **Distributed load** (`DistributedLoad` L632_671-1, 17+j10 / 66+j38 / 117+j68 kW/kvar along
  632-671): CIM 18 has no load spread along an `ACLineSegment` (EnergyConsumer attaches at a
  node only). Approximated: the line is split at an added node 670 (667 ft from 632) and the
  load is lumped there as three EnergyConsumers, one per phase. Logged in `distribution/CIM18_GAPS.md`.

## Open questions

- The regulator tap sign (step +10 = boost) is inferred, not stated in the file.
- The eight OverheadByPhase lines have WireConfiguration (geometry) but no impedance in the file.
  The impedance is CYME's Carson-type computation from the geometry, and is not reproduced here.
- The load model 1 "DEFAULT" definition is missing from the file.
- The OverheadByPhase `ConductorPosition` reading (left to right = positions 1..n) is inferred.
  The phase-conductor IDs are consistent with it on all eight lines, but CYME does not define
  it explicitly.

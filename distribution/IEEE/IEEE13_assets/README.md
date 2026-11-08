# IEEE 13 node feeder (assets variant)

Translated from `CIMHub_2_0/test_data/models/feeders/OpenDSS/IEEE/IEEE13_assets/IEEE13_Assets.dss`
to `.cimtbl` (profile `cim18v17`, model `IEEE13_assets`). Load the master; it imports the rest in
dependency order (references must be declared before use):

| file | OpenDSS | CIM |
|---|---|---|
| `IEEE13_assets.cimtbl` | circuit / Vsource, Set Voltagebases | Substation, Feeder, BaseVoltage, LoadResponseCharacteristic, EnergySource |
| `wireinfos.cimtbl` | WireData, TSData, CNData | OverheadWireInfo, TapeShieldCableInfo, ConcentricNeutralCableInfo |
| `linespacings.cimtbl` | LineSpacing | XYSpacing (template) + XYConductorPosition |
| `linegeometries.cimtbl` | LineGeometry (incl. `like=`), inline Spacing/Wires on a Line | WireConfiguration (+ inline XYSpacing + XYConductorPosition) |
| `linecodes.cimtbl` | inline rmatrix/xmatrix on Line.645646 (no LineCode in this deck) | PerLengthPhaseImpedance + PhaseImpedanceData |
| `xfmrcodes.cimtbl` | XfmrCode SubXfmr, FdrXfmr | TransformerTankConfiguration + TransformerLug + TransformerWinding + TransformerMeshImpedance (tank-only templates) |
| `transformers.cimtbl` | Transformer Sub, XFM1 (XfmrCode instances) | PowerTransformer + TransformerTank + PowerTransformerEnd + TransformerPhaseEnd |
| `regulators.cimtbl` | Transformer Reg1-3 (XfmrCode RegLeg) + RegControl | VoltageRegulator + AutoTransformerEnd + TransformerLug + TransformerWinding + TransformerMeshImpedance + RatioTapChanger + TapChangerControl |
| `switches.cimtbl` | Line.671692 `Switch=y` | LoadBreakSwitch |
| `lines.cimtbl` | Line | ACLineSegment (+ OperationalLimitSet / CurrentLimit for 645646 normamps) |
| `loads.cimtbl` | Load | EnergyConsumer |
| `capacitors.cimtbl` | Capacitor + CapControl | LinearShuntCompensator + RegulatingControl |

There is no `der.cimtbl`: the deck has no PVSystem, Storage, or house load.

## Translation conventions

Follows `IEEE13_CDPSM/README.md` and the `cimtbl-translate` skill. What's specific to this deck:

- **mRIDs.** Prefix + OpenDSS name, lowercased. The prefixes marked *proposed* below are new and
  need maintainer approval.
- **Units.** Transcribed with the OpenDSS unit in the header: `radius (in)`, `gmr (in)`,
  `rDC20 (ohm/kft)`, `rAC25 (ohm/mile)`, `length (ft)`, `length (mi)`, `x`/`y` in `ft`.
- **Wire and cable data.** `NormAmps` -> `ratedCurrent`, `Rdc` -> `rDC20`, `GMRac` -> `gmr`,
  `Rac` -> `rAC25`/`rAC50`/`rAC75` (see the derivations below). The DIAM and cable diameters
  are CIM diameters or radii. Each derived value is listed below.
- **LineGeometry -> WireConfiguration.** `spacing=` points at the library `XYSpacing`. `cond=`
  positions (inline geometries 606, 607) get their own `XYSpacing`. `kind` is `phase` for the
  first `nphases` conductors, `neutral` for the rest. Positions use `h` as `yCoord`.
- **Connectivity.** Same as the CDPSM model: `node`/`bus` = the bus name lowercased; `phases` = the
  node suffixes in written order (`632.3.2` -> `CB`). Bus `RG60` is `rg60`.
- **Loads.** 2.4 kV line-to-neutral loads and regulators sit on `bv_4p16kv` (line-to-line
  convention, as in the CDPSM model). The 0.277 kV loads sit on `bv_480v`.
- **XfmrCode -> tank-only template.** SubXfmr and FdrXfmr are TransformerTankConfigurations
  (`xc_subxfmr`, `xc_fdrxfmr`) with lugs, one TransformerWinding per coil (lug to lug) and one
  TransformerMeshImpedance per leg. No phases: lug `sequenceNumber` = the conductor, in terminal
  order (end 1 A B C (N), then end 2). SubXfmr has 7 lugs (H1-H3, X1-X3, X0), FdrXfmr 8 (adds H0).
  Coil ratings are on a three-phase basis: `ratedU` = the side's kV, `baseU` = the coil voltage
  (delta: line to line; wye: kV / sqrt(3)), `ratedS` = the code's kva, `baseS` = kva / 3. On that
  base the deck's `%r` per winding and `XHL` apply unchanged to every coil and leg.
- **Transformer instances.** Sub and XFM1 are a PowerTransformer + one TransformerTank on the
  template + PowerTransformerEnds (node, phases, connection; no ratedU/ratedS/r and no per-end
  mesh: those are the template's) + TransformerPhaseEnds carrying the lugs' sequenceNumbers and
  the real phase, `phaseNeutralU`, `grounded` and `Terminal`. Each wye end's terminal is `ABCN`
  with a grounded `N` phase end.
- **Regulators.** The CDPSM model's VoltageRegulator model (see its README). RegLeg's values are
  written on each unit: a regulator has no reusable configuration in cim18v17 (each owns its
  winding). The bus is changed: `Reg1 Buses=[650.1 RG60.1]` has its end-1 node on `650` directly
  (the CDPSM deck put a breaker in front).
- **Source.** The same circuit line and impedance as `IEEE13_CDPSM` (basekv 115, MVAsc3 20000,
  MVAsc1 21000, OpenDSS defaults X1/R1 = 4, X0/R0 = 3). The values are copied, not recomputed.

## Derived values (not in the deck, not unit conversions)

These follow the CIMHub OpenDSS importer (`cimhub_opendss/src/cimhub_opendss/importer/conductors/`)
and the OpenDSS `ExportCIMXML.pas` it cites. A converter test can compare them directly.

| value | from | rule |
|---|---|---|
| `radius` (wires) | `DIAM` | DIAM / 2. OpenDSS gives a diameter; CIM stores a radius. |
| TS `diameterOverScreen` | `DiaShield` 0.88, `TapeLayer` 0.005 | DiaShield - 2 x TapeLayer = 0.870 |
| CN `diameterOverScreen` | `DiaCable` 1.29, `DiaStrand` 0.0641 | DiaCable - 2 x DiaStrand = 1.1618 |
| CN `diameterOverNeutral`, `diameterOverJacket` | `DiaCable` | both = DiaCable |
| CN `neutralStrandRadius` | `DiaStrand` | DiaStrand / 2 = 0.03205 |
| `rAC25`, `rAC50`, `rAC75` | `Rac` | all = Rac (OpenDSS gives no temperature) |
| TransformerTankConfiguration `noLoadLoss` (W) | `%NoLoadLoss` 0.6 % of 500 kVA | 3000 W (the CIM attribute is in W; the loader has no percent-to-W conversion) |
| `vectorGroup` | Delta-wye and Yn-Yn connections | Dyn1 (sub), YNyn0 (xfm1), as in the CDPSM model |
| wye coil `baseU` | `kv` 4.16, 0.48 | kv / sqrt(3) = 2.40178, 0.27713 kV |
| coil `baseS` | `kva` 5000, 500 | kva / 3 = 1666.6667, 166.6667 kVA |
| TransformerPhaseEnd `phaseNeutralU` | `kv` 115, 4.16, 0.48 | kv / sqrt(3) = 66395.3, 2401.78, 277.13 V (0 on N) |
| regulator TransformerWinding `ratedS` | RegLeg `kvas` 1666 (through rating) | 10 % regulation range x 1666 = 166.6 kVA (buck/boost rating) |

## Deviations from the deck

| item | deck | here | why |
|---|---|---|---|
| Sub %r and XHL | `%r=(.5 1000 /)`, `XHL=(8 1000 /)` | 0.0005 % / 0.008 % | The RPN expressions are evaluated, not converted. Bus 650 stays near 1.0 pu. The CDPSM model uses the nameplate 1 % / 8 % instead. |
| Sub end-2 neutral | no Rneut/Xneut | solidly grounded (no rground/xground); terminal `ABCN` with a grounded `N` phase end | CIMHub treats an unset neutral as solidly grounded. |
| Feeder name | `IEEE13NodecktAssets` | `ieee13nodecktassets` (mRID `fdr_ieee13nodecktassets`) | Lowercased, as the CDPSM model does. |
| Substation | none in the deck | `sub_ieee13` / `ieee13_sub` | Same invented substation as the CDPSM model, so the names match. Not in the deck. |
| XFM1 4.16 kV end | `Buses=[633 634]` | node `633` | The deck has no fuse, so no `XF1` node. |
| Reg end-1 node | `Buses=[650.1 RG60.1]` | `650` | The deck has no breaker (the CDPSM model puts the regulators behind `BRKR`). |
| Regulator controls | `Set Controlmode=OFF` (last Set) | `enabled=false`, `controlEnabled=false` | Controlmode OFF disables every control in OpenDSS. The taps stay at the deck's values. |
| Cap controls | `Set Controlmode=OFF` | `enabled=false`, `controlEnabled=false` | As above. |
| RegControl LDC | R=3 X=9 | 0.085714 / 0.257143 ohm | As in the CDPSM model: LDC settings are volts on the 120 V / 0.2 A base. |

## Not represented (and why)

- **`XfmrCode` RegLeg** has no configuration: a regulator has no reusable configuration in
  cim18v17, so its values are written on each VoltageRegulator.
- **Per-conductor wire assignment.** Each LineGeometry's `wires=[...]` (or `cond=<n> wire=`)
  is one `WireSequenceConfiguration` per conductor on the template: `<wc>_<n>`,
  `sequenceNumber` = the conductor's position in the spacing, `WireInfo` = that wire. The
  lines carry no `ACLineSegmentPhase.WireInfo`; the wire comes from their WireConfiguration.
- **Geometry-based impedance.** The geometry lines (all but 645646) carry `WireConfiguration` and
  no `PerLengthImpedance`. OpenDSS computes their impedance from the geometry (Carson, Kron
  reduction). That computation is not in this file.
- **`reduce=y`** (Kron reduction) on every LineGeometry: not represented.
- **`set earthmodel=carson`**: the CIM `EarthResistivity` is not written (no value in the deck).
- **EpsR** (relative permittivity of the cable insulation): no CIM attribute.
- **Cap1 on/off times** (`on=8 off=19`, hours): no cim18v17 attribute for a switching time.
- **Line.671692 stand-in impedance** (`r1=1e-4 r0=1e-4`): dropped, as in the CDPSM model
  (CIM switches are ideal).
- **`wires=`, `like=` semantics**: `LineGeometry.604 like=603` is written as its own
  WireConfiguration `wc_604` on the same spacing `spc_505` with its own copy of 603's wires
  (`wc_604_<n>`). `LineGeometry.605` is defined but unused (its line is
  commented out in the deck); `wc_605` is written anyway.
- **Solution commands** (`calcv`, `Solve`, `BusCoords`, `Clear`): not represented.
- **Loader gap, `percent`-unit columns**: any `percent` header is treated as a relative impedance
  and needs a base. So `TapeShieldCableInfo.tapeLap` is written unitless (20). This matches the
  CDPSM model's `percentMagnetizingCurrent`.

## Cap controls

- `Cap1` (`type=time`): `RegulatingControl` `cap_cap1_ctrl`, `mode=timeScheduled`. The on/off hours
  are not represented.
- `Cap2` (`type=voltage on=115 off=125 ptratio=20`): `cap_cap2_ctrl`, `mode=voltage`.
  `targetValue = (115 + 125) / 2 x 20 = 2400 V`, `targetDeadband = (125 - 115) x 20 = 200 V`
  (the full band, the CDPSM regulator convention). Sensing is `ln_684611_T2` (line 684611,
  terminal 2, bus 611). `monitoredPhase = C`: `ptphase=1` is the element's first conductor,
  node 611.3.

## Proposed mRID prefixes (need maintainer approval)

The skill's table has no entry for these. I picked the prefixes below and used them consistently.
None has been added to the skill table.

| prefix | classes | example |
|---|---|---|
| `wire_` / `cable_` | OverheadWireInfo / TapeShieldCableInfo, ConcentricNeutralCableInfo | `wire_acsr_556_5`, `cable_ts_1/0`, `cable_cn_250` |
| `spc_` | XYSpacing (LineSpacing and inline spacings) | `spc_500`, `spc_606` |
| `wc_` | WireConfiguration (LineGeometry and inline geometry) | `wc_601`, `wc_684611` |

The `wc_` prefix matches the one used in `CIM-Tables/tests/test_bind_cim18v17.py` (`wc_601`).
Children follow the existing rule: XYConductorPosition `<spc>_<n>` (for example `spc_500_1`), and the
capacitor's control `<cap>_ctrl`.

Wire mRIDs contain `/` (`wire_acsr_4/0`, `wire_cu_1/0`, `cable_ts_1/0`), kept as the OpenDSS name
lowercased. The loader accepts them. Flag if the maintainers prefer a different form.

## Element counts (deck -> output)

| element | deck | output |
|---|---|---|
| Vsource | 1 | 1 EnergySource |
| WireData | 4 | 4 OverheadWireInfo |
| TSData | 1 | 1 TapeShieldCableInfo |
| CNData | 1 | 1 ConcentricNeutralCableInfo |
| LineSpacing | 3 | 3 XYSpacing templates (+2 inline, for 606 and 607) = 5 XYSpacing |
| LineSpacing positions + inline positions | 4+3+2 + 3+2 | 14 XYConductorPosition |
| LineGeometry + inline Spacing/Wires | 7 + 1 | 8 WireConfiguration |
| LineGeometry wires (per conductor) | 4+4+3+3+2+3+2 + 2 | 23 WireSequenceConfiguration |
| inline line matrix (645646) | 1 | 1 PerLengthPhaseImpedance, 3 PhaseImpedanceData |
| XfmrCode | 3 | 2 TransformerTankConfiguration (SubXfmr, FdrXfmr), 15 TransformerLug, 12 TransformerWinding, 6 TransformerMeshImpedance; RegLeg is written per regulator |
| Transformer Sub, XFM1 | 2 | 2 PowerTransformer, 2 TransformerTank, 4 PowerTransformerEnd, 15 TransformerPhaseEnd |
| Transformer Reg1-3 | 3 | 3 VoltageRegulator, 6 AutoTransformerEnd, 9 TransformerLug, 3 TransformerWinding, 3 TransformerMeshImpedance |
| RegControl | 3 | 3 TapChangerControl, 3 RatioTapChanger |
| Load | 15 | 15 EnergyConsumer (+ 17 EnergyConsumerPhase) |
| Capacitor | 2 | 2 LinearShuntCompensator (+ 4 phase children) |
| CapControl | 2 | 2 RegulatingControl |
| Line (with geometry, inline spacing, or matrix) | 11 | 11 ACLineSegment, 26 ACLineSegmentPhase |
| Line `Switch=y` | 1 | 1 LoadBreakSwitch |
| Line normamps (limit) | 1 (645646) | 1 OperationalLimitSet + CurrentLimit |
| bus names | 16 | 16 ConnectivityNode, 52 Terminal |
| Set Voltagebases | 3 | 3 BaseVoltage |
| load models | 3 | 3 LoadResponseCharacteristic |

## Open questions

- `Set Controlmode=OFF` as `enabled=false` on every control is one reading of OpenDSS. Confirm it's
  the intended meaning for the converter test.

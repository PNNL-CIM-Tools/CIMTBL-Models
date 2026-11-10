# IEEE 13 node feeder (OpenDSS original deck)

Translated by hand from OpenDSS's [`IEEE13Nodeckt.dss`](https://github.com/dss-extensions/electricdss-tst/blob/master/Version8/Distrib/IEEETestCases/13Bus/IEEE13Nodeckt.dss)
(its `redirect IEEELineCodes.dss` only defines numbered line codes; the `mtx601`-`mtx607`
codes the lines use are defined inline in the deck) to `.cimtbl` (profile `cim18v17`).
Load the master; it imports the rest in dependency order (references must be declared
before use):

| file | OpenDSS | CIM |
|---|---|---|
| `IEEE13_original.cimtbl` | circuit / Vsource, voltage bases, load models | Substation (synthetic), Feeder, BaseVoltage, LoadResponseCharacteristic, EnergySource |
| `linecodes.cimtbl` | LineCode `mtx601`-`mtx607` | PerLengthPhaseImpedance + PhaseImpedanceData |
| `transformers.cimtbl` | Transformer `Sub`, `XFM1` | PowerTransformer + PowerTransformerEnd + TransformerMeshImpedance |
| `regulators.cimtbl` | Transformer `Reg1`-`Reg3` + RegControl | VoltageRegulator + AutoTransformerEnd + TransformerLug + TransformerWinding + TransformerMeshImpedance + RatioTapChanger + TapChangerControl |
| `switches.cimtbl` | Line `671692` with `Switch=y` | LoadBreakSwitch |
| `lines.cimtbl` | Line (11) | ACLineSegment |
| `loads.cimtbl` | Load (15) | EnergyConsumer |
| `capacitors.cimtbl` | Capacitor (2) | LinearShuntCompensator |

Not written, because the deck has no such element: `xfmrcodes.cimtbl` (no XfmrCode),
`der.cimtbl` (no PVSystem or Storage), and the house / Tpoletop / 240 V / 13.2 kV parts of
IEEE13_CDPSM.

## Translation conventions

Same as IEEE13_CDPSM (see its README):

- mRIDs: prefix + OpenDSS name, lowercased, with the OpenDSS name in `name`
  (`ld_671`, `ln_650632`, `vr_reg1`, `sw_671692`, `lc_mtx601`, `cap_cap1`, `src_source`,
  `fdr_ieee13nodeckt`). Buses keep the bare OpenDSS bus name (`sourcebus`, `650`, `rg60`, ...).
  Children extend the parent mRID (`vr_reg1_1`, `vr_reg1_ctrl`, `vr_reg1_tap`); the
  Terminal `vr_reg1_T2` is generated.
- `PhaseImpedanceData` has no mRID; `identifier` is `<lc mRID>_<row><column>`.
- Connectivity: `node` / `node1` / `node2` = the bus name without suffix. `phases` = the
  node suffix in written order (`.3.2` -> `CB`, `.3.1` -> `CA`); no suffix = `ABC`.
- Delta loads/shunts follow the binder's rule: `ABC` delta -> `AB`, `BC`, `AC` children.
- Units go in the column header and values are transcribed as written in OpenDSS:
  `length (ft)`, `p (kW)`, `q (kVAr)`, `r (ohm/mile)`, `x (ohm/mile)`, `ratedU (kV)`,
  `ratedS (kVA)`, `r (percent)`, `x (percent)`, `nominalVoltage (kV)`, `voltageMagnitude (kV)`.
- Sign: loads positive (CIM load convention); this deck has no generation.
- Load models `1/2/5` -> `zip_constant_pq / zip_constant_z / zip_constant_i`.
- Transformer percent impedances stay percent: `%r` on each end's own ratedU²/ratedS;
  `X` on the From end's ratedU²/ratedS (mesh).
- A TransformerEnd's `node` puts its Terminal on the PowerTransformer (`xf_<name>_T<n>`).
- Regulators as in IEEE13_CDPSM: each one is a VoltageRegulator (`vr_reg1`) with two
  AutoTransformerEnds (end 1 = S on 650, end 2 = L on RG60; phase `AN` / `BN` / `CN`, baseU 2.4 kV,
  ratedS = the 1666 kVA through rating), lugs S, L, SL, one TransformerWinding S -> SL
  with the tap at L (ratedS 166.6 kVA, the buck/boost rating, derived as 10 % of the
  through rating), and an `Update` row that sets `VoltageRegulator.AutoTransformerWinding`.
  The deck's `XHL=0.01` and `%LoadLoss=0.01` go on one TransformerMeshImpedance between
  the two ends (x 0.01 %, r 0.01 %): an AutoTransformerEnd has no r. `construction`
  (type A/B) is unset; the deck doesn't say.

Master / check output: `check_cimtbl.py` on `IEEE13_original.cimtbl` gives
`230 objects (26 Identity-only)`, profile `cim18v17`, model `IEEE13_original`, container
`fdr_ieee13nodeckt`.

## Deviations from the deck (realism audit)

Values written in the source deck are transcribed as written. These are the places where
the file differs from the deck:

| item | deck | here | why |
|---|---|---|---|
| Sub impedance | `XHL=(8 1000 /)`, `%r=(.5 1000 /)` on both windings | `r (percent)` 0.0005 on each end, mesh `x (percent)` 0.008 | The RPN is evaluated, not converted: 8/1000 = 0.008 %, 0.5/1000 = 0.0005 %. The deck says this puts bus 650 at 1.0 pu. The published nameplate (R 1 %, X 8 %) is **not** used here; IEEE13_CDPSM uses it. |
| Vsource voltage | `basekv=115 pu=1.0001` | `nominalVoltage (kV)=115`, `voltageMagnitude (kV)=115.0115` | CIM stores absolute volts, and there is no `pu` unit on `voltageMagnitude`. 115.0115 = 1.0001 x 115 (derived). IEEE13_CDPSM used pu 1.00. |
| Line susceptance | `cmatrix` (nF/mile) on mtx606 and mtx607 only | `b (uS/mile)` = 2 pi 60 C, 144.745 and 88.9699 | CIM stores `b`, not C. Same derivation as IEEE13_CDPSM. mtx601-605 have no cmatrix, so `b` is unset. |
| Regulator LDC | `R=3 X=9` (volts on 120 V / 0.2 A base) | `lineDropR (ohm)` 0.085714, `lineDropX (ohm)` 0.257143 | Converted to primary ohms as in IEEE13_CDPSM: R x ptratio / ctprim = 3 x 20 / 700. |
| Regulator taps | Not set in the deck (RegControl solves them) | `step` 10 / 8 / 11 | Taken from the deck's commented "Alternate Solution Script" (`Taps=[1.0 1.0625]` etc.): (tap - 1) / 0.00625. A solver-state value, not a deck value. |
| Regulator `ctRatio` / `targetValue` | RegControl `ptratio=20 ctprim=700 vreg=122 band=2` | `ctRatio` 3500, `targetValue` 2440, `targetDeadband` 40 | Derived: 700 A / 0.2 A; 122 x 20; 2 x 20. |
| BaseVoltage units | `Set Voltagebases=[115, 4.16, .48]` (kV) | `nominalVoltage (kV)` 115, 4.16, 0.48 | Written as in the deck. IEEE13_CDPSM also uses `(kV)`. |
| Lines 632-670 and 684-611 | `Bus1=632.1.2.3` and `Bus1=684.3` | `node1` = `632` and `684` | The deck does not use IEEE13_CDPSM's intermediate buses (`MID`, `TAP`); they belong to the CDPSM Recloser/Sectionaliser. |
| Regulator primary | `Buses=[650.1 RG60.1]` | end 1 `node` = `650` | No breaker in this deck. IEEE13_CDPSM puts a BRKR node in front. |
| xfm1 primary | `bus=633` | `node` = `633` | Deck bus 633 directly. IEEE13_CDPSM uses `XF1`, its fuse's downstream node. |
| Switch | `Line.671692 Switch=y` only | one LoadBreakSwitch | The deck has no Relay/Recloser/Fuse/Breaker, so no protection class, so LoadBreakSwitch. |
| OperationalLimitSet / CurrentLimit | none | none | The deck has no `normamps=`. IEEE13_CDPSM has them. |
| Load `kV=0.277` | line-to-neutral 277 V | `BaseVoltage` `bv_480v` | Same as IEEE13_CDPSM (the 480 V system). |
| Bus coordinates, solve commands, `Show` comments | `BusCoords`, `calcv`, `Solve` | not represented | Not model data (as in IEEE13_CDPSM). |
| Switch stand-in impedance | `r1=1e-4 r0=1e-4` | dropped | CIM switches are ideal (as in IEEE13_CDPSM). |
| Regulator bank | `bank=reg1` | not represented | Not a CIM concept here (as in IEEE13_CDPSM, which uses `Bank=Reg`). |
| `Set DefaultBaseFrequency=60` | 60 Hz | `calculatedFrequency (Hz)` 60 | Matches `BaseFreq=60` on the line codes. |

## Judgment calls (conventions did not cover these)

- **Sub grounding.** The deck gives the sub's wye winding (`wdg=2 bus=650 conn=wye`) no
  neutral bus and no Rneut/Xneut. I took it as solidly grounded with no neutral conductor:
  `connectionKind` `Yn`, `grounded` true, phases `ABC`, rground/xground unset. IEEE13_CDPSM
  has `ABCN` and `rground` 0 / `xground` 0.4 because its deck sets `Rneut=0 Xneut=0.4`.
  Not verified against OpenDSS documentation (web search was unavailable). The
  `cimhub_opendss` exporter treats a wye with Rneut=0 / Xneut=0 as needing no neutral
  suffix, which is consistent with this reading but does not confirm the unset default.
- **Sub vector group `Dyn1`.** Not in the deck. The 115 kV delta / 4.16 kV wye pair with
  `Angle=30` gives Dyn1, as in IEEE13_CDPSM.
- **xfm1 vector group `YNyn0`** and `Yn` ends with ABC phases, as in IEEE13_CDPSM (no Rneut in either deck).
- **Substation `sub_ieee13` is synthetic.** The deck has only the circuit, which is the
  Feeder. The Substation is the container for the source and the sub transformer, as in
  IEEE13_CDPSM.
- **EnergySource impedances.** r/x from MVAsc3 = 20000 and r0/x0 from MVAsc1 = 21000,
  using OpenDSS defaults X1/R1 = 4 and X0/R0 = 3 (assumed; the deck does not set them).
  Same values as IEEE13_CDPSM.
- **Capacitor `bPerSection`** = nomQ / nomU², as in IEEE13_CDPSM (0.034671 S for 600 kVAr at
  4.16 kV, 0.017361 S for 100 kVAr at 2.4 kV).
- **Capacitor 2 BaseVoltage** `bv_4p16kv` with nomU 2.4 kV (line-to-neutral of the 4.16 kV
  system), as in IEEE13_CDPSM.
- **Load BaseVoltages.** Loads at 2.4 kV line-to-neutral use `bv_4p16kv`, as in IEEE13_CDPSM. The deck has no 2.4 kV BaseVoltage.
- **mtx606** uses the active "Corrected mtx606 Feb 3 2016" definition. The earlier
  "Original 606" values sit in a commented-out block of the deck and are not used.
- **mtx601/mtx602 off-diagonals.** The deck's values are the corrected ones (Kersting-matching). They
  match IEEE13_CDPSM's `linecodes.cimtbl`, though its deck had them swapped.

## Element counts (source deck vs output)

| source element | count | output | count |
|---|---|---|---|
| `new circuit` (Vsource) | 1 | EnergySource (+ Feeder; Substation synthetic) | 1 (+ 1 + 1) |
| `Transformer.Sub` (2 windings) | 1 | PowerTransformer + 2 PowerTransformerEnd + 1 TransformerMeshImpedance | 1 / 2 / 1 |
| `Transformer.XFM1` (2 windings) | 1 | same | 1 / 2 / 1 |
| `Transformer.Reg1-3` (2 windings each) | 3 | VoltageRegulator + 6 AutoTransformerEnd + 9 TransformerLug + 3 TransformerWinding + 3 TransformerMeshImpedance | 3 / 6 / 9 / 3 / 3 |
| `regcontrol` | 3 | RatioTapChanger + TapChangerControl | 3 / 3 |
| `linecode` mtx601-607 | 7 | PerLengthPhaseImpedance + PhaseImpedanceData | 7 / 26 (6+6+3+3+1+6+1) |
| `Line` (LineCode) | 11 | ACLineSegment + ACLineSegmentPhase | 11 / 26 |
| `Line` with `Switch=y` | 1 | LoadBreakSwitch + SwitchPhase | 1 / 3 |
| `Load` | 15 | EnergyConsumer + EnergyConsumerPhase | 15 / 17 (671 delta -> 3, 646 and 692 -> 1 each) |
| `Capacitor` | 2 | LinearShuntCompensator + LinearShuntCompensatorPhase | 2 / 4 |
| buses (`IEEE13Node_BusXY.csv`, incl. SourceBus) | 16 | ConnectivityNode | 16 |
| (generated) | | Terminal | 52 (22 ACLine + 2 switch + 15 load + 2 cap + 1 source + 4 PT ends + 6 regulator ends) |
| (generated) | | EnergySourcePhase | 3 |

Total output objects: 230, matching the check.

## Not represented

- Bus coordinates (`IEEE13Node_BusXY.csv`), `BusCoords`, `calcv`, `Solve`, `Show` commands.
- Switch stand-in impedance `r1=1e-4`.
- OpenDSS `Bank=` and `normamps=` (the deck has no normamps).
- Relay / Recloser / Fuse / Sectionaliser (none in the deck).
- Transformer `XfmrCode` / TransformerTank (none in the deck).

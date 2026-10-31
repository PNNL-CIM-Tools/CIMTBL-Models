# IEEE 13 node feeder (CDPSM variant)

Translated from `CIMHub_2_0/test_data/models/feeders/OpenDSS/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss`
to `.cimtbl` (profile `cim18v17`). Load the master; it imports the rest in
dependency order (references must be declared before use):

| file | OpenDSS | CIM |
|---|---|---|
| `IEEE13_CDPSM.cimtbl` | circuit / Vsource, voltage bases, load models | Substation, Feeder, BaseVoltage, LoadResponseCharacteristic, EnergySource |
| `linecodes.cimtbl` | LineCode | PerLengthPhaseImpedance + PhaseImpedanceData |
| `xfmrcodes.cimtbl` | XfmrCode | TransformerTankConfiguration (+ phase ends, windings, mesh) |
| `transformers.cimtbl` | Transformer | PowerTransformer + PowerTransformerEnd + TransformerMeshImpedance (or TransformerTank for an XfmrCode instance) |
| `regulators.cimtbl` | Transformer + RegControl | PowerTransformer + RatioTapChanger + TapChangerControl |
| `switches.cimtbl` | Line `Switch=y` | Breaker / Recloser / Fuse / Sectionaliser / LoadBreakSwitch |
| `lines.cimtbl` | Line | ACLineSegment, OperationalLimitSet + CurrentLimit (normamps) |
| `loads.cimtbl` | Load | EnergyConsumer |
| `capacitors.cimtbl` | Capacitor | LinearShuntCompensator |
| `der.cimtbl` | PVSystem, Storage | PowerElectronicsConnection + PhotoVoltaicUnit / BatteryUnit |

The split follows the per-family files of larger decks (IEEE 9500: `LineCodes.dss`,
`Transformers.dss`, `Regulators.dss`, ...).

## Translation conventions

- **mRIDs** are the row keys and every reference is by mRID; an mRID must be
  unique within the whole model, not just its class (CIM 18). They follow the
  `cimtbl-translate` skill's prefix table (`.claude/skills/cimtbl-translate/`):
  a class-family prefix + the OpenDSS name lowercased (`ld_671`, `ln_650632`,
  `xf_reg1`, `sw_brkr1`, `lc_mtx601`), with the OpenDSS name kept in `name`.
  Buses keep the bare OpenDSS bus name. Child rows extend their parent's mRID
  (`xf_reg1_2`, `xf_reg1_tap`, `ln_650632_limits`); generated Terminals are
  `<equipment mRID>_T<n>`. The two DER connections behind OpenDSS PVSystem.School
  and Storage.School are `pv_school` / `storage_school`.
- **`PhaseImpedanceData`** is not an IdentifiedObject (no mRID); each row's
  `identifier` (`lc_mtx601_21` = row 2, column 1) seeds a deterministic UUID.
- **Connectivity**: `node` / `node1` / `node2` = the OpenDSS bus name (no node suffix).
- **`phases`** = the bus node suffix in written order, `.1 .2 .3` -> `A B C`
  (`632.3.2` -> `CB`). On a split-phase secondary (center-tap) bus, `.1 .2` ->
  `s1 s2`. Write `N` only for a real neutral conductor (explicit node `.4`, or a
  center-tap secondary end, `s1s2N`); OpenDSS `.0` is ground, not a conductor.
  Bus with no suffix = `ABC`.
  - The binder sets every Terminal's PhaseCode to the canonical set
    (`CB` -> `BC`, `s1s2` -> `s12`) and creates one `<Class>Phase` per token in
    order (line conductor k = line-code matrix row k).
  - A delta shunt (`phaseConnection=D`) gets one child per line-to-line branch
    via the `phases` extension: `BC` -> one `BC` child; `ABC` -> `AB`, `BC`, `AC`.
- **Units** go in the column header: the value is transcribed as written in
  OpenDSS, with its OpenDSS unit (`length (ft)`, `p (kW)`, `r (ohm/mile)`).
  Never pre-convert.
- **Transformers**
  - Winding `%r` -> `PowerTransformerEnd.r (percent)`, on the end's own
    ratedU²/ratedS.
  - Each `X**` -> `TransformerMeshImpedance.x (percent)`, on the From end
    (`XHL` = end 1 -> 2, `XHT` = 1 -> 3, `XLT` = 2 -> 3).
  - `ratedU` = OpenDSS `kv` (line-to-line for 3-phase; across the winding for
    1-phase).
  - An end's `node` puts its Terminal on the PowerTransformer.
- **XfmrCode** -> TransformerTankConfiguration, with:
  - `%Rs` -> `TransformerWinding.r (percent)`, `X**` -> mesh `x (percent)`;
  - `baseU` = `kvs`, `baseS` = `kVAs`, `ratedS` = the winding's own share;
  - the primary phase end as `X`, assigned by the instance's terminal phases;
  - instance = `PowerTransformer` + `TransformerTank` (`TankConfiguration=`) +
    `PowerTransformerEnd`s with node/phases.
- **RegControl** -> CIM primary quantities:
  - `targetValue` = vreg × ptratio, `targetDeadband` = band × ptratio;
  - `lineDropR/X` = R or X (LDC volts) × ptratio / CTprim, in ohms;
  - `step` = solved tap position, (tap − 1) / 0.00625, with ±16 steps.
- **Load models** `1/2/5` -> `zip_constant_pq / zip_constant_z / zip_constant_i`.
  p/q are totals; `pf` -> q = p·tan(acos pf).
- **DER sign**: CIM load convention, so generation and discharge are negative p.
  PV p = −irrad × Pmpp.
- **Capacitor**: `nomU` = OpenDSS kV, `bPerSection` = Q / U².
- **Not represented**:
  - switch stand-in impedances (r1=1e-4);
  - Relay/Recloser trip settings (no protection classes in cim18v17);
  - OpenDSS `Bank=`;
  - bus coordinates;
  - solution commands.

## Deviations from the deck (realism audit)

| item | deck | here | why |
|---|---|---|---|
| sub3 impedance | `%r=(.5 1000 /)`, `XHL=0.01`, `XHT=XLT=0.025` (near-ideal so bus 650 = 1.0 pu) | %r 0.5 / 0.5 / 0.5, XHL 8, XHT 10, XLT 4 | published nameplate R = 1 %, X = 8 %; tertiary XHT/XLT assumed (no published data). **650 no longer sits at 1.0 pu**, so the published voltages won't match exactly |
| mtx601 / mtx602 off-diagonals | Zab and Zbc swapped | Kersting / `IEEE13_original` "corrected 9-14-2011" | CDPSM deck predates the correction |
| RegControl LDC | R=3 X=9 | 0.085714 / 0.257143 ohm | LDC settings are volts on the 120 V / 0.2 A base, not ohms |

Kept as-is, but worth knowing:

- mtx601–605 have **no shunt susceptance** (CDPSM cmatrix = 0). The published
  IEEE 13 B matrices are a few µS/mile.
- mtx606 uses Dugan's 2016 CN-cable recomputation (383.948 nF/mile). Kersting's
  published value is 257 nF/mile ("too low by 1.5").
- xfm1 X = 2 % is the published value, but low for a 500 kVA unit (typically ~5 %).
- The source is near-infinite (MVAsc3 = 20000, MVAsc1 = 21000).
- Regulators are near-ideal (0.01 %), which is normal practice.
- **tpoletop (5 kVA) is overloaded**. The house load is 5 kW at pf 0.85, about
  5.9 kVA. Storage charging at 5 kW, net of PV at 4 kW, brings it to about 7 kVA,
  roughly 140 %.
- ct5 values (R 1.2 %, X 1.7 %, 10 W no-load) are plausible for 5 kVA.
- house load/PV/storage `kv=0.208` on `phases=2` wye: OpenDSS treats it as
  line-to-line, so 120 V legs, which is correct. Its BaseVoltage is 240 (split-phase).

## Open questions

- `TransformerTankConfiguration` cannot carry per-tank tap state. A RatioTapChanger
  on a configuration's phase end is shared by every tank, so the regulators
  here are three separate PowerTransformers.
- The single-phase configuration's primary phase end uses `X`, so the code
  isn't tied to one phase. `../../templates/padmount_1ph_250kva.cimtbl` uses
  explicit `A`/`B` for H1A/H1B; one convention should be chosen.

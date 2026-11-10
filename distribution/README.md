# Distribution models

## IEEE 13 node test feeder

Each folder is one model: a master file named after the folder, which imports one file per equipment family in
order (line codes before lines, transformer codes before transformers, and so on). Each folder's README lists the
source, the translation decisions, and how the model differs from the others.

| model | source | what it adds |
|---|---|---|
| [`IEEE/IEEE13_original`](IEEE/IEEE13_original) | OpenDSS `IEEE13Nodeckt.dss` | The feeder as distributed with OpenDSS. |
| [`IEEE/IEEE13_CDPSM`](IEEE/IEEE13_CDPSM) | Powergrid-Models `IEEE13_CDPSM.dss` | The CIM sampler: every switch class, a 240 V house on a 1-phase tank, PV and a battery. The worked example for translations. |
| [`IEEE/IEEE13_assets`](IEEE/IEEE13_assets) | Powergrid-Models `IEEE13_Assets.dss` | Lines from wires, cables and spacings; transformers from codes; capacitor controls. |
| [`IEEE/IEEE13_OCHRE`](IEEE/IEEE13_OCHRE) | Powergrid-Models `IEEE13_OCHRE/` | 40 center-tapped service transformers, triplex lines and triplex loads. |
| [`IEEE/IEEE13_CYME`](IEEE/IEEE13_CYME) | A CYME 9.4 study file | The feeder as CYME holds it: conductor geometry per line, a distributed load (lumped at an added node 670), a fixed-tap regulator. |

## Transformer templates

[`templates/`](templates) holds reusable transformer designs. A single tank is a `TransformerTankConfiguration`,
and a bank of tanks is a `TransformerBankConfiguration`; an instance's `TransformerTank` points at one with
`TankConfiguration=`, like an OpenDSS XfmrCode. A template numbers the conductors its windings land on, and an
instance says which phase each number is.

The examples build instances from the templates:

- [`padmount_example.cimtbl`](padmount_example.cimtbl): a single-phase padmount, from `padmount_1ph_250kva`;
- [`open_wye_open_delta_example.cimtbl`](open_wye_open_delta_example.cimtbl): an open wye - open delta bank, from
  `bank_oyod_50_50_7200_12470y`;
- [`regulator_example.cimtbl`](regulator_example.cimtbl): a single-phase ANSI type A step-voltage regulator.

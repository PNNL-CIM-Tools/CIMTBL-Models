# CIMTBL-Models

Power-system models in `.cimtbl`, a hand-editable tabular text format for CIM (IEC 61970/61968) models. Each
file declares its CIM profile (`cim18v17`) and loads into a [cim-graph](https://github.com/PNNL-CIM-Tools/CIM-Graph)
model, which can be written out as CIM XML. The format and its loader are
[cim-tables](https://github.com/PNNL-CIM-Tools/CIM-Tables).

## Loading a model

```
pip install --pre cim-tables
```

```python
import cimtables

model = cimtables.load_model('distribution/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.cimtbl')
```

Load a model's master file; it imports the rest of the model's files in order. To check a model and count its
objects by class, without installing anything:

```
uv run --no-project --prerelease=allow --with cim-tables python -I .claude/skills/cimtbl-translate/check_cimtbl.py distribution/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.cimtbl
```

A model that doesn't load fails at the file and line of the first bad row.

## Models

| path | what |
|---|---|
| [`distribution/IEEE/`](distribution/IEEE) | Five translations of the IEEE 13 node test feeder: the OpenDSS original deck, the CDPSM, assets and OCHRE variants, and a CYME study. Each folder's README lists its sources, translation decisions and differences. |
| [`distribution/templates/`](distribution/templates) | Reusable transformer tank and bank configurations (pole-mount, padmount, open wye - open delta), like OpenDSS XfmrCodes. |
| [`distribution/*_example.cimtbl`](distribution) | Small models built on the templates: a padmount, an open wye - open delta bank, and a step-voltage regulator. |
| [`tiered_tso_dso/IEEE13/`](tiered_tso_dso/IEEE13) | IEEE 13 at three levels of data disclosure: public feeder aggregates, switch-delimited areas, and a positive-sequence equivalent. |
| [`transmission/`](transmission) | Transmission models (none yet). |

See [`distribution/README.md`](distribution/README.md) for more on the distribution models.

## Conventions

- Every row is keyed by its `mRID`, and references are by mRID. A class prefix keeps mRIDs unique across classes
  (`ld_671` for a load, `671` for its bus); the source's own name is kept in `name`.
- A master file sets `Authority = https://github.com/PNNL-CIM-Tools/CIMTBL-Models` and a `Model =` name. The UUIDs
  are seeded from those and the mRIDs, so they are stable from one load to the next.
- Values carry their units in the column header (`p (kW)`, `length (ft)`, `r (ohm/mile)`).
- CIM 18 gaps found while translating, with how each is approximated here, are tracked in
  [`.development/CIM18_GAPS.md`](.development/CIM18_GAPS.md).
- The conventions for writing and translating models, including how to check one, are in
  [`.claude/skills/cimtbl-translate/SKILL.md`](.claude/skills/cimtbl-translate/SKILL.md). For transformer
  templates from a winding diagram, see [`.claude/skills/cimtbl-transformer-template/SKILL.md`](.claude/skills/cimtbl-transformer-template/SKILL.md).

## Sources

The IEEE 13 node test feeder is from the IEEE PES Distribution Test Feeders. The translations come from:

- OpenDSS's `IEEE13Nodeckt.dss` (`IEEE13_original`);
- GRIDAPPSD [Powergrid-Models](https://github.com/GRIDAPPSD/Powergrid-Models) (`IEEE13_CDPSM`, `IEEE13_assets`,
  `IEEE13_OCHRE`);
- a CYME 9.4 study file of the feeder, Eaton's QA validation case (`IEEE13_CYME`; the study file is not
  distributed here);
- the SRP Overhead Distribution Construction Standards (the open wye - open delta bank template).

## License

BSD 3-Clause; see [LICENSE](LICENSE).

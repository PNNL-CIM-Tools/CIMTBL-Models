# CIM 18 gaps found while translating models

Concepts a source model uses that cim18v17 cannot represent. Each entry says how the
.cimtbl approximates it today and which models are affected. These are TODOs for the
CIM 18 profile, not for the translations.

## TODO (CIM18 gap): distributed load along a line segment

- **Source:** CYME `DistributedLoad` on a section (IEEE 13 node feeder, 632-671); the
  IEEE 13 spec's distributed load on 632-671.
- **CIM 18:** no class for a load spread along an `ACLineSegment` (EnergyConsumer is
  connected at a node only).
- **Approximation:** the line is split at an added mid-line node and the load is lumped
  there as an `EnergyConsumer` (as OpenDSS IEEE 13 does with bus 670).
- **Models:** `IEEE/IEEE13_CYME`: the split is 632-670 at 667 ft and 670-671 at 1333 ft, the load
  is three per-phase EnergyConsumers at node 670 (A 17 + j10, B 66 + j38, C 117 + j68 kW/kvar).

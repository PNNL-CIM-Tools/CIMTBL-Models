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

## TODO (CIM18 gap): ownership of network equipment

- **Source:** PSS/E RAW v34 Owner table (I, OWNAME) and the owner fields on network records:
  O1/F1..O4/F4 (up to four owners with their fractions) on loads, generators, branches,
  transformers, switched shunts, FACTS and VSC DC, and OWNER on buses (IEEE 14, WECC 240).
- **CIM 18:** ownership is an asset-management concept (`AssetOwner` / `Ownership` with a share,
  on an `Asset`). A `PowerSystemResource` in the network profile parts has no owner, and a
  bus-branch import has no `Asset` to hang one on.
- **Approximation:** none; the fields are untranscribed in the RAW `.cimtbl` import
  (CIMHub `cimhub_raw`, RAW_REWRITE_PLAN.md RAW-2), so a RAW round trip loses them.
- **Models:** every RAW case (IEEE 14 and WECC 240 each have one owner).

## TODO (CIM18 gap): zone membership of a bus

- **Source:** PSS/E RAW v34 Zone table and bus ZONE (IEEE 14, WECC 240). A zone is a planner's
  grouping of buses, independent of substations.
- **CIM 18:** a bus (`TopologicalNode`, `ConnectivityNode`) reaches a region only through its
  `ConnectivityNodeContainer` → `Substation.Region` → `SubGeographicalRegion`. There is no
  association from a node to a zone, so every bus of a substation must share one zone.
- **Needed:** an association from `TopologicalNode` (and `ConnectivityNode`) to the zone class
  (`SubGeographicalRegion`, or a dedicated zone/load area), independent of the container.
- **Approximation:** the RAW import maps Zone → `SubGeographicalRegion` and never merges buses of two
  zones into one `Substation`. Equipment that joins two zones (a transformer, a zero-impedance device)
  sits on a substation boundary, so the grouping is finer than the physical substation (WECC 240:
  buses 1001 and 4006 each join two zones).
- **Models:** every RAW case with more than one zone (WECC 240: 14 zones).

## TODO (CIM18 gap): control-area membership of a bus, and the area slack bus

- **Source:** PSS/E RAW v34 bus AREA and the Area record's swing bus ISW (IEEE 14, WECC 240: 4 areas).
- **CIM 18:** cim18v17 (profile of 2026-11-08) ties equipment to a `ControlArea`: generating units through
  `ControlAreaGeneratingUnit`, loads through `LoadGroup` → `SubLoadArea` (an `EnergyArea`) →
  `ControlArea`, and boundary terminals through `TieFlow`. A bus itself has no area: neither
  `TopologicalNode`, `ConnectivityNode` nor a `BusbarSection` reaches a `ControlArea`, so a bus with only
  branches on it (or a `BusbarSection`) has no area. Nothing names an area's slack bus.
- **Needed:** a node (or `BusbarSection`) → `ControlArea` association, and a `ControlArea` → slack
  (`TopologicalNode` or `SynchronousMachine`) reference.
- **Approximation:** the RAW import writes the equipment memberships it can, including a pair of `TieFlow`s
  on each tie's metered terminal. A bus's AREA is traced on export from generating units and tie flows, across
  devices inside one area; the import lists any bus the trace cannot reach (`untranscribed: area=`), such as
  an isolated bus with no equipment. ISW is untranscribed (CIMHub `cimhub_raw` R5, 2026-11-08).
- **Models:** every RAW case.

## TODO (CIM18 gap): the area and zone of machines and DC equipment (load-area hierarchy resolved 2026-11-08)

- **Source:** PSS/E RAW v34 Load, Induction Machine and Multi-Terminal DC bus records each carry their own
  AREA and ZONE (defaulting to the bus's).
- **CIM 18:** loads are covered by cim18v17 (profile of 2026-11-08): `ConformLoad` / `NonConformLoad` →
  `LoadGroup` → `SubLoadArea` → `LoadArea` (`SubLoadArea.LoadArea`, added 2026-11-08) → (as the area's one
  `EnergyArea`) `ControlArea`. Still missing: any area or zone link for an `AsynchronousMachine` or DC
  equipment, and a zone link for any equipment (a `SubLoadArea` names no `SubGeographicalRegion`).
- **Needed:** an area/zone association for `AsynchronousMachine` and the DC classes; an equipment → zone link.
- **Approximation:** the RAW import puts each load in a `SubLoadArea` per (area, zone) pair under a `LoadArea`
  per area. A load's zone is otherwise read from its bus's substation. Induction machine and DC AREA/ZONE are
  untranscribed.
- **Models:** every RAW case with loads (all); induction machines and DC lines in none of the public ones.

## TODO (CIM18 gap): metered end of a branch

- **Source:** PSS/E RAW v34 MET on non-transformer branches, system switching devices and multi-section
  lines (NMETR on transformers): the end PSS/E meters, with losses assigned to the other end
  (WECC 240: 81 of 329 branches meter bus J).
- **CIM 18:** a branch's terminals carry no metered-end flag. `TieFlow` marks a metering terminal only for a
  `ControlArea` interchange, and so only on branches between areas.
- **Needed:** a metered-end (loss-allocation) marker on a `Terminal`, or on `ACDCTerminal.sequenceNumber`
  semantics.
- **Approximation:** on a tie (a device between areas), the RAW `.cimtbl` import puts both areas' `TieFlow`s
  on the metered terminal, so MET/NMETR survive there (R5). Elsewhere untranscribed (CIMHub `cimhub_raw`,
  RAW_REWRITE_PLAN.md RAW-22, and R4 for NMETR); a round trip writes MET = 1 and NMETR = 2 there. Power flow does
  not need it; zone and owner loss reports would.
- **Models:** every RAW case with branches.

## TODO (CIM18 gap): a scheduled transfer between two control areas

- **Source:** PSS/E RAW v34 Inter-area transfer records: ARFROM, ARTO, a one-character TRID and PTRAN (MW,
  positive when ARFROM sells to ARTO). No public case has one.
- **CIM 18:** cim18v17 has no scheduled-transfer class. cim17v40's `InterchangeSchedule` (a market `Curve`) is
  gone; `TieCorridor` and `PowerTransferCorridor` group ties but carry no schedule; `ControlArea.netInterchange`
  is the area's net only (and is marked ToBeDeleted).
- **Needed:** a transfer between two `ControlArea`s with an identifier and an active power.
- **Approximation:** the RAW import lists each record verbatim on the `ControlArea` table comment of
  `area_interchange.cimtbl` (CIMHub `cimhub_raw` R5, 2026-11-08); a round trip loses them.
- **Models:** RAW cases with inter-area transfers (none of the public ones).

## TODO (CIM18 gap): a shunt switched with its line, in a bus-branch model

- **Source:** PSS/E RAW v34 branch GI/BI and GJ/BJ: line-connected shunts (reactors) at each end of a
  branch, switched in and out with the line (no public case sets one).
- **CIM 18:** a `ShuntCompensator` on a bus-branch `TopologicalNode` has no association to the line it is
  switched with. In a node-breaker model the shunt would sit on the line's side of the breaker, which says it.
- **Needed:** none if the model is node-breaker; otherwise a shunt → `ACLineSegment` (or
  `Terminal`) association.
- **Approximation:** the RAW import writes an ordinary `LinearShuntCompensator` per end
  (`cap_<I>_<J>_<CKT>_i` / `_j`), with the line's in-service status, linked to the line by its mRID only
  (RAW_REWRITE_PLAN.md RAW-13). In a RAW node-breaker substation (R6, 2026-11-09) the shunt sits on its line
  end's `ConnectivityNode`, which says it.
- **Models:** none of the public RAW cases.

## TODO (CIM18 gap): a shunt's share of a coordinated voltage control

- **Source:** PSS/E RAW v34 Switched Shunt RMPCT: the percent of the Mvar holding the regulated bus's voltage that
  this shunt contributes, when several devices regulate one bus.
- **CIM 18:** `SynchronousMachine.qPercent` gives a machine's share of a coordinated reactive control; a
  `ShuntCompensator` or a `PowerElectronicsConnection` (or any other `RegulatingCondEq`) has none. The same
  applies to a RAW generator's RMPCT when the generator is a renewable (WMOD 1) `PowerElectronicsConnection`.
- **Needed:** a participation share on `RegulatingCondEq` (or on the `RegulatingCondEq` → `RegulatingControl`
  link).
- **Approximation:** the RAW import leaves RMPCT untranscribed; the exporter writes 100.
- **Models:** the public RAW cases have RMPCT = 100 on every switched shunt.

## TODO (CIM18 gap): the kind of a renewable bus-branch generator

- **Source:** PSS/E RAW v34 Generator WMOD 1-3: a renewable machine (wind or solar, unstated which), whose
  reactive limits do not come from a synchronous machine. RAW does not say PV, wind, or which wind technology.
- **CIM 18:** a converter-interfaced plant is a `PowerElectronicsConnection` with a `PhotoVoltaicUnit` or
  `PowerElectronicsWindUnit`; a type 1/2 wind plant is an `AsynchronousMachine`. A concentrating solar thermal plant
  is a synchronous machine (WMOD 0 in PSS/E).
- **Needed:** nothing in CIM; the source lacks the kind. A converter could take it from a side file (fuel type).
- **Approximation:** the RAW import writes WMOD 1 as a `PowerElectronicsConnection` + a plain (concrete)
  `PowerElectronicsUnit`, with no kind (RAW_REWRITE_PLAN.md RAW-24).
- **Models:** WECC240 has 37 WMOD 1 machines (11 wind, 26 solar by its working workbook).

## TODO (profile extension): a synchronous machine's positive-sequence reactance

- **Source:** PSS/E RAW v34 Generator ZX (with ZR, ZSORCE: pu on MBASE, subtransient or transient by study).
- **cim18v17:** `SynchronousMachine` has `r`, `r0`, `r2`, `x0`, `x2`, but no positive-sequence reactance; the
  canonical CIM 18 saturated reactances (`satDirectSubtransX`, `satDirectTransX`, `satDirectSyncX`) are not in the
  profile either.
- **Needed:** a new cim18v17 extension attribute for the machine's positive-sequence (source) reactance (user,
  2026-11-08: log as a TODO and a new extension).
- **Approximation:** the RAW import maps ZR to `r (ohm)` and leaves ZX untranscribed; the exporter writes 1.0.
- **Models:** IEEE14 (ZX 1.0), WECC240 (ZX 0.2 on every machine).

## TODO (CIM18 gap): the in-service status of a node

- **Source:** PSS/E RAW v34 substation node STATUS (1 in service, 0 out of service).
- **CIM 18:** a `ConnectivityNode` has no `inService` (only `Equipment` does), and RAW does not say which node is a
  busbar, so there is no `BusbarSection` to carry it.
- **Needed:** an in-service flag on a `ConnectivityNode`, or a source that names its busbars.
- **Approximation:** the RAW import lists STATUS 0 on the node's row (`untranscribed: status=0`); the export
  writes 1 (CIMHub `cimhub_raw` R6, 2026-11-09).
- **Models:** the committed RAW IEEE118 with four node-breaker substations: block 100's transfer bus (node 2).

## TODO (CIM18 gap): a substation's DC grounding resistance

- **Source:** PSS/E RAW v34 substation SGR (ohm), for geomagnetically induced current (GIC) studies.
- **CIM 18:** `Substation` has no grounding resistance; the grounding classes (`Ground`, `GroundingImpedance`,
  `PetersenCoil`) are conducting equipment for fault studies, not a station's DC earth resistance.
- **Needed:** a DC grounding resistance on a `Substation`, if GIC studies are to round-trip.
- **Approximation:** untranscribed; the export writes the default 0.1 (CIMHub `cimhub_raw` R6, 2026-11-09).
- **Models:** every RAW case with SUBSTATION data (IEEE118: 0.1, the default).

## TODO (CIM18 gap): a solved voltage per node of a split bus

- **Source:** PSS/E RAW v34 substation node VM (pu, default -1.0: not given) and VA (deg): the solved voltage of
  each bus section when a node-breaker bus is split.
- **CIM 18:** `SvVoltage` attaches only to a `TopologicalNode`, which holds the bus's own VM/VA.
- **Needed:** none if the split sections are their own `TopologicalNode`s; otherwise a per-node solved voltage.
- **Approximation:** the RAW import lists a given VM/VA on the node's row; the export writes the defaults (CIMHub
  `cimhub_raw` R6, 2026-11-09).
- **Models:** none of the public RAW cases (the hand-built R6 forms atom has one).

## TODO (CIM18 gap): the side of a voltage-controlling winding its controlled bus is on

- **Source:** PSS/E RAW v34 transformer CONTk's sign: positive adjusts the ratio as if bus CONTk is on the winding
  2 or 3 side, negative as if bus |CONTk| is on the winding 1 side. It matters only when the bus is not one of the
  transformer's own (I, J, K).
- **CIM 18:** a `TapChangerControl` names its regulated `Terminal`; a solver infers the direction from the topology,
  and nothing records the source's stated side.
- **Needed:** none if the topology always decides; otherwise a direction flag on `TapChangerControl`.
- **Approximation:** the control regulates bus |CONTk|; the sign is listed on the control row, and the export writes
  CONTk positive (CIMHub `cimhub_raw` R4b, 2026-11-09).
- **Models:** none of the public RAW cases (the hand-built R4b atom has one).

## TODO (CIM18 gap): a FACTS device's series element, UPFC and IPFC

- **Source:** PSS/E RAW v34 FACTS device with J ≠ 0: a series element between buses I and J (MODE 1..8: SSSC,
  UPFC with an active-power bridge TRMX, IPFC master/slave pairs via MNAME), with its setpoints PDES, QDES, SET1,
  SET2, VSREF and limits VTMN, VTMX, VSMX, IMX, LINX.
- **CIM 18:** `StaticSynchronousSeriesCompensator` (SSSC) and `StaticSynchronousCompensator` (shunt) exist as bare
  `FACTSEquipment`; nothing combines a shunt and a series element, or pairs two series elements, and no class holds
  the series setpoints.
- **Needed:** a UPFC / IPFC form, or series-element setpoints on `StaticSynchronousSeriesCompensator`.
- **Approximation:** a series element raises (no case has one); a shunt-only device's series fields are listed on
  its row when not the default (CIMHub `cimhub_raw` P2a, 2026-11-09).
- **Models:** none of the public RAW cases.

## TODO (CIM18 gap): a FACTS shunt's share of a coordinated voltage control

- **Source:** PSS/E RAW v34 FACTS device RMPCT: the percent of the Mvar needed at the regulated bus that the shunt
  element supplies (as switched shunt and WMOD 1 generator RMPCT).
- **CIM 18:** `qPercent` is on `SynchronousMachine` only; `VsConverter` has `qShare`.
- **Needed:** `qPercent` on `RegulatingCondEq` (proposed to the profile owner 2026-11-09, not taken for now).
- **Approximation:** listed on the device's row when not 100 (CIMHub `cimhub_raw` P2a, 2026-11-09).
- **Models:** none of the public RAW cases (the hand-built P2a atom has one).

## TODO (CIM18 gap): a VSC converter's minimum loss and power weighting factor

- **Source:** PSS/E RAW v34 VSC converter MINLOSS (kW) and PWF (the split of a rating violation's reduction between
  P and Q).
- **CIM 18:** `ACDCConverter` has `idleLoss`, `switchingLoss` and `resistiveLoss`, but no floor on the loss and no
  reduction weighting.
- **Needed:** two attributes on `VsConverter`, if solvers need them.
- **Approximation:** listed on the converter's row when not the default (CIMHub `cimhub_raw` P2a, 2026-11-09).
- **Models:** none of the public RAW cases (the hand-built P2a atom has both).

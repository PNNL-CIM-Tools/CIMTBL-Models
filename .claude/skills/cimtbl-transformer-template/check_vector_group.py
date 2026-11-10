"""Read a three-phase tank template's coil pairs back as a vector group.

Usage: python -I check_vector_group.py TEMPLATE.cimtbl [...]   (needs cim-tables installed)

A template has no phases (an instance's TransformerPhaseEnds carry them), so each lug's
phase comes from its designation, the standard labelling: H1/X1/Y1 = A, 2 = B, 3 = C,
0 = N, side H = 1, X = 2, Y = 3 (IEC 1U/1V/1W/1N and 2U/... likewise).

Each TransformerMeshImpedance pairs two coils on one core leg (FromWinding, ToWinding).
A coil's voltage is V(From lug) - V(To lug) at the nominal phasors (A 0, B -120, C +120
degrees, N 0 V), with the side-2 (and side-3) coils rotated by -30 degrees per IEC clock
number. The clock number at which every paired coil lines up with its side-1 coil (same
direction, so same polarity) is the vector group. No such number means a coil pair, a
From/To polarity, or a lug is misread. Only configurations with three side-1 phase lugs
are checked; single-phase and center-tap tanks are skipped.
"""
import cmath
import math
import re
import sys

import cimtables

PHASORS = {'A': cmath.rect(1, 0), 'B': cmath.rect(1, math.radians(-120)), 'C': cmath.rect(1, math.radians(120)), 'N': 0}
ANSI = re.compile(r'([HXY])([0-3])')
IEC = re.compile(r'([123])([UVWN])')


def side_and_phase(designation: str) -> tuple[int, str] | None:
    """(side, phase) from a lug designation, or None if it isn't a standard phase label."""
    if match := ANSI.fullmatch(designation):
        return 'HXY'.index(match[1]) + 1, 'NABC'[int(match[2])]
    if match := IEC.fullmatch(designation):
        return int(match[1]), {'U': 'A', 'V': 'B', 'W': 'C', 'N': 'N'}[match[2]]
    return None


def coil(winding) -> tuple[int, complex]:
    """(side, voltage phasor) of a winding from its From and To lugs."""
    (side, from_phase), (_, to_phase) = (side_and_phase(lug.designation)
                                         for lug in (winding.FromTransformerLug, winding.ToTransformerLug))
    voltage = PHASORS[from_phase] - PHASORS[to_phase]
    if abs(voltage) < 1e-9:
        raise ValueError(f'{winding.mRID}: coil from {from_phase} to {to_phase} has no voltage')
    return side, voltage


def angle(side: int, voltage: complex, clock: int) -> float:
    return math.degrees(cmath.phase(voltage)) + (0 if side == 1 else -30 * clock)


def side_letter(windings, side: int) -> str:
    """D, Y or YN for one side, from its coils (YN when a coil ends on a neutral lug)."""
    phases = {side_and_phase(lug.designation)[1] for w in windings
              for lug in (w.FromTransformerLug, w.ToTransformerLug) if side_and_phase(lug.designation)[0] == side}
    letter = 'YN' if 'N' in phases else 'D'
    return letter if side == 1 else letter.lower()


def check_configuration(configuration) -> None:
    labels = [side_and_phase(lug.designation) for lug in configuration.TransformerLugs]
    if {(1, 'A'), (1, 'B'), (1, 'C')} - set(labels):
        print(f'  {configuration.mRID}: not three-phase, skipped')
        return
    pairs = []
    for winding in configuration.TransformerWinding:
        for mesh in winding.FromMeshImpedance:
            first, second = sorted((mesh.FromWinding, mesh.ToWinding), key=lambda w: coil(w)[0])
            if coil(first)[0] == 1:
                pairs.append((mesh.mRID, first, second))
    clocks = [k for k in range(12)
              if all(abs((angle(*coil(lv), k) - angle(*coil(hv), k) + 180) % 360 - 180) < 1e-6 for _, hv, lv in pairs)]
    print(f'  {configuration.mRID}: {len(pairs)} coil pairs')
    for mesh_mrid, hv, lv in pairs:
        print(f'    {mesh_mrid}: {hv.mRID} at {angle(*coil(hv), 0):7.1f} deg, '
              f'{lv.mRID} at {angle(*coil(lv), 0):7.1f} deg before rotation')
    if len(clocks) != 1:
        print('    FAIL: no single clock number lines every pair up; check the coil pairs, polarity and lugs')
        sys.exit(1)
    windings = [w for _, hv, lv in pairs for w in (hv, lv)]
    print(f'    vector group {side_letter(windings, 1)}{side_letter(windings, 2)}{clocks[0]}')


for template_path in sys.argv[1:]:
    network = cimtables.load_model(template_path)
    print(template_path)
    for configuration in network.graph.get(network.cim.TransformerTankConfiguration, {}).values():
        check_configuration(configuration)

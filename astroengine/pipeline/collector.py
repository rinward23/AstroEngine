# >>> AUTO-GEN BEGIN: pipeline-collector v1.1
from __future__ import annotations
from typing import List

from ..detectors.lunations import find_lunations
from ..detectors.eclipses import find_eclipses
from ..detectors.stations import find_stations
from ..detectors.returns import solar_lunar_returns
from ..detectors.progressions import secondary_progressions
from ..detectors.directions import solar_arc_directions
from ..detectors.progressed_aspects import progressed_natal_aspects
from ..detectors.directed_aspects import solar_arc_natal_aspects
from ..timelords.profections import annual_profections
from ..detectors.common import iso_to_jd


def collect_events(args) -> List[object]:
    ev: List[object] = []
    start_jd = iso_to_jd(args.start_utc)
    end_jd = iso_to_jd(args.end_utc)

    if getattr(args, 'lunations', False):
        ev += find_lunations(start_jd, end_jd)
    if getattr(args, 'eclipses', False):
        ev += find_eclipses(start_jd, end_jd)
    if getattr(args, 'stations', False):
        ev += find_stations(start_jd, end_jd, None)
    if getattr(args, 'returns', False) and getattr(args, 'natal_utc', None):
        ev += solar_lunar_returns(iso_to_jd(args.natal_utc), start_jd, end_jd, getattr(args, 'return_kind', 'solar'))
    if getattr(args, 'progressions', False) and getattr(args, 'natal_utc', None):
        ev += secondary_progressions(args.natal_utc, args.start_utc, args.end_utc)
    if getattr(args, 'directions', False) and getattr(args, 'natal_utc', None):
        ev += solar_arc_directions(args.natal_utc, args.start_utc, args.end_utc)
    if getattr(args, 'profections', False) and getattr(args, 'natal_utc', None) and (args.lat is not None) and (args.lon is not None):
        ev += annual_profections(args.natal_utc, args.start_utc, args.end_utc, args.lat, args.lon)
    if getattr(args, 'prog_aspects', False) and getattr(args, 'natal_utc', None):
        angles = [int(x) for x in getattr(args, 'aspects', '0,60,90,120,180').split(',') if x]
        ev += progressed_natal_aspects(args.natal_utc, args.start_utc, args.end_utc, aspects=angles, orb_deg=getattr(args, 'orb', 1.0))
    if getattr(args, 'dir_aspects', False) and getattr(args, 'natal_utc', None):
        angles = [int(x) for x in getattr(args, 'aspects', '0,60,90,120,180').split(',') if x]
        ev += solar_arc_natal_aspects(args.natal_utc, args.start_utc, args.end_utc, aspects=angles, orb_deg=getattr(args, 'orb', 1.0))
    return ev
# >>> AUTO-GEN END: pipeline-collector v1.1

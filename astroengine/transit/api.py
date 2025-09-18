# >>> AUTO-GEN BEGIN: TransitAPI v1.0
from dataclasses import dataclass
from typing import Iterable, Literal, Optional, Sequence

AspectName = Literal[
    "conjunction","opposition","square","trine","sextile",
    "quincunx","semisextile","semisquare","sesquisquare"
]

@dataclass
class TransitScanConfig:
    natal_id: str
    start_iso: str
    end_iso: str
    step: str = "1h"
    aspects: Sequence[AspectName] = ("conjunction","opposition","square","trine","sextile")
    include_declination: bool = False
    include_antiscia: bool = False
    topocentric: bool = False
    site_lat: Optional[float] = None
    site_lon: Optional[float] = None
    site_elev_m: float = 0.0
    ephemeris_profile: str = "default"
    orb_policy: str = "default"
    severity_profile: str = "standard"
    family_cap_per_day: int = 3

@dataclass
class TransitEvent:
    t_exact: str
    t_applying: bool
    partile: bool
    aspect: AspectName
    transiting_body: str
    natal_point: str
    orb_deg: float
    severity: float
    family: str
    lon_transit: float
    lon_natal: float
    decl_transit: Optional[float] = None
    notes: Optional[str] = None

class TransitEngine:
    """Facade: ephemeris → detect → refine → score. See detectors/refine modules."""
    def __init__(self, engine_config): ...
    def scan(self, cfg: TransitScanConfig) -> Iterable[TransitEvent]: ...
# >>> AUTO-GEN END: TransitAPI v1.0

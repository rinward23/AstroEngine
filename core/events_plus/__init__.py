
"""Event detectors exposed for API compatibility."""


from .detectors import (
    CombustCfg,
    EventInterval,
    detect_combust_cazimi,
    detect_returns,
    detect_voc_moon,
)

__all__ = [
    "CombustCfg",
    "EventInterval",
    "detect_combust_cazimi",
    "detect_returns",
    "detect_voc_moon",

]

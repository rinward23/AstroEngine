"""Orb and severity profiles for transit evaluations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple

if TYPE_CHECKING:
    from .api import TransitEvent

# <<< AUTO-GEN START: Profiles v1.0 >>>
DECLINATION_ORB = 0.5
PARTILE_ORB = 0.1667


class OrbPolicy:
    """Callable policy that resolves allowable orbs for aspects."""

    MINOR_ASPECTS = {
        "semisextile",
        "semisquare",
        "sesquisquare",
        "quincunx",
    }

    LUMINARIES = {"sun", "moon"}
    PERSONAL = {"mercury", "venus", "mars"}
    SOCIAL = {"jupiter", "saturn"}
    OUTER = {"uranus", "neptune", "pluto"}
    NODES = {
        "mean node",
        "true node",
        "north node",
        "south node",
        "node",
    }

    DEFAULT_ORBS = {
        "luminary": 8.0,
        "personal": 6.0,
        "social": 5.0,
        "outer": 4.0,
        "node": 4.0,
        "minor": 2.0,
    }

    def __call__(self, transiting_body: str, natal_point: str, aspect: str) -> float:
        aspect_key = aspect.lower()
        if aspect_key in self.MINOR_ASPECTS:
            return self.DEFAULT_ORBS["minor"]
        category = self._classify_body(transiting_body)
        return self.DEFAULT_ORBS.get(category, self.DEFAULT_ORBS["personal"])

    def _classify_body(self, body: str) -> str:
        key = body.lower()
        if key in self.LUMINARIES:
            return "luminary"
        if key in self.PERSONAL:
            return "personal"
        if key in self.SOCIAL:
            return "social"
        if key in self.OUTER:
            return "outer"
        if key in self.NODES:
            return "node"
        return "personal"


class SeverityModel:
    """Score transit strength using quadratic falloff."""

    ASPECT_WEIGHTS = {
        "conjunction": 1.0,
        "opposition": 1.0,
        "square": 0.95,
        "trine": 0.75,
        "sextile": 0.60,
        "semisextile": 0.5,
        "semisquare": 0.45,
        "sesquisquare": 0.5,
        "quincunx": 0.55,
    }

    BODY_WEIGHTS = {
        "luminary": 1.0,
        "personal": 0.95,
        "social": 1.0,
        "outer": 1.05,
        "node": 0.90,
    }

    def __init__(
        self,
        aspect_weights: Dict[str, float] | None = None,
        body_weights: Dict[str, float] | None = None,
    ) -> None:
        self.aspect_weights = aspect_weights or dict(self.ASPECT_WEIGHTS)
        self.body_weights = body_weights or dict(self.BODY_WEIGHTS)

    def score_from_diff(
        self,
        diff_deg: float,
        orb_allow: float,
        aspect: str,
        body: str,
        partile: bool,
    ) -> float:
        if orb_allow <= 0:
            return 0.0
        diff = abs(diff_deg)
        if diff > orb_allow:
            return 0.0
        closeness = 1.0 - (diff / orb_allow) ** 2
        closeness = max(closeness, 0.0)
        aspect_weight = self.aspect_weights.get(aspect.lower(), 0.5)
        body_weight = self.body_weights.get(self._classify_body(body), 1.0)
        score = closeness * aspect_weight * body_weight
        if partile:
            score *= 1.1
            score = min(score, 1.2)
        return max(0.0, min(score, 1.0))

    def score_event(self, event: TransitEvent, orb_policy: OrbPolicy) -> float:
        orb_allow = orb_policy(event.transiting_body, event.natal_point, event.aspect)
        partile = event.orb_deg <= PARTILE_ORB
        return self.score_from_diff(
            event.orb_deg,
            orb_allow,
            event.aspect,
            event.transiting_body,
            partile,
        )

    def _classify_body(self, body: str) -> str:
        key = body.lower()
        if key in OrbPolicy.LUMINARIES:
            return "luminary"
        if key in OrbPolicy.PERSONAL:
            return "personal"
        if key in OrbPolicy.SOCIAL:
            return "social"
        if key in OrbPolicy.OUTER:
            return "outer"
        if key in OrbPolicy.NODES:
            return "node"
        return "personal"


def build_default_profiles() -> Tuple[OrbPolicy, SeverityModel]:
    """Factory returning the default orb policy and severity model."""

    return OrbPolicy(), SeverityModel()


__all__ = [
    "DECLINATION_ORB",
    "PARTILE_ORB",
    "OrbPolicy",
    "SeverityModel",
    "build_default_profiles",
]
# <<< AUTO-GEN END: Profiles v1.0 >>>

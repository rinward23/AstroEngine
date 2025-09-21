"""Compatibility layer for :mod:`astroengine.core.domains` plus domain rollups."""

# >>> AUTO-GEN BEGIN: AE Domain Scoring v1.0
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import json
from pathlib import Path


@dataclass
class SubchannelScore:
    id: str
    valence: str  # 'positive' | 'negative'
    score: float = 0.0


@dataclass
class ChannelScore:
    id: str
    sub: Dict[str, SubchannelScore] = field(default_factory=dict)

    @property
    def score(self) -> float:
        pos = self.sub.get("positive")
        neg = self.sub.get("negative")
        return (pos.score if pos else 0.0) - (neg.score if neg else 0.0)


@dataclass
class DomainScore:
    id: str
    channels: Dict[str, ChannelScore] = field(default_factory=dict)

    @property
    def score(self) -> float:
        return sum(ch.score for ch in self.channels.values())


# Load profiles
_DEF_TREE = Path(__file__).resolve().parent.parent / "profiles" / "domain_tree.json"
_DEF_MAP = Path(__file__).resolve().parent.parent / "profiles" / "domain_mapping.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_text().splitlines()
    payload = "\n".join(line for line in raw if not line.strip().startswith("#"))
    return json.loads(payload)


def _make_empty_scores(tree: dict) -> Dict[str, DomainScore]:
    out: Dict[str, DomainScore] = {}
    for d in tree.get("domains", []):
        dd = DomainScore(id=d["id"])
        for ch in d.get("channels", []):
            cc = ChannelScore(id=ch["id"])
            for sub in ch.get("subchannels", []):
                cc.sub[sub["id"]] = SubchannelScore(id=sub["id"], valence=sub.get("valence", "positive"))
            dd.channels[cc.id] = cc
        out[dd.id] = dd
    return out


def _valence_for(aspect_name: str, moving: str, mapping: dict) -> str:
    v = mapping.get("aspect_valence", {}).get(aspect_name, "neutral")
    if v == "neutral" and aspect_name == "conjunction":
        ov = mapping.get("conjunction_valence_overrides", {})
        return ov.get(moving.lower(), "neutral")
    return v


def _channel_weights_for(planet: str, mapping: dict) -> Dict[str, float]:
    return {k: float(v) for k, v in mapping.get("planet_channels", {}).get(planet.lower(), {}).items()}


@dataclass
class EventLike:
    kind: str          # e.g., 'aspect_trine', 'decl_parallel', 'antiscia'
    when_iso: str
    moving: str
    target: str
    orb_abs: float
    applying_or_separating: str
    score: float


def rollup_domain_scores(events: List[EventLike], *, tree_path: str | None = None, mapping_path: str | None = None) -> Dict[str, DomainScore]:
    tree = _load_json(Path(tree_path) if tree_path else _DEF_TREE)
    mapping = _load_json(Path(mapping_path) if mapping_path else _DEF_MAP)
    scores = _make_empty_scores(tree)

    for e in events:
        # Determine aspect family name if applicable
        fam = e.kind.split("aspect_")[-1] if e.kind.startswith("aspect_") else None
        val = _valence_for(fam, e.moving, mapping) if fam else "neutral"

        # Planet-driven channel weights: combine moving + target (average)
        w_m = _channel_weights_for(e.moving, mapping)
        w_t = _channel_weights_for(e.target, mapping)
        # Merge and average common keys
        keys = set(w_m) | set(w_t)
        combined: Dict[str, float] = {}
        for k in keys:
            combined[k] = 0.5 * w_m.get(k, 0.0) + 0.5 * w_t.get(k, 0.0)

        # Distribute to channels and subchannels by valence
        for key, w in combined.items():
            if w <= 0:
                continue
            dom_id, ch_id = key.split(":", 1)
            dom = scores.get(dom_id)
            if not dom:
                continue
            ch = dom.channels.get(ch_id)
            if not ch:
                continue
            if val == "negative":
                ch.sub.get("negative").score += e.score * w
            elif val == "positive":
                ch.sub.get("positive").score += e.score * w
            else:
                # neutral: split 50/50
                ch.sub.get("positive").score += 0.5 * e.score * w
                ch.sub.get("negative").score += 0.5 * e.score * w

    return scores
# >>> AUTO-GEN END: AE Domain Scoring v1.0

from .core.domains import (
    DEFAULT_HOUSE_DOMAIN_WEIGHTS,
    DEFAULT_PLANET_DOMAIN_WEIGHTS,
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    DomainResolution,
    DomainResolver,
    natal_domain_factor,
)

__all__ = [
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "DEFAULT_PLANET_DOMAIN_WEIGHTS",
    "DEFAULT_HOUSE_DOMAIN_WEIGHTS",
    "DomainResolver",
    "DomainResolution",
    "natal_domain_factor",
    "SubchannelScore",
    "ChannelScore",
    "DomainScore",
    "rollup_domain_scores",
]

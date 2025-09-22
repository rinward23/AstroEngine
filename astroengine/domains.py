"""Domain aggregation helpers exposed at the package root."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .core.domains import (
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    DomainResolution,
    DomainResolver,
    natal_domain_factor,
)
from .infrastructure.paths import profiles_dir

__all__ = [
    "DOMAINS",
    "ELEMENTS",
    "ZODIAC_ELEMENT_MAP",
    "DomainResolver",
    "DomainResolution",
    "natal_domain_factor",
    "rollup_domain_scores",
    "DomainScore",
    "ChannelScore",
    "SubchannelScore",
]


@dataclass
class SubchannelScore:
    id: str
    valence: str
    score: float = 0.0


@dataclass
class ChannelScore:
    id: str
    sub: Dict[str, SubchannelScore] = field(default_factory=dict)

    @property
    def score(self) -> float:
        positive = self.sub.get("positive")
        negative = self.sub.get("negative")
        pos_val = positive.score if positive else 0.0
        neg_val = negative.score if negative else 0.0
        return pos_val - neg_val


@dataclass
class DomainScore:
    id: str
    channels: Dict[str, ChannelScore] = field(default_factory=dict)

    @property
    def score(self) -> float:
        return sum(ch.score for ch in self.channels.values())


_DEF_TREE = profiles_dir() / "domain_tree.json"
_DEF_MAP = profiles_dir() / "domain_mapping.json"


def _load_json(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    payload = "\n".join(line for line in lines if not line.strip().startswith("#"))
    return json.loads(payload) if payload.strip() else {}


def _make_empty_scores(tree: Mapping[str, Any]) -> Dict[str, DomainScore]:
    result: Dict[str, DomainScore] = {}
    for domain_entry in tree.get("domains", []):
        domain = DomainScore(id=str(domain_entry.get("id")))
        for channel_entry in domain_entry.get("channels", []):
            channel = ChannelScore(id=str(channel_entry.get("id")))
            for sub_entry in channel_entry.get("subchannels", []):
                sub = SubchannelScore(
                    id=str(sub_entry.get("id")),
                    valence=str(sub_entry.get("valence", "positive")),
                )
                channel.sub[sub.id] = sub
            domain.channels[channel.id] = channel
        result[domain.id] = domain
    return result


def _channel_weights_for(body: str, mapping: Mapping[str, Any]) -> Dict[str, float]:
    planet_map = mapping.get("planet_channels", {})
    return {
        key: float(value)
        for key, value in planet_map.get((body or "").lower(), {}).items()
    }


def _event_attr(event: object, key: str) -> Any:
    if isinstance(event, Mapping):
        return event.get(key)
    return getattr(event, key, None)


def _aspect_valence(event: object, mapping: Mapping[str, Any]) -> str:
    kind = _event_attr(event, "kind") or ""
    if kind.startswith("aspect_"):
        aspect = kind.split("_", 1)[1]
        if aspect == "conjunction":
            moving = (_event_attr(event, "moving") or "").lower()
            overrides = mapping.get("conjunction_valence_overrides", {})
            return str(overrides.get(moving, mapping.get("aspect_valence", {}).get(aspect, "neutral")))
        return str(mapping.get("aspect_valence", {}).get(aspect, "neutral"))
    return "neutral"


def rollup_domain_scores(
    events: Iterable[object],
    *,
    tree_path: str | Path | None = None,
    mapping_path: str | Path | None = None,
) -> Dict[str, DomainScore]:
    tree = _load_json(Path(tree_path) if tree_path else _DEF_TREE)
    mapping = _load_json(Path(mapping_path) if mapping_path else _DEF_MAP)
    scores = _make_empty_scores(tree)

    for event in events:
        moving = _event_attr(event, "moving")
        target = _event_attr(event, "target")
        if not moving and not target:
            continue

        base_weights: Dict[str, float] = {}
        for body in (moving, target):
            if not body:
                continue
            for key, value in _channel_weights_for(str(body), mapping).items():
                base_weights[key] = base_weights.get(key, 0.0) + float(value)

        if not base_weights:
            continue

        valence = _aspect_valence(event, mapping)
        weight_multiplier = float(_event_attr(event, "score") or 1.0)

        for channel_key, weight in base_weights.items():
            try:
                domain_id, channel_id = channel_key.split(":", 1)
            except ValueError:
                continue
            domain = scores.get(domain_id)
            if not domain:
                continue
            channel = domain.channels.get(channel_id)
            if not channel:
                continue

            effective = float(weight) * weight_multiplier
            if valence == "negative":
                target_sub = channel.sub.get("negative")
                if target_sub:
                    target_sub.score += effective
            elif valence == "positive":
                target_sub = channel.sub.get("positive")
                if target_sub:
                    target_sub.score += effective
            else:
                pos = channel.sub.get("positive")
                neg = channel.sub.get("negative")
                if pos:
                    pos.score += effective * 0.5
                if neg:
                    neg.score += effective * 0.5

    return scores

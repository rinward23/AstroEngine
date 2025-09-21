# >>> AUTO-GEN BEGIN: AE Domain Scoring v1.1
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
import json
from pathlib import Path


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


_DEF_TREE = Path(__file__).resolve().parent.parent / "profiles" / "domain_tree.json"
_DEF_MAP = Path(__file__).resolve().parent.parent / "profiles" / "domain_mapping.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


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


def _channel_weights_for(planet: str, mapping: dict) -> Dict[str, float]:
    return {k: float(v) for k, v in mapping.get("planet_channels", {}).get(planet.lower(), {}).items()}


def rollup_domain_scores(events: List[object], *, tree_path: str | None = None, mapping_path: str | None = None) -> Dict[str, DomainScore]:
    tree = _load_json(Path(tree_path) if tree_path else _DEF_TREE)
    mapping = _load_json(Path(mapping_path) if mapping_path else _DEF_MAP)
    scores = _make_empty_scores(tree)

    for e in events:
        # Planet-driven channel weights: combine moving + target (average)
        w_m = _channel_weights_for(e.moving, mapping)
        w_t = _channel_weights_for(e.target, mapping)
        keys = set(w_m) | set(w_t)
        combined: Dict[str, float] = {k: 0.5 * w_m.get(k, 0.0) + 0.5 * w_t.get(k, 0.0) for k in keys}

        # Decide how to push score based on event.valence
        if getattr(e, "valence", "neutral") == "positive":
            pos_share, neg_share = 1.0, 0.0
        elif getattr(e, "valence", "neutral") == "negative":
            pos_share, neg_share = 0.0, 1.0
        else:
            # Neutral: amplify/attenuate already baked into valence_factor -> use 50/50 split
            pos_share, neg_share = 0.5, 0.5

        magnitude = float(getattr(e, "score", 0.0)) * float(getattr(e, "valence_factor", 1.0))

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
            pos_bucket = ch.sub.get("positive")
            neg_bucket = ch.sub.get("negative")
            if pos_bucket:
                pos_bucket.score += magnitude * w * pos_share
            if neg_bucket:
                neg_bucket.score += magnitude * w * neg_share

    return scores
# >>> AUTO-GEN END: AE Domain Scoring v1.1


import json
from pathlib import Path


@dataclass
class SubchannelScore:
    id: str

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



    tree = _load_json(Path(tree_path) if tree_path else _DEF_TREE)
    mapping = _load_json(Path(mapping_path) if mapping_path else _DEF_MAP)
    scores = _make_empty_scores(tree)

    for e in events:

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


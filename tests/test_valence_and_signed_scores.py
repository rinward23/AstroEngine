# >>> AUTO-GEN BEGIN: AE Valence & Signed Score Tests v1.0
import importlib.util
from pathlib import Path


def _load_valence():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "astroengine" / "valence.py"
    spec = importlib.util.spec_from_file_location("astroengine.valence", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


combine_valence = _load_valence().combine_valence


def test_valence_priority_aspect_over_bodies():
    # Square is negative regardless of benefic bodies
    val, factor = combine_valence(moving="venus", target="jupiter", contact_kind="aspect_square", aspect_name="square")
    assert val == "negative" and factor > 0


def test_bodies_vote_when_aspect_neutral():
    # Conjunction neutral -> bodies decide; Moon(+), Saturn(-) => neutral
    val, factor = combine_valence(moving="moon", target="saturn", contact_kind="aspect_conjunction", aspect_name="conjunction")
    assert val == "neutral" and factor > 0


def test_neutral_amplify_vs_attenuate():
    # Conjunction uses neutral_mode=amplify -> factor amplified
    val1, f1 = combine_valence(moving="mercury", target="mercury", contact_kind="aspect_conjunction", aspect_name="conjunction")
    # Quincunx neutral attenuate -> factor reduced
    val2, f2 = combine_valence(moving="neptune", target="neptune", contact_kind="aspect_quincunx", aspect_name="quincunx")
    assert val1 == "neutral" and val2 == "neutral" and f1 > f2
# >>> AUTO-GEN END: AE Valence & Signed Score Tests v1.0

import pytest

from astroengine.utils import target_frames


def test_expand_targets_handles_aliases_and_deduplicates() -> None:
    frames = ["natal", "points"]
    bodies = ["Sun", "points:Fortune", "Sun", "natal_Mars", "  "]

    expanded = target_frames.expand_targets(frames, bodies)

    assert expanded == [
        "natal_Sun",
        "points_Sun",
        "points_Fortune",
        "natal_Mars",
    ]
    # ``Sun`` is only expanded once per frame even when repeated.
    assert expanded.count("natal_Sun") == 1
    assert expanded.count("points_Sun") == 1


def test_expand_targets_uses_default_frames_when_none_provided() -> None:
    expanded = target_frames.expand_targets([], ["Moon"])
    assert expanded == ["natal_Moon"]


@pytest.mark.parametrize(
    "frames, expected",
    [
        (None, {"natal": target_frames.TARGET_FRAME_BODIES["natal"]}),
        (["natal", "custom", "broken"], {"natal": target_frames.TARGET_FRAME_BODIES["natal"], "custom": ("Alpha",)}),
    ],
)
def test_frame_body_options_filters_unknown_or_invalid_frames(monkeypatch, frames, expected):
    original = target_frames.TARGET_FRAME_BODIES.copy()
    monkeypatch.setattr(
        target_frames,
        "TARGET_FRAME_BODIES",
        {**original, "custom": ("Alpha",), "broken": None},
        raising=False,
    )

    try:
        options = target_frames.frame_body_options(frames)
        assert options == expected
    finally:
        monkeypatch.setattr(target_frames, "TARGET_FRAME_BODIES", original, raising=False)

from ui.streamlit.utils import hits_to_dataframe


def test_hits_to_dataframe_shapes():
    hits = [{"a": "Mars", "b": "Venus", "aspect": "sextile", "exact_time": "2025-02-14T08:12:00Z", "orb": 0.12, "orb_limit": 3.0, "severity": 0.66}]
    df = hits_to_dataframe(hits)
    assert list(df.columns)[:3] == ["a", "b", "pair"]
    assert df.iloc[0]["pair"].startswith("Mars")


def test_hits_to_dataframe_missing_numeric_columns():
    hits = [{"a": "Sun", "b": "Moon", "aspect": "conjunction", "exact_time": "2025-02-14T08:12:00Z"}]
    df = hits_to_dataframe(hits)
    assert df["severity"].isna().all()
    assert df["orb"].isna().all()
    assert df["orb_limit"].isna().all()

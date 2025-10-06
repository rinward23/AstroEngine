from __future__ import annotations

from typing import Any

import pandas as pd

PAIR_SEP = "–"

def hits_to_dataframe(hits: list[dict[str, Any]]) -> pd.DataFrame:
    """Normalize /aspects/search hits to a DataFrame.
    Expected keys: a,b,aspect,exact_time,orb,orb_limit,severity
    """
    if not hits:
        return pd.DataFrame(columns=["a","b","pair","aspect","exact_time","orb","orb_limit","severity"])  # noqa: E501
    df = pd.DataFrame(hits)
    if "pair" not in df.columns:
        df["pair"] = df.apply(lambda r: f"{r['a']}{PAIR_SEP}{r['b']}", axis=1)
    # Ensure types
    df["exact_time"] = pd.to_datetime(df["exact_time"], utc=True)
    for col in ["orb", "orb_limit", "severity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.Series(data=pd.NA, index=df.index, dtype="Float64")
    desired = ["a", "b", "pair", "aspect", "exact_time", "orb", "orb_limit", "severity"]
    ordered = [c for c in desired if c in df.columns] + [c for c in df.columns if c not in desired]
    df = df.loc[:, ordered]
    return df

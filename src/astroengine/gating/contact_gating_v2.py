from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import pandas as pd


@dataclass
class Condition:
    """Column comparison used in gating rules."""

    column: str
    op: str
    value: object

    def matches(self, frame: pd.DataFrame) -> pd.Series:
        if self.column not in frame.columns:
            raise KeyError(f"Column '{self.column}' required by gating condition is missing from contacts table")

        series = frame[self.column]
        if self.op == "eq":
            return series == self._cast(series)
        if self.op == "neq":
            return series != self._cast(series)
        if self.op == "lt":
            return series < self._cast(series)
        if self.op == "lte":
            return series <= self._cast(series)
        if self.op == "gt":
            return series > self._cast(series)
        if self.op == "gte":
            return series >= self._cast(series)
        raise ValueError(f"Unsupported condition operator '{self.op}'")

    def _cast(self, series: pd.Series):
        if pd.api.types.is_bool_dtype(series):
            if isinstance(self.value, str):
                return self.value.lower() == "true"
            return bool(self.value)
        if pd.api.types.is_numeric_dtype(series):
            return float(self.value)
        return self.value


@dataclass
class Rule:
    rule_id: str
    rule_type: str
    factor: float = 1.0
    conditions: Sequence[Condition] = field(default_factory=list)
    description: str | None = None

    def applies(self, frame: pd.DataFrame) -> pd.Series:
        mask = pd.Series(True, index=frame.index, dtype="bool")
        for condition in self.conditions:
            mask &= condition.matches(frame)
        return mask


@dataclass
class ContactGateResult:
    state_table: pd.DataFrame
    summary: Dict[str, int]


class ContactGatingV2:
    """Evaluate contact gating rules and persist state transitions."""

    def __init__(self, rules: Dict[str, Iterable[Dict[str, object]]], output_path: Path):
        self.hard_vetoes = self._build_rules(rules.get("hard_vetoes", []), "hard_veto")
        self.dampeners = self._build_rules(rules.get("dampeners", []), "dampener")
        self.boosters = self._build_rules(rules.get("boosters", []), "booster")
        self.output_path = output_path

    @staticmethod
    def _build_rules(raw_rules: Iterable[Dict[str, object]], rule_type: str) -> List[Rule]:
        rules: List[Rule] = []
        for raw in raw_rules:
            conditions = [
                Condition(
                    column=str(item["column"]),
                    op=str(item["op"]),
                    value=item.get("value"),
                )
                for item in raw.get("conditions", [])
            ]
            rules.append(
                Rule(
                    rule_id=str(raw.get("id")),
                    rule_type=rule_type,
                    factor=float(raw.get("factor", 0.0 if rule_type == "hard_veto" else 1.0)),
                    description=raw.get("description"),
                    conditions=conditions,
                )
            )
        return rules

    def process(self, contacts: pd.DataFrame) -> ContactGateResult:
        working = contacts.copy()
        if "base_score" not in working.columns:
            working["base_score"] = 1.0
        working["multiplier"] = 1.0
        working["state"] = "open"
        working["rules_applied"] = [[] for _ in range(len(working))]

        for rule in self.hard_vetoes:
            mask = rule.applies(working)
            if mask.any():
                working.loc[mask, "state"] = "vetoed"
                working.loc[mask, "multiplier"] = 0.0
                self._append_reason(working, mask, f"veto:{rule.rule_id}")

        active_mask = working["state"] != "vetoed"
        for rule in self.dampeners:
            mask = rule.applies(working) & active_mask
            if mask.any():
                working.loc[mask, "state"] = "dampened"
                working.loc[mask, "multiplier"] *= rule.factor
                self._append_reason(working, mask, f"dampener:{rule.rule_id}")

        for rule in self.boosters:
            mask = rule.applies(working) & active_mask
            if mask.any():
                states = working.loc[mask, "state"].where(lambda s: s != "open", other="boosted")
                working.loc[mask, "state"] = states
                working.loc[mask, "multiplier"] *= rule.factor
                self._append_reason(working, mask, f"booster:{rule.rule_id}")

        working["final_score"] = working["base_score"] * working["multiplier"]

        summary = working["state"].value_counts().to_dict()
        self._write_output(working)
        return ContactGateResult(working, summary)

    def _write_output(self, frame: pd.DataFrame) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(self.output_path, index=False)

    @staticmethod
    def _append_reason(frame: pd.DataFrame, mask: pd.Series, reason: str) -> None:
        for idx in frame.index[mask]:
            reasons = list(frame.at[idx, "rules_applied"])
            reasons.append(reason)
            frame.at[idx, "rules_applied"] = reasons


__all__ = ["ContactGatingV2", "ContactGateResult"]

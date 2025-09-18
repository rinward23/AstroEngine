from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Tuple

import pandas as pd
import yaml

from ..connectors import ConnectorRegistry, DEFAULT_CONNECTORS
from ..directions_progressions import (
    PrimaryDirectionCalculator,
    SecondaryProgressionCalculator,
)
from ..gating.contact_gating_v2 import ContactGatingV2, ContactGateResult
from ..synastry_composite import CompositeTransitPipeline, CompositeTransitResult
from ..timelords import ProfectionCalculator, ZodiacalReleasingCalculator


@dataclass
class EngineRequest:
    module: str
    submodule: str
    channel: str
    subchannel: str
    data: Mapping[str, Any] | None = None
    datasets: Tuple[Mapping[str, Any], ...] | None = None


class AstroEngine:
    """Runtime orchestrator that loads modules based on the ruleset configuration."""

    def __init__(
        self,
        ruleset_path: Path,
        *,
        output_root: Path | None = None,
        connectors: ConnectorRegistry | None = None,
    ) -> None:
        self.ruleset_path = Path(ruleset_path)
        self.ruleset = self._load_ruleset(self.ruleset_path)
        self.output_root = Path(output_root) if output_root else Path('.')
        self.connectors = connectors or DEFAULT_CONNECTORS
        self._registry = self._index_submodules(self.ruleset.get("modules", {}))

    @staticmethod
    def _load_ruleset(path: Path) -> Mapping[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def _index_submodules(self, modules: Mapping[str, Any]) -> Dict[Tuple[str, str], Mapping[str, Any]]:
        registry: Dict[Tuple[str, str], Mapping[str, Any]] = {}
        for module_name, module_cfg in modules.items():
            for submodule_name, submodule_cfg in module_cfg.get("submodules", {}).items():
                registry[(module_name, submodule_name)] = submodule_cfg
        return registry

    def run(self, request: EngineRequest | Mapping[str, Any]) -> Any:
        payload = EngineRequest(**request) if isinstance(request, Mapping) else request
        submodule_cfg = self._registry[(payload.module, payload.submodule)]
        channel_cfg = self._resolve_channel(submodule_cfg, payload.channel, payload.subchannel)
        resolved_data = self._prepare_data(payload)

        if payload.module == "gating" and payload.submodule == "contact_gating_v2":
            return self._run_contact_gating(submodule_cfg, channel_cfg, resolved_data)
        if payload.module == "timelords":
            return self._run_timelords(channel_cfg, resolved_data)
        if payload.module == "directions_progressions":
            return self._run_directions(submodule_cfg, channel_cfg, resolved_data)
        if payload.module == "synastry_composite":
            return self._run_synastry(channel_cfg, resolved_data)
        raise KeyError(f"Unsupported module '{payload.module}'")

    def _prepare_data(self, request: EngineRequest) -> MutableMapping[str, Any]:
        resolved: MutableMapping[str, Any] = {}
        if request.datasets:
            for entry in request.datasets:
                connector_name = entry["connector"]
                alias = entry["alias"]
                location = Path(entry["path"])
                loader = self.connectors.resolve(connector_name)
                resolved[alias] = loader(location)
        if request.data:
            resolved.update(request.data)
        return resolved

    @staticmethod
    def _resolve_channel(submodule_cfg: Mapping[str, Any], channel: str, subchannel: str) -> Mapping[str, Any]:
        channels = submodule_cfg.get("channels", {})
        channel_cfg = channels[channel]
        subchannel_cfg = channel_cfg.get("subchannels", {})[subchannel]
        return subchannel_cfg

    def _run_contact_gating(
        self,
        submodule_cfg: Mapping[str, Any],
        channel_cfg: Mapping[str, Any],
        data: Mapping[str, Any],
    ) -> ContactGateResult:
        output_rel = submodule_cfg.get("outputs", {}).get("state_table", "tables/contact_gate_states.parquet")
        output_path = (self.output_root / output_rel).resolve()
        contacts = self._ensure_dataframe(data.get("contacts"), "contacts")
        gating = ContactGatingV2(channel_cfg, output_path)
        return gating.process(contacts)

    def _run_timelords(self, channel_cfg: Mapping[str, Any], data: Mapping[str, Any]) -> Dict[str, pd.DataFrame]:
        results: Dict[str, pd.DataFrame] = {}
        if "base_periods" in channel_cfg:
            calculator = ZodiacalReleasingCalculator(channel_cfg["base_periods"])
            start_sign = data["start_sign"]
            start_date = data["start_date"]
            spans = data.get("spans", 4)
            results["zodiacal_releasing"] = calculator.compute(start_sign, start_date, spans)
        if "zodiac_sequence" in channel_cfg:
            calculator = ProfectionCalculator(channel_cfg["zodiac_sequence"])
            ascendant_sign = data["ascendant_sign"]
            years = data.get("years", 12)
            results["profections"] = calculator.tabulate(ascendant_sign, years)
        return results

    def _run_directions(
        self,
        submodule_cfg: Mapping[str, Any],
        channel_cfg: Mapping[str, Any],
        data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        if "aspects" in channel_cfg:
            calculator = PrimaryDirectionCalculator(
                channel_cfg["aspects"],
                channel_cfg.get("orb", 1.0),
                channel_cfg.get("rate_degrees_per_year", 1.0),
            )
            positions = data["positions"]
            pairs = data.get("pairs", [])
            results["primary_directions"] = calculator.compute(positions, pairs)
        if "motion_rate_degrees_per_year" in channel_cfg:
            calculator = SecondaryProgressionCalculator(channel_cfg["motion_rate_degrees_per_year"])
            positions = data["positions"]
            years = data.get("years", range(0, 3))
            results["secondary_progressions"] = calculator.tabulate(positions, years)
        return results

    def _run_synastry(self, channel_cfg: Mapping[str, Any], data: Mapping[str, Any]) -> CompositeTransitResult:
        pipeline = CompositeTransitPipeline(channel_cfg["orb"], channel_cfg.get("tracked_points", []))
        natal_a = data["natal_a"]
        natal_b = data["natal_b"]
        transits = data["transits"]
        return pipeline.run(natal_a, natal_b, transits)

    @staticmethod
    def _ensure_dataframe(value: Any, name: str) -> pd.DataFrame:
        if isinstance(value, pd.DataFrame):
            return value
        raise TypeError(f"Expected pandas.DataFrame for '{name}', received {type(value)!r}")


__all__ = ["AstroEngine", "EngineRequest"]

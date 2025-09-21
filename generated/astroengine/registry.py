# >>> AUTO-GEN BEGIN: registry loader v1.0
from __future__ import annotations
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "registry"

class Registry:
    """Loads YAML registries. Units: degrees for angles."""
    def __init__(self):
        self.aspects = self._load_yaml(REG / "aspects.yaml").get("aspects", [])
        self.orbs = self._load_yaml(REG / "orbs_policy.yaml")
        self.domains = self._load_yaml(REG / "domains.yaml")
        self.plugins = self._load_yaml(REG / "plugins.yaml").get("plugins", [])

    @staticmethod
    def _load_yaml(p: Path):
        return yaml.safe_load(p.read_text()) if p.exists() else {}

REGISTRY = Registry()
# >>> AUTO-GEN END: registry loader v1.0

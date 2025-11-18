from importlib import util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate.py"


def load_module():
    spec = util.spec_from_file_location("sdk_generator", SCRIPT_PATH)
    module = util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def test_generator_records_schema_metadata():
    module = load_module()
    repo_root = Path(__file__).resolve().parents[3]
    schema_path = (repo_root / "openapi" / "v1.0.json").resolve()
    metadata = module.generate(schema_path)
    assert metadata["schema_version"] == "1.0.0"
    assert len(metadata["schema_hash"]) == 64
    assert "datasets" in metadata

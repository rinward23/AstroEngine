import sys
from types import ModuleType

from importlib.metadata import PackageNotFoundError

from astroengine.utils.dependencies import DependencySpec, inspect_dependencies


def test_inspect_dependencies_pass() -> None:
    spec = DependencySpec("packaging>=20", min_version="20")
    status = inspect_dependencies([spec])[0]

    assert status.status == "PASS"
    data = status.data()
    assert data["requirement"].startswith("packaging")
    assert "version" in status.detail


def test_inspect_dependencies_optional_missing() -> None:
    spec = DependencySpec(
        "astroengine-missing-dep",
        import_name="astroengine_missing_dep",
        required=False,
    )
    status = inspect_dependencies([spec])[0]

    assert status.status == "WARN"
    assert "import failed" in status.detail
    assert status.data()["required"] is False


def test_inspect_dependencies_missing_distribution_required(monkeypatch) -> None:
    module_name = "astroengine.tests_required_module"
    fake_module = ModuleType(module_name)
    fake_module.__version__ = "1.0"
    monkeypatch.setitem(sys.modules, module_name, fake_module)

    def _raise_package_not_found(name: str) -> str:
        raise PackageNotFoundError(name)

    dependencies_module = sys.modules["astroengine.utils.dependencies"]
    monkeypatch.setattr(dependencies_module.metadata, "version", _raise_package_not_found)

    spec = DependencySpec("astroengine-required-dep", import_name=module_name)
    status = inspect_dependencies([spec])[0]

    assert status.status == "FAIL"
    assert "distribution metadata" in status.detail
    assert status.error.startswith("PackageNotFoundError")

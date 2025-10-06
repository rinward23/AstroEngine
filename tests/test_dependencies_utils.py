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

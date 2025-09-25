# >>> AUTO-GEN BEGIN: test_maint v1.0
def test_maint_import_and_help():
    import importlib

    import astroengine.maint as _  # noqa: F401

    module = importlib.import_module("astroengine.maint")
    assert hasattr(module, "main")


# >>> AUTO-GEN END: test_maint v1.0

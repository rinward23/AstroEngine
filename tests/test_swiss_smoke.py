# >>> AUTO-GEN BEGIN: swiss smoketest (optional) v1.0
import os

import pytest

pytestmark = pytest.mark.swiss  # will auto-skip unless Swiss is available


def test_swiss_import_and_path():
    import swisseph as swe

    p = os.getenv("SE_EPHE_PATH")
    assert p, "SE_EPHE_PATH must be set for Swiss tests"
    assert swe is not None


# >>> AUTO-GEN END: swiss smoketest (optional) v1.0

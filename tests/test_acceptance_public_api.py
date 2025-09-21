# >>> AUTO-GEN BEGIN: acceptance api v1.0
from importlib import import_module, invalidate_caches
import sys
from pathlib import Path

def test_public_api_imports():
    generated = Path(__file__).resolve().parents[1] / "generated"
    if str(generated) in sys.path:
        sys.path.remove(str(generated))
    sys.path.insert(0, str(generated))
    for key in list(sys.modules):
        if key == 'astroengine' or key.startswith('astroengine.'):
            sys.modules.pop(key)
    invalidate_caches()
    m = import_module('astroengine')
    assert hasattr(m, 'REGISTRY')
# >>> AUTO-GEN END: acceptance api v1.0

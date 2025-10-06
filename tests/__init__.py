"""Test suite package marker to ensure deterministic module names."""

# Enabling package semantics avoids module name collisions when pytest collects
# similarly named modules from nested directories (e.g. ``test_returns`` in both
# ``tests`` and ``tests.analysis``). Without this marker pytest can import a
# nested module as ``test_returns`` and later refuse to load the top-level test
# module with the same basename. By making the ``tests`` directory a proper
# package we guarantee fully qualified names such as ``tests.analysis.test_returns``
# and ``tests.test_returns`` coexist without shadowing each other.


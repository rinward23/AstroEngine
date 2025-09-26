"""Sample plugin exposing a basic VCA ruleset."""


def register(registry):
    """Register a single ruleset in the provided registry."""

    registry.register_ruleset(
        "vca.basic",
        {"weights": {"Mind": 0.34, "Body": 0.33, "Spirit": 0.33}},
    )

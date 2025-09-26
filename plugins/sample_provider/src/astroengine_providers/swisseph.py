"""Sample provider returning a static Swiss Ephemeris descriptor."""


def provider():
    """Return the provider name and payload expected by the registry."""

    return "swiss_ephemeris", {"impl": "swisseph", "version": "mvp"}

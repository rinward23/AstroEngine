


def resolve_provider(name: str | None) -> object:
    """Compatibility shim for legacy callers."""
    return get_provider(name or "swiss")

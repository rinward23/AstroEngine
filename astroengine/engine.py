"""High level transit scanning helpers used by the CLI."""




def events_to_dicts(events: Iterable[TransitEvent]) -> List[dict]:
    return [e.to_dict() for e in events]

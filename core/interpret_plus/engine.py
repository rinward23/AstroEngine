from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from collections.abc import Mapping, MutableMapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - optional dependency for richer rulepacks
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


# --------------------------- Data Models -----------------------------------
@dataclass
class Finding:
    """Structured interpretation assembled from a rule match."""

    id: str
    scope: str  # synastry|composite|davison
    title: str
    text: str
    score: float
    tags: list[str]
    meta: dict[str, Any]


Rule = dict[str, Any]
Request = dict[str, Any]
SynastryHit = dict[str, Any]
Pack = dict[str, Any]


# --------------------------- Constants -------------------------------------
ASPECT_SYMBOLS: dict[str, str] = {
    "conjunction": "☌",
    "opposition": "☍",
    "trine": "△",
    "square": "□",
    "sextile": "✶",
    "quincunx": "⚻",
}

ARCHETYPES: dict[str, str] = {
    "Sun": "Core Self",
    "Moon": "Emotional Body",
    "Mercury": "Mind & Speech",
    "Venus": "Relating & Pleasure",
    "Mars": "Drive & Desire",
    "Jupiter": "Growth",
    "Saturn": "Structure & Commitment",
    "Uranus": "Revolution & Freedom",
    "Neptune": "Dreaming & Ideals",
    "Pluto": "Transformation & Depth",
    "Asc": "Ascendant",
    "MC": "Midheaven",
}

ASPECT_ALIASES: dict[Any, str] = {
    0: "conjunction",
    30: "semi-sextile",
    45: "semi-square",
    60: "sextile",
    90: "square",
    120: "trine",
    135: "sesquiquadrate",
    150: "quincunx",
    180: "opposition",
    "0": "conjunction",
    "60": "sextile",
    "90": "square",
    "120": "trine",
    "180": "opposition",
}

ASPECT_FAMILIES: dict[str, Sequence[str]] = {
    "harmonious": ("sextile", "trine"),
    "challenging": ("square", "opposition", "sesquiquadrate", "semi-square"),
    "neutral": ("conjunction", "quincunx", "semi-sextile"),
}

ASPECT_TO_FAMILY: dict[str, str] = {
    aspect: family
    for family, aspects in ASPECT_FAMILIES.items()
    for aspect in aspects
}


# --------------------------- Helper Functions ------------------------------
def _fmt(template: str, ctx: Mapping[str, Any]) -> str:
    """Best-effort format that falls back to the template on error."""

    try:
        return template.format(**ctx)
    except Exception:
        return template


def _coerce_seq(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, (list, tuple, set)):
        return tuple(str(item) for item in raw)
    return (str(raw),)


def _normalise_aspect(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return ASPECT_ALIASES.get(int(value))
    value_str = str(value).strip().lower()
    return ASPECT_ALIASES.get(value_str) or value_str


def _aspect_family(aspect: str | None) -> str | None:
    if aspect is None:
        return None
    return ASPECT_TO_FAMILY.get(aspect.lower())


def _strength_transform(strength: float, spec: str | None) -> float:
    if spec is None or spec == "linear":
        return strength
    if spec.startswith("cosine"):
        power = 1.0
        if "^" in spec:
            try:
                power = float(spec.split("^", 1)[1])
            except ValueError:
                power = 1.0
        # Emphasise higher strengths, flatten lower ones.
        transformed = math.cos((1.0 - max(min(strength, 1.0), 0.0)) * math.pi / 2.0)
        return transformed**power
    if spec.startswith("power^"):
        try:
            exponent = float(spec.split("^", 1)[1])
        except ValueError:
            exponent = 1.0
        return strength**exponent
    return strength


def _distance(a: float, b: float) -> float:
    diff = abs((a - b + 180.0) % 360.0 - 180.0)
    return diff


def _ensure_profile(profiles: MutableMapping[str, Any]) -> None:
    if "default" not in profiles:
        profiles["default"] = {"tags": {}}


def _merge_profiles(base: MutableMapping[str, Any], extra: Mapping[str, Any]) -> MutableMapping[str, Any]:
    merged = dict(base)
    for name, payload in extra.items():
        if name not in merged:
            merged[name] = deepcopy(payload)
            continue
        existing = merged[name]
        for key, value in payload.items():
            if isinstance(value, Mapping) and isinstance(existing.get(key), Mapping):
                merged[name][key] = {**existing[key], **value}
            else:
                merged[name][key] = deepcopy(value)
    return merged


def _load_raw(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    if path.endswith(".json") or yaml is None:
        return json.loads(raw)
    return yaml.safe_load(raw)


def _normalise_pack(data: Any, *, source: str, stack: Sequence[str] = ()) -> Pack:
    """Normalise raw YAML/JSON payload into a rulepack dictionary."""

    pack_id = os.path.splitext(os.path.basename(source))[0]

    if isinstance(data, list):
        return {
            "rulepack": pack_id,
            "version": "1",
            "rules": list(data),
            "profiles": {"default": {"tags": {}}},
            "tag_map": {},
            "meta": {},
            "source": source,
        }

    if not isinstance(data, dict):
        raise ValueError(f"Unsupported rulepack payload in {source!r}")

    includes = data.get("includes") or []
    base_dir = os.path.dirname(source)

    combined_rules: list[Rule] = []
    combined_tag_map: dict[str, Any] = {}
    combined_profiles: dict[str, Any] = {}
    combined_meta: dict[str, Any] = {}

    for entry in includes:
        include_path = entry.get("path")
        include_id = entry.get("id")
        if include_path is None and include_id:
            include_path = os.path.join("..", "packs", f"{include_id}.yaml")
        if include_path is None:
            raise ValueError(f"Meta-pack entry missing path/id in {source!r}")

        resolved = os.path.normpath(os.path.join(base_dir, include_path))
        if resolved in stack:
            raise ValueError(f"Recursive rulepack include detected: {resolved}")
        child = load_rules(resolved, _stack=(*stack, source))
        weight = float(entry.get("weight", 1.0))

        for rule in child.get("rules", []):
            clone = deepcopy(rule)
            meta = clone.setdefault("meta", {})
            meta.setdefault("source_pack", child.get("rulepack"))
            if weight != 1.0:
                meta["include_weight"] = weight
            combined_rules.append(clone)

        combined_tag_map.update(child.get("tag_map", {}))
        combined_profiles = _merge_profiles(combined_profiles, child.get("profiles", {}))
        combined_meta.setdefault("includes", []).append(child.get("rulepack"))

    rules = list(data.get("rules", []))
    for rule in rules:
        rule_meta = rule.setdefault("meta", {})
        rule_meta.setdefault("source_pack", data.get("rulepack", pack_id))
        combined_rules.append(rule)

    tag_map = dict(combined_tag_map)
    tag_map.update(data.get("tag_map") or data.get("tags") or {})

    profiles = _merge_profiles(combined_profiles, data.get("profiles", {}))
    _ensure_profile(profiles)

    meta = dict(combined_meta)
    meta.update(data.get("meta", {}))

    pack: Pack = {
        "rulepack": data.get("rulepack", pack_id),
        "version": str(data.get("version", "1")),
        "rules": combined_rules,
        "profiles": profiles,
        "tag_map": tag_map,
        "meta": meta,
        "source": source,
    }
    if "default_profile" in data:
        pack["default_profile"] = data["default_profile"]
    if "description" in data:
        pack["description"] = data["description"]
    return pack


def load_rules(path: str, _stack: Sequence[str] = ()) -> Pack:
    """Load a rulepack from YAML or JSON, resolving meta-pack includes."""

    payload = _load_raw(path)
    return _normalise_pack(payload, source=path, stack=_stack)


# --------------------------- DSL Normalisation ------------------------------
def _extract_result(rule: Rule) -> dict[str, Any]:
    result = rule.get("then") or {}
    if not result:
        result = {
            "title": rule.get("title"),
            "text": rule.get("text", ""),
            "tags": rule.get("tags", []),
            "base_score": rule.get("base_score", rule.get("score", 1.0)),
            "score_fn": rule.get("score_fn"),
        }
        if "boost" in rule:
            result["boost"] = rule["boost"]
        if "limit" in rule:
            result["limit"] = rule["limit"]
    result.setdefault("title", rule.get("title") or rule.get("id", ""))
    result.setdefault("text", rule.get("text", ""))
    result.setdefault("tags", rule.get("tags", []))
    result.setdefault("base_score", rule.get("base_score", rule.get("score", 1.0)))
    if "score_fn" not in result and "score_fn" in rule:
        result["score_fn"] = rule["score_fn"]
    return result


def _normalise_rule(rule: Rule) -> Rule:
    clone = deepcopy(rule)
    clone["then"] = _extract_result(rule)
    return clone


# --------------------------- Matching Primitives ---------------------------
def _matches_bodies(hit: SynastryHit, cond: Mapping[str, Any]) -> bool:
    bodies = set(_coerce_seq(cond.get("bodies")))
    bodies_a = set(_coerce_seq(cond.get("bodiesA")))
    bodies_b = set(_coerce_seq(cond.get("bodiesB")))

    a = hit.get("a")
    b = hit.get("b")

    if bodies_a or bodies_b:
        if bodies_a and "*" not in bodies_a and a not in bodies_a:
            return False
        if bodies_b and "*" not in bodies_b and b not in bodies_b:
            return False
        return True

    if not bodies:
        return True

    if len(bodies) == 1:
        return a in bodies or b in bodies

    return {a, b} == bodies


def _match_synastry_condition(cond: Mapping[str, Any], hits: Sequence[SynastryHit]) -> list[SynastryHit]:
    aspect_names = {_normalise_aspect(item) for item in cond.get("aspects", [])}
    aspect_in = {str(name).lower() for name in cond.get("aspect_in", [])}
    aspect_names.discard(None)
    families = {str(name).lower() for name in cond.get("family", [])}
    min_severity = float(cond.get("min_severity", 0.0))

    matches: list[SynastryHit] = []
    for hit in hits:
        aspect = _normalise_aspect(hit.get("aspect"))
        if aspect_names and aspect not in aspect_names:
            continue
        if aspect_in and (aspect or "") not in aspect_in:
            continue
        if families:
            fam = _aspect_family(aspect)
            if fam not in families:
                continue
        if not _matches_bodies(hit, cond):
            continue
        severity = float(hit.get("severity", 0.0))
        if severity < min_severity:
            continue
        enriched = dict(hit)
        enriched["aspect"] = aspect
        enriched["family"] = _aspect_family(aspect)
        enriched["strength"] = max(severity, min_severity)
        matches.append(enriched)
    return matches


def _evaluate_group(cond: Mapping[str, Any], hits: Sequence[SynastryHit]) -> list[SynastryHit]:
    block = cond.get("group") or {}
    if not block:
        return []

    if "any" in block:
        subconditions = block["any"] or []
        matched: dict[tuple[str, str, str], SynastryHit] = {}
        for sub in subconditions:
            for hit in _match_synastry_condition(sub, hits):
                key = (hit.get("a"), hit.get("b"), hit.get("aspect"))
                if key not in matched:
                    matched[key] = hit
        matches = list(matched.values())
    elif "all" in block:
        matches = []
        for sub in block["all"] or []:
            sub_matches = _match_synastry_condition(sub, hits)
            if not sub_matches:
                return []
            matches.extend(sub_matches)
    else:
        matches = []

    threshold = block.get("count") or block.get("count_at_least")
    if threshold is not None and len(matches) < int(threshold):
        return []
    return matches


def _match_synastry(rule: Rule, hits: Sequence[SynastryHit]) -> list[dict[str, Any]]:
    cond = rule.get("when", {}) or {}

    group_matches = _evaluate_group(cond, hits)
    if group_matches:
        strength = sum(float(hit.get("strength", 0.0)) for hit in group_matches) / max(len(group_matches), 1)
        return [
            {
                "kind": "group",
                "hits": group_matches,
                "strength": strength,
                "primary": group_matches[0],
            }
        ]
    if "group" in cond:
        return []

    matches = _match_synastry_condition(cond, hits)
    results: list[dict[str, Any]] = []
    for hit in matches:
        results.append(
            {
                "kind": "synastry",
                "hits": [hit],
                "strength": float(hit.get("strength", 0.0)),
                "primary": hit,
            }
        )
    return results


def _match_chart(rule: Rule, request: Request) -> list[dict[str, Any]]:
    cond = rule.get("when", {}) or {}
    positions = request.get("positions", {}) or {}
    houses_data = request.get("houses", {}) or {}
    angles = request.get("angles", {}) or {}

    house_block = cond.get("house")
    if house_block:
        scope = house_block.get("scope")
        if scope and scope != request.get("scope"):
            return []
        target_bodies = _coerce_seq(house_block.get("target"))
        houses = {str(item) for item in house_block.get("in", [])}
        angles_any = [str(item) for item in house_block.get("angles_any", house_block.get("angle", []))]
        orb = float(house_block.get("orb", 2.0))

        matches: list[dict[str, Any]] = []
        for body in target_bodies:
            info = houses_data.get(body)
            if isinstance(info, Mapping):
                body_house = str(info.get("house", ""))
            else:
                body_house = str(info or "")
            if houses and body_house not in houses:
                continue
            longitude = None
            if isinstance(info, Mapping) and "longitude" in info:
                longitude = float(info["longitude"])
            elif body in positions:
                longitude = float(positions[body])
            if angles_any and longitude is not None:
                if not any(
                    name in angles and _distance(longitude, float(angles[name])) <= orb
                    for name in angles_any
                ):
                    continue
            matches.append({
                "kind": "chart",
                "body": body,
                "longitude": longitude,
                "house": body_house,
            })
        return matches

    bodies = _coerce_seq(cond.get("bodies") or cond.get("body"))
    ranges = cond.get("longitude_ranges") or []
    normalised_ranges = [tuple(map(float, window)) for window in ranges]
    matches: list[dict[str, Any]] = []
    for body in bodies:
        if body not in positions:
            continue
        longitude = float(positions[body])
        if normalised_ranges:
            in_range = any(lo <= longitude < hi for lo, hi in normalised_ranges)
            if not in_range:
                continue
        matches.append({
            "kind": "chart",
            "body": body,
            "longitude": longitude,
            "house": str(houses_data.get(body, "")),
        })
    return matches


# --------------------------- Scoring Helpers -------------------------------
def _profile_multiplier(tags: Sequence[str], pack: Pack, profile_name: str | None) -> float:
    profile = pack.get("profiles", {}).get(profile_name or "", {})
    if not profile:
        profile = pack.get("profiles", {}).get(pack.get("default_profile", "default"), {})
    tags_weights = profile.get("tags", {}) if isinstance(profile, Mapping) else {}

    tag_map = pack.get("tag_map", {})
    weights: list[float] = []
    for tag in tags:
        entry = tag_map.get(tag, {})
        bucket = entry.get("bucket") if isinstance(entry, Mapping) else None
        sub_weight = float(entry.get("weight", 1.0)) if isinstance(entry, Mapping) else 1.0
        bucket_weight = float(tags_weights.get(bucket, 1.0)) if bucket else 1.0
        weights.append(sub_weight * bucket_weight)

    if not weights:
        return 1.0
    return sum(weights) / len(weights)


def _apply_boost(score: float, boost: Mapping[str, Any] | None) -> float:
    if not boost:
        return score
    factor = float(boost.get("by", 1.0))
    cap = boost.get("cap")
    adjusted = score * factor
    if cap is not None:
        adjusted = min(adjusted, float(cap))
    return adjusted


def _build_conflict_key(match: Mapping[str, Any], rule: Rule, scope: str) -> tuple[Any, ...]:
    if match.get("kind") == "synastry":
        primary = match.get("primary", {})
        pair = tuple(sorted((primary.get("a"), primary.get("b"))))
        aspect = primary.get("aspect")
        return (scope, pair, aspect)
    if match.get("kind") == "group":
        return (scope, rule.get("id"), "group")
    body = match.get("body") or match.get("primary", {}).get("body")
    return (scope, body)


def _pair_key(match: Mapping[str, Any]) -> tuple[str, str] | None:
    primary = match.get("primary")
    if not isinstance(primary, Mapping):
        return None
    a = primary.get("a")
    b = primary.get("b")
    if a and b:
        return tuple(sorted((a, b)))
    return None


def _prepare_candidate(
    rule: Rule,
    match: Mapping[str, Any],
    pack: Pack,
    scope: str,
    profile: str | None,
) -> dict[str, Any] | None:
    then = rule.get("then", {}) or {}
    tags = list(then.get("tags", []))

    base_score = float(then.get("base_score", 1.0))
    include_weight = float(rule.get("meta", {}).get("include_weight", 1.0))
    strength = float(match.get("strength", 1.0))
    score_fn = then.get("score_fn")
    transformed_strength = _strength_transform(strength, score_fn)
    raw_score = base_score * transformed_strength
    profile_factor = _profile_multiplier(tags, pack, profile)
    score = raw_score * profile_factor * include_weight
    score = _apply_boost(score, then.get("boost"))

    primary = match.get("primary", {})
    aspect = primary.get("aspect") if isinstance(primary, Mapping) else None

    context = {
        "count": len(match.get("hits", [])),
        "strength": strength,
        "scope": scope,
        "rule_id": rule.get("id"),
    }

    if match.get("kind") in {"synastry", "group"}:
        a = primary.get("a")
        b = primary.get("b")
        aspect = primary.get("aspect")
        ctx = {
            "a": a,
            "b": b,
            "aspect": aspect,
            "aspect_symbol": ASPECT_SYMBOLS.get(aspect or "", aspect or ""),
            "severity": primary.get("severity", primary.get("strength", strength)),
            "a_arch": ARCHETYPES.get(a, a),
            "b_arch": ARCHETYPES.get(b, b),
            "hits": match.get("hits", []),
        }
        context.update(ctx)
    elif match.get("kind") == "chart":
        body = match.get("body")
        ctx = {
            "body": body,
            "arch": ARCHETYPES.get(body, body),
            "longitude": match.get("longitude"),
            "house": match.get("house"),
        }
        context.update(ctx)

    title = then.get("title") or rule.get("title") or rule.get("id", "")
    text = _fmt(then.get("text", ""), context)

    candidate = {
        "rule_id": rule.get("id", "rule"),
        "scope": scope,
        "title": title,
        "text": text,
        "tags": tags,
        "score": score,
        "raw_score": raw_score,
        "profile_factor": profile_factor,
        "match": match,
        "limit": then.get("limit"),
        "has_boost": bool(then.get("boost")),
        "meta": {
            "rule": rule.get("id"),
            "source_pack": rule.get("meta", {}).get("source_pack"),
            "hits": match.get("hits", []),
            "context": context,
        },
    }
    candidate["conflict_key"] = _build_conflict_key(match, rule, scope)
    candidate["pair_key"] = _pair_key(match)
    return candidate


def _resolve_conflicts(candidates: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for cand in candidates:
        key = cand.get("conflict_key")
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = cand
            continue
        if cand.get("has_boost") and not existing.get("has_boost"):
            by_key[key] = cand
            continue
        if cand["raw_score"] > existing["raw_score"]:
            by_key[key] = cand
    return list(by_key.values())


def _apply_limits(candidates: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    results: list[dict[str, Any]] = []
    for cand in sorted(candidates, key=lambda item: (-item["score"], item["rule_id"])):
        limit = cand.get("limit") or {}
        pair_key = cand.get("pair_key")
        if limit.get("per_pair") and pair_key:
            max_allowed = int(limit.get("max", 1))
            if counts[pair_key] >= max_allowed:
                continue
            counts[pair_key] += 1
        results.append(cand)
    results.sort(key=lambda item: (-item["score"], item["rule_id"]))
    return results


# --------------------------- Engine ----------------------------------------
def interpret(request: Request, rules: Sequence[Rule] | Pack) -> list[Finding]:
    """Evaluate the supplied rules or rulepack against the request payload."""

    if isinstance(rules, Mapping) and "rules" in rules:
        pack = rules  # type: ignore[assignment]
    else:
        pack = {
            "rulepack": "inline",
            "version": "1",
            "rules": list(rules),
            "profiles": {"default": {"tags": {}}},
            "tag_map": {},
            "meta": {},
        }

    scope = request.get("scope")
    profile = request.get("profile")

    matches: list[dict[str, Any]] = []
    for raw_rule in pack.get("rules", []):
        rule = _normalise_rule(raw_rule)
        if rule.get("scope") != scope:
            continue

        if scope == "synastry":
            hits = request.get("hits", []) or []
            for match in _match_synastry(rule, hits):
                candidate = _prepare_candidate(rule, match, pack, scope, profile)
                if candidate:
                    matches.append(candidate)
        else:
            for match in _match_chart(rule, request):
                candidate = _prepare_candidate(rule, match, pack, scope, profile)
                if candidate:
                    matches.append(candidate)

    resolved = _resolve_conflicts(matches)
    limited = _apply_limits(resolved)

    findings: list[Finding] = []
    for cand in limited:
        findings.append(
            Finding(
                id=str(cand.get("rule_id")),
                scope=str(cand.get("scope")),
                title=str(cand.get("title")),
                text=str(cand.get("text")),
                score=float(cand.get("score", 0.0)),
                tags=list(cand.get("tags", [])),
                meta=cand.get("meta", {}),
            )
        )

    findings.sort(key=lambda item: (-item.score, item.id))
    return findings


__all__ = [
    "ARCHETYPES",
    "ASPECT_SYMBOLS",
    "Finding",
    "interpret",
    "load_rules",
]

"""Runtime dependency probing utilities.

The helpers defined here keep AstroEngine's diagnostics lightweight while
ensuring that every module required for Solar Fire aligned workflows is
available.  Each dependency probe records the originating requirement as
well as the import name so higher layers can provide actionable guidance
without inventing synthetic data.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from importlib import import_module, metadata
from importlib.metadata import PackageNotFoundError
from typing import Literal

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version

__all__ = [
    "DependencySpec",
    "DependencyStatus",
    "inspect_dependencies",
]


Status = Literal["PASS", "WARN", "FAIL"]


@dataclass(frozen=True, slots=True)
class DependencySpec:
    """Describe a runtime dependency that should be present."""

    requirement: str
    """The canonical requirement string (e.g. ``"numpy>=1.26"``)."""

    import_name: str | None = None
    """Override for the module import name when it differs from the distribution."""

    required: bool = True
    """Whether a missing dependency should be treated as a failure."""

    min_version: str | None = None
    """Minimum acceptable version of the installed distribution."""

    note: str | None = None
    """Additional context included in diagnostic payloads."""

    def distribution(self) -> str:
        """Return the normalized distribution name."""

        return Requirement(self.requirement).name

    def module(self) -> str:
        """Return the module import path associated with the spec."""

        target = self.import_name or self.distribution()
        return target.replace("-", "_")


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    """Result of probing a dependency's availability."""

    spec: DependencySpec
    status: Status
    detail: str
    module_version: str | None = None
    distribution_version: str | None = None
    error: str | None = None

    def data(self) -> dict[str, object]:
        """Return structured metadata for diagnostics reporting."""

        payload: dict[str, object] = {
            "requirement": self.spec.requirement,
            "import_name": self.spec.module(),
            "required": self.spec.required,
        }
        if self.module_version:
            payload["module_version"] = self.module_version
        if self.distribution_version:
            payload["distribution_version"] = self.distribution_version
        if self.spec.note:
            payload["note"] = self.spec.note
        if self.error:
            payload["error"] = self.error
        return payload


def _format_exception(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}".strip()


def _version_satisfies(current: str | None, minimum: str) -> tuple[bool, str | None]:
    """Check whether ``current`` meets the ``minimum`` semantic version."""

    if current is None:
        return False, None
    try:
        current_version = Version(current)
        minimum_version = Version(minimum)
    except InvalidVersion as exc:
        return False, _format_exception(exc)
    return current_version >= minimum_version, str(current_version)


def _inspect_dependency(spec: DependencySpec) -> DependencyStatus:
    module_name = spec.module()
    try:
        module = import_module(module_name)
    except Exception as exc:  # pragma: no cover - exercised via CLI diagnostics
        status: Status = "FAIL" if spec.required else "WARN"
        detail = f"import failed for {module_name}"
        return DependencyStatus(
            spec=spec,
            status=status,
            detail=detail,
            error=_format_exception(exc),
        )

    module_version = getattr(module, "__version__", None)
    dist_name = spec.distribution()
    dist_version: str | None
    dist_error: str | None = None
    try:
        dist_version = metadata.version(dist_name)
    except PackageNotFoundError as exc:
        dist_version = None
        dist_error = _format_exception(exc)

    if dist_version is None and dist_error:
        status = "FAIL" if spec.required else "WARN"
        detail = f"distribution metadata for {dist_name} unavailable"
        return DependencyStatus(
            spec=spec,
            status=status,
            detail=detail,
            module_version=module_version,
            distribution_version=dist_version,
            error=dist_error,
        )

    if spec.min_version:
        candidate_version = dist_version or module_version
        meets, failure_detail = _version_satisfies(candidate_version, spec.min_version)
        if not meets:
            status = "FAIL" if spec.required else "WARN"
            detail = (
                failure_detail
                or f"missing version metadata; requires >= {spec.min_version}"
            )
            return DependencyStatus(
                spec=spec,
                status=status,
                detail=detail,
                module_version=module_version,
                distribution_version=dist_version,
                error=dist_error,
            )

    detail_parts: list[str] = ["available"]
    if not spec.required:
        detail_parts.append("optional")
    if dist_version:
        detail_parts.append(f"version {dist_version}")
    elif module_version:
        detail_parts.append(f"module version {module_version}")
    if spec.note:
        detail_parts.append(spec.note)
    detail = "; ".join(detail_parts)
    return DependencyStatus(
        spec=spec,
        status="PASS",
        detail=detail,
        module_version=module_version,
        distribution_version=dist_version,
        error=dist_error,
    )


def inspect_dependencies(specs: Sequence[DependencySpec] | Iterable[DependencySpec]) -> list[DependencyStatus]:
    """Evaluate all provided dependency specs."""

    return [_inspect_dependency(spec) for spec in specs]


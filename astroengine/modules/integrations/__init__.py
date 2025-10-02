"""Registry metadata for third-party astrology tool integrations."""

from __future__ import annotations

from ..registry import AstroRegistry


SWISS_EPHEMERIS_URL = "https://www.astro.com/swisseph/"
PYSWISSEPH_URL = "https://pypi.org/project/pyswisseph/"
SKYFIELD_URL = "https://rhodesmill.org/skyfield/"
JPLEPHEM_URL = "https://pypi.org/project/jplephem/"
FLATLIB_URL = "https://github.com/flatangle/flatlib"
MAITREYA_URL = "https://sourceforge.net/projects/maitreya/"
JHORA_URL = "https://www.vedicastrologer.org/jh/"
PANCHANGA_URL = "https://github.com/karthikraman/panchangam"


def register_integrations_module(registry: AstroRegistry) -> None:
    """Register external library integrations in the AstroRegistry."""

    module = registry.register_module(
        "integrations",
        metadata={
            "description": "External tool compatibility map for Solar Fire derived datasets.",
            "data_inputs": ["csv", "sqlite"],
            "integrity_note": (
                "Only catalogue integrations backed by verifiable upstream data sources."
            ),
        },
    )

    ephemeris = module.register_submodule(
        "ephemeris_tooling",
        metadata={
            "description": "Libraries that deliver ephemeris positions for transit calculations.",
        },
    )

    swiss_channel = ephemeris.register_channel(
        "swiss_ephemeris",
        metadata={
            "description": "Swiss Ephemeris stack used for high-precision charting.",
            "project_url": SWISS_EPHEMERIS_URL,
        },
    )
    swiss_channel.register_subchannel(
        "sweph",
        metadata={
            "description": "C library distribution of Swiss Ephemeris (libswe).",
            "project_url": SWISS_EPHEMERIS_URL,
            "license": "Swiss Ephemeris Public License",
        },
        payload={"ephemeris_path": "datasets/swisseph_stub"},
    )
    swiss_channel.register_subchannel(
        "pyswisseph",
        metadata={
            "description": "Python bindings for Swiss Ephemeris maintained on PyPI.",
            "project_url": PYSWISSEPH_URL,
            "version": ">=2.10.3.2",
        },
    )

    skyfield_channel = ephemeris.register_channel(
        "skyfield",
        metadata={
            "description": "Skyfield ephemeris provider with DE440s kernels.",
            "project_url": SKYFIELD_URL,
        },
    )
    skyfield_channel.register_subchannel(
        "skyfield_core",
        metadata={
            "description": "Skyfield library backed by JPL DE ephemerides.",
            "project_url": SKYFIELD_URL,
            "companion_package": JPLEPHEM_URL,
        },
        payload={"kernel_helper": "astroengine/providers/skyfield_kernels.py"},
    )

    python_toolkits = module.register_submodule(
        "python_toolkits",
        metadata={
            "description": "Pure-Python libraries bundled with AstroEngine for chart analysis.",
        },
    )
    toolkit_channel = python_toolkits.register_channel(
        "libraries",
        metadata={"description": "Runtime dependencies exposed via the Python API."},
    )
    toolkit_channel.register_subchannel(
        "flatlib",
        metadata={
            "description": "Traditional astrology computations implemented in Python.",
            "project_url": FLATLIB_URL,
            "version": ">=0.2.3",
        },
    )

    vedic = module.register_submodule(
        "vedic_workflows",
        metadata={
            "description": "Desktop tools frequently used alongside Solar Fire exports.",
        },
    )
    desktop_channel = vedic.register_channel(
        "desktop_suites",
        metadata={"description": "Free suites requiring manual data export for ingestion."},
    )
    desktop_channel.register_subchannel(
        "maitreya",
        metadata={
            "description": "Maitreya 8 open-source Vedic astrology application.",
            "project_url": MAITREYA_URL,
            "integration_notes": "Supports report exports suitable for downstream indexing.",
        },
    )
    desktop_channel.register_subchannel(
        "jhora",
        metadata={
            "description": "Jagannatha Hora desktop suite for Vedic calculations.",
            "project_url": JHORA_URL,
            "integration_notes": "Use the program's export utilities to capture transit tables for ingestion.",
        },
    )

    panchanga_channel = vedic.register_channel(
        "panchanga_projects",
        metadata={
            "description": "Community maintained Panchanga calculation projects.",
        },
    )
    panchanga_channel.register_subchannel(
        "open_source_panchanga",
        metadata={
            "description": "Python toolkit for almanac generation maintained on GitHub.",
            "project_url": PANCHANGA_URL,
        },
    )

__all__ = ["register_integrations_module"]

from __future__ import annotations

import csv
from dataclasses import dataclass


@dataclass
class Star:
    name: str
    ra_deg: float   # ICRS/J2000 RA in degrees
    dec_deg: float  # ICRS/J2000 Dec in degrees
    vmag: float
    alias: str | None = None

# Minimal built-in catalog (J2000 approx)
BUILTIN_STARS: dict[str, Star] = {
    "Sirius":   Star("Sirius",   ra_deg=101.2875, dec_deg=-16.7161, vmag=-1.46, alias="Alpha Canis Majoris"),
    "Regulus":  Star("Regulus",  ra_deg=152.0933, dec_deg= 11.9672, vmag=1.35,  alias="Alpha Leonis"),
    "Spica":    Star("Spica",    ra_deg=201.2983, dec_deg=-11.1614, vmag=1.04,  alias="Alpha Virginis"),
    "Aldebaran":Star("Aldebaran",ra_deg= 68.9800, dec_deg= 16.5093, vmag=0.86,  alias="Alpha Tauri"),
    "Antares":  Star("Antares",  ra_deg=247.3519, dec_deg=-26.4320, vmag=1.06,  alias="Alpha Scorpii"),
    "Algol":    Star("Algol",    ra_deg= 47.0422, dec_deg= 40.9556, vmag=2.12,  alias="Beta Persei"),
}


def load_catalog(csv_path: str | None = None) -> dict[str, Star]:
    if not csv_path:
        return dict(BUILTIN_STARS)
    out: dict[str, Star] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("name") or row.get("Name")
            ra = float(row.get("ra_deg") or row.get("ra"))
            dec = float(row.get("dec_deg") or row.get("dec"))
            vmag = float(row.get("vmag") or row.get("Vmag") or 99.9)
            alias = row.get("alias") or row.get("Alias")
            out[name] = Star(name=name, ra_deg=ra, dec_deg=dec, vmag=vmag, alias=alias)
    return out

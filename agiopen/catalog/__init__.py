"""Fixture catalog: manufacturer datasheet values and photometry curves.

`fixtures.json` holds one entry per fixture variant (watts, PPF, dimensions, warranty...).
`photometry/*.json` holds named light distributions:

- `model: tabulated`: intensity per angle on C-planes 0-90 (0 = along the fixture length);
- `model: batwing` / `cosine`: generic shapes with their parameters.

A project references an entry with `fixtures[].catalog`; any field given in the project
overrides the catalog value.
"""
from __future__ import annotations

import difflib
import json
from functools import lru_cache
from pathlib import Path

from ..photometry import Batwing, CosinePower, Distribution, TabulatedDistribution

HERE = Path(__file__).parent


class CatalogError(ValueError):
    pass


@lru_cache(maxsize=1)
def fixtures() -> dict[str, dict]:
    data = json.loads((HERE / "fixtures.json").read_text(encoding="utf-8"))
    return {f["id"]: f for f in data["fixtures"]}


def get(fixture_id: str) -> dict:
    cat = fixtures()
    if fixture_id not in cat:
        close = difflib.get_close_matches(fixture_id, list(cat), n=3, cutoff=0.5)
        hint = f" Did you mean {', '.join(close)}?" if close else " Run `agiopen catalog` for the list."
        raise CatalogError(f"Unknown catalog fixture '{fixture_id}'.{hint}")
    return cat[fixture_id]


@lru_cache(maxsize=None)
def photometry(name: str) -> dict:
    p = HERE / "photometry" / f"{name}.json"
    if not p.exists():
        names = sorted(q.stem for q in (HERE / "photometry").glob("*.json"))
        raise CatalogError(f"Unknown photometry '{name}'. Available: {', '.join(names)}.")
    return json.loads(p.read_text(encoding="utf-8"))


def distribution(name: str) -> Distribution:
    d = photometry(name)
    model = d.get("model", "tabulated")
    if model == "tabulated":
        return TabulatedDistribution(d["angles_deg"], d["planes"])
    if model == "batwing":
        return Batwing(d.get("beam_angle", 120.0), d.get("batwing_power", 1.5))
    if model == "cosine":
        return CosinePower(d.get("cos_power", 1.0))
    raise CatalogError(f"Photometry '{name}': unknown model '{model}'.")


def fixture_fields(fixture_id: str, units: str) -> dict:
    """Catalog entry -> Fixture fields, lengths in the project units."""
    e = get(fixture_id)
    scale = 1 / 304.8 if units == "imperial" else 1 / 1000
    out = {
        "name": e["name"], "manufacturer": e["manufacturer"], "family": e["family"],
        "watts": e["watts"], "ppf": e["ppf"], "warranty": e.get("warranty", ""),
        "photometry": e.get("photometry", ""),
        "description": e["name"],
    }
    if e.get("length_mm"):
        out["length"] = round(e["length_mm"] * scale, 3)
        out["width"] = round(e.get("width_mm", 0) * scale, 3)
    return out

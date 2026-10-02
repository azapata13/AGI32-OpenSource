import math
from pathlib import Path

import numpy as np

from agiopen import spec_from_dict
from agiopen.engine import run
from agiopen.photometry import Batwing, CosinePower, parse_ies

ROOT = Path(__file__).parents[1]


def _flux(dist):
    th = np.linspace(0, np.pi / 2, 4001)
    return np.trapezoid(dist.intensity(th, np.zeros_like(th)) * np.sin(th) * 2 * np.pi, th)


def test_distributions_are_normalised():
    for d in (CosinePower(1), CosinePower(3), Batwing(120), Batwing(150)):
        assert abs(_flux(d) - 1) < 1e-3


def test_ies_lambertian_matches_cosine():
    ies = parse_ies(ROOT / "examples/ies/generic_lambertian.ies")
    th = np.radians([0, 20, 45, 70])
    assert np.allclose(ies.intensity(th, np.zeros(4)), CosinePower(1).intensity(th, 0), rtol=0.02)


def _single(dist="cosine", h=2.0, size=60.0, reflections=False, ies=""):
    return {
        "meta": {"project_name": "unit", "units": "metric"},
        "site": {"type": "indoor_room", "width": size, "length": size, "height": h + 1,
                 "wall_reflectance": 0.0, "ceiling_reflectance": 0.0, "floor_reflectance": 0.0},
        "fixtures": [{"id": "f", "name": "f", "watts": 100, "ppf": 1000, "distribution": dist,
                      "cos_power": 1.0, "ies_file": ies}],
        "canopies": [{"label": "c", "x": 0, "y": 0, "width": size, "length": size, "height": 0}],
        "layout": [{"fixture": "f", "mode": "explicit", "positions": [[size / 2, size / 2]],
                    "mounting_height": h}],
        "calc": {"include_reflections": reflections, "grid_spacing": 0.25},
    }


def test_point_source_nadir_inverse_square():
    """E(nadir) = PPF * I0 / h^2 with I0 = (n+1)/(2 pi) for a Lambertian source."""
    h = 2.0
    d = _single(h=h, size=0.25)
    g = run(spec_from_dict(d)).grids[0]
    expected = 1000 * (2 / (2 * math.pi)) / h ** 2
    assert abs(g.max - expected) / expected < 0.01


def test_flux_conservation_on_large_plane():
    g = run(spec_from_dict(_single(h=1.0, size=80.0))).grids[0]
    captured = g.avg * g.rect.area
    assert abs(captured - 1000) / 1000 < 0.02


def test_ies_file_used_in_engine():
    d = _single(h=1.0, size=40.0, ies="examples/ies/generic_lambertian.ies")
    spec = spec_from_dict(d)
    spec.base_dir = ROOT
    g = run(spec).grids[0]
    assert abs(g.avg * g.rect.area - 1000) / 1000 < 0.03


def test_reflections_raise_ppfd_in_white_room():
    base = _single(h=1.5, size=4.0)
    white = _single(h=1.5, size=4.0, reflections=True)
    white["site"].update(wall_reflectance=0.8, ceiling_reflectance=0.8, floor_reflectance=0.2)
    a = run(spec_from_dict(base)).grids[0].avg
    b = run(spec_from_dict(white)).grids[0].avg
    assert b > a * 1.05

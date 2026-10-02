import json
from pathlib import Path

import numpy as np
import pytest

from agiopen import catalog, spec_from_dict
from agiopen.photometry import TabulatedDistribution
from agiopen.spec import SpecError

ROOT = Path(__file__).parents[1]


def _flux_3d(d):
    th = np.linspace(0, np.pi / 2, 721)
    ph = np.linspace(0, 2 * np.pi, 181)
    T, P = np.meshgrid(th, ph, indexing="ij")
    return np.trapezoid(np.trapezoid(d.intensity(T, P) * np.sin(T), ph, axis=1), th)


def test_catalog_entries_are_consistent():
    for f in catalog.fixtures().values():
        assert f["watts"] > 0 and f["ppf"] > 0, f["id"]
        # catches unit slips (European decimals, mm read as W); datasheets themselves differ by a few %
        assert abs(f["ppf"] / f["watts"] / f["efficacy"] - 1) < 0.1, f["id"]
        catalog.photometry(f["photometry"])  # every referenced curve exists


@pytest.mark.parametrize("name", sorted(p.stem for p in (ROOT / "agiopen/catalog/photometry").glob("*.json")))
def test_catalog_photometry_is_normalised(name):
    assert abs(_flux_3d(catalog.distribution(name)) - 1) < 2e-3


def test_tabulated_planes():
    d = TabulatedDistribution([0, 45, 90], [1, 2, 0], [1, 0.5, 0])
    th = np.radians(45.0)
    assert d.intensity(th, 0.0) == pytest.approx(4 * d.intensity(th, np.pi / 2))
    assert d.intensity(0.0, 0.0) == pytest.approx(d.intensity(0.0, 1.0))


def test_catalog_fills_fixture_and_overrides_win():
    raw = json.loads((ROOT / "examples/barn_auto_layout.json").read_text())
    raw["fixtures"] = [{"id": "tl", "catalog": "dli-vertex-1050w-r90g5b5"}]
    f = spec_from_dict(raw).fixtures[0]
    assert (f.watts, f.ppf, f.manufacturer, f.photometry) == (1050, 3925, "DLI", "dli-vertex")
    assert f.length == pytest.approx(945 / 304.8, abs=1e-3)  # imperial project -> ft
    raw["fixtures"] = [{"id": "tl", "catalog": "dli-vertex-1050w-r90g5b5", "ppf": 3800}]
    assert spec_from_dict(raw).fixtures[0].ppf == 3800


def test_unknown_catalog_id_suggests():
    raw = json.loads((ROOT / "examples/barn_auto_layout.json").read_text())
    raw["fixtures"] = [{"id": "tl", "catalog": "dli-nxs-540w-r90g5b"}]
    with pytest.raises(SpecError, match="dli-nxs-540w-r90g5b5"):
        spec_from_dict(raw)

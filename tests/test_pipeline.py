import json
import re
from pathlib import Path

import pytest

from agiopen import SpecError, load_spec, spec_from_dict
from agiopen.engine import run
from agiopen.intake.extract import _parse_json
from agiopen.intake.validate import missing_information
from agiopen.report import build_report

ROOT = Path(__file__).parents[1]
EXAMPLES = sorted((ROOT / "examples").glob("*.json"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_runs_and_reports(path, tmp_path):
    spec = load_spec(path)
    res = run(spec)
    assert res.luminaires and all(g.avg > 0 for g in res.grids)
    out = build_report(res, tmp_path)
    assert out.name == spec.report_filename
    pdf = out.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    assert pages >= 8


def test_report_filename_convention():
    spec = load_spec(ROOT / "examples/greenhouse_poly_leafy.json")
    spec.meta.revision = 2
    assert spec.report_filename == ("Example Hort Lighting Light Simulation - Grower A - "
                                    "GH Leafy 30x102 V2 - 2026-06-03.pdf")


def test_rack_layout_and_tier_occlusion():
    res = run(load_spec(ROOT / "examples/vertical_propagation_rack.json"))
    assert len(res.luminaires) == 24
    avgs = [g.avg for g in res.grids]
    # identical tiers: occlusion by the shelf above makes every tier see only its own bars
    assert max(avgs) - min(avgs) < 0.02 * max(avgs)


def test_auto_layout_reaches_target():
    spec = load_spec(ROOT / "examples/barn_auto_layout.json")
    res = run(spec)
    assert res.grids[0].avg >= spec.target.ppfd_min


def test_dimmed_fixtures_in_schedule_and_watts():
    res = run(load_spec(ROOT / "examples/indoor_flower_room.json"))
    rows = res.schedule()
    assert {round(r["dimming"], 2) for r in rows} == {1.0, 0.75}
    assert round(res.total_watts) == 38 * 900 + 66 * 675


def test_validation_errors_are_clear():
    d = json.loads((ROOT / "examples/greenhouse_poly_leafy.json").read_text())
    d["layout"][0]["fixture"] = "nope"
    with pytest.raises(SpecError, match="unknown fixture"):
        spec_from_dict(d)
    d = json.loads((ROOT / "examples/greenhouse_poly_leafy.json").read_text())
    d["site"]["colour"] = "green"
    with pytest.raises(SpecError, match="unknown field"):
        spec_from_dict(d)


def test_missing_information_flags_generic_photometry():
    gaps = missing_information(load_spec(ROOT / "examples/greenhouse_poly_leafy.json"))
    assert any("IES" in g for g in gaps)


def test_intake_json_parsing():
    assert _parse_json('Here:\n{"spec": {"a": 1}, "missing": []}') == {"spec": {"a": 1}, "missing": []}

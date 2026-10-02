"""Command line: `python -m agiopen <command>`.

  run      project.json [-o out_dir]   compute and write the PDF summary
  check    project.json                validate the spec, list what is missing
  results  project.json                print the Results Summary as JSON
  intake   documents... [-o spec.json] draft a spec from client documents (needs ANTHROPIC_API_KEY)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .spec import SpecError, load_spec


def _results_json(res) -> dict:
    return {
        "distance_plane_to_fixture_m": res.distance_plane_to_fixture,
        "reflected_ppfd": round(res.reflected_ppfd, 2),
        "grids": [{"label": g.label, "avg": round(g.avg, 2), "max": round(g.max), "min": round(g.min),
                   "min_avg": round(g.min_avg, 2), "min_max": round(g.min_max, 2), "points": g.n_points}
                  for g in res.grids],
        "luminaires": len(res.luminaires),
        "total_watts": round(res.total_watts),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agiopen", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("spec")
    p_run.add_argument("-o", "--out", default="out")
    p_chk = sub.add_parser("check")
    p_chk.add_argument("spec")
    p_res = sub.add_parser("results")
    p_res.add_argument("spec")
    p_in = sub.add_parser("intake")
    p_in.add_argument("documents", nargs="+")
    p_in.add_argument("-o", "--out", default="project.json")
    args = ap.parse_args(argv)

    if args.cmd == "intake":
        from .intake.extract import extract_spec
        draft, missing = extract_spec([Path(d) for d in args.documents])
        Path(args.out).write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Draft written to {args.out}")
        if missing:
            print("Missing or uncertain information to confirm with the client:")
            for m in missing:
                print(f"  - {m}")
        return 0

    try:
        spec = load_spec(args.spec)
    except SpecError as exc:
        print(f"Spec error: {exc}", file=sys.stderr)
        return 2
    if args.cmd == "check":
        from .intake.validate import missing_information
        gaps = missing_information(spec)
        print("Spec is valid." if not gaps else "Spec is valid but these points should be confirmed:")
        for g in gaps:
            print(f"  - {g}")
        return 0

    from .engine import run
    t0 = time.time()
    res = run(spec)
    if args.cmd == "results":
        print(json.dumps(_results_json(res), indent=2))
        return 0
    from .report import build_report
    out = build_report(res, args.out)
    print(json.dumps(_results_json(res), indent=2))
    print(f"Report: {out}  ({time.time() - t0:.1f}s)")
    return 0

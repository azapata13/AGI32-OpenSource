"""Compare engine results with reference reports: python benchmarks/run.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
from agiopen import load_spec  # noqa: E402
from agiopen.engine import run  # noqa: E402

cases = json.loads((ROOT / "benchmarks/cases.json").read_text())["cases"]
print(f"{'case':<18}{'avg ref':>9}{'avg':>9}{'err':>8}{'min ref':>9}{'min':>7}{'max ref':>9}{'max':>7}{'U ref':>7}{'U':>6}")
worst = 0.0
for c in cases:
    g = run(load_spec(ROOT / "examples" / c["example"])).grids[0]
    r = c["reference"]
    err = (g.avg - r["avg"]) / r["avg"]
    worst = max(worst, abs(err))
    print(f"{c['id']:<18}{r['avg']:>9.1f}{g.avg:>9.1f}{err:>+8.1%}{r['min']:>9}{g.min:>7.0f}"
          f"{r['max']:>9}{g.max:>7.0f}{r['min_avg']:>7.2f}{g.min_avg:>6.2f}")
print(f"worst average error: {worst:.1%}")

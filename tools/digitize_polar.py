"""Digitise a polar intensity plot from a spec-sheet image into I(theta) curves.

Used when a manufacturer publishes polar curves but not IES files. The plot must be drawn
downward with the fixture at the apex. Output: relative intensity per angle (0-90 deg from
nadir) for the outer filled curve (wide plane) and, when found, the inner outlined curve
(narrow plane). Results are approximate (+-5 % typical) and must be replaced by the real IES
file when it becomes available.

    python tools/digitize_polar.py image.png --box x0 y0 x1 y1 [--plot check.png]
"""
from __future__ import annotations

import argparse
import json

import numpy as np
from PIL import Image


def _masks(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g - b > 45) & (g - r > 12)
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    return green, lum


def digitize(img: np.ndarray, step_deg: float = 2.5):
    green, lum = _masks(img.astype(int))
    ys, xs = np.nonzero(green)
    top = ys.min()
    cx = float(np.median(xs[ys <= top + 2]))
    cy = float(top)
    angles = np.arange(0, 90 + 1e-9, step_deg)
    outer, inner = [], []
    rmax = int(np.hypot(*img.shape[:2]))
    fill_lum = np.median(lum[green])
    for side in (-1, 1):
        o_side, i_side = [], []
        for t in angles:
            tr = np.radians(t)
            dx, dy = side * np.sin(tr), np.cos(tr)
            rs = np.arange(2, rmax)
            px = np.round(cx + rs * dx).astype(int)
            py = np.round(cy + rs * dy).astype(int)
            ok = (px >= 0) & (px < img.shape[1]) & (py >= 0) & (py < img.shape[0])
            rs, px, py = rs[ok], px[ok], py[ok]
            g = green[py, px]
            if not g.any():
                o_side.append(0.0); i_side.append(np.nan); continue
            # outer boundary: last green pixel of the first continuous green run
            first_off = np.argmax(~g[1:] & g[:-1]) if (~g[1:] & g[:-1]).any() else len(g) - 1
            r_out = rs[first_off]
            o_side.append(float(r_out))
            dark = g & (lum[py, px] < fill_lum - 6) & (rs < r_out - 6) & (rs > 8)
            i_side.append(float(rs[dark][-1]) if dark.any() else np.nan)
        outer.append(o_side); inner.append(i_side)
    outer = np.nanmean(np.array(outer), axis=0)
    inner = np.array(inner)
    return angles, outer, inner, (cx, cy)


def clean_inner(angles, outer, inner, ring_tol=3.0):
    """Remove dark pixels that sit on concentric grid rings (same radius at every angle)."""
    vals = inner[~np.isnan(inner)]
    if vals.size == 0:
        return None
    hist, edges = np.histogram(vals, bins=np.arange(0, vals.max() + 4, 2))
    rings = edges[:-1][hist > 0.35 * inner.shape[0] * inner.shape[1] / 4]
    res = []
    for k in range(inner.shape[1]):
        cand = [v for v in inner[:, k] if not np.isnan(v)
                and not any(abs(v - r) < ring_tol for r in rings)]
        res.append(np.mean(cand) if cand else np.nan)
    res = np.array(res)
    if np.isnan(res).all():
        return None
    # the inner curve can never exceed the outer one
    return np.fmin(np.nan_to_num(res, nan=0.0), outer)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--box", nargs=4, type=int, required=True)
    ap.add_argument("--plot")
    ap.add_argument("--name", default="curve")
    args = ap.parse_args()
    im = np.asarray(Image.open(args.image).convert("RGB"))
    x0, y0, x1, y1 = args.box
    crop = im[y0:y1, x0:x1]
    ang, outer, inner, origin = digitize(crop)
    inner_c = clean_inner(ang, outer, inner)
    out = {"name": args.name, "angles_deg": ang.round(2).tolist(),
           "wide_plane": (outer / outer.max()).round(4).tolist(),
           "narrow_plane": None if inner_c is None else (inner_c / outer.max()).round(4).tolist()}
    print(json.dumps(out))
    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.imshow(crop)
        cx, cy = origin
        for curve, col in ((outer, "red"), (inner_c, "blue")):
            if curve is None:
                continue
            for side in (-1, 1):
                ax.plot(cx + side * curve * np.sin(np.radians(ang)), cy + curve * np.cos(np.radians(ang)),
                        color=col, lw=1)
        fig.savefig(args.plot, dpi=120)


if __name__ == "__main__":
    main()

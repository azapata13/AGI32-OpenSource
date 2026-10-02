"""Drawings for the report (matplotlib -> PNG bytes)."""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from ..engine import GridResult, Results  # noqa: E402

CANOPY = "#4caf50"
CANOPY_EDGE = "#2e7d32"
FIXTURE = "#d62728"
STRUCT = "#7a7a7a"
WALL = "#3b6ea5"


def _to_png(fig, dpi=200) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _u(res: Results):
    k = res.spec.meta.to_m
    return (lambda v: v / k), res.spec.meta.length_unit


def _fmt_len(v_m: float, res: Results) -> str:
    conv, unit = _u(res)
    v = conv(v_m)
    if unit == "ft":
        return f"{v:.2f}".rstrip("0").rstrip(".") + " ft"
    return f"{v:.2f}".rstrip("0").rstrip(".") + " m"


class _Frame:
    """Maps model (x, y) in metres to drawing units; rotates long sites to landscape."""

    def __init__(self, res: Results):
        self.conv, _ = _u(res)
        g = res.geometry
        self.W, self.L = g.width, g.length
        self.rot = g.length > g.width * 1.15

    def pt(self, x, y):
        c = self.conv
        return (c(y), c(self.W - x)) if self.rot else (c(x), c(y))

    def rect(self, x0, y0, x1, y1):
        (a0, b0), (a1, b1) = self.pt(x0, y0), self.pt(x1, y1)
        return min(a0, a1), min(b0, b1), abs(a1 - a0), abs(b1 - b0)

    @property
    def extent(self):
        return self.rect(0, 0, self.W, self.L)[2:]


def _fixture_patches(ax, res: Results, fr: "_Frame"):
    k = res.spec.meta.to_m
    for l in res.luminaires:
        f = l.fixture
        length = (f.length * k) if f.length else 0.35
        width = (f.width * k) if f.width else 0.12
        c, s = np.cos(l.rotation), np.sin(l.rotation)
        dx, dy = abs(length * c) + abs(width * s), abs(length * s) + abs(width * c)
        x, y, w, h = fr.rect(l.x - dx / 2, l.y - dy / 2, l.x + dx / 2, l.y + dy / 2)
        ax.add_patch(Rectangle((x, y), w, h, facecolor=FIXTURE, edgecolor="#7f0000", lw=0.3, zorder=5))


def _dim(ax, x0, y0, x1, y1, text, offset=0.0, vertical=False):
    ax.annotate("", xy=(x0, y0), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="<->", lw=0.6, color="black"), zorder=6)
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    ax.text(xm + (offset if vertical else 0), ym + (0 if vertical else offset), text,
            ha="center", va="center", fontsize=6, rotation=90 if vertical else 0,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.5), zorder=7)


def plan_view(res: Results, show_values: bool = False, region=None, figsize=(10.5, 6.2),
              grids=None) -> bytes:
    g = res.geometry
    fr = _Frame(res)
    EW, EH = fr.extent
    fig, ax = plt.subplots(figsize=figsize)
    ax.add_patch(Rectangle((0, 0), EW, EH, fill=False, ec=WALL, lw=1.2))
    for x in g.structure.bay_lines:
        (a0, b0), (a1, b1) = fr.pt(x, 0), fr.pt(x, g.length)
        ax.plot([a0, a1], [b0, b1], color=STRUCT, lw=0.4, ls="--")
    for c in g.canopies:
        x, y, w, h = fr.rect(c.x0, c.y0, c.x1, c.y1)
        ax.add_patch(Rectangle((x, y), w, h, facecolor=CANOPY if not show_values else "#e8f5e9",
                               edgecolor=CANOPY_EDGE, lw=0.6, alpha=0.55 if not show_values else 1))
    if show_values:
        _values(ax, res, fr, region, figsize, grids)
    else:
        _fixture_patches(ax, res, fr)
    pad = max(EW, EH) * 0.04
    if region is None:
        wlab, llab = _fmt_len(g.width, res), _fmt_len(g.length, res)
        hlab, vlab = (llab, wlab) if fr.rot else (wlab, llab)
        _dim(ax, 0, -pad, EW, -pad, hlab)
        _dim(ax, -pad, 0, -pad, EH, vlab, vertical=True)
        if len(res.luminaires) > 1 and not show_values:
            pts = sorted({tuple(round(v, 3) for v in fr.pt(l.x, l.y)) for l in res.luminaires})
            hs = sorted({p[0] for p in pts})
            vs = sorted({p[1] for p in pts})
            conv = fr.conv
            if len(hs) > 1:
                _dim(ax, hs[0], EH + pad, hs[1], EH + pad, _fmt_len((hs[1] - hs[0]) / conv(1), res))
            if len(vs) > 1:
                _dim(ax, EW + pad, vs[0], EW + pad, vs[1], _fmt_len((vs[1] - vs[0]) / conv(1), res),
                     vertical=True)
        ax.set_xlim(-2.5 * pad, EW + 2.5 * pad)
        ax.set_ylim(-2.5 * pad, EH + 2.5 * pad)
    else:
        (x0, x1), (y0, y1) = region
        x, y, w, h = fr.rect(x0, y0, x1, y1)
        cell = 0.6 * min(w, h) / 8
        ax.set_xlim(x - cell, x + w + cell)
        ax.set_ylim(y - cell, y + h + cell)
    ax.set_aspect("equal")
    ax.axis("off")
    return _to_png(fig)


def _values(ax, res: Results, fr: "_Frame", region, figsize, grids=None):
    conv = fr.conv
    for gr in grids or res.grids:
        xs, ys = gr.xs, gr.ys
        mx = np.ones_like(xs, dtype=bool)
        my = np.ones_like(ys, dtype=bool)
        if region:
            (x0, x1), (y0, y1) = region
            mx = (xs >= x0) & (xs <= x1)
            my = (ys >= y0) & (ys <= y1)
        sub = gr.ppfd[np.ix_(my, mx)]
        if sub.size == 0:
            continue
        cw, ch = conv(gr.rect.width) / len(xs), conv(gr.rect.length) / len(ys)
        # font size from the visible span: points per drawing unit on the page
        if region:
            (x0, x1), (y0, y1) = region
            vis_w, vis_h = fr.rect(x0, y0, x1, y1)[2:]
        else:
            vis_w, vis_h = fr.extent
        pts_per_unit = min(figsize[0] * 72 / max(vis_w, 1e-9), figsize[1] * 72 / max(vis_h, 1e-9))
        cell_pts = min(cw, ch) * pts_per_unit
        fs = float(np.clip(cell_pts * 0.32, 1.6, 9))
        lo, hi = gr.min, gr.max
        for j, y in enumerate(ys[my]):
            for i, x in enumerate(xs[mx]):
                v = sub[j, i]
                t = (v - lo) / (hi - lo) if hi > lo else 0.5
                rx, ry, rw, rh = fr.rect(x - cw / 2 / conv(1), y - ch / 2 / conv(1),
                                         x + cw / 2 / conv(1), y + ch / 2 / conv(1))
                ax.add_patch(Rectangle((rx, ry), rw, rh, facecolor=plt.cm.RdYlGn(0.15 + 0.7 * t),
                                       edgecolor="none", alpha=0.35, zorder=2))
                px, py = fr.pt(x, y)
                ax.text(px, py, f"{v:.0f}", ha="center", va="center", fontsize=fs, zorder=4)


def zoom_region(res: Results, max_cols=16, max_rows=10):
    """A representative window at the edge of the first grid: edge and interior values."""
    gr = res.grids[0]
    rot = res.geometry.length > res.geometry.width * 1.15
    if rot:  # on the page, model Y runs horizontally
        max_cols, max_rows = max_rows, max_cols
    nx, ny = min(max_cols, len(gr.xs)), min(max_rows, len(gr.ys))
    j0 = max((len(gr.ys) - ny) // 2, 0)
    x0, x1 = gr.xs[0] - 1e-6, gr.xs[nx - 1] + 1e-6
    y0, y1 = gr.ys[j0] - 1e-6, gr.ys[j0 + ny - 1] + 1e-6
    return (x0, x1), (y0, y1)


def elevation(res: Results, axis: str = "x", figsize=(10.5, 4.2)) -> bytes:
    """axis='x': front view (X horizontal). axis='y': side view (Y horizontal)."""
    conv, unit = _u(res)
    g = res.geometry
    s = res.spec.site
    span = g.width if axis == "x" else g.length
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot([0, conv(span)], [0, 0], color="black", lw=1)
    # envelope
    if s.type == "greenhouse" and axis == "x":
        bays = max(s.bays, 1)
        bw = g.width / bays
        for b in range(bays):
            xs = [b * bw, b * bw, (b + 0.5) * bw, (b + 1) * bw, (b + 1) * bw]
            zs = [0, g.height, g.ridge, g.height, 0]
            if s.peaks_per_bay > 1:
                p = s.peaks_per_bay
                xs = [b * bw] + [b * bw + bw * (i / (2 * p)) for i in range(2 * p + 1)] + [(b + 1) * bw]
                zs = [0] + [g.height if i % 2 == 0 else g.ridge for i in range(2 * p + 1)] + [0]
            ax.plot([conv(v) for v in xs], [conv(v) for v in zs], color=WALL, lw=1)
        truss_z = (s.truss_height * res.spec.meta.to_m) or g.height
        ax.plot([0, conv(g.width)], [conv(truss_z)] * 2, color=STRUCT, lw=1.5)
    else:
        top = g.ridge if s.type == "greenhouse" else g.height
        ax.plot([0, 0, conv(span), conv(span)], [0, conv(top), conv(top), 0], color=WALL, lw=1)
    # canopies (with tiers)
    for c in g.canopies:
        a0, a1 = (c.x0, c.x1) if axis == "x" else (c.y0, c.y1)
        h = min(0.25, c.z) if s.type in ("vertical_rack", "container") else c.z
        ax.add_patch(Rectangle((conv(a0), conv(c.z - h)), conv(a1 - a0), conv(h),
                               facecolor=CANOPY, edgecolor=CANOPY_EDGE, lw=0.5, alpha=0.8))
        if s.type in ("vertical_rack", "container"):
            ax.plot([conv(a0), conv(a1)], [conv(c.z - h)] * 2, color="#bbbbbb", lw=2)
    # fixtures
    seen = set()
    for l in res.luminaires:
        a = l.x if axis == "x" else l.y
        key = (round(a, 2), round(l.z, 2))
        if key in seen:
            continue
        seen.add(key)
        flen = l.fixture.length * res.spec.meta.to_m
        along = abs(np.cos(l.rotation)) if axis == "x" else abs(np.sin(l.rotation))
        w = max(flen * along, 0.25)
        ax.add_patch(Rectangle((conv(a - w / 2), conv(l.z)), conv(w), conv(0.08),
                               facecolor=FIXTURE, edgecolor="#7f0000", lw=0.3, zorder=5))
    d = res.distance_plane_to_fixture
    if res.luminaires and d:
        l0 = min(res.luminaires, key=lambda l: (l.z, l.x if axis == "x" else l.y))
        a = (l0.x if axis == "x" else l0.y)
        _dim(ax, conv(a), conv(l0.z - d), conv(a), conv(l0.z), _fmt_len(d, res),
             conv(span) * 0.03, vertical=True)
    ax.set_aspect("equal")
    ax.set_xlim(-conv(span) * 0.03, conv(span) * 1.03)
    ax.axis("off")
    ax.set_title("Front elevation" if axis == "x" else "Side elevation", fontsize=8)
    return _to_png(fig)


def iso_render(res: Results, figsize=(9, 5.5)) -> bytes:
    g = res.geometry
    s = res.spec.site
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")
    W, L = g.width, g.length
    polys, colors = [], []
    # floor
    polys.append([(0, 0, 0), (W, 0, 0), (W, L, 0), (0, L, 0)]); colors.append("#d9d9d9")
    for c in g.canopies:
        polys.append([(c.x0, c.y0, c.z), (c.x1, c.y0, c.z), (c.x1, c.y1, c.z), (c.x0, c.y1, c.z)])
        colors.append(CANOPY)
    ax.add_collection3d(Poly3DCollection(polys, facecolors=colors, edgecolors="#555555",
                                         linewidths=0.2, alpha=0.9))
    # envelope wireframe
    top = g.height
    for (x, y) in ((0, 0), (W, 0), (W, L), (0, L)):
        ax.plot([x, x], [y, y], [0, top], color=WALL, lw=0.6)
    for z in (top,):
        ax.plot([0, W, W, 0, 0], [0, 0, L, L, 0], [z] * 5, color=WALL, lw=0.6)
    if s.type == "greenhouse":
        bays = max(s.bays, 1)
        bw = W / bays
        for b in range(bays):
            for y in (0, L):
                ax.plot([b * bw, (b + .5) * bw, (b + 1) * bw], [y] * 3, [top, g.ridge, top], color=WALL, lw=0.6)
            ax.plot([(b + .5) * bw] * 2, [0, L], [g.ridge] * 2, color=WALL, lw=0.4)
    xs = [l.x for l in res.luminaires]
    if xs:
        ax.scatter(xs, [l.y for l in res.luminaires], [l.z for l in res.luminaires],
                   s=4, c=FIXTURE, depthshade=False)
    ax.set_box_aspect((W, L, max(g.ridge, g.height) * 1.2))
    ax.view_init(elev=28, azim=-58)
    ax.set_axis_off()
    return _to_png(fig, dpi=170)

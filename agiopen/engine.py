"""Calculation engine: fixture placement, point-by-point PPFD, statistics."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import catalog
from .geometry import Geometry, Rect, build_geometry
from .photometry import Batwing, CosinePower, Distribution, parse_ies
from .spec import Fixture, LayoutBlock, ProjectSpec, SpecError


@dataclass
class Luminaire:
    fixture: Fixture
    x: float
    y: float
    z: float  # bottom of fixture
    rotation: float  # radians, fixture length along +X when 0
    dimming: float
    group: str = ""

    @property
    def flux(self) -> float:
        return self.fixture.ppf * self.dimming

    @property
    def watts(self) -> float:
        return self.fixture.watts * self.dimming


@dataclass
class GridResult:
    label: str
    group: str
    rect: Rect
    xs: np.ndarray  # cell-centre X coordinates (m)
    ys: np.ndarray
    ppfd: np.ndarray  # shape (len(ys), len(xs)), µmol/s/m²
    plane_offset: float = 0.0  # metres below canopy top (0 = top)

    @property
    def avg(self) -> float:
        return float(self.ppfd.mean())

    @property
    def max(self) -> float:
        return float(self.ppfd.max())

    @property
    def min(self) -> float:
        return float(self.ppfd.min())

    @property
    def n_points(self) -> int:
        return int(self.ppfd.size)

    @property
    def min_avg(self) -> float:
        return self.min / self.avg if self.avg else 0.0

    @property
    def min_max(self) -> float:
        return self.min / self.max if self.max else 0.0


@dataclass
class Results:
    spec: ProjectSpec
    geometry: Geometry
    luminaires: list[Luminaire]
    grids: list[GridResult]
    reflected_ppfd: float = 0.0
    extra_grids: list[GridResult] = field(default_factory=list)

    @property
    def total_watts(self) -> float:
        return sum(l.watts for l in self.luminaires)

    @property
    def lpd_area_m2(self) -> float:
        if self.spec.site.type in ("vertical_rack", "container"):
            return self.geometry.canopy_area
        return self.geometry.floor_area

    @property
    def distance_plane_to_fixture(self) -> float:
        """Most common vertical gap between a fixture and the canopy right below it (m)."""
        gaps = []
        for l in self.luminaires:
            below = [g.rect.z for g in self.grids
                     if g.rect.x0 - 0.01 <= l.x <= g.rect.x1 + 0.01
                     and g.rect.y0 - 0.01 <= l.y <= g.rect.y1 + 0.01 and g.rect.z < l.z]
            if below:
                gaps.append(round(l.z - max(below), 3))
        if not gaps:
            return 0.0
        vals, counts = np.unique(gaps, return_counts=True)
        return float(vals[np.argmax(counts)])

    def schedule(self) -> list[dict]:
        """Luminaire schedule rows: one per (fixture, dimming level)."""
        rows: dict[tuple[str, float], dict] = {}
        for l in self.luminaires:
            key = (l.fixture.id, round(l.dimming, 3))
            r = rows.setdefault(key, {"fixture": l.fixture, "dimming": l.dimming, "qty": 0})
            r["qty"] += 1
        return list(rows.values())


# ---------------------------------------------------------------- distributions
_DIST_CACHE: dict[str, Distribution] = {}


def distribution_for(f: Fixture, base_dir: Path) -> Distribution:
    if f.ies_file:
        p = (base_dir / f.ies_file) if not Path(f.ies_file).is_absolute() else Path(f.ies_file)
        key = str(p.resolve())
        if key not in _DIST_CACHE:
            _DIST_CACHE[key] = parse_ies(p)
        return _DIST_CACHE[key]
    if f.photometry:
        key = f"catalog:{f.photometry}"
        if key not in _DIST_CACHE:
            try:
                _DIST_CACHE[key] = catalog.distribution(f.photometry)
            except catalog.CatalogError as exc:
                raise SpecError(f"Fixture '{f.id}': {exc}") from None
        return _DIST_CACHE[key]
    key = f"{f.distribution}:{f.beam_angle}:{f.batwing_power}:{f.cos_power}"
    if key not in _DIST_CACHE:
        if f.distribution == "batwing":
            _DIST_CACHE[key] = Batwing(f.beam_angle, f.batwing_power)
        elif f.distribution == "cosine":
            _DIST_CACHE[key] = CosinePower(f.cos_power)
        else:
            raise SpecError(f"Fixture '{f.id}': unknown distribution '{f.distribution}'.")
    return _DIST_CACHE[key]


# ---------------------------------------------------------------- placement
def _mount_z(spec: ProjectSpec, geo: Geometry, b: LayoutBlock, canopies: list[Rect]) -> float:
    k = spec.meta.to_m
    if b.mounting_height is not None:
        return b.mounting_height * k
    if b.distance_to_canopy is not None:
        return max(c.z for c in canopies) + b.distance_to_canopy * k
    return spec.site.truss_height * k


def _target_canopies(geo: Geometry, b: LayoutBlock) -> list[Rect]:
    cs = [c for c in geo.canopies if (not b.canopy or c.label == b.canopy)
          and (not b.group or c.group == b.group or not c.group)]
    if not cs:
        raise SpecError(f"Layout block for '{b.fixture}' matches no canopy.")
    return cs


def _even(n: int, lo: float, hi: float) -> np.ndarray:
    step = (hi - lo) / n
    return lo + step * (np.arange(n) + 0.5)


def _grid_positions(spec, geo, b: LayoutBlock, cols: int, rows: int, stagger: bool):
    k = spec.meta.to_m
    cs = _target_canopies(geo, b)
    x_lo, x_hi = min(c.x0 for c in cs), max(c.x1 for c in cs)
    y_lo, y_hi = min(c.y0 for c in cs), max(c.y1 for c in cs)
    if b.spacing_x and b.spacing_y:
        xs = b.origin_x * k + b.spacing_x * k * np.arange(cols)
        ys = b.origin_y * k + b.spacing_y * k * np.arange(rows)
        sx = b.spacing_x * k
    else:
        xs, ys = _even(cols, x_lo, x_hi), _even(rows, y_lo, y_hi)
        sx = (x_hi - x_lo) / cols
    pts = []
    for j, y in enumerate(ys):
        shift = sx / 2 if (stagger and j % 2) else 0.0
        for x in xs:
            xx = x + shift
            if stagger and j % 2 and xx > x_hi:
                continue
            pts.append((xx, y))
    return pts


def place(spec: ProjectSpec, geo: Geometry, blocks: list[LayoutBlock] | None = None) -> list[Luminaire]:
    k = spec.meta.to_m
    out: list[Luminaire] = []
    for b in blocks or spec.layout:
        f = spec.fixture(b.fixture)
        rot = math.radians(b.rotation_deg)
        if b.mode == "explicit":
            z_default = _mount_z(spec, geo, b, _target_canopies(geo, b)) if (
                b.mounting_height is not None or b.distance_to_canopy is not None
                or spec.site.truss_height) else 0.0
            for p in b.positions:
                z = p[2] * k if len(p) > 2 else z_default
                out.append(Luminaire(f, p[0] * k, p[1] * k, z, rot, b.dimming, b.group))
        elif b.mode in ("grid", "staggered"):
            if not (b.cols and b.rows):
                raise SpecError(f"Layout '{b.fixture}': grid mode needs rows and cols.")
            z = _mount_z(spec, geo, b, _target_canopies(geo, b))
            for x, y in _grid_positions(spec, geo, b, b.cols, b.rows, b.mode == "staggered"):
                out.append(Luminaire(f, x, y, z, rot, b.dimming, b.group))
        elif b.mode == "rack":
            out += _rack_positions(spec, geo, b, f)
        elif b.mode == "auto":
            out += _auto_layout(spec, geo, b, f)
    return out


def _rack_positions(spec, geo, b: LayoutBlock, f: Fixture) -> list[Luminaire]:
    """Linear bars end to end along each tier's length, `cols` bars across its width."""
    k = spec.meta.to_m
    bar = (f.length or 4.0) * k if spec.meta.units == "imperial" else (f.length or 1.2)
    out = []
    for c in _target_canopies(geo, b):
        n_long = max(int(math.floor(c.length / bar + 1e-6)), 1)
        cols = b.cols or max(int(round(c.width / (1.0 * k if k != 1 else 0.3))), 1)
        z = c.z + b.distance_to_canopy * k
        y_used = n_long * bar
        y0 = c.y0 + (c.length - y_used) / 2 + bar / 2
        for xi in _even(cols, c.x0, c.x1):
            for j in range(n_long):
                out.append(Luminaire(f, xi, y0 + j * bar, z, math.pi / 2, b.dimming, b.group))
    return out


def _auto_layout(spec, geo, b: LayoutBlock, f: Fixture) -> list[Luminaire]:
    """Pick the smallest regular grid whose average PPFD reaches the target band."""
    cs = _target_canopies(geo, b)
    x_lo, x_hi = min(c.x0 for c in cs), max(c.x1 for c in cs)
    y_lo, y_hi = min(c.y0 for c in cs), max(c.y1 for c in cs)
    area = sum(c.area for c in cs)
    target = spec.target.ppfd_mid
    z = _mount_z(spec, geo, b, cs)
    cu = 0.8
    best = None
    tried = set()
    for _ in range(8):
        n = max(int(math.ceil(target * area / (f.ppf * b.dimming * cu))), 1)
        aspect = (x_hi - x_lo) / (y_hi - y_lo)
        cols = max(int(round(math.sqrt(n * aspect))), 1)
        rows = max(int(math.ceil(n / cols)), 1)
        if (cols, rows) in tried:
            break
        tried.add((cols, rows))
        lums = [Luminaire(f, x, y, z, math.radians(b.rotation_deg), b.dimming, b.group)
                for x, y in _grid_positions(spec, geo, b, cols, rows, False)]
        avg = np.mean([g.avg for g in compute_grids(spec, geo, lums, coarse=True)[0]])
        ok = avg >= (spec.target.ppfd_min or target)
        if ok and (best is None or len(lums) < len(best[1])):
            best = (avg, lums)
        # Measured coefficient of utilisation for the next guess.
        cu = max(avg / (f.ppf * b.dimming * len(lums) / area), 0.05)
    if best is None:
        best = (avg, lums)
    return best[1]


# ---------------------------------------------------------------- calculation
def _auto_spacing(rect: Rect, imperial: bool) -> float:
    base = 0.3048 if imperial else 0.25
    step = base
    while (rect.width / step) * (rect.length / step) > 6000:
        step *= 1.5
    return step


def _sources(luminaires: list[Luminaire], spec: ProjectSpec):
    """Expand luminaires into point sources (linear fixtures -> segments)."""
    k = spec.meta.to_m
    xs, ys, zs, fl, rot, dist = [], [], [], [], [], []
    for l in luminaires:
        length = l.fixture.length * k
        n = max(int(math.ceil(length / 0.3)), 1) if length > 0.5 else 1
        offs = (np.arange(n) + 0.5) / n * length - length / 2 if n > 1 else np.zeros(1)
        for o in offs:
            xs.append(l.x + o * math.cos(l.rotation))
            ys.append(l.y + o * math.sin(l.rotation))
            zs.append(l.z)
            fl.append(l.flux * spec.calc.llf / n)
            rot.append(l.rotation)
            dist.append(distribution_for(l.fixture, spec.base_dir))
    return (np.array(xs), np.array(ys), np.array(zs), np.array(fl), np.array(rot), dist)


def _direct(px, py, pz, src, shelves: list[Rect]) -> np.ndarray:
    sx, sy, sz, fl, rot, dists = src
    E = np.zeros(px.shape[0])
    # group sources by distribution object for vectorised evaluation
    groups: dict[int, list[int]] = {}
    for i, d in enumerate(dists):
        groups.setdefault(id(d), []).append(i)
    for idxs in groups.values():
        idx = np.array(idxs)
        d = dists[idx[0]]
        for chunk in np.array_split(idx, max(1, len(idx) // 400 + 1)):
            dx = px[:, None] - sx[None, chunk]
            dy = py[:, None] - sy[None, chunk]
            dz = sz[None, chunk] - pz[:, None]
            r2 = dx * dx + dy * dy + dz * dz
            r = np.sqrt(r2)
            cos_t = np.where(dz > 0, dz / r, 0.0)
            theta = np.arccos(np.clip(cos_t, -1, 1))
            phi = np.arctan2(dy, dx) - rot[None, chunk]
            I = d.intensity(theta, phi)
            contrib = fl[None, chunk] * I * cos_t / np.maximum(r2, 1e-6)
            for sh in shelves:
                between = (sh.z > pz[:, None]) & (sh.z < sz[None, chunk])
                t = (sh.z - pz[:, None]) / np.where(dz > 0, dz, 1)
                ix = px[:, None] - dx * t
                iy = py[:, None] - dy * t
                hit = between & (ix > sh.x0) & (ix < sh.x1) & (iy > sh.y0) & (iy < sh.y1)
                contrib = np.where(hit, 0.0, contrib)
            E += contrib.sum(axis=1)
    return E


def _wall_images(src, geo: Geometry, rho: float, factor: float = 0.8):
    """First-order image sources across the four walls (lifts PPFD near reflective walls)."""
    sx, sy, sz, fl, rot, dists = src
    xs, ys, zs, fls, rots, ds = [], [], [], [], [], []
    for mx, my, ox, oy in ((-1, 1, 0.0, 0.0), (-1, 1, 2 * geo.width, 0.0),
                           (1, -1, 0.0, 0.0), (1, -1, 0.0, 2 * geo.length)):
        xs.append(ox + mx * sx); ys.append(oy + my * sy); zs.append(sz)
        fls.append(fl * rho * factor)
        rots.append(np.pi - rot if mx < 0 else -rot)
        ds += list(dists)
    return (np.concatenate(xs), np.concatenate(ys), np.concatenate(zs), np.concatenate(fls),
            np.concatenate(rots), ds)


def _reflected(spec: ProjectSpec, geo: Geometry, lums: list[Luminaire], direct_on_canopy: float,
               image_on_canopy: float = 0.0) -> float:
    """Uniform interreflected PPFD from a flux balance (integrating-sphere approximation)."""
    if not spec.calc.include_reflections:
        return 0.0
    phi_total = sum(l.flux for l in lums) * spec.calc.llf
    phi_rest = max(phi_total - direct_on_canopy, 0.0)
    receivers = [s for s in geo.surfaces if s.receives_direct and s.area > 0]
    a_recv = sum(s.area for s in receivers)
    first_bounce = direct_on_canopy * 0.26
    for s in receivers:
        first_bounce += phi_rest * (s.area / a_recv) * s.reflectance
    all_areas = geo.surfaces + []
    a_total = sum(s.area for s in all_areas) + geo.canopy_area
    rho_avg = (sum(s.area * s.reflectance for s in all_areas) + geo.canopy_area * 0.26) / a_total
    first_bounce = max(first_bounce - image_on_canopy, 0.0)
    return spec.calc.reflection_factor * first_bounce / (a_total * (1 - rho_avg))


def compute_grids(spec: ProjectSpec, geo: Geometry, lums: list[Luminaire], coarse: bool = False,
                  plane_offsets: tuple[float, ...] = (0.0,)):
    imperial = spec.meta.units == "imperial"
    src = _sources(lums, spec)
    walls = [s for s in geo.surfaces if s.kind == "wall"]
    rho_wall = walls[0].reflectance if walls else 0.0
    use_images = spec.calc.include_reflections and rho_wall > 0 and len(src[0])
    img = _wall_images(src, geo, rho_wall) if use_images else None
    image_flux = 0.0
    grids: list[GridResult] = []
    for off in plane_offsets:
        for c in geo.canopies:
            step = (spec.calc.grid_spacing * spec.meta.to_m) if spec.calc.grid_spacing else _auto_spacing(c, imperial)
            if coarse:
                step = max(step * 2, min(c.width, c.length) / 8)
            nx, ny = max(int(round(c.width / step)), 1), max(int(round(c.length / step)), 1)
            xs = c.x0 + (np.arange(nx) + 0.5) * c.width / nx
            ys = c.y0 + (np.arange(ny) + 0.5) * c.length / ny
            X, Y = np.meshgrid(xs, ys)
            Z = np.full(X.size, c.z - off)
            E = _direct(X.ravel(), Y.ravel(), Z, src, geo.shelves) if len(src[0]) else np.zeros(X.size)
            if img is not None:
                Ei = _direct(X.ravel(), Y.ravel(), Z, img, geo.shelves)
                if off == 0.0:
                    image_flux += Ei.mean() * c.area
                E = E + Ei
            grids.append(GridResult(c.label, c.group, c, xs, ys, E.reshape(ny, nx), off))
    top = [g for g in grids if g.plane_offset == 0.0]
    direct_flux = sum(g.avg * g.rect.area for g in top) - image_flux
    refl = _reflected(spec, geo, lums, direct_flux, image_flux)
    for g in grids:
        g.ppfd = g.ppfd + refl
    return grids, refl


def run(spec: ProjectSpec) -> Results:
    geo = build_geometry(spec)
    lums = place(spec, geo)
    k = spec.meta.to_m
    offsets = (0.0,) + tuple(o * k for o in spec.calc.extra_planes)
    grids, refl = compute_grids(spec, geo, lums, plane_offsets=offsets)
    main = [g for g in grids if g.plane_offset == 0.0]
    extra = [g for g in grids if g.plane_offset != 0.0]
    return Results(spec, geo, lums, main, refl, extra)

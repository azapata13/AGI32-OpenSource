"""Site geometry: canopies, room surfaces and greenhouse structure, all in metres."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .spec import Canopy, ProjectSpec


@dataclass
class Rect:
    """Axis-aligned horizontal rectangle (canopy top, shelf)."""

    label: str
    x0: float
    y0: float
    x1: float
    y1: float
    z: float
    reflectance: float = 0.26
    group: str = ""

    @property
    def area(self) -> float:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def length(self) -> float:
        return self.y1 - self.y0


@dataclass
class Surface:
    name: str
    kind: str  # floor | wall | ceiling | roof | structure | rack
    area: float
    reflectance: float
    transparency: float = 0.0
    receives_direct: bool = True


@dataclass
class Structure:
    """Line elements used only for drawings (posts, trusses, ridges, rack uprights)."""

    posts: list[tuple[float, float, float, float]] = field(default_factory=list)  # x, y, z0, z1
    trusses: list[tuple[float, float, float, float, float]] = field(default_factory=list)  # y, x0, x1, z, peak
    bay_lines: list[float] = field(default_factory=list)  # x positions of gutters


@dataclass
class Geometry:
    width: float
    length: float
    height: float
    ridge: float
    canopies: list[Rect]
    surfaces: list[Surface]
    structure: Structure
    shelves: list[Rect]  # opaque horizontal planes used for occlusion

    @property
    def floor_area(self) -> float:
        return self.width * self.length

    @property
    def canopy_area(self) -> float:
        return sum(c.area for c in self.canopies)


def _canopy_rect(c: Canopy, k: float) -> Rect:
    return Rect(c.label, c.x * k, c.y * k, (c.x + c.width) * k, (c.y + c.length) * k,
                c.height * k, c.reflectance, c.group)


def auto_greenhouse_canopies(spec: ProjectSpec, height: float | None = None,
                             margin: float | None = None) -> list[Canopy]:
    """One canopy per bay, leaving a margin along the outside walls (declared units)."""
    s = spec.site
    imperial = spec.meta.units == "imperial"
    height = height if height is not None else (3.0 if imperial else 0.9)
    margin = margin if margin is not None else (1.0 if imperial else 0.3)
    bay_w = s.width / max(s.bays, 1)
    out = []
    for b in range(max(s.bays, 1)):
        x0 = b * bay_w + (margin if b == 0 else 0.0)
        x1 = (b + 1) * bay_w - (margin if b == s.bays - 1 else 0.0)
        out.append(Canopy(f"Bay {b + 1}", x0, margin, x1 - x0, s.length - 2 * margin, height))
    return out


def build_geometry(spec: ProjectSpec) -> Geometry:
    k = spec.meta.to_m
    s = spec.site
    W, L, H = s.width * k, s.length * k, s.height * k
    canopies_src = spec.canopies or auto_greenhouse_canopies(spec)
    canopies = [_canopy_rect(c, k) for c in canopies_src]
    surfaces: list[Surface] = []
    structure = Structure()
    shelves: list[Rect] = []

    footprint = sum(c.area for c in canopies if c.z <= max(c.z for c in canopies))
    if s.type == "greenhouse":
        bays = max(s.bays, 1)
        bay_w = W / bays
        ridge = (s.ridge_height * k) if s.ridge_height else H + 0.35 * bay_w / max(s.peaks_per_bay, 1)
        rise = ridge - H
        roof_slope_len = np.hypot(bay_w / (2 * s.peaks_per_bay), rise) * 2 * s.peaks_per_bay
        glass_t = s.glazing_transmission
        surfaces += [
            Surface("Greenhouse floor", "floor", max(W * L - footprint, 0.0), 0.29),
            Surface("Glass / poly walls", "wall", 2 * (W + L) * H, 0.0, glass_t),
            Surface("Glass / poly roof", "roof", roof_slope_len * L * bays, 0.0, glass_t, False),
        ]
        truss_z = (s.truss_height * k) if s.truss_height else H
        spacing = (s.post_spacing * k) if s.post_spacing else (3.0 if k == 1.0 else 10 * k)
        n_frames = int(np.floor(L / spacing)) + 1
        struct_area = 0.0
        for j in range(n_frames):
            y = min(j * spacing, L)
            for b in range(bays + 1):
                structure.posts.append((b * bay_w, y, 0.0, H))
            for b in range(bays):
                structure.trusses.append((y, b * bay_w, (b + 1) * bay_w, truss_z, ridge))
            struct_area += W * 0.15 + (bays + 1) * H * 0.1
        structure.bay_lines = [b * bay_w for b in range(bays + 1)]
        surfaces.append(Surface("Posts and trusses", "structure", struct_area, s.structure_reflectance))
    else:
        ridge = H
        surfaces += [
            Surface("Floor", "floor", max(W * L - footprint, 0.0), s.floor_reflectance),
            Surface("Walls", "wall", 2 * (W + L) * H, s.wall_reflectance),
            Surface("Ceiling", "ceiling", W * L, s.ceiling_reflectance, 0.0, False),
        ]
        if s.type in ("vertical_rack", "container"):
            levels = sorted({round(c.z, 4) for c in canopies})
            if len(levels) > 1:
                # Every canopy except those on the top level has a shelf above it.
                for c in canopies:
                    above = [z for z in levels if z > c.z + 1e-6]
                    if above:
                        shelves.append(Rect(f"shelf over {c.label}", c.x0, c.y0, c.x1, c.y1,
                                            min(above) - 0.02, 0.8))
            rack_area = sum(c.area for c in canopies) * 0.5
            surfaces.append(Surface("White racking", "rack", rack_area, 0.8))
            for c in canopies:
                for (x, y) in ((c.x0, c.y0), (c.x1, c.y0), (c.x0, c.y1), (c.x1, c.y1)):
                    structure.posts.append((x, y, 0.0, c.z))
    return Geometry(W, L, H, ridge, canopies, surfaces, structure, shelves)

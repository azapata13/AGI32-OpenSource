"""ProjectSpec: the single input contract of the pipeline.

Client documents -> (intake) -> ProjectSpec JSON -> (engine) -> results -> (report) -> PDF.

Lengths in the JSON are expressed in the project's declared units (feet for imperial,
metres for metric). Internally everything is converted to metres.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Any

FT = 0.3048

SITE_TYPES = ("greenhouse", "indoor_room", "vertical_rack", "container")
LAYOUT_MODES = ("grid", "staggered", "rack", "explicit", "auto")


class SpecError(ValueError):
    """Raised when a ProjectSpec is incomplete or inconsistent."""


@dataclass
class Meta:
    project_name: str
    client: str = ""
    prepared_for: str = ""
    site_address: str = ""
    company: str = "AGI32 OpenSource"
    designer: str = ""
    date: str = field(default_factory=lambda: date.today().isoformat())
    revision: int = 1
    units: str = "imperial"
    design_hours: float = 0.0
    information_provided: list[str] = field(default_factory=list)
    comparison_labels: list[str] = field(default_factory=list)

    @property
    def to_m(self) -> float:
        return FT if self.units == "imperial" else 1.0

    @property
    def length_unit(self) -> str:
        return "ft" if self.units == "imperial" else "m"


@dataclass
class Fixture:
    id: str
    name: str
    watts: float
    ppf: float
    manufacturer: str = "Generic"
    family: str = ""
    description: str = ""
    warranty: str = ""
    dlc_reference: str = ""
    ies_file: str = ""
    # Generic distribution used when no IES file: I(theta) = I0 * cos(theta)^n.
    # n = 1 is Lambertian (~120 deg beam). Larger n = narrower beam.
    distribution: str = "batwing"  # batwing (wide toplight) | cosine
    beam_angle: float = 120.0  # full angle (deg) for batwing
    batwing_power: float = 1.5  # edge lift inside the beam: I ~ 1/cos^p (3 = flat field)
    cos_power: float = 1.0  # exponent n for cosine: I = I0 cos^n
    length: float = 0.0  # declared units; > 0 means a linear source (bar)
    width: float = 0.0
    image: str = ""  # optional product photo for the fixture page

    @property
    def efficacy(self) -> float:
        return round(self.ppf / self.watts, 2) if self.watts else 0.0


@dataclass
class Canopy:
    label: str
    x: float
    y: float
    width: float  # along X
    length: float  # along Y
    height: float  # top of canopy above floor
    reflectance: float = 0.26
    group: str = ""  # comparison option or zone label


@dataclass
class Site:
    type: str
    width: float  # X extent
    length: float  # Y extent
    height: float  # wall / gutter height
    # Greenhouse
    bays: int = 1
    roof: str = "gable"  # gable | barrel | venlo
    peaks_per_bay: int = 1
    ridge_height: float = 0.0
    truss_height: float = 0.0  # bottom of truss = default fixture mounting height
    post_spacing: float = 0.0
    glazing_transmission: float = 0.8
    structure_reflectance: float = 0.5
    # Rooms
    wall_reflectance: float = 0.8
    ceiling_reflectance: float = 0.8
    floor_reflectance: float = 0.2


@dataclass
class LayoutBlock:
    fixture: str
    mode: str = "grid"
    mounting_height: float | None = None  # bottom of fixture above floor
    distance_to_canopy: float | None = None  # alternative to mounting_height
    rows: int = 0  # along Y
    cols: int = 0  # along X
    spacing_x: float = 0.0
    spacing_y: float = 0.0
    origin_x: float = 0.0
    origin_y: float = 0.0
    rotation_deg: float = 0.0
    dimming: float = 1.0
    canopy: str = ""  # restrict "rack"/"auto" mode to one canopy label
    positions: list[list[float]] = field(default_factory=list)  # explicit [x, y(, z)]
    group: str = ""


@dataclass
class Target:
    ppfd_min: float = 0.0
    ppfd_max: float = 0.0
    uniformity_min: float = 0.0  # Min/Avg

    @property
    def ppfd_mid(self) -> float:
        if self.ppfd_min and self.ppfd_max:
            return (self.ppfd_min + self.ppfd_max) / 2
        return self.ppfd_min or self.ppfd_max


@dataclass
class Calc:
    grid_spacing: float = 0.0  # 0 = automatic
    include_reflections: bool = True
    reflection_factor: float = 0.6  # calibrated against reference AGi32 reports
    llf: float = 1.0
    extra_planes: list[float] = field(default_factory=list)  # offsets below canopy top


@dataclass
class ProjectSpec:
    meta: Meta
    site: Site
    fixtures: list[Fixture]
    canopies: list[Canopy]
    layout: list[LayoutBlock]
    target: Target = field(default_factory=Target)
    calc: Calc = field(default_factory=Calc)
    base_dir: Path = field(default=Path("."), repr=False)

    # ------------------------------------------------------------------ helpers
    def fixture(self, fixture_id: str) -> Fixture:
        for f in self.fixtures:
            if f.id == fixture_id:
                return f
        raise SpecError(f"Layout references unknown fixture '{fixture_id}'.")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("base_dir", None)
        return d

    @property
    def report_filename(self) -> str:
        name = self.meta.project_name
        if self.meta.revision > 1:
            name = f"{name} V{self.meta.revision}"
        parts = [f"{self.meta.company} Light Simulation"]
        if self.meta.client:
            parts.append(self.meta.client)
        parts += [name, self.meta.date]
        return " - ".join(parts) + ".pdf"


def _build(cls, data: dict[str, Any], where: str):
    known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
    unknown = set(data) - known
    if unknown:
        raise SpecError(f"{where}: unknown field(s) {sorted(unknown)}")
    try:
        return cls(**data)
    except TypeError as exc:  # missing required field
        raise SpecError(f"{where}: {exc}") from None


def load_spec(path: str | Path) -> ProjectSpec:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    spec = spec_from_dict(raw)
    spec.base_dir = path.parent
    return spec


def spec_from_dict(raw: dict[str, Any]) -> ProjectSpec:
    for key in ("meta", "site", "fixtures", "layout"):
        if key not in raw:
            raise SpecError(f"Missing top-level section '{key}'.")
    spec = ProjectSpec(
        meta=_build(Meta, raw["meta"], "meta"),
        site=_build(Site, raw["site"], "site"),
        fixtures=[_build(Fixture, f, f"fixtures[{i}]") for i, f in enumerate(raw["fixtures"])],
        canopies=[_build(Canopy, c, f"canopies[{i}]") for i, c in enumerate(raw.get("canopies", []))],
        layout=[_build(LayoutBlock, b, f"layout[{i}]") for i, b in enumerate(raw["layout"])],
        target=_build(Target, raw.get("target", {}), "target"),
        calc=_build(Calc, raw.get("calc", {}), "calc"),
    )
    validate(spec)
    return spec


def validate(spec: ProjectSpec) -> None:
    m, s = spec.meta, spec.site
    if m.units not in ("imperial", "metric"):
        raise SpecError("meta.units must be 'imperial' or 'metric'.")
    if s.type not in SITE_TYPES:
        raise SpecError(f"site.type must be one of {SITE_TYPES}.")
    for dim in ("width", "length", "height"):
        if getattr(s, dim) <= 0:
            raise SpecError(f"site.{dim} must be > 0.")
    if not spec.fixtures:
        raise SpecError("At least one fixture is required.")
    for f in spec.fixtures:
        if f.watts <= 0 or f.ppf <= 0:
            raise SpecError(f"Fixture '{f.id}': watts and ppf must be > 0.")
    if not spec.canopies and s.type != "greenhouse":
        raise SpecError("At least one canopy is required (greenhouses can derive one).")
    for b in spec.layout:
        spec.fixture(b.fixture)
        if b.mode not in LAYOUT_MODES:
            raise SpecError(f"layout.mode must be one of {LAYOUT_MODES}.")
        if b.mode == "explicit" and not b.positions:
            raise SpecError("layout mode 'explicit' needs positions.")
        if b.mode != "rack" and b.mounting_height is None and b.distance_to_canopy is None \
                and not s.truss_height:
            raise SpecError(
                "Each layout block needs mounting_height or distance_to_canopy "
                "(or site.truss_height for greenhouses)."
            )
        if b.mode == "rack" and b.distance_to_canopy is None:
            raise SpecError("layout mode 'rack' needs distance_to_canopy (fixture above each tier).")
        if b.mode == "auto" and not spec.target.ppfd_mid:
            raise SpecError("layout mode 'auto' needs target.ppfd_min/ppfd_max.")

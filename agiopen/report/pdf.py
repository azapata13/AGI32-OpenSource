"""PDF report in the standard horticultural light-simulation layout (see docs/report-format.md)."""
from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas

from .. import __version__
from ..engine import Results
from . import drawings

def _register_fonts():
    """DejaVu ships with matplotlib and covers µ, ², accents."""
    import matplotlib
    base = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("Sans", str(base / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Sans-Bold", str(base / "DejaVuSans-Bold.ttf")))


_register_fonts()

PAGE = landscape(letter)
M = 0.4 * inch
TITLE_H = 1.05 * inch
INK = colors.HexColor("#1f2a24")
RULE = colors.HexColor("#9aa59f")
HEAD_BG = colors.HexColor("#e7efe9")

DISCLAIMER = (
    "DISCLAIMER: Calculations follow IES and CIE practice. Measured values may differ from "
    "calculated results because of tolerances in calculation methods, testing procedures, "
    "component performance, measurement technique and field conditions such as voltage and "
    "temperature. Input data such as room dimensions, reflectances, furniture and architectural "
    "elements significantly affect the calculations; if real conditions do not match the input "
    "data, measured and calculated values will differ."
)

_small = ParagraphStyle("small", fontName="Sans", fontSize=5.6, leading=6.6, textColor=INK)
_cell = ParagraphStyle("cell", fontName="Sans", fontSize=7, leading=8.4, textColor=INK)
_body = ParagraphStyle("body", fontName="Sans", fontSize=11, leading=15, textColor=INK)


class Report:
    def __init__(self, res: Results):
        self.res = res
        self.spec = res.spec
        self.meta = res.spec.meta
        self.pages: list = []

    # ------------------------------------------------------------- frame
    def _title_block(self, c: canvas.Canvas, n: int, total: int):
        m = self.meta
        W, H = PAGE
        y0 = M
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(M, y0, W - 2 * M, TITLE_H)
        cols = [M, M + 3.9 * inch, M + 6.6 * inch, W - M - 1.9 * inch, W - M]
        for x in cols[1:-1]:
            c.line(x, y0, x, y0 + TITLE_H)
        c.setFillColor(INK)
        c.setFont("Sans-Bold", 6.6)
        c.drawString(cols[0] + 6, y0 + TITLE_H - 12,
                     f"{m.company}{' - ' + m.designer if m.designer else ''} - Horticulture Light Design")
        c.setFont("Sans", 7)
        lines = [f"Project Name : {self._project_label()}", m.site_address,
                 f"Prepared For: {m.prepared_for}" if m.prepared_for else ""]
        for i, t in enumerate([t for t in lines if t]):
            c.drawString(cols[0] + 6, y0 + TITLE_H - 24 - 10 * i, t[:70])
        p = Paragraph(DISCLAIMER, _small)
        p.wrapOn(c, cols[2] - cols[1] - 10, TITLE_H)
        p.drawOn(c, cols[1] + 5, y0 + 4)
        c.setFont("Sans", 6.5)
        fn = f"Filename: {self._model_filename()}"
        while pdfmetrics.stringWidth(fn, "Sans", 6.5) > cols[3] - cols[2] - 10 and len(fn) > 12:
            fn = fn[:-2]
        c.drawString(cols[2] + 6, y0 + TITLE_H - 12, fn)
        c.drawString(cols[2] + 6, y0 + TITLE_H - 24, f"By : {m.designer}")
        c.drawString(cols[2] + 6, y0 + TITLE_H - 36, f"Units: {m.units.capitalize()}")
        c.drawString(cols[3] + 6, y0 + TITLE_H - 12, f"Date: {m.date}")
        c.drawString(cols[3] + 6, y0 + TITLE_H - 24, f"Engine: agiopen {__version__}")
        c.drawString(cols[3] + 6, y0 + TITLE_H - 36, f"Total Time (Hrs.): {m.design_hours:.2f}")
        c.setFont("Sans-Bold", 8)
        c.drawRightString(W - M - 6, y0 + 8, f"Page {n} of {total}")

    def _project_label(self) -> str:
        n = self.meta.project_name
        return f"{n} V{self.meta.revision}" if self.meta.revision > 1 else n

    def _model_filename(self) -> str:
        return f"{self._project_label()}.json"

    def _area(self):
        W, H = PAGE
        return M, M + TITLE_H + 8, W - 2 * M, H - 2 * M - TITLE_H - 8

    def _img(self, c, png: bytes, x, y, w, h):
        img = ImageReader(io.BytesIO(png))
        iw, ih = img.getSize()
        s = min(w / iw, h / ih)
        c.drawImage(img, x + (w - iw * s) / 2, y + (h - ih * s) / 2, iw * s, ih * s)

    def _heading(self, c, text, x, y, size=13):
        c.setFont("Sans-Bold", size)
        c.setFillColor(INK)
        c.drawString(x, y, text)

    # ------------------------------------------------------------- tables
    def _table(self, rows, col_w, title=None):
        data = [[Paragraph(str(v), _cell) for v in r] for r in rows]
        t = Table(data, colWidths=col_w)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return t

    def calc_summary_rows(self, grids=None):
        rows = [["Label", "CalcType", "Units", "Avg", "Max", "Min", "Min/Avg", "Min/Max", "# Pts"]]
        for g in grids or self.res.grids:
            label = f"{g.label}_Top" if g.plane_offset == 0 else \
                f"{g.label}_-{drawings._fmt_len(g.plane_offset, self.res)}"
            rows.append([label, "PPFD", "µmol/s/m²", f"{g.avg:.2f}", f"{g.max:.0f}",
                         f"{g.min:.0f}", f"{g.min_avg:.2f}", f"{g.min_max:.2f}", g.n_points])
        return rows

    def schedule_rows(self):
        rows = [["Symbol", "Qty", "LLF", "Description", "Lum. Watts", "Total Watts",
                 "Manufacturer", "Luminaire PPF"]]
        for i, r in enumerate(self.res.schedule()):
            f, dim, q = r["fixture"], r["dimming"], r["qty"]
            desc = f.description or f.name
            if dim < 0.999:
                desc += f" (dimmed {dim * 100:.0f})"
            rows.append([chr(65 + i), q, f"{self.spec.calc.llf:.3f}", desc, f"{f.watts * dim:.0f}",
                         f"{f.watts * dim * q:.0f}", f.manufacturer, f"{f.ppf * dim:.0f}"])
        return rows

    def lpd_rows(self):
        imperial = self.meta.units == "imperial"
        a = self.res.lpd_area_m2
        area = a / 0.092903 if imperial else a
        w = self.res.total_watts
        unit = "Watts/Sq.Ft." if imperial else "Watts/Sq.m"
        label = "LPDArea_" + ("racking" if self.spec.site.type in ("vertical_rack", "container")
                              else "Growing area")
        return [["Label", "Area", "Total Watts", "LPD", "LPD Units"],
                [label, f"{area:.0f}", f"{w:.0f}", f"{w / area:.3f}", unit]]

    # ------------------------------------------------------------- pages
    def page_cover(self, c):
        x, y, w, h = self._area()
        fam = ", ".join(dict.fromkeys(f.family or f.name for f in self._used_fixtures()))
        c.setFont("Sans-Bold", 20)
        c.setFillColor(INK)
        c.drawString(x, y + h - 22, f"LED Grow Light Plan Using: {fam}")
        self._img(c, drawings.iso_render(self.res), x, y, w, h - 40)

    def _used_fixtures(self):
        seen = {}
        for l in self.res.luminaires:
            seen.setdefault(l.fixture.id, l.fixture)
        return list(seen.values())

    def page_fixture(self, c, f):
        x, y, w, h = self._area()
        self._heading(c, f.family or f.name, x, y + h - 22, 18)
        lines = [f"Power: {f.watts:.0f}W", f"PPF: {f.ppf:,.0f} umols/s",
                 f"Efficacy: {f.efficacy} umols/J"]
        if f.warranty:
            lines.append(f"Warranty: {f.warranty}")
        if f.dlc_reference:
            lines.append(f"DLC Listing Reference: {f.dlc_reference}")
        c.setFont("Sans", 12)
        for i, t in enumerate(lines):
            c.drawString(x, y + h - 60 - 20 * i, t)
        if f.image:
            p = Path(self.spec.base_dir) / f.image
            if p.exists():
                self._img(c, p.read_bytes(), x + w * 0.45, y, w * 0.55, h - 40)

    def page_info(self, c):
        x, y, w, h = self._area()
        self._heading(c, "Information Provided:", x, y + h - 22)
        yy = y + h - 50
        for t in self.meta.information_provided:
            p = Paragraph(f"• {t}", _body)
            _, ph = p.wrapOn(c, w * 0.8, h)
            p.drawOn(c, x + 10, yy - ph)
            yy -= ph + 6

    def page_results(self, c):
        x, y, w, h = self._area()
        self._heading(c, "Results Summary", x, y + h - 20)
        d = self.res.distance_plane_to_fixture
        c.setFont("Sans", 10)
        c.drawString(x, y + h - 38, "Distance Between Calculation Plane and Fixture: "
                     f"{drawings._fmt_len(d, self.res)} - See Layout")
        yy = y + h - 52
        blocks = [
            ("Calculation Summary", self.calc_summary_rows(),
             [2.6 * inch, .7 * inch, .9 * inch, .7 * inch, .6 * inch, .6 * inch, .7 * inch, .7 * inch, .6 * inch]),
            ("Luminaire Schedule", self.schedule_rows(),
             [.65 * inch, .45 * inch, .6 * inch, 3.4 * inch, .8 * inch, .9 * inch, 1.2 * inch, 1.0 * inch]),
            ("LPD Area Summary", self.lpd_rows(), [2.6 * inch, 1 * inch, 1.1 * inch, 1 * inch, 1.2 * inch]),
        ]
        for title, rows, cw in blocks:
            c.setFont("Sans-Bold", 9)
            c.drawString(x, yy - 10, title)
            t = self._table(rows, cw)
            _, th = t.wrapOn(c, w, h)
            t.drawOn(c, x, yy - 14 - th)
            yy -= th + 30
        note = ("*Important note regarding uniformity: values cover every calculation point of the "
                "growing area, edges included. Uniformity measured between a few fixtures in the "
                "middle of the area will be higher. See the point-by-point pages for details.")
        p = Paragraph(note, _cell)
        _, ph = p.wrapOn(c, w * 0.55, 60)
        p.drawOn(c, x, y + 4)
        # approval block
        bx, bw = x + w - 3.6 * inch, 3.6 * inch
        c.setFont("Sans-Bold", 9)
        c.drawString(bx, y + 62, "Light Level Approval")
        c.setFont("Sans", 8)
        for i, lab in enumerate(("Customer Signature", f"{self.meta.company} Rep")):
            yy2 = y + 40 - 26 * i
            c.line(bx, yy2, bx + 2.2 * inch, yy2)
            c.line(bx + 2.4 * inch, yy2, bx + bw, yy2)
            c.drawString(bx, yy2 - 9, lab)
            c.drawString(bx + 2.4 * inch, yy2 - 9, "Date")

    def page_legend(self, c):
        x, y, w, h = self._area()
        self._heading(c, "Lighting Design Legend and Reflectivities Applied", x, y + h - 20)
        rows = [["Surface", "Reflectivity", "Transparency"],
                ["Plant canopy (calculation plane)", "26% (green plants)", "0%"]]
        for s in self.res.geometry.surfaces:
            rows.append([s.name, f"{s.reflectance * 100:.0f}%", f"{s.transparency * 100:.0f}%"])
        rows.append([".IES file / LED fixture", "N/A", "N/A"])
        t = self._table(rows, [2.6 * inch, 1.3 * inch, 1.1 * inch])
        _, th = t.wrapOn(c, w, h)
        t.drawOn(c, x, y + h - 40 - th)
        self._img(c, drawings.plan_view(self.res, figsize=(6, 4)), x + w * 0.45, y + h * 0.42, w * 0.55, h * 0.55)
        self._img(c, drawings.elevation(self.res, "x", figsize=(6, 2.6)), x + w * 0.45, y, w * 0.55, h * 0.4)

    def page_plan(self, c):
        x, y, w, h = self._area()
        strip = self._summary_strip(c, x, y, w)
        self._img(c, drawings.plan_view(self.res), x, y + strip + 6, w, h - strip - 6)

    def _summary_strip(self, c, x, y, w) -> float:
        """Luminaire schedule and calculation summary under the plan; returns height used."""
        t1 = self._table(self.schedule_rows(),
                         [.6 * inch, .4 * inch, .5 * inch, 2.9 * inch, .7 * inch, .8 * inch, 1.1 * inch, .9 * inch])
        _, h1 = t1.wrapOn(c, w, 2 * inch)
        t2 = self._table(self.calc_summary_rows(),
                         [2.2 * inch, .6 * inch, .8 * inch, .6 * inch, .5 * inch, .5 * inch, .6 * inch, .6 * inch, .5 * inch])
        _, h2 = t2.wrapOn(c, w, 2 * inch)
        t2.drawOn(c, x, y)
        t1.drawOn(c, x, y + h2 + 4)
        return h1 + h2 + 4

    def page_points(self, c, zoom=False, grid=None):
        x, y, w, h = self._area()
        region = drawings.zoom_region(self.res) if zoom else None
        title = "Point by point - zoom" if zoom else "Point by point"
        if grid is not None:
            title += f" - {grid.label}"
            gr = grid
            pad = 0.15 * max(gr.rect.width, gr.rect.length)
            region = ((gr.rect.x0 - pad, gr.rect.x1 + pad), (gr.rect.y0 - pad, gr.rect.y1 + pad))
        self._heading(c, title, x, y + h - 14, 10)
        png = drawings.plan_view(self.res, show_values=True, region=region,
                                 grids=[grid] if grid is not None else None)
        self._img(c, png, x, y, w, h - 20)

    def _overlapping_grids(self) -> bool:
        gs = self.res.grids
        for i, a in enumerate(gs):
            for b in gs[i + 1:]:
                if a.rect.x0 < b.rect.x1 and b.rect.x0 < a.rect.x1 and \
                        a.rect.y0 < b.rect.y1 and b.rect.y0 < a.rect.y1:
                    return True
        return False

    def page_elevation(self, c):
        x, y, w, h = self._area()
        self._img(c, drawings.elevation(self.res, "x"), x, y + h / 2, w, h / 2)
        self._img(c, drawings.elevation(self.res, "y"), x, y, w, h / 2)

    def page_planes(self, c):
        x, y, w, h = self._area()
        self._heading(c, "Canopy height sensitivity", x, y + h - 20)
        c.setFont("Sans", 9)
        c.drawString(x, y + h - 38, "PPFD on planes below the canopy top. A sensor left in place "
                     "while the crop grows reads one of these planes, not the top.")
        t = self._table(self.calc_summary_rows(self.res.grids + self.res.extra_grids),
                        [2.8 * inch, .7 * inch, .9 * inch, .7 * inch, .6 * inch, .6 * inch, .7 * inch, .7 * inch, .6 * inch])
        _, th = t.wrapOn(c, w, h)
        t.drawOn(c, x, y + h - 52 - th)

    # ------------------------------------------------------------- build
    def build(self, out: str | Path) -> Path:
        out = Path(out)
        plan = [self.page_cover]
        plan += [lambda c, f=f: self.page_fixture(c, f) for f in self._used_fixtures()]
        if self.meta.information_provided:
            plan.append(self.page_info)
        plan += [self.page_results, self.page_legend, self.page_plan]
        if self._overlapping_grids():  # stacked tiers: one point-by-point page per tier
            plan += [lambda c, g=g: self.page_points(c, grid=g) for g in self.res.grids]
        else:
            plan += [lambda c: self.page_points(c, False), lambda c: self.page_points(c, True)]
        plan.append(self.page_elevation)
        if self.res.extra_grids:
            plan.append(self.page_planes)
        c = canvas.Canvas(str(out), pagesize=PAGE)
        c.setTitle(out.stem)
        c.setAuthor(self.meta.designer or self.meta.company)
        for i, page in enumerate(plan, 1):
            page(c)
            self._title_block(c, i, len(plan))
            c.showPage()
        c.save()
        return out


def build_report(res: Results, out_dir: str | Path = ".", filename: str | None = None) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return Report(res).build(out_dir / (filename or res.spec.report_filename))

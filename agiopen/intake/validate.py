"""Gaps a designer should confirm before sending the summary to the client."""
from __future__ import annotations

from ..spec import ProjectSpec


def missing_information(spec: ProjectSpec) -> list[str]:
    out: list[str] = []
    m, s, t = spec.meta, spec.site, spec.target
    if not m.prepared_for:
        out.append("meta.prepared_for: name of the person receiving the report.")
    if not m.site_address:
        out.append("meta.site_address: city / address shown in the header.")
    if not (t.ppfd_min or t.ppfd_max):
        out.append("target: no PPFD or DLI target given; results cannot be judged against a goal.")
    for f in spec.fixtures:
        if not f.ies_file and f.photometry:
            from ..catalog import photometry
            info = photometry(f.photometry)
            if info.get("confidence") != "high":
                out.append(f"fixture '{f.id}': no IES file, catalog curve '{f.photometry}' is used "
                           f"(confidence {info.get('confidence')}: {info.get('source')}). "
                           "Ask the manufacturer for the IES file.")
        elif not f.ies_file:
            out.append(f"fixture '{f.id}': no IES file, a generic {f.distribution} distribution is "
                       "used. Add the manufacturer IES file for report-grade accuracy.")
        if not f.warranty:
            out.append(f"fixture '{f.id}': warranty missing on the fixture page.")
    if s.type == "greenhouse":
        if not s.truss_height:
            out.append("site.truss_height: bottom of truss (fixture mounting height) not given.")
        if not spec.canopies:
            out.append("canopies: none given, one canopy per bay at the default height is assumed.")
    if s.type in ("vertical_rack", "container") and len({c.height for c in spec.canopies}) < 2:
        out.append("canopies: vertical racks usually have several tiers; only one height found.")
    if not m.information_provided:
        out.append("meta.information_provided: no client statements recorded for page 3.")
    return out

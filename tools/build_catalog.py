"""Datasheet values -> agiopen/catalog/fixtures.json. Edit the tables below and rerun."""
import json
from pathlib import Path

OUT = Path(__file__).parents[1] / "agiopen" / "catalog"
DLI_SRC = "https://hortamericascanada.com (DLI datasheet, 347-400V)"
fixtures = []

def dli(model, watts, spectrum, ppf, eff, dims, kg):
    fam = "DLI NXS" if model == "NXS" else "DLI Vertex"
    sid = spectrum.lower().replace("-", "")
    fixtures.append({
        "id": f"dli-{model.lower()}-{watts}w-{sid}",
        "manufacturer": "DLI", "family": fam,
        "name": f"DLI {model} {watts}W 347-400V {spectrum}" + " MW",
        "watts": watts, "ppf": ppf, "efficacy": eff, "spectrum": spectrum,
        "length_mm": dims[0], "width_mm": dims[1], "height_mm": dims[2], "weight_kg": kg,
        "voltage": "347-400V", "ip": "IP65", "dimming": "20-100%", "certification": "CSA, DLC",
        "warranty": "", "photometry": "dli-nxs-mw" if model == "NXS" else "dli-vertex-mw",
        "source": DLI_SRC,
    })

NXS = (670, 305, 100)
dli("NXS", 375, "R90G5B5", 1400, 3.73, NXS, 9)
for s in ("R85G5B5FR5", "R90G5B5"):
    dli("NXS", 540, s, 2000, 3.70, NXS, 9)
for s in ("R85G5B5FR5", "R87G8B5-FR8", "R90G5B5-FR8", "R90G5B5"):
    dli("NXS", 670, s, 2500, 3.73, NXS, 9)
for s in ("R100-G5B5", "R85G5B5FR5", "R87G8B5-FR8", "R90G5B5-FR8", "R90G5B5"):
    dli("NXS", 760, s, 2800, 3.68, NXS, 9)
V82, V94 = (820, 260, 133), (945, 260, 133)
dli("Vertex", 795, "R90G5B5", 2950, 3.71, V82, 11.0)
dli("Vertex", 870, "R85G5B5FR5", 3080, 3.54, V82, 11.0)
dli("Vertex", 870, "R87G8B5-FR8", 3080, 3.54, V82, 11.0)
dli("Vertex", 870, "R90G5B5", 3150, 3.62, V82, 11.0)
dli("Vertex", 870, "R90G5B5-FR8", 3150, 3.62, V82, 11.0)
dli("Vertex", 970, "R82G12B6-FR9", 3350, 3.45, V94, 12.4)
dli("Vertex", 1050, "R85G5B5FR5", 3800, 3.62, V94, 12.4)
dli("Vertex", 1050, "R87G8B5-FR8", 3800, 3.62, V94, 12.4)
dli("Vertex", 1050, "R90G5B5-FR8", 3925, 3.74, V94, 12.4)
dli("Vertex", 1050, "R90G5B5", 3925, 3.73, V94, 12.4)
dli("Vertex", 1170, "R90G5B5", 4400, 3.76, (892, 307, 135), 14.5)

PL_W = "5 year limited warranty"
def pl(fid, family, name, watts, ppf, eff, spectrum, dims, kg, photometry, src, **extra):
    e = {"id": fid, "manufacturer": "P.L. Light Systems", "family": family, "name": name,
         "watts": watts, "ppf": ppf, "efficacy": eff, "spectrum": spectrum,
         "length_mm": dims[0], "width_mm": dims[1], "height_mm": dims[2], "weight_kg": kg,
         "warranty": PL_W, "photometry": photometry, "source": src}
    e.update(extra)
    fixtures.append(e)

def slug(s):
    return s.lower().replace(":", "").replace("-", "")

PARFX = "https://pllight.com/parfx-ultra/"
lite = [("R90W5B5", 2185, 3.6), ("R80W5B7FR8", 2005, 3.4), ("R37W37B18FR8", 1557, 2.6),
        ("R57W30B12FR1", 1722, 2.9), ("R40W40B18FR2", 1588, 2.6)]
for s, p, e in lite:
    pl(f"pl-parfx-ultra-lite-600w-{slug(s)}", "PL ParFX Ultra Lite", f"ParFX Ultra Lite 600W {s}",
       600, p, e, s, (495, 306, 93), 9.4, "pl-parfx-medium-wide", PARFX, voltage="277-400V", ip="IP66")
ultra = [("R95B5", 2827, 3.7), ("R90W5B5", 2774, 3.7), ("R80W5B7FR8", 2849, 3.8),
         ("R37W37B18FR8", 2215, 2.9), ("R57W30B12FR1", 2189, 2.9), ("R78W9B5FR8", 2819, 3.8),
         ("R85W5B5FR5", 2929, 3.6)]
for s, p, e in ultra:
    pl(f"pl-parfx-ultra-750w-{slug(s)}", "PL ParFX Ultra", f"ParFX Ultra 750W {s}",
       750, p, e, s, (620, 296, 91), 10, "pl-parfx-medium-wide", PARFX, voltage="277-400V", ip="IP66")
plus = [("R95B5", 4019, 3.9), ("R90W5B5", 3813, 3.7), ("R80W5B7FR8", 3945, 3.8),
        ("R37W37B18FR8", 2990, 2.9), ("R57W30B12FR1", 3140, 3.0), ("R78W9B5FR8", 3869, 3.8),
        ("R85W5B5FR5", 3817, 3.7), ("R40W40B18FR2", 2765, 2.7)]
for s, p, e in plus:
    pl(f"pl-parfx-ultra-plus-1040w-{slug(s)}", "PL ParFX Ultra Plus", f"ParFX Ultra Plus 1040W {s}",
       1040, p, e, s, (582, 355, 105), 13, "pl-parfx-medium-wide", PARFX, voltage="277-400V", ip="IP66")
pl("pl-parfx-ultra-plus-2ch-1040w-r90w5b5fr8", "PL ParFX Ultra Plus", "ParFX Ultra Plus 2CH 1040W R90W5B5 (+FR 95W)",
   1040, 3744, 3.6, "R90W5B5 (+FR channel)", (582, 355, 105), 13, "pl-parfx-medium-wide", PARFX,
   notes="Mode 1 (CH1 on). CH1+CH2 (1135 W): 3716 umol/s.")
pl("pl-parfx-ultra-max-2ch-1170w-r90w5b5fr8", "PL ParFX Ultra Max", "ParFX Ultra Max 2CH 1170W R90W5B5 (+FR 115W)",
   1170, 4308, 3.68, "R90W5B5 (+FR channel)", (708, 355, 105), 15.8, "pl-parfx-medium-wide", PARFX,
   notes="Mode 1 (CH1 on). CH1+CH2 (1285 W): 4274 umol/s.")
for s, p, e in [("R95B5", 4585, 3.82), ("R89W5B6", 4345, 3.62), ("R81W5B6FR8", 4270, 3.56)]:
    pl(f"pl-parfx-ultra-max-3ch-1200w-{slug(s)}", "PL ParFX Ultra Max", f"ParFX Ultra Max 3CH {s}",
       1200, p, e, s, (708, 385, 105), 16.0, "pl-parfx-ultra-wide", PARFX,
       notes="Sample recipe of a dynamic 3-channel fixture; watts = PPF / efficacy.")
for s, p, e in [("R95B5", 5180, 4.26), ("R90W5B5", 4950, 4.07), ("R80W7B5FR8", 4807, 3.95), ("R76W6B8FR10", 4783, 3.93)]:
    pl(f"pl-parfx-ultra-max-4ch-1216w-{slug(s)}", "PL ParFX Ultra Max", f"ParFX Ultra Max 4CH {s}",
       1216, p, e, s, (722, 385, 116), 0, "pl-parfx-ultra-wide", PARFX,
       notes="Sample recipe of a dynamic 4-channel fixture; watts = PPF / efficacy.")
pl("pl-vertimax-640w", "PL VertiMax", "VertiMax 640W", 640, 1800, 2.8, "", (1144, 1187, 78), 12.5,
   "lambertian", "https://pllight.com/vertimax/",
   notes="Large flat panel for vertical farms; modelled as a Lambertian source along its length.")
for s, p, e in [("R90W5B5", 805, 3.5), ("R79W8B5FR8", 780, 3.4), ("R95B5", 830, 3.6),
                ("R44W33B23", 600, 2.6), ("R37W37B18FR8", 628, 2.7)]:
    pl(f"pl-balensbeam-230w-{slug(s)}", "PL BalensBeam", f"BalensBeam 230W {s}", 230, p, e, s,
       (1244, 101, 86), 4.17, "lambertian", "https://pllight.com/balensbeam/", linear=True)
for s, p, e in [("R33W56B11", 354, 2.9), ("R61W26B13", 373, 3.0)]:
    pl(f"pl-budboost-120w-{slug(s)}", "PL BudBoost", f"BudBoost 120W {s}", 120, p, e, s,
       (1133, 90, 82), 2.7, "lambertian", "https://pllight.com/budboost/", linear=True)
for n, w, p in [(1, 338, 1042), (2, 670.8, 2084)]:
    pl(f"pl-triplane-linear-ho-rwmb-{n}m", "PL TriPlane Linear", f"TriPlane Linear HO RWMB ({n} module{'s' if n > 1 else ''})",
       w, p, 3.3, "RWMB", (0, 0, 0), 0, "lambertian", "https://pllight.com/triplane-linear/",
       notes="1-module watts are AC-derated per module (the driver needs 2 modules). Modular linear system (Standard / Wide / Focused / Asymmetric optics); set length to the installed run.")
for n, w, p in [(1, 320, 825), (2, 641.1, 1651)]:
    pl(f"pl-triplane-linear-ho-daylight-{n}m", "PL TriPlane Linear", f"TriPlane Linear HO Daylight ({n} module{'s' if n > 1 else ''})",
       w, p, 2.6, "Daylight", (0, 0, 0), 0, "lambertian", "https://pllight.com/triplane-linear/",
       notes="Modular linear system; set length to the installed run.")
for n, w, p in [(1, 350, 1105), (2, 705.1, 2209)]:
    pl(f"pl-triplane-linear-ho-rwmbfr-{n}m", "PL TriPlane Linear", f"TriPlane Linear HO RWMB_FR ({n} module{'s' if n > 1 else ''})",
       w, p, 3.1, "RWMB_FR", (0, 0, 0), 0, "lambertian", "https://pllight.com/triplane-linear/",
       notes="Modular linear system; set length to the installed run.")

ids = [f["id"] for f in fixtures]
assert len(ids) == len(set(ids)), "duplicate ids"
doc = {"note": "Values copied from manufacturer datasheets (DLI datasheets via hortamericascanada.com, "
               "P.L. Light spec sheets via pllight.com, 2026). PPF in umol/s (400-800 nm for DLI, "
               "350-800 nm for P.L. Light). Check the current datasheet before quoting.",
       "fixtures": fixtures}
(OUT / "fixtures.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
print(len(fixtures), "fixtures")

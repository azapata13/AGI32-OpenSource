"""Regenerate schemas/project.schema.json from the dataclasses in agiopen/spec.py."""
import json
import sys
import typing
from dataclasses import MISSING, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from agiopen import spec as S  # noqa: E402

PY = {str: "string", float: "number", int: "integer", bool: "boolean"}


def prop(tp):
    origin = typing.get_origin(tp)
    if origin in (list,):
        (arg,) = typing.get_args(tp)
        return {"type": "array", "items": prop(arg)}
    if origin in (typing.Union, getattr(__import__("types"), "UnionType", None)):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        return {**prop(args[0]), "nullable": True}
    return {"type": PY.get(tp, "object")}


def obj(cls):
    hints = typing.get_type_hints(cls)
    props, req = {}, []
    for f in fields(cls):
        if f.name == "base_dir":
            continue
        props[f.name] = prop(hints[f.name])
        if f.default is MISSING and f.default_factory is MISSING:
            req.append(f.name)
    return {"type": "object", "additionalProperties": False, "properties": props, "required": req}


schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "AGI32 OpenSource ProjectSpec",
    "type": "object",
    "required": ["meta", "site", "fixtures", "layout"],
    "properties": {
        "meta": obj(S.Meta), "site": obj(S.Site),
        "fixtures": {"type": "array", "items": obj(S.Fixture)},
        "canopies": {"type": "array", "items": obj(S.Canopy)},
        "layout": {"type": "array", "items": obj(S.LayoutBlock)},
        "target": obj(S.Target), "calc": obj(S.Calc),
    },
}
schema["properties"]["site"]["properties"]["type"]["enum"] = list(S.SITE_TYPES)
schema["properties"]["layout"]["items"]["properties"]["mode"]["enum"] = list(S.LAYOUT_MODES)
schema["properties"]["meta"]["properties"]["units"]["enum"] = ["imperial", "metric"]
schema["properties"]["fixtures"]["items"]["properties"]["distribution"]["enum"] = ["batwing", "cosine"]
out = Path(__file__).parents[1] / "schemas" / "project.schema.json"
out.write_text(json.dumps(schema, indent=2) + "\n")
print(f"wrote {out}")

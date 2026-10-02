"""Draft a ProjectSpec from client documents with a Claude model.

Needs `pip install anthropic` and ANTHROPIC_API_KEY. PDFs and images (plans, drawings, spec
sheets) are sent as-is so the model can read dimensions from drawings; text-like files are
inlined. The draft is validated; whatever the model could not determine comes back in
`missing` for the designer to confirm with the client.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from pathlib import Path

from ..spec import SpecError, spec_from_dict
from .validate import missing_information

PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")
SCHEMA = (Path(__file__).parents[2] / "schemas" / "project.schema.json")
DEFAULT_MODEL = os.environ.get("AGIOPEN_MODEL", "claude-sonnet-5-5")


def _blocks(paths: list[Path]) -> list[dict]:
    blocks: list[dict] = []
    for p in paths:
        mime = mimetypes.guess_type(p.name)[0] or ""
        data = p.read_bytes()
        if mime == "application/pdf":
            blocks.append({"type": "document", "title": p.name, "source": {
                "type": "base64", "media_type": mime, "data": base64.b64encode(data).decode()}})
        elif mime.startswith("image/"):
            blocks.append({"type": "text", "text": f"Image: {p.name}"})
            blocks.append({"type": "image", "source": {
                "type": "base64", "media_type": mime, "data": base64.b64encode(data).decode()}})
        elif p.suffix.lower() == ".docx":
            try:
                import docx  # python-docx
            except ImportError as exc:
                raise SpecError("Reading .docx needs `pip install python-docx`.") from exc
            text = "\n".join(par.text for par in docx.Document(str(p)).paragraphs)
            blocks.append({"type": "text", "text": f"--- {p.name} ---\n{text}"})
        else:
            blocks.append({"type": "text",
                           "text": f"--- {p.name} ---\n{data.decode('utf-8', errors='replace')}"})
    return blocks


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise SpecError("The model did not return JSON.")
    return json.loads(m.group(0))


def extract_spec(paths: list[Path], model: str = DEFAULT_MODEL) -> tuple[dict, list[str]]:
    try:
        import anthropic
    except ImportError as exc:
        raise SpecError("Intake needs `pip install anthropic` and ANTHROPIC_API_KEY.") from exc
    client = anthropic.Anthropic()
    system = PROMPT
    if SCHEMA.exists():
        system += "\n\n## JSON schema\n\n" + SCHEMA.read_text(encoding="utf-8")
    msg = client.messages.create(
        model=model, max_tokens=16000, system=system,
        messages=[{"role": "user", "content": _blocks(paths) + [
            {"type": "text", "text": "Return the JSON object now."}]}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    out = _parse_json(text)
    draft, missing = out.get("spec", out), list(out.get("missing", []))
    try:
        spec = spec_from_dict(draft)
        missing += [g for g in missing_information(spec) if g not in missing]
    except SpecError as exc:
        missing.insert(0, f"Draft is not runnable yet: {exc}")
    return draft, missing

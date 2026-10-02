# Notes for AI agents working in this repo

Goal: client documents in, AGi32-style PDF summary out. The output format is the contract;
read `docs/report-format.md` before touching `agiopen/report/`.

- Pipeline: `agiopen/intake` (docs -> project.json) -> `agiopen/spec.py` (validation) ->
  `agiopen/geometry.py` + `agiopen/engine.py` (PPFD) -> `agiopen/report/` (PDF).
- Internal units are metres. JSON lengths are in `meta.units`; convert with `spec.meta.to_m`.
- After changing a dataclass in `spec.py`, run `python tools/gen_schema.py`.
- Before changing the engine or defaults, run `python benchmarks/run.py` and report the
  table before/after. Do not tune defaults on a case whose geometry confidence is "low".
- The repo is public: never commit client names, addresses, Drive links or confidential guides.
  Benchmarks stay anonymised.
- Tests: `python -m pytest -q`.
- Fixture catalog: edit `tools/build_catalog.py`, rerun it, never hand-edit `fixtures.json`.
  Each photometry curve states its source and confidence; keep that honest.

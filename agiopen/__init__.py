"""AGI32 OpenSource: horticultural lighting simulation and report generation."""
__version__ = "0.1.0"

from .spec import ProjectSpec, SpecError, load_spec, spec_from_dict  # noqa: F401
from .engine import Results, run  # noqa: F401

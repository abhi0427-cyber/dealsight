"""Rule registry — auto-discovers rule modules in this package."""

import importlib
import pkgutil
from pathlib import Path
from typing import Callable

# Registry: rule_code → check function
# Each check function signature:
#   check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]
#   Returns list of (code, severity, evidence_dict) — empty list means pass.
_REGISTRY: dict[str, Callable] = {}


def register(code: str):
    """Decorator to register a rule check function."""
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[code] = fn
        return fn
    return decorator


def get_all_rules() -> dict[str, Callable]:
    """Return all registered rules, auto-importing modules first."""
    # Auto-import all r??_*.py modules in this package
    pkg_dir = Path(__file__).parent
    for info in pkgutil.iter_modules([str(pkg_dir)]):
        if info.name.startswith("r"):
            importlib.import_module(f".{info.name}", package=__name__)
    return dict(_REGISTRY)

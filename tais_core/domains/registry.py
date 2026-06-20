from pathlib import Path
from typing import Union

from tais_core.dsl.codegen import load_domain_from_spec

_HERE = Path(__file__).resolve().parent.parent / "dsl" / "specs"

BUILTIN_SPEC_NAMES = {
    "gridworld": _HERE / "gridworld.yaml",
    "grid": _HERE / "gridworld.yaml",
    "rules": _HERE / "rules.yaml",
    "ruleworld": _HERE / "rules.yaml",
    "logic": _HERE / "logic.yaml",
    "logicworld": _HERE / "logic.yaml",
    "chemistry_lite": _HERE / "chemistry_lite.yaml",
    "hazard": _HERE / "hazard.yaml",
    "hazardworld": _HERE / "hazard.yaml",
    "sequences": _HERE / "sequences.yaml",
    "sequenceworld": _HERE / "sequences.yaml",
    "logic_large": _HERE / "logic_large.yaml",
    "hazard_large": _HERE / "hazard_large.yaml",
    "rules_chain_long": _HERE / "rules_chain_long.yaml",
    "webnav": _HERE / "webnav.yaml",
    "codesynt": _HERE / "codesynt.yaml",
}


_CACHE = {}

def load_domain(name_or_path: Union[str, Path], use_cache: bool = True):
    cache_key = str(name_or_path)
    if use_cache and cache_key in _CACHE:
        return _CACHE[cache_key]

    p = Path(name_or_path)
    if p.exists():
        domain = load_domain_from_spec(p)
    else:
        name = str(name_or_path).lower()
        if name in BUILTIN_SPEC_NAMES:
            domain = load_domain_from_spec(BUILTIN_SPEC_NAMES[name])
        else:
            raise ValueError(
                f"Unknown domain {name_or_path!r}. "
                f"Use a file path or one of: {sorted(BUILTIN_SPEC_NAMES)}"
            )

    if use_cache:
        _CACHE[cache_key] = domain
    return domain

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
}


def load_domain(name_or_path: Union[str, Path]):
    p = Path(name_or_path)
    if p.exists():
        return load_domain_from_spec(p)
    name = str(name_or_path).lower()
    if name in BUILTIN_SPEC_NAMES:
        return load_domain_from_spec(BUILTIN_SPEC_NAMES[name])
    raise ValueError(
        f"Unknown domain {name_or_path!r}. "
        f"Use a file path or one of: {sorted(BUILTIN_SPEC_NAMES)}"
    )

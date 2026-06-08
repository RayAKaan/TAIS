import json
from pathlib import Path
from typing import Any, Dict, Union

PathLike = Union[str, Path]


def load_spec(path: PathLike) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Spec file not found: {p}")
    if p.stat().st_size == 0:
        raise ValueError(f"Empty spec file: {p}")
    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        import yaml
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif suffix == ".json":
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported spec file suffix: {suffix} (expected .yaml, .yml, or .json)")
    if not isinstance(data, dict):
        raise ValueError(f"Spec must be a dict at top level, got {type(data).__name__}")
    return data

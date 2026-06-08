from __future__ import annotations

import datetime as _dt
import os
import platform
import subprocess
import sys
from typing import Any, Dict, Optional


def _run(cmd: list[str]) -> Optional[str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def git_sha() -> Optional[str]:
    return _run(["git", "rev-parse", "HEAD"])


def git_branch() -> Optional[str]:
    return _run(["git", "branch", "--show-current"])


def dependency_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {}
    packages = ["numpy", "scipy", "matplotlib", "yaml"]
    for pkg in packages:
        try:
            from importlib.metadata import version
            versions[pkg] = version(pkg)
        except Exception:
            pass
    return versions


def capture_provenance(experiment_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "experiment": experiment_name,
        "timestamp_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "parameters": parameters,
        "git_sha": git_sha(),
        "git_branch": git_branch(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "dependencies": dependency_versions(),
    }

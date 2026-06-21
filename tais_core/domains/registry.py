"""
Legacy domain registry — delegates to ``tais_core.dsl.codegen.load_domain``.

This module is kept for backward compatibility. Prefer importing
``load_domain`` from ``tais_core.dsl.codegen`` or ``tais_core.domains``
directly.
"""
import threading
from pathlib import Path
from typing import Union

from tais_core.dsl.codegen import load_domain as _load_domain

# Re-export for existing callers
load_domain = _load_domain

# Preserve the module-level lock so callers that import ``registry``
# still get thread-safe access.
_CACHE_LOCK = threading.Lock()

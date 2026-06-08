"""TAIS Domain Specification Language."""
from .parser import load_spec
from .validator import validate_spec, DomainSpecError
from .codegen import load_domain_from_spec, BuiltinDSLWorld, DeclarativeDSLWorld

__all__ = [
    "load_spec",
    "validate_spec",
    "DomainSpecError",
    "load_domain_from_spec",
    "BuiltinDSLWorld",
    "DeclarativeDSLWorld",
]

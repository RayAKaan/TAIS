from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Condition:
    name: str
    pretrain_domains: List[str] = field(default_factory=list)
    pretrain_ticks: int = 0
    engines: Optional[Dict[str, bool]] = None
    eval_domain: Optional[str] = None
    eval_ticks: Optional[int] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_fresh(self) -> bool:
        return len(self.pretrain_domains) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pretrain_domains": list(self.pretrain_domains),
            "pretrain_ticks": self.pretrain_ticks,
            "engines": self.engines,
            "eval_domain": self.eval_domain,
            "eval_ticks": self.eval_ticks,
            "description": self.description,
            "metadata": dict(self.metadata),
        }

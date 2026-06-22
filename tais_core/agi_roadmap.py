"""
tais_core.agi_roadmap
======================

References to the actual implementations of AGI Roadmap Steps 1-5.

This module provides a unified view of the roadmap and its current
implementation status. Each step can be enabled/disabled independently
to support incremental development and testing.

Current implementation status:
    Step 1 (graph_chunking):      IMPLEMENTED — tais_core.graph_chunking
    Step 2 (causal_intervention): IMPLEMENTED — tais_core.causal_intervention
    Step 3 (schema_learning):     IMPLEMENTED — tais_core.schema_learning
    Step 4 (language_grounding):  IMPLEMENTED — tais_core.language_grounding
    Step 5 (open_ended_learning): IMPLEMENTED — tais_core.open_ended_learning
"""

from __future__ import annotations

from typing import Dict, List

# Step 1
from .graph_chunking import (
    ChunkedWLSimilarity,
    CommunityDetection,
    HierarchicalCompressor,
)

# Step 2
from .causal_intervention import (
    CausalInterventionEngine,
    CounterfactualEstimator,
    InterventionValidator,
)

# Step 3
from .schema_learning import CompositionLearner, SchemaExtractor, SchemaLearner

# Step 4
from .language_grounding import GraphDescriber, NLGraphParser, SchemaDescriber

# Step 5
from .open_ended_learning import (
    CuriosityDrive,
    ExplorationController,
    GoalGenerator,
    SchemaGapDetector,
    SelfEvaluator,
)


class AGIRoadmap:
    """Unified access to all AGI Roadmap implementations."""

    def __init__(self):
        self.steps = {
            1: {"name": "graph_chunking", "implemented": True},
            2: {"name": "causal_intervention", "implemented": True},
            3: {"name": "schema_learning", "implemented": True},
            4: {"name": "language_grounding", "implemented": True},
            5: {"name": "open_ended_learning", "implemented": True},
        }

    def summary(self) -> List[Dict]:
        return [
            {
                "step": num,
                "name": info["name"],
                "implemented": info["implemented"],
                "module": f"tais_core.{info['name']}",
            }
            for num, info in sorted(self.steps.items())
        ]

    def is_implemented(self, step: int) -> bool:
        return self.steps.get(step, {}).get("implemented", False)

    def all_implemented(self) -> bool:
        return all(v["implemented"] for v in self.steps.values())

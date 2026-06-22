"""
tais_core.language_grounding
=============================

AGI Roadmap Step 4: Bidirectional Natural-Language ↔ Graph grounding.

This module translates between structural graph patterns and natural
language descriptions. It uses template-based NL generation and parsing,
NOT LLMs, making it deterministic and testable.

Three components:
    1. GraphDescriber — RealityGraph → NL description
    2. NLGraphParser — NL description → structured patterns
    3. SchemaDescriber — AbstractSchema → compact NL label
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .reality import Entity, GraphPattern, RealityGraph, Relation
from .schema_learning import AbstractSchema, AnonymousRelation, VariableSlot
from .structural_similarity import wl_relabeled_graph, wl_similarity


# ─── GRAPH DESCRIBER ─────────────────────────────────────────────────────────


class GraphDescriber:
    """Convert RealityGraph observations into natural language descriptions.

    The describer identifies structural patterns and renders them as
    compact English sentences. This is template-based, not generative AI.
    """

    def __init__(self):
        # Known entity type synonyms for natural-sounding output
        self._type_names: Dict[str, str] = {
            "AGENT": "agent",
            "RESOURCE": "resource",
            "THREAT": "threat",
            "GOAL": "goal",
            "OBSTACLE": "obstacle",
            "PATH": "path",
            "TOOL": "tool",
            "BARRIER": "barrier",
            "EXIT": "exit",
            "KEY": "key",
            "LOCK": "lock",
            "BRIDGE": "bridge",
            "TRAP": "trap",
            "REWARD": "reward",
            "INFO": "information",
            "PORTAL": "portal",
            "SHIELD": "shield",
            "WEAPON": "weapon",
            "ALLY": "ally",
            "ENEMY": "enemy",
            "VARIABLE": "variable",
            "CLAUSE": "clause",
            "FORMULA": "formula",
            "ATOM": "atom",
            "SYMBOL": "symbol",
            "BODY": "body",
            "HEAD": "head",
        }

    def describe(self, graph: RealityGraph) -> str:
        """Generate a natural language description of a graph."""
        entities = list(graph.entities())
        relations = list(graph.relations())

        if not entities:
            return "empty observation"

        sentences: List[str] = []

        # Count entity types
        type_counts = Counter(e.etype for e in entities)

        # Describe entities
        entity_parts = []
        for etype, count in type_counts.most_common(5):
            name = self._type_names.get(etype, etype.lower())
            if count == 1:
                entity_parts.append(f"a {name}")
            else:
                entity_parts.append(f"{count} {name}s")

        if entity_parts:
            if len(entity_parts) == 1:
                sentences.append(f"There is {entity_parts[0]}.")
            else:
                first = ", ".join(entity_parts[:-1])
                sentences.append(f"There are {first} and {entity_parts[-1]}.")

        # Describe relations
        rel_descriptions = self._describe_relations(relations, entities)
        sentences.extend(rel_descriptions)

        # Describe structural patterns
        pattern_desc = self._describe_structural_patterns(graph)
        if pattern_desc:
            sentences.append(pattern_desc)

        return " ".join(sentences)

    def _describe_relations(
        self, relations: List[Relation], entities: List[Entity]
    ) -> List[str]:
        """Describe relations in natural language."""
        entity_map: Dict[str, Entity] = {e.id: e for e in entities}
        sentences: List[str] = []

        for rel in relations[:10]:  # Limit to avoid overly long descriptions
            src = entity_map.get(rel.source)
            tgt = entity_map.get(rel.target)
            if not src or not tgt:
                continue

            src_name = self._type_names.get(src.etype, src.etype.lower())
            tgt_name = self._type_names.get(tgt.etype, tgt.etype.lower())

            if rel.rtype == "NEAR":
                sentences.append(f"A {src_name} is near a {tgt_name}.")
            elif rel.rtype in ("SEES", "VISIBLE", "OBSERVES"):
                sentences.append(f"A {src_name} sees a {tgt_name}.")
            elif rel.rtype in ("REQUIRES", "NEEDS", "DEPENDS_ON"):
                sentences.append(f"A {tgt_name} requires a {src_name}.")
            elif rel.rtype == "CONNECTS":
                sentences.append(f"A {src_name} connects to a {tgt_name}.")
            elif rel.rtype == "LINKED":
                sentences.append(f"A {src_name} is linked to a {tgt_name}.")
            elif rel.rtype == "ADJACENT":
                sentences.append(f"A {src_name} is adjacent to a {tgt_name}.")
            elif rel.rtype in ("CONTAINS", "HAS"):
                sentences.append(f"A {src_name} contains a {tgt_name}.")
            else:
                sentences.append(
                    f"A {src_name} is {rel.rtype.lower()} a {tgt_name}."
                )

        return sentences

    def _describe_structural_patterns(self, graph: RealityGraph) -> Optional[str]:
        """Identify and describe interesting structural patterns."""
        entities = list(graph.entities())
        entity_ids = {e.id for e in entities}

        # Threat-near-resource pattern
        for rel in graph.relations():
            if rel.rtype == "NEAR":
                src = graph.get_entity(rel.source)
                tgt = graph.get_entity(rel.target)
                if src and tgt:
                    src_type = self._type_names.get(src.etype, src.etype.lower())
                    tgt_type = self._type_names.get(tgt.etype, tgt.etype.lower())
                    # Check if an agent sees the resource
                    for rel2, neighbor in graph.neighbors_in(rel.source):
                        if neighbor.etype == "AGENT":
                            return f"Warning: a {tgt_type} near a {src_type} is visible to an agent."
                    for rel2, neighbor in graph.neighbors_in(rel.target):
                        if neighbor.etype == "AGENT":
                            return f"Warning: a {src_type} near a {tgt_type} is visible to an agent."

        # Agent-goal pattern
        for e in entities:
            if e.etype == "GOAL":
                for rel, neighbor in graph.neighbors_in(e.id):
                    if neighbor.etype == "AGENT":
                        return f"An agent is near a goal."

        return None

    def describe_schema(self, schema: AbstractSchema) -> str:
        """Describe an abstract schema in natural language."""
        parts = []
        slot_types = Counter(s.structural_role for s in schema.slots)
        for role, count in slot_types.most_common():
            if count == 1:
                parts.append(f"one {role} entity")
            else:
                parts.append(f"{count} {role} entities")

        if parts:
            first = ", ".join(parts[:-1]) if len(parts) > 1 else parts[0]
            if len(parts) > 1:
                slot_desc = f"{first} and {parts[-1]}"
            else:
                slot_desc = first
        else:
            slot_desc = "no entities"

        rel_descriptions = []
        for r in schema.relations:
            rel_descriptions.append(
                f"{r.source_role} to {r.target_role} ({r.relation_type})"
            )

        rel_desc = ", ".join(rel_descriptions) if rel_descriptions else "no relations"

        return f"Schema '{schema.name}': {slot_desc} with relations: {rel_desc}. Expected outcome: {schema.expected_outcome_signature}."


# ─── NL GRAPH PARSER ─────────────────────────────────────────────────────────


@dataclass
class ParsedPattern:
    """A structural pattern parsed from natural language."""

    pattern_type: str  # "threat_near_resource", "agent_at_goal", "generic"
    entities: List[Entity]
    relations: List[Relation]
    confidence: float
    raw_text: str

    def to_pattern(self) -> GraphPattern:
        return GraphPattern(
            entities=self.entities,
            relations=self.relations,
            name=f"nl_pattern_{self.pattern_type}",
        )


class NLGraphParser:
    """Parse natural language descriptions into structured graph patterns.

    Uses regex-based templates for known structural patterns.
    This is NOT an LLM — it's a deterministic parser for controlled
    vocabulary.
    """

    def __init__(self):
        self._patterns: List[Dict[str, Any]] = self._build_patterns()

    def _build_patterns(self) -> List[Dict[str, Any]]:
        """Build the pattern template library."""
        return [
            {
                "name": "threat_near_resource",
                "regex": r"(?:threat|danger|hazard)\s+(?:near|next to|adjacent to|beside)\s+(?:resource|treasure|item|supply)",
                "entity_types": ["THREAT", "RESOURCE"],
                "relation_type": "NEAR",
                "confidence": 0.9,
            },
            {
                "name": "agent_approaches_goal",
                "regex": r"(?:agent|player|character|robot)\s+(?:approaches|moves toward|goes to|heads to|approaching)\s+(?:goal|target|objective|destination)",
                "entity_types": ["AGENT", "GOAL"],
                "relation_type": "APPROACHES",
                "confidence": 0.85,
            },
            {
                "name": "threat_visible_to_agent",
                "regex": r"(?:agent|player|character|robot)\s+(?:sees|spots|detects|observes|notices)\s+(?:threat|danger|enemy|hazard)",
                "entity_types": ["AGENT", "THREAT"],
                "relation_type": "SEES",
                "confidence": 0.85,
            },
            {
                "name": "resource_visible_to_agent",
                "regex": r"(?:agent|player|character|robot)\s+(?:sees|spots|detects|observes|notices)\s+(?:resource|treasure|item|supply)",
                "entity_types": ["AGENT", "RESOURCE"],
                "relation_type": "SEES",
                "confidence": 0.8,
            },
            {
                "name": "agent_avoids_threat",
                "regex": r"(?:agent|player|character|robot)\s+(?:avoids|flees from|runs from|escapes|avoids)\s+(?:threat|danger|enemy|hazard)",
                "entity_types": ["AGENT", "THREAT"],
                "relation_type": "AVOIDS",
                "confidence": 0.8,
            },
            {
                "name": "resource_requires_other",
                "regex": r"(?:resource|treasure|item|supply)\s+(?:requires|needs|depends on|uses)\s+(?:resource|tool|key|item)",
                "entity_types": ["RESOURCE", "RESOURCE"],
                "relation_type": "REQUIRES",
                "confidence": 0.7,
            },
            {
                "name": "dangerous_resource",
                "regex": r"(?:dangerous|unsafe|risky|hazardous)\s+(?:resource|treasure|item|supply|area)",
                "entity_types": ["THREAT", "RESOURCE"],
                "relation_type": "NEAR",
                "confidence": 0.7,
            },
            {
                "name": "safe_resource",
                "regex": r"(?:safe|secure|protected|clear)\s+(?:resource|treasure|item|supply|area)",
                "entity_types": ["RESOURCE"],
                "relation_type": "SAFE",
                "confidence": 0.7,
            },
            {
                "name": "generic_relation",
                "regex": r"(.+?)\s+(?:is|are)\s+(.+?)\s+(?:a|an|the)\s+(.+)",
                "entity_types": ["ENTITY", "ENTITY"],
                "relation_type": "LINKED",
                "confidence": 0.3,
            },
        ]

    def parse(self, text: str) -> List[ParsedPattern]:
        """Parse NL text into structured patterns.

        Returns a list of ParsedPatterns sorted by confidence (highest first).
        """
        text_lower = text.lower().strip()
        results: List[ParsedPattern] = []

        for pattern_def in self._patterns:
            match = re.search(pattern_def["regex"], text_lower)
            if match:
                entity_types = pattern_def["entity_types"]
                relation_type = pattern_def["relation_type"]

                entities: List[Entity] = []
                relations: List[Relation] = []

                for i, etype in enumerate(entity_types):
                    eid = f"nl_e_{i}"
                    entities.append(Entity(eid, etype, {"source": "nl_parser"}))

                if len(entity_types) >= 2:
                    e0 = f"nl_e_{0}"
                    e1 = f"nl_e_{1}"
                    relations.append(
                        Relation(e0, relation_type, e1, {"source": "nl_parser"})
                    )

                results.append(
                    ParsedPattern(
                        pattern_type=pattern_def["name"],
                        entities=entities,
                        relations=relations,
                        confidence=pattern_def["confidence"],
                        raw_text=text,
                    )
                )

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def parse_schema_description(self, text: str) -> Optional[AbstractSchema]:
        """Parse a schema description into an AbstractSchema.

        Format: "Schema 'name': role1 and role2 entities with relations: r1 to r2 (type). Expected outcome: GOOD."
        """
        schema_match = re.search(r"Schema '([^']+)':", text)
        if not schema_match:
            return None

        name = schema_match.group(1)

        # Parse slots
        slot_part = text.split(":")[1] if ":" in text else ""
        slots: List[VariableSlot] = []

        role_pattern = re.findall(r"(\d+)\s+(\w+)\s+entities?", slot_part)
        for count_str, role in role_pattern:
            count = int(count_str)
            for _ in range(count):
                slot_id = f"slot_{role}_{len(slots)}"
                slots.append(
                    VariableSlot(
                        slot_id=slot_id,
                        structural_role=role,
                        degree_range=(1, 5),
                    )
                )

        # Parse relations
        rel_part = text.split("relations:")[1] if "relations:" in text else ""
        rel_end = rel_part.split(".")[0] if "." in rel_part else rel_part
        relations: List[AnonymousRelation] = []

        rel_pattern = re.findall(
            r"(\w+)\s+to\s+(\w+)\s+\((\w+)\)", rel_end
        )
        for src_role, tgt_role, rtype in rel_pattern:
            relations.append(
                AnonymousRelation(
                    source_role=src_role,
                    target_role=tgt_role,
                    relation_type=rtype,
                )
            )

        # Parse outcome
        outcome = "NEUTRAL"
        outcome_match = re.search(
            r"Expected outcome:\s*(\w+)", text
        )
        if outcome_match:
            outcome = outcome_match.group(1).upper()

        if not slots:
            return None

        return AbstractSchema(
            name=name,
            slots=slots,
            relations=relations,
            expected_outcome_signature=outcome,
        )


# ─── SCHEMA DESCRIBER ────────────────────────────────────────────────────────


class SchemaDescriber:
    """Compact NL descriptions of schemas for communication.

    Used by the SpeechOrgan to describe transfer insights and
    causal discoveries in natural language.
    """

    def describe_transfer_insight(
        self,
        schema: AbstractSchema,
        source_domain: str,
        target_domain: str,
        similarity: float,
    ) -> str:
        """Describe a cross-domain transfer insight."""
        return (
            f"I recognized that {target_domain} has a similar structure to {source_domain}. "
            f"Both have {self._slot_summary(schema)}. "
            f"The pattern '{schema.name}' applies with {similarity:.0%} confidence. "
            f"{self._action_advice(schema)}"
        )

    def describe_causal_discovery(
        self,
        action_name: str,
        effect: float,
        confidence: float,
    ) -> str:
        """Describe a discovered causal relationship."""
        direction = "improves" if effect > 0 else "harms"
        return (
            f"I discovered that {action_name} {direction} the situation "
            f"(effect={abs(effect):.2f}, confidence={confidence:.0%})."
        )

    def describe_curiosity_goal(self, goal: str, reason: str) -> str:
        """Describe a self-generated learning goal."""
        return f"I want to learn about {goal} because {reason}."

    def describe_schema(self, schema: AbstractSchema) -> str:
        """Compact NL description of a schema."""
        slot_desc = self._slot_summary(schema)
        return (
            f"Schema '{schema.name}': {slot_desc}. "
            f"Expected outcome: {schema.expected_outcome_signature}. "
            f"Confidence: {schema.confidence:.0%}."
        )

    def _slot_summary(self, schema: AbstractSchema) -> str:
        """Generate a compact slot summary."""
        slot_types = Counter(s.structural_role for s in schema.slots)
        parts = []
        for role, count in slot_types.most_common():
            if count == 1:
                parts.append(f"one {role}")
            else:
                parts.append(f"{count} {role}s")
        if len(parts) == 1:
            return parts[0]
        return ", ".join(parts[:-1]) + " and " + parts[-1]

    def _action_advice(self, schema: AbstractSchema) -> str:
        """Generate action advice from schema."""
        if schema.recommended_action_role:
            return f"I recommend using '{schema.recommended_action_role}'."
        return "The same approach should work here."

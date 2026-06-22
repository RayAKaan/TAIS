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

    Uses a robust token-based semantic parser that handles arbitrary
    sentence structures via multiple extraction strategies:
        1. SVO triples (subject-verb-object)
        2. Copular + property (X is Y)
        3. Copular + spatial (X is near Y)
        4. Verb + preposition (X verb prep Y)
        5. Possessive (X's Y)
        6. Verb scan fallback
        7. Comma-separated lists

    This is NOT an LLM — it's a deterministic parser for controlled
    vocabulary with semantic word classification.
    """

    # ── Semantic word maps ─────────────────────────────────────────────────

    ENTITY_WORDS: Dict[str, str] = {
        "agent": "AGENT",
        "player": "AGENT",
        "character": "AGENT",
        "robot": "AGENT",
        "threat": "THREAT",
        "danger": "THREAT",
        "hazard": "THREAT",
        "enemy": "THREAT",
        "resource": "RESOURCE",
        "treasure": "RESOURCE",
        "item": "RESOURCE",
        "supply": "RESOURCE",
        "tool": "RESOURCE",
        "key": "RESOURCE",
        "goal": "GOAL",
        "target": "GOAL",
        "objective": "GOAL",
        "destination": "GOAL",
        "obstacle": "OBSTACLE",
        "barrier": "OBSTACLE",
        "trap": "OBSTACLE",
        "path": "PATH",
        "exit": "EXIT",
        "lock": "LOCK",
        "bridge": "BRIDGE",
        "reward": "REWARD",
        "portal": "PORTAL",
        "shield": "SHIELD",
        "weapon": "WEAPON",
        "ally": "ALLY",
        "variable": "VARIABLE",
        "clause": "CLAUSE",
        "formula": "FORMULA",
        "atom": "ATOM",
        "symbol": "SYMBOL",
        "body": "BODY",
        "head": "HEAD",
        "information": "INFO",
        "area": "AREA",
    }

    VERB_RELATION_MAP: Dict[str, str] = {
        "approaches": "APPROACHES",
        "approach": "APPROACHES",
        "approaching": "APPROACHES",
        "moves": "APPROACHES",
        "move": "APPROACHES",
        "goes": "APPROACHES",
        "go": "APPROACHES",
        "heads": "APPROACHES",
        "head": "APPROACHES",
        "sees": "SEES",
        "see": "SEES",
        "spots": "SEES",
        "spot": "SEES",
        "detects": "SEES",
        "detect": "SEES",
        "observes": "SEES",
        "observe": "SEES",
        "notices": "SEES",
        "notice": "SEES",
        "avoids": "AVOIDS",
        "avoid": "AVOIDS",
        "flees": "AVOIDS",
        "flee": "AVOIDS",
        "escapes": "AVOIDS",
        "escape": "AVOIDS",
        "requires": "REQUIRES",
        "require": "REQUIRES",
        "needs": "REQUIRES",
        "need": "REQUIRES",
        "uses": "USES",
        "use": "USES",
        "reaches": "REACHES",
        "reach": "REACHES",
        "reaching": "REACHES",
    }

    SPATIAL_PREPOSITIONS: Set[str] = {
        "near", "next", "adjacent", "beside", "behind",
        "in front of", "across", "beyond", "above", "below",
        "under", "over", "inside", "outside", "between",
        "among", "through", "around", "along",
    }

    SPATIAL_RELATION_MAP: Dict[str, str] = {
        "near": "NEAR",
        "next": "ADJACENT",
        "adjacent": "ADJACENT",
        "beside": "BESIDE",
        "behind": "BEHIND",
        "above": "ABOVE",
        "below": "BELOW",
        "under": "UNDER",
        "over": "OVER",
        "inside": "INSIDE",
        "outside": "OUTSIDE",
    }

    COPULAR_VERBS: Set[str] = {"is", "are", "was", "were", "be", "been", "being"}

    PROPERTY_VALENCE_MAP: Dict[str, str] = {
        "dangerous": "DANGEROUS",
        "unsafe": "DANGEROUS",
        "risky": "DANGEROUS",
        "hazardous": "DANGEROUS",
        "safe": "SAFE",
        "secure": "SAFE",
        "protected": "SAFE",
        "clear": "SAFE",
        "visible": "VISIBLE",
        "hidden": "HIDDEN",
        "blocked": "BLOCKED",
        "open": "OPEN",
        "closed": "CLOSED",
        "nearby": "NEARBY",
        "far": "FAR",
    }

    STOP_WORDS: Set[str] = {
        "the", "a", "an", "this", "that", "these", "those",
        "it", "its", "they", "them", "their",
        "there", "here",
        "is", "are", "was", "were", "be", "been", "being",
        "has", "have", "had", "do", "does", "did",
        "will", "would", "can", "could", "may", "might",
        "shall", "should", "must",
        "not", "no", "nor",
        "and", "or", "but", "if", "then", "else",
        "to", "of", "in", "for", "on", "with", "at",
        "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below",
        "very", "just", "also", "too",
    }

    def __init__(self):
        pass

    def _tokenize(self, text: str) -> List[str]:
        """Split text into tokens, preserving multi-word expressions."""
        text_lower = text.lower().strip()
        if not text_lower:
            return []

        # Handle multi-word prepositions first
        for mwe in ["in front of", "next to", "adjacent to"]:
            text_lower = text_lower.replace(mwe, mwe.replace(" ", "_"))

        # Split on whitespace and punctuation
        tokens = re.findall(r"[a-zA-Z_]+", text_lower)
        # Restore multi-word tokens
        tokens = [t.replace("_", " ") for t in tokens]
        return tokens

    def _canonicalize_entity_name(self, token: str) -> Optional[str]:
        """Map a token to a canonical entity type, or None if not an entity.

        Filters out stop words, verbs, prepositions, and property words
        that should not be treated as entities.
        """
        t = token.lower().strip()
        if t in self.STOP_WORDS:
            return None
        if t in self.VERB_RELATION_MAP:
            return None
        if t in self.SPATIAL_PREPOSITIONS:
            return None
        if t in self.PROPERTY_VALENCE_MAP:
            return None
        if t in self.COPULAR_VERBS:
            return None
        return self.ENTITY_WORDS.get(t, t.upper())

    def _extract_svo(
        self, tokens: List[str]
    ) -> List[Tuple[str, str, str, float]]:
        """Extract (subject, verb_relation, object, confidence) triples."""
        results: List[Tuple[str, str, str, float]] = []

        # Pattern 1: SVO — subject verb object
        for i in range(1, len(tokens) - 1):
            subj = self._canonicalize_entity_name(tokens[i - 1])
            verb = tokens[i].lower().strip()
            obj = self._canonicalize_entity_name(tokens[i + 1])
            if subj is not None and obj is not None and verb in self.VERB_RELATION_MAP:
                results.append((subj, self.VERB_RELATION_MAP[verb], obj, 0.85))

        # Pattern 2: copular + property — "X is Y" / "X is a Y"
        for i in range(1, len(tokens) - 1):
            prev = self._canonicalize_entity_name(tokens[i - 1])
            cop = tokens[i].lower().strip()
            if prev is not None and cop in self.COPULAR_VERBS:
                # Check next token for property or entity
                nxt = tokens[i + 1].lower().strip()
                if nxt in self.PROPERTY_VALENCE_MAP:
                    # X is [dangerous/safe/...] → property relation
                    property_type = self.PROPERTY_VALENCE_MAP[nxt]
                    results.append((prev, property_type, prev, 0.7))
                elif nxt in ("a", "an", "the"):
                    # "X is a Y" — skip determiner
                    if i + 2 < len(tokens):
                        obj = self._canonicalize_entity_name(tokens[i + 2])
                        if obj is not None:
                            results.append((prev, "LINKED", obj, 0.6))
                elif nxt in self.SPATIAL_PREPOSITIONS:
                    # "X is near Y"
                    if i + 2 < len(tokens):
                        obj = self._canonicalize_entity_name(tokens[i + 2])
                        if obj is not None:
                            rel = nxt.upper()
                            if rel == "NEAR":
                                rel = "NEAR"
                            elif rel == "NEXT":
                                rel = "ADJACENT"
                            else:
                                rel = rel.upper()
                            results.append((prev, rel, obj, 0.75))
                else:
                    obj = self._canonicalize_entity_name(nxt)
                    if obj is not None:
                        results.append((prev, "LINKED", obj, 0.5))

        # Pattern 3: verb + preposition — "X [verb] [prep] Y"
        for i in range(1, len(tokens) - 2):
            subj = self._canonicalize_entity_name(tokens[i - 1])
            verb = tokens[i].lower().strip()
            prep = tokens[i + 1].lower().strip()
            obj = self._canonicalize_entity_name(tokens[i + 2])
            if (
                subj is not None
                and obj is not None
                and verb in self.VERB_RELATION_MAP
                and prep in self.SPATIAL_PREPOSITIONS
            ):
                results.append(
                    (subj, self.VERB_RELATION_MAP[verb], obj, 0.75)
                )

        # Pattern 4: possessive — "X's Y"
        for i in range(len(tokens) - 1):
            if tokens[i + 1].lower().strip() == "'s" or tokens[i].endswith("'s"):
                base_token = tokens[i].rstrip("'s")
                subj = self._canonicalize_entity_name(base_token)
                if i + 2 < len(tokens):
                    obj = self._canonicalize_entity_name(tokens[i + 2])
                else:
                    obj = None
                if subj is not None and obj is not None:
                    results.append((subj, "HAS", obj, 0.7))

        # Pattern 5: spatial relation — "X near Y", "X beside Y", etc.
        for i in range(1, len(tokens) - 1):
            subj = self._canonicalize_entity_name(tokens[i - 1])
            mid = tokens[i].lower().strip()
            obj = self._canonicalize_entity_name(tokens[i + 1])
            if subj is not None and obj is not None and mid in self.SPATIAL_RELATION_MAP:
                results.append((subj, self.SPATIAL_RELATION_MAP[mid], obj, 0.8))

        # Pattern 6: verb scan fallback — find any entity-verb-entity
        # after filtering nouns
        nouns = [
            (i, t) for i, t in enumerate(tokens)
            if self._canonicalize_entity_name(t) is not None
        ]
        for j in range(1, len(nouns)):
            i1, _ = nouns[j - 1]
            i2, _ = nouns[j]
            # Look for verbs between them
            for k in range(i1 + 1, i2):
                verb = tokens[k].lower().strip()
                if verb in self.VERB_RELATION_MAP:
                    subj = self._canonicalize_entity_name(tokens[i1])
                    obj = self._canonicalize_entity_name(tokens[i2])
                    if subj is not None and obj is not None:
                        results.append(
                            (subj, self.VERB_RELATION_MAP[verb], obj, 0.5)
                        )

        # Pattern 6: comma-separated adjacency — "X, Y, Z"
        for i in range(len(tokens) - 2):
            if tokens[i + 1] == "," or tokens[i + 1] == "and":
                subj = self._canonicalize_entity_name(tokens[i])
                obj = self._canonicalize_entity_name(tokens[i + 2])
                if subj is not None and obj is not None:
                    results.append((subj, "ADJACENT", obj, 0.4))

        return results

    def _classify_pattern_type(
        self, subj: str, rel: str, obj: str
    ) -> str:
        """Classify a triple into a named pattern type for backward compat."""
        pair = (subj, rel, obj)
        if subj == "THREAT" and rel == "NEAR" and obj == "RESOURCE":
            return "threat_near_resource"
        if subj == "AGENT" and rel == "APPROACHES" and obj == "GOAL":
            return "agent_approaches_goal"
        if subj == "AGENT" and rel == "SEES" and obj == "THREAT":
            return "threat_visible_to_agent"
        if subj == "AGENT" and rel == "SEES" and obj == "RESOURCE":
            return "resource_visible_to_agent"
        if subj == "AGENT" and rel == "AVOIDS" and obj == "THREAT":
            return "agent_avoids_threat"
        if subj == "RESOURCE" and rel == "REQUIRES" and obj == "RESOURCE":
            return "resource_requires_other"
        if subj == "AGENT" and rel == "REACHES" and obj == "GOAL":
            return "agent_approaches_goal"
        if rel == "ADJACENT":
            return "adjacent_entities"
        if rel in ("DANGEROUS", "SAFE", "VISIBLE", "HIDDEN", "BLOCKED"):
            return "property_descriptor"
        return "generic_relation"

    def _parse_robust(self, text: str) -> List[ParsedPattern]:
        """Robust token-based semantic parser.

        Handles arbitrary sentence structures by decomposing into
        SVO triples and entity-relation-entity patterns.
        """
        text_lower = text.lower().strip()
        if not text_lower:
            return []

        tokens = self._tokenize(text_lower)
        if len(tokens) < 2:
            return []

        triples = self._extract_svo(tokens)
        if not triples:
            return []

        seen: Set[Tuple[str, str, str]] = set()
        results: List[ParsedPattern] = []
        for subj, rel, obj, conf in triples:
            key = (subj, rel, obj)
            if key in seen:
                continue
            seen.add(key)

            entity_types: List[str] = [subj]
            if obj != subj:
                entity_types.append(obj)

            entities: List[Entity] = []
            for i, etype in enumerate(entity_types):
                entities.append(
                    Entity(f"nl_e_{i}", etype, {"source": "nl_parser"})
                )

            relations: List[Relation] = []
            if len(entity_types) >= 2:
                e0_id = f"nl_e_{0}"
                e1_id = f"nl_e_{1}"
                relations.append(
                    Relation(e0_id, rel, e1_id, {"source": "nl_parser"})
                )

            pattern_type = self._classify_pattern_type(subj, rel, obj)

            results.append(
                ParsedPattern(
                    pattern_type=pattern_type,
                    entities=entities,
                    relations=relations,
                    confidence=conf,
                    raw_text=text,
                )
            )

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def parse(self, text: str) -> List[ParsedPattern]:
        """Parse NL text into structured patterns.

        Primary method uses robust token-based parsing.
        Returns a list of ParsedPatterns sorted by confidence (highest first).
        """
        return self._parse_robust(text)

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

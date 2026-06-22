"""
tais_core.language_grounding
==============================

Step 4: Language Grounding — bidirectional mapping between natural language
and RealityGraph/Schema representations.

The core insight: language is the universal API. Without it, the system
can only learn from its own graphs. With it, it can learn from text,
instructions, and the entire internet.

This module provides:
1. NL -> RealityGraph: parse natural language descriptions into graph structures
2. Schema -> NL: describe schemas in natural language
3. Schema <-> NL: bidirectional grounding where language compresses schemas

Key design decisions:
- Uses a ROBUST token-based semantic parser (not fragile regex templates).
- The parser handles arbitrary sentence structures by decomposing them
  into subject-verb-object triples, then extracting entities and relations.
- Structural role extraction maps noun phrases to graph positions based
  on their grammatical role (subject = SOURCE, object = SINK, etc.)
- Language handling is done by an external LLM (or template system for
  structured inputs). The reasoning stays symbolic.

Surface independence: the grounding maps language to structural roles,
not to entity type names. "The dangerous thing is near the resource"
maps to the same graph structure regardless of domain vocabulary.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .reality import Entity, RealityGraph, Relation
from .schema_learning import Schema, SchemaSlot, SchemaLearner
from .structural_similarity import wl_relabeled_graph, wl_similarity
from .analogy_engine import entity_structural_signature


# --- LINGUISTIC CONSTANTS -------------------------------------------------------

# Determiners and articles
DETERMINERS = {"the", "a", "an", "this", "that", "these", "those", "some", "any", "every"}

# Common stop words (not entity candidates)
STOP_WORDS = DETERMINERS | {
    "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "having",
    "do", "does", "did", "doing",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "it", "its", "they", "them", "their", "we", "us", "our",
    "i", "me", "my", "you", "your", "he", "him", "his", "she", "her",
    "not", "no", "nor", "but", "or", "and", "if", "then",
    "of", "for", "with", "as", "by", "from", "to", "at", "in", "on",
    "about", "into", "through", "during", "before", "after",
    "above", "below", "between", "under", "over", "up", "down",
    "very", "too", "also", "just", "only", "still", "already",
    "than", "so", "such", "more", "most", "less", "least",
    "what", "which", "who", "whom", "whose", "where", "when", "how", "why",
    "there", "here", "now", "then",
}

# Spatial relation indicators
SPATIAL_PREPOSITIONS = {
    "near", "next", "close", "beside", "besides", "around", "between",
    "among", "within", "outside", "inside", "alongside", "adjacent",
}

# Directional relation indicators
DIRECTIONAL_PREPOSITIONS = {
    "toward", "towards", "away", "from", "to", "into", "onto",
    "above", "below", "before", "after", "behind", "front",
}

# Verb categories mapped to structural relation types
VERB_RELATION_MAP = {
    # Approach verbs
    "approaches": "APPROACHES", "approach": "APPROACHES",
    "moves": "APPROACHES", "move": "APPROACHES", "goes": "APPROACHES", "go": "APPROACHES",
    "reaches": "APPROACHES", "reach": "APPROACHES",
    "enters": "APPROACHES", "enter": "APPROACHES",
    "visits": "APPROACHES", "visit": "APPROACHES",
    # Avoid verbs
    "avoids": "AVOIDS", "avoid": "AVOIDS",
    "flees": "AVOIDS", "flee": "AVOIDS",
    "escapes": "AVOIDS", "escape": "AVOIDS",
    "leaves": "AVOIDS", "leave": "AVOIDS",
    "retreats": "AVOIDS", "retreat": "AVOIDS",
    # Threat verbs
    "attacks": "THREATENS", "attack": "THREATENS",
    "threatens": "THREATENS", "threaten": "THREATENS",
    "endangers": "THREATENS", "endanger": "THREATENS",
    "harms": "THREATENS", "harm": "THREATENS",
    "damages": "THREATENS", "damage": "THREATENS",
    "blocks": "THREATENS", "block": "THREATENS",
    # Support verbs
    "protects": "SUPPORTS", "protect": "SUPPORTS",
    "helps": "SUPPORTS", "help": "SUPPORTS",
    "supports": "SUPPORTS", "support": "SUPPORTS",
    "aids": "SUPPORTS", "aid": "SUPPORTS",
    "assists": "SUPPORTS", "assist": "SUPPORTS",
    "enables": "SUPPORTS", "enable": "SUPPORTS",
    # Observe verbs
    "sees": "SEES", "see": "SEES",
    "observes": "SEES", "observe": "SEES",
    "detects": "SEES", "detect": "SEES",
    "notices": "SEES", "notice": "SEES",
    "watches": "SEES", "watch": "SEES",
    # Connect verbs
    "connects": "CONNECTS", "connect": "CONNECTS",
    "links": "CONNECTS", "link": "CONNECTS",
    "joins": "CONNECTS", "join": "CONNECTS",
    "contains": "CONTAINS", "contain": "CONTAINS",
    "holds": "CONTAINS", "hold": "CONTAINS",
    # Generic action
    "interacts": "RELATED", "interact": "RELATED",
    "affects": "RELATED", "affect": "RELATED",
    "influences": "RELATED", "influence": "RELATED",
}

# Property ADJECTIVES -> structural valence
# These are FILTERED from entity names -- they describe properties, not entities
PROPERTY_ADJECTIVES = {
    "dangerous": "NEGATIVE", "risky": "NEGATIVE", "harmful": "NEGATIVE",
    "toxic": "NEGATIVE", "hostile": "NEGATIVE", "unstable": "NEGATIVE",
    "safe": "POSITIVE", "important": "POSITIVE", "valuable": "POSITIVE",
    "beneficial": "POSITIVE", "stable": "POSITIVE", "friendly": "POSITIVE",
    "useful": "POSITIVE", "helpful": "POSITIVE", "secure": "POSITIVE",
}

# Entity-valence hints: nouns that suggest a valence
# These are NOT filtered from entity names -- they ARE entities with valence
ENTITY_VALENCE_HINTS = {
    "goal": "POSITIVE", "target": "POSITIVE", "objective": "POSITIVE",
    "threat": "NEGATIVE", "obstacle": "NEGATIVE", "hazard": "NEGATIVE",
    "enemy": "NEGATIVE", "trap": "NEGATIVE", "wall": "NEGATIVE",
    "resource": "POSITIVE", "food": "POSITIVE", "reward": "POSITIVE",
    "exit": "POSITIVE", "treasure": "POSITIVE", "prize": "POSITIVE",
    "predator": "NEGATIVE", "monster": "NEGATIVE", "danger": "NEGATIVE",
}

# Combined map for property detection (used in _extract_properties)
PROPERTY_VALENCE_MAP = {**PROPERTY_ADJECTIVES, **ENTITY_VALENCE_HINTS}

# Copular verbs (is, seems, appears, becomes)
COPULAR_VERBS = {"is", "are", "was", "were", "seems", "appears", "becomes", "become", "remains", "stays"}


# --- PARSED ENTITY --------------------------------------------------------------

@dataclass
class ParsedEntity:
    """An entity extracted from natural language."""
    name: str
    etype: str = "UNKNOWN"
    properties: Dict[str, Any] = field(default_factory=dict)
    valence: Optional[str] = None  # POSITIVE, NEGATIVE, or None


@dataclass
class ParsedRelation:
    """A relation extracted from natural language."""
    source: str
    target: str
    rtype: str  # Structural relation type (NEAR, APPROACHES, etc.)
    raw_text: str = ""


@dataclass
class ParsedGraph:
    """A graph structure parsed from natural language."""
    entities: List[ParsedEntity]
    relations: List[ParsedRelation]
    raw_text: str
    confidence: float = 0.5


# --- SEMANTIC TRIPLE ------------------------------------------------------------

@dataclass
class SemanticTriple:
    """A subject-verb-object triple extracted from a sentence."""
    subject: str
    verb: str
    obj: str
    verb_type: str = "ACTION"  # ACTION, SPATIAL, COPULAR, POSSESSION
    preposition: str = ""
    raw_text: str = ""


# --- ROBUST NL -> GRAPH PARSER --------------------------------------------------

class NLGraphParser:
    """Parses natural language descriptions into RealityGraph structures.

    Uses a ROBUST token-based semantic parser instead of fragile regex
    templates. The parser:

    1. Tokenizes text into sentences and words
    2. Identifies noun phrases (entity candidates)
    3. Extracts subject-verb-object (SVO) triples
    4. Maps verbs to structural relation types
    5. Handles modifiers (adjectives -> properties, prepositions -> relations)
    6. Builds a graph from extracted triples

    This handles arbitrary sentence structures because it decomposes them
    into primitive SVO triples, rather than trying to match whole-sentence
    regex patterns.

    The parser is surface-independent: it maps to structural relation types
    (NEAR, APPROACHES, THREATENS) not to domain-specific types.
    """

    def __init__(self, use_llm: bool = False, llm_api: Optional[Any] = None):
        self.use_llm = use_llm
        self.llm_api = llm_api
        self._entity_id_counter = 0

    def parse(self, text: str) -> ParsedGraph:
        """Parse natural language text into a graph structure."""
        if self.use_llm and self.llm_api:
            return self._parse_with_llm(text)
        return self._parse_robust(text)

    def _parse_robust(self, text: str) -> ParsedGraph:
        """Robust token-based semantic parsing.

        Algorithm:
        1. Split into sentences
        2. For each sentence, extract SVO triples
        3. Map entities and relations from triples
        4. Handle modifiers and properties
        5. Combine into a ParsedGraph
        """
        text_lower = text.lower().strip()
        entities: Dict[str, ParsedEntity] = {}
        relations: List[ParsedRelation] = []

        # Split into sentences
        sentences = self._split_sentences(text_lower)

        for sentence in sentences:
            # Extract SVO triples from this sentence
            triples = self._extract_triples(sentence)

            for triple in triples:
                # Process subject
                subj = self._canonicalize_entity_name(triple.subject)
                obj = self._canonicalize_entity_name(triple.obj)

                if subj and subj not in STOP_WORDS:
                    if subj not in entities:
                        entities[subj] = ParsedEntity(name=subj)
                    # Subject = agent/SOURCE role
                    entities[subj].etype = self._infer_etype(subj, "SUBJECT")

                if obj and obj not in STOP_WORDS:
                    if obj not in entities:
                        entities[obj] = ParsedEntity(name=obj)
                    # Object = target/SINK role
                    entities[obj].etype = self._infer_etype(obj, "OBJECT")

                # Extract relation
                if subj and obj and subj in entities and obj in entities:
                    rtype = self._verb_to_rtype(triple)
                    if rtype:
                        relations.append(ParsedRelation(
                            source=subj, target=obj,
                            rtype=rtype,
                            raw_text=triple.raw_text,
                        ))

            # Also extract property assertions (adjective modifiers)
            props = self._extract_properties(sentence)
            for name, valence in props:
                if name not in entities:
                    entities[name] = ParsedEntity(name=name)
                entities[name].valence = valence

        # If no entities found, try a simpler heuristic
        if not entities:
            entities, relations = self._simple_heuristic_parse(text_lower)

        # Compute confidence based on extraction quality
        confidence = min(1.0, len(entities) * 0.15 + len(relations) * 0.2 + 0.1)

        return ParsedGraph(
            entities=list(entities.values()),
            relations=relations,
            raw_text=text,
            confidence=min(confidence, 0.95),
        )

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'[.!?\n]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_triples(self, sentence: str) -> List[SemanticTriple]:
        """Extract subject-verb-object triples from a sentence.

        Handles multiple patterns:
        - "X VERB Y" (active voice)
        - "X is ADJ" (copular + property)
        - "X is near Y" (copular + spatial)
        - "X VERB PREP Y" (verb + prepositional phrase)
        - "X's Y" (possessive)
        """
        triples = []
        tokens = sentence.split()

        if len(tokens) < 2:
            return triples

        # Pattern 1: "X is/are ADJ" -> property assertion
        for cop in COPULAR_VERBS:
            pattern = rf'(\w+)\s+{cop}\s+(?:the\s+|a\s+|an\s+)?(\w+)'
            for match in re.finditer(pattern, sentence):
                subj, comp = match.group(1), match.group(2)
                if comp in PROPERTY_VALENCE_MAP:
                    triples.append(SemanticTriple(
                        subject=subj, verb=cop, obj=comp,
                        verb_type="COPULAR", raw_text=match.group(0),
                    ))
                elif comp in SPATIAL_PREPOSITIONS or comp in DIRECTIONAL_PREPOSITIONS:
                    remaining = sentence[match.end():].strip()
                    if remaining:
                        next_word = remaining.split()[0] if remaining.split() else ""
                        next_word = self._canonicalize_entity_name(next_word)
                        if next_word:
                            triples.append(SemanticTriple(
                                subject=subj, verb=cop, obj=next_word,
                                verb_type="SPATIAL", preposition=comp,
                                raw_text=match.group(0) + " " + next_word,
                            ))

        # Pattern 2: "X VERB (PREP) Y" -> verb + optional preposition
        for verb in VERB_RELATION_MAP:
            pattern = rf'(\w+)\s+{verb}\s+(?:(?:to|toward|towards|from|away)\s+)?(?:the\s+|a\s+|an\s+)?(\w+)'
            for match in re.finditer(pattern, sentence):
                subj, obj = match.group(1), match.group(2)
                subj = self._canonicalize_entity_name(subj)
                obj = self._canonicalize_entity_name(obj)
                if subj and obj:
                    triples.append(SemanticTriple(
                        subject=subj, verb=verb, obj=obj,
                        verb_type="ACTION", raw_text=match.group(0),
                    ))

        # Pattern 3: "X is ADJ PREP Y" -> property + spatial relation
        for cop in COPULAR_VERBS:
            for prep in SPATIAL_PREPOSITIONS | DIRECTIONAL_PREPOSITIONS:
                pattern = rf'(\w+)\s+{cop}\s+\w+\s+{prep}\s+(?:to\s+)?(?:the\s+)?(\w+)'
                for match in re.finditer(pattern, sentence):
                    subj, obj = match.group(1), match.group(2)
                    if subj not in STOP_WORDS and obj not in STOP_WORDS:
                        if obj not in SPATIAL_PREPOSITIONS and obj not in DIRECTIONAL_PREPOSITIONS and obj not in PROPERTY_VALENCE_MAP:
                            triples.append(SemanticTriple(
                                subject=subj, verb=cop, obj=obj,
                                verb_type="SPATIAL", preposition=prep,
                                raw_text=match.group(0),
                            ))
                pattern2 = rf'(\w+)\s+{cop}\s+{prep}\s+(?:to\s+)?(?:the\s+)?(\w+)'
                for match in re.finditer(pattern2, sentence):
                    subj, obj = match.group(1), match.group(2)
                    if subj not in STOP_WORDS and obj not in STOP_WORDS:
                        if obj not in SPATIAL_PREPOSITIONS and obj not in DIRECTIONAL_PREPOSITIONS and obj not in PROPERTY_VALENCE_MAP:
                            triples.append(SemanticTriple(
                                subject=subj, verb=cop, obj=obj,
                                verb_type="SPATIAL", preposition=prep,
                                raw_text=match.group(0),
                            ))

        # Pattern 4: "X near/next to Y" -> spatial relation (no verb)
        for prep in SPATIAL_PREPOSITIONS:
            pattern = rf'(\w+)\s+(?:is\s+)?{prep}\s+(?:to\s+)?(?:the\s+|a\s+|an\s+)?(\w+)'
            for match in re.finditer(pattern, sentence):
                subj, obj = match.group(1), match.group(2)
                subj = self._canonicalize_entity_name(subj)
                obj = self._canonicalize_entity_name(obj)
                if subj and obj:
                    triples.append(SemanticTriple(
                        subject=subj, verb="is", obj=obj,
                        verb_type="SPATIAL", preposition=prep,
                        raw_text=match.group(0),
                    ))

        # Pattern 5: Simple "X VERB Y" fallback -- scan for any known verb
        if not triples:
            for i, token in enumerate(tokens):
                if token in VERB_RELATION_MAP:
                    subj = self._find_entity_before(tokens, i)
                    obj = self._find_entity_after(tokens, i)
                    subj = self._canonicalize_entity_name(subj) if subj else ""
                    obj = self._canonicalize_entity_name(obj) if obj else ""
                    if subj and obj:
                        triples.append(SemanticTriple(
                            subject=subj, verb=token, obj=obj,
                            verb_type="ACTION", raw_text=f"{subj} {token} {obj}",
                        ))

        # Pattern 6: Possessive "X's Y" -> CONTAINS relation
        for match in re.finditer(r"(\w+)'s\s+(\w+)", sentence):
            owner, owned = match.group(1), match.group(2)
            if owner not in STOP_WORDS and owned not in STOP_WORDS:
                triples.append(SemanticTriple(
                    subject=owner, verb="has", obj=owned,
                    verb_type="POSSESSION", raw_text=match.group(0),
                ))

        # Pattern 7: Comma-separated entity lists "X, Y, and Z"
        if not triples:
            entity_list = re.findall(r'\b([a-z]+)\b', sentence)
            content_words = [w for w in entity_list if w not in STOP_WORDS and len(w) > 2]
            if len(content_words) >= 2:
                for i in range(len(content_words) - 1):
                    triples.append(SemanticTriple(
                        subject=content_words[i],
                        verb="near",
                        obj=content_words[i + 1],
                        verb_type="SPATIAL",
                        raw_text=f"{content_words[i]} near {content_words[i + 1]}",
                    ))

        return triples

    def _find_entity_before(self, tokens: List[str], verb_idx: int) -> Optional[str]:
        """Find the nearest entity-like word before the verb."""
        for i in range(verb_idx - 1, -1, -1):
            if tokens[i] not in STOP_WORDS and len(tokens[i]) > 1:
                return tokens[i]
        return None

    def _find_entity_after(self, tokens: List[str], verb_idx: int) -> Optional[str]:
        """Find the nearest entity-like word after the verb."""
        skip = {"to", "toward", "towards", "from", "away", "at", "in", "on"}
        for i in range(verb_idx + 1, len(tokens)):
            if tokens[i] in skip:
                continue
            if tokens[i] not in STOP_WORDS and len(tokens[i]) > 1:
                return tokens[i]
        return None

    def _canonicalize_entity_name(self, name: str) -> str:
        """Normalize entity name for consistency.

        Filters out adjectives (properties), prepositions (relation
        indicators), verbs (they indicate relations, not entities),
        and stop words (determiners, pronouns, etc.).
        """
        name = re.sub(r'[^a-z0-9_]', '', name.lower().strip())

        if not name or len(name) <= 1:
            return ""

        # Filter out stop words (determiners, pronouns, etc.)
        if name in STOP_WORDS:
            return ""

        # Filter out property ADJECTIVES only
        if name in PROPERTY_ADJECTIVES:
            return ""

        # Filter out spatial/directional prepositions
        if name in SPATIAL_PREPOSITIONS or name in DIRECTIONAL_PREPOSITIONS:
            return ""

        # Filter out known verbs
        if name in VERB_RELATION_MAP:
            return ""

        # Filter out copular verbs
        if name in COPULAR_VERBS:
            return ""

        return name

    def _infer_etype(self, name: str, grammatical_role: str) -> str:
        """Infer entity type from name and grammatical role."""
        name_lower = name.lower()
        for keyword, etype in [
            ("agent", "AGENT"), ("player", "AGENT"), ("robot", "AGENT"),
            ("goal", "TARGET"), ("target", "TARGET"), ("objective", "TARGET"),
            ("resource", "RESOURCE"), ("food", "RESOURCE"), ("item", "RESOURCE"),
            ("threat", "THREAT"), ("enemy", "THREAT"), ("obstacle", "THREAT"),
            ("wall", "OBSTACLE"), ("barrier", "OBSTACLE"), ("block", "OBSTACLE"),
        ]:
            if keyword in name_lower:
                return etype

        if grammatical_role == "SUBJECT":
            return "AGENT"
        elif grammatical_role == "OBJECT":
            return "PATIENT"
        return "ENTITY"

    def _verb_to_rtype(self, triple: SemanticTriple) -> Optional[str]:
        """Convert a semantic triple to a structural relation type."""
        if triple.verb_type == "SPATIAL":
            prep = triple.preposition
            if prep in SPATIAL_PREPOSITIONS:
                return "NEAR"
            if prep in DIRECTIONAL_PREPOSITIONS:
                if prep in ("toward", "towards", "to", "into", "onto"):
                    return "APPROACHES"
                elif prep in ("away", "from"):
                    return "AVOIDS"
            return "NEAR"

        if triple.verb_type == "POSSESSION":
            return "CONTAINS"

        if triple.verb_type == "COPULAR":
            if triple.obj in PROPERTY_VALENCE_MAP:
                return None
            return "NEAR"

        return VERB_RELATION_MAP.get(triple.verb, "RELATED")

    def _extract_properties(self, sentence: str) -> List[Tuple[str, str]]:
        """Extract property assertions from a sentence.

        Returns list of (entity_name, valence) pairs.
        All names are canonicalized to filter out non-entity words.
        """
        props = []

        # "X is ADJ" patterns
        for cop in COPULAR_VERBS:
            for adj, valence in PROPERTY_VALENCE_MAP.items():
                pattern = rf'(\w+)\s+{cop}\s+{adj}\b'
                for match in re.finditer(pattern, sentence):
                    name = self._canonicalize_entity_name(match.group(1))
                    if name:
                        props.append((name, valence))

        # "ADJ X" patterns (adjective before noun)
        for adj, valence in PROPERTY_VALENCE_MAP.items():
            pattern = rf'(?:a|an|the)?\s*{adj}\s+(\w+)'
            for match in re.finditer(pattern, sentence):
                name = self._canonicalize_entity_name(match.group(1))
                if name:
                    props.append((name, valence))

        # Entity names that suggest valence
        for keyword, valence in PROPERTY_VALENCE_MAP.items():
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, sentence):
                name = self._canonicalize_entity_name(keyword)
                if name:
                    props.append((name, valence))

        return props

    def _simple_heuristic_parse(self, text: str) -> Tuple[Dict[str, ParsedEntity], List[ParsedRelation]]:
        """Fallback: simple word-pair extraction for very simple inputs."""
        entities: Dict[str, ParsedEntity] = {}
        relations: List[ParsedRelation] = []

        words = re.findall(r'\b[a-z]+\b', text)
        all_filtered = STOP_WORDS | set(VERB_RELATION_MAP.keys()) | set(COPULAR_VERBS) | set(SPATIAL_PREPOSITIONS) | set(DIRECTIONAL_PREPOSITIONS) | set(PROPERTY_VALENCE_MAP.keys())
        content_words = [w for w in words if w not in all_filtered and len(w) > 2]

        if len(content_words) >= 2:
            for i, word in enumerate(content_words[:8]):
                valence = PROPERTY_VALENCE_MAP.get(word)
                entities[word] = ParsedEntity(
                    name=word,
                    etype=f"ENTITY_{i}",
                    valence=valence,
                )

            ent_names = list(entities.keys())
            for i in range(len(ent_names) - 1):
                relations.append(ParsedRelation(
                    source=ent_names[i], target=ent_names[i + 1],
                    rtype="NEAR",
                ))

        return entities, relations

    def _parse_with_llm(self, text: str) -> ParsedGraph:
        """LLM-based parsing (future implementation)."""
        return self._parse_robust(text)


# --- GRAPH -> NL DESCRIPTION ----------------------------------------------------

class GraphDescriber:
    """Describes RealityGraph structures and Schemas in natural language.

    This is the reverse direction: given a graph or schema, produce a
    human-readable description. This is useful for:
    - Explaining transfer reasoning to users
    - Compressing schemas into compact language representations
    - Debugging and interpretability
    """

    ROLE_DESCRIPTIONS = {
        "HUB_OUT": "a central node that influences many others",
        "HUB_IN": "a central node influenced by many others",
        "BRIDGE": "a connector between different parts of the structure",
        "SOURCE": "an origin point with outgoing influence",
        "SINK": "an endpoint that receives influence",
        "ISOLATED": "an isolated element with no connections",
    }

    VALENCE_DESCRIPTIONS = {
        "POSITIVE": "beneficial",
        "NEGATIVE": "harmful",
        "NEUTRAL": "neutral",
        "GOOD": "beneficial",
        "BAD": "harmful",
        "MIXED": "mixed",
        "VARIES": "variable",
    }

    def describe_graph(self, graph: RealityGraph) -> str:
        """Describe a RealityGraph in natural language."""
        if not graph._entities:
            return "An empty structure."

        parts = []
        etype_counts = Counter(e.etype for e in graph.entities())
        rtype_counts = Counter(r.rtype for r in graph.relations())

        ent_desc = ", ".join(f"{count} {etype.lower()}{'s' if count > 1 else ''}"
                           for etype, count in etype_counts.most_common())
        parts.append(f"A structure with {ent_desc}")

        if rtype_counts:
            rel_desc = ", ".join(f"{count} {rtype.lower()} link{'s' if count > 1 else ''}"
                               for rtype, count in rtype_counts.most_common())
            parts.append(f"connected by {rel_desc}")

        role_counts = Counter(
            entity_structural_signature(graph, e.id)
            for e in graph.entities()
        )
        role_desc_parts = []
        for role, count in role_counts.most_common(3):
            desc = self.ROLE_DESCRIPTIONS.get(role, f"a node with {role}")
            if count > 1:
                role_desc_parts.append(f"{count} are {desc}")
            else:
                role_desc_parts.append(f"one is {desc}")

        if role_desc_parts:
            parts.append("Structurally: " + "; ".join(role_desc_parts))

        return ". ".join(parts) + "."

    def describe_schema(self, schema: Schema) -> str:
        """Describe a schema in natural language."""
        parts = []

        parts.append(f"Schema '{schema.name}' with {len(schema.slots)} elements")

        role_groups = defaultdict(list)
        for slot in schema.slots:
            role_groups[slot.structural_role].append(slot.slot_id)

        for role, slot_ids in role_groups.items():
            desc = self.ROLE_DESCRIPTIONS.get(role, role)
            parts.append(f"  {', '.join(slot_ids)}: {desc}")

        if schema.relations:
            parts.append(f"  {len(schema.relations)} connection{'s' if len(schema.relations) > 1 else ''} between elements")

        val_desc = self.VALENCE_DESCRIPTIONS.get(schema.expected_outcome_signature, schema.expected_outcome_signature)
        parts.append(f"  Expected outcome: {val_desc}")

        if schema.recommended_action_role:
            parts.append(f"  Effective action: {schema.recommended_action_role.lower().replace('_', ' ')}")

        if schema.source_domains:
            parts.append(f"  Observed in: {', '.join(sorted(schema.source_domains))}")

        return "\n".join(parts)

    def describe_transfer(
        self,
        source_schema: Schema,
        target_graph: RealityGraph,
        mapping: Dict[str, str],
    ) -> str:
        """Describe a transfer reasoning step in natural language."""
        parts = []
        parts.append(f"Transfer reasoning:")

        parts.append(f"  In previous experience, I learned that in a structure with {source_schema.expected_outcome_signature.lower()} outcome,")
        if source_schema.recommended_action_role:
            parts.append(f"  the action '{source_schema.recommended_action_role.lower().replace('_', ' ')}' is effective.")

        parts.append(f"  The current situation has {len(mapping)} structurally matching elements:")
        for slot_id, entity_id in mapping.items():
            parts.append(f"    {slot_id} -> {entity_id}")

        if source_schema.recommended_action_role:
            parts.append(f"  Therefore, I recommend: {source_schema.recommended_action_role.lower().replace('_', ' ')}")

        return "\n".join(parts)

    def compress_schema_to_nl(self, schema: Schema) -> str:
        """Compress a schema into a compact natural language representation."""
        slot_descs = []
        for slot in schema.slots:
            role_desc = self.ROLE_DESCRIPTIONS.get(slot.structural_role, slot.structural_role)
            slot_descs.append(f"{slot.slot_id} ({role_desc})")

        val_desc = self.VALENCE_DESCRIPTIONS.get(schema.expected_outcome_signature, schema.expected_outcome_signature)

        action_desc = ""
        if schema.recommended_action_role:
            action_desc = f", {schema.recommended_action_role.lower().replace('_', ' ')} is effective"

        return (
            f"A {val_desc} situation with {', '.join(slot_descs[:3])}"
            f" and {len(schema.relations)} connections{action_desc}."
        )


# --- SCHEMA DESCRIBER ------------------------------------------------------------

class SchemaDescriber:
    """Describes schema-level insights and causal discoveries in natural language.

    Provides human-readable descriptions of transfer reasoning and causal
    discoveries for interpretability and user-facing explanations.
    """

    def describe_transfer_insight(
        self,
        schema: Schema,
        source_domain: str,
        target_domain: str,
        match_score: float = 0.0,
    ) -> str:
        """Describe a schema transfer insight between two domains."""
        pct = round(match_score * 100)
        return (
            f"Schema '{schema.name}' learned in {source_domain} "
            f"transfers to {target_domain} with {pct}% structural match."
        )

    def describe_causal_discovery(
        self,
        action_name: str,
        effect: float = 0.0,
        confidence: float = 0.0,
    ) -> str:
        """Describe a discovered causal effect."""
        direction = "improves" if effect > 0 else "harms"
        return (
            f"Discovered that '{action_name}' {direction} outcomes "
            f"(effect={effect:.2f}, confidence={confidence:.2f})."
        )


# --- LANGUAGE GROUNDING ENGINE --------------------------------------------------

class LanguageGroundingEngine:
    """Bidirectional grounding between NL and graph/schema representations.

    This is the integration point: it connects the NL parser, graph describer,
    and schema learner to enable:
    1. Learning from natural language descriptions
    2. Explaining reasoning in natural language
    3. Compressing schemas into language for efficient storage
    """

    def __init__(
        self,
        parser: Optional[NLGraphParser] = None,
        describer: Optional[GraphDescriber] = None,
        schema_learner: Optional[SchemaLearner] = None,
    ):
        self.parser = parser or NLGraphParser()
        self.describer = describer or GraphDescriber()
        self.schema_learner = schema_learner
        self._parse_cache: Dict[str, ParsedGraph] = {}

    def text_to_graph(self, text: str) -> RealityGraph:
        """Convert natural language text to a RealityGraph."""
        if text in self._parse_cache:
            parsed = self._parse_cache[text]
        else:
            parsed = self.parser.parse(text)
            self._parse_cache[text] = parsed

        graph = RealityGraph("nl_parsed", f"from_text_{hashlib.md5(text.encode()).hexdigest()[:8]}")

        for pe in parsed.entities:
            etype = pe.etype if pe.etype != "UNKNOWN" else "ENTITY"
            props = dict(pe.properties)
            if pe.valence:
                props["valence"] = pe.valence
            graph.add_entity(Entity(pe.name, etype, props))

        for pr in parsed.relations:
            if graph.get_entity(pr.source) and graph.get_entity(pr.target):
                graph.add_relation(Relation(pr.source, pr.rtype, pr.target))

        return graph

    def graph_to_text(self, graph: RealityGraph) -> str:
        """Convert a RealityGraph to natural language description."""
        return self.describer.describe_graph(graph)

    def schema_to_text(self, schema: Schema) -> str:
        """Convert a schema to natural language description."""
        return self.describer.describe_schema(schema)

    def compress_schema(self, schema: Schema) -> str:
        """Compress a schema to a compact NL representation."""
        return self.describer.compress_schema_to_nl(schema)

    def explain_transfer(
        self,
        source_schema: Schema,
        target_graph: RealityGraph,
        mapping: Dict[str, str],
    ) -> str:
        """Explain a transfer reasoning step in natural language."""
        return self.describer.describe_transfer(source_schema, target_graph, mapping)

    def learn_from_text(
        self,
        text: str,
        action_op: Optional[str] = None,
        outcome_valence: str = "NEUTRAL",
        domain: str = "nl_input",
    ) -> Optional[Schema]:
        """Learn a schema from a natural language description."""
        if self.schema_learner is None:
            return None

        graph = self.text_to_graph(text)
        if not graph._entities:
            return None

        from .reality import Consequence, Transformation
        net_reward = 1.0 if outcome_valence == "POSITIVE" else (-1.0 if outcome_valence == "NEGATIVE" else 0.0)
        consequence = Consequence(reward=max(0, net_reward), penalty=max(0, -net_reward))

        action = Transformation(
            name=f"nl_action_{action_op or 'unknown'}",
            domain=domain,
            universal_op=action_op or "OBSERVE",
        )

        return self.schema_learner.learn_from_episode(graph, action, consequence, domain, tick=0)

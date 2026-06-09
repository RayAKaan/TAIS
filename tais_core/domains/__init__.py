"""Tiny validation domains for the TAIS universal base."""

from .gridworld import GridGraphWorld, make_grid_graph
from .sequences import SequenceWorld, make_sequence_graph
from .rules import (
    RuleWorld,
    RuleWorldEasy,
    RuleWorldChain,
    RuleWorldChainLong,
    RuleWorldDistractor,
    make_rule_graph,
    make_rule_graph_easy,
    make_rule_graph_chain,
    make_rule_graph_distractor,
    make_rule_graph_chain_long,
)
from .hazard import (
    HazardGraphWorld,
    HazardGraphWorldLarge,
    make_hazard_graph_easy,
    make_hazard_graph_distractor,
    make_hazard_graph_large,
)
from .logic import (
    LogicWorld,
    LogicWorldChain,
    LogicWorldLarge,
    LogicWorldUnsat,
    make_logic_graph_easy,
    make_logic_graph_chain,
    make_logic_graph_large,
    make_logic_graph_unsat,
)
from .registry import load_domain

__all__ = [
    "GridGraphWorld",
    "make_grid_graph",
    "SequenceWorld",
    "make_sequence_graph",
    "RuleWorld",
    "RuleWorldEasy",
    "RuleWorldChain",
    "RuleWorldChainLong",
    "RuleWorldDistractor",
    "make_rule_graph",
    "make_rule_graph_easy",
    "make_rule_graph_chain",
    "make_rule_graph_distractor",
    "make_rule_graph_chain_long",
    "HazardGraphWorld",
    "HazardGraphWorldLarge",
    "make_hazard_graph_easy",
    "make_hazard_graph_distractor",
    "make_hazard_graph_large",
    "LogicWorld",
    "LogicWorldChain",
    "LogicWorldLarge",
    "LogicWorldUnsat",
    "make_logic_graph_easy",
    "make_logic_graph_chain",
    "make_logic_graph_large",
    "make_logic_graph_unsat",
    "load_domain",
]

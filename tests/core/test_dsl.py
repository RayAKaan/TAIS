"""Tests for the TAIS Domain Specification Language."""
import os
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
_SPECS = _ROOT / "tais_core" / "dsl" / "specs"


class TestParser(unittest.TestCase):
    def test_load_gridworld_yaml(self):
        from tais_core.dsl.parser import load_spec
        spec = load_spec(_SPECS / "gridworld.yaml")
        self.assertEqual(spec["name"], "GridWorld")
        self.assertIn("backend", spec)

    def test_load_chemistry_yaml(self):
        from tais_core.dsl.parser import load_spec
        spec = load_spec(_SPECS / "chemistry_lite.yaml")
        self.assertEqual(spec["name"], "ChemistryLite")
        self.assertIn("entities", spec)

    def test_invalid_suffix_raises(self):
        from tais_core.dsl.parser import load_spec
        not_a_spec = _ROOT / "tests/core/test_dsl.py"
        with self.assertRaises(ValueError):
            load_spec(not_a_spec)

    def test_nonexistent_file_raises(self):
        from tais_core.dsl.parser import load_spec
        with self.assertRaises(FileNotFoundError):
            load_spec(_SPECS / "no_such_file.yaml")


class TestValidator(unittest.TestCase):
    def test_valid_backend_spec_passes(self):
        from tais_core.dsl.parser import load_spec
        from tais_core.dsl.validator import validate_spec
        spec = load_spec(_SPECS / "gridworld.yaml")
        result = validate_spec(spec)
        self.assertIs(result, spec)

    def test_valid_declarative_spec_passes(self):
        from tais_core.dsl.parser import load_spec
        from tais_core.dsl.validator import validate_spec
        spec = load_spec(_SPECS / "chemistry_lite.yaml")
        result = validate_spec(spec)
        self.assertIs(result, spec)

    def test_missing_name_raises(self):
        from tais_core.dsl.validator import validate_spec, DomainSpecError
        with self.assertRaises(DomainSpecError):
            validate_spec({"version": "1.0"})

    def test_invalid_universal_op_raises(self):
        from tais_core.dsl.validator import validate_spec, DomainSpecError
        bad_spec = {
            "name": "Bad",
            "version": "1.0",
            "entities": {"E": {}},
            "relations": {},
            "actions": [{"name": "bad_action", "universal_op": "NOT_AN_OP"}],
            "graph": {"entities": [], "relations": []},
        }
        with self.assertRaises(DomainSpecError):
            validate_spec(bad_spec)

    def test_nonexistent_action_role_raises(self):
        from tais_core.dsl.validator import validate_spec, DomainSpecError
        bad_spec = {
            "name": "Bad",
            "version": "1.0",
            "entities": {"E": {}},
            "relations": {},
            "actions": [{"name": "real_action", "universal_op": "VERIFY"}],
            "action_roles": {"APPROACH_GOOD": "no_such_action"},
            "graph": {"entities": [], "relations": []},
        }
        with self.assertRaises(DomainSpecError):
            validate_spec(bad_spec)


class TestBuiltinLoader(unittest.TestCase):
    def test_load_gridworld(self):
        from tais_core import load_domain, UniversalMote
        world = load_domain("gridworld")
        graph = world.initial_graph()
        self.assertGreater(len(graph), 0)
        mote = UniversalMote(energy=100)
        graph, cons, action = mote.step(world, graph, mote_position="mote", tick=0)
        self.assertIsNotNone(cons)
        self.assertIsInstance(world.domain_name, str)

    def test_load_rules(self):
        from tais_core import load_domain, UniversalMote
        world = load_domain("rules")
        graph = world.initial_graph()
        self.assertGreater(len(graph), 0)
        mote = UniversalMote(energy=100)
        graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=0)
        self.assertIsNotNone(cons)

    def test_load_logic(self):
        from tais_core import load_domain, UniversalMote
        world = load_domain("logic")
        graph = world.initial_graph()
        self.assertGreater(len(graph), 0)
        mote = UniversalMote(energy=100)
        graph, cons, action = mote.step(world, graph, mote_position="ASSIGN", tick=0)
        self.assertIsNotNone(cons)

    def test_load_by_path(self):
        from tais_core.dsl.codegen import load_domain_from_spec
        world = load_domain_from_spec(_SPECS / "gridworld.yaml")
        graph = world.initial_graph()
        self.assertGreater(len(graph), 0)


class TestDeclarativeLoader(unittest.TestCase):
    def test_load_chemistry(self):
        from tais_core import load_domain
        world = load_domain("chemistry_lite")
        graph = world.initial_graph()
        self.assertIn("atom_c", graph)
        self.assertIn("atom_o", graph)
        self.assertIn("unstable_molecule", graph)

    def test_chemistry_valid_actions(self):
        from tais_core import load_domain
        world = load_domain("chemistry_lite")
        graph = world.initial_graph()
        actions = world.valid_actions(graph, {})
        names = [a.name for a in actions]
        self.assertIn("form_bond", names)
        self.assertIn("check_valence", names)

    def test_chemistry_form_bond_effect(self):
        from tais_core import load_domain
        world = load_domain("chemistry_lite")
        graph = world.initial_graph()
        actions = world.valid_actions(graph, {})
        action = next(a for a in actions if a.name == "form_bond")
        after, cons = world.act(graph, action, {})
        self.assertTrue(cons.valid)
        self.assertEqual(cons.task_signal, "TASK_SUCCESS")
        self.assertIsNotNone(after.get_entity("stable_molecule"))
        self.assertGreater(world.evaluate(after, {}), world.evaluate(graph, {}))

    def test_chemistry_unknown_action(self):
        from tais_core import load_domain
        from tais_core.reality import Transformation
        world = load_domain("chemistry_lite")
        graph = world.initial_graph()
        bad_action = Transformation(name="no_such_action", domain="chemistry_lite", universal_op="VERIFY")
        after, cons = world.act(graph, bad_action, {})
        self.assertFalse(cons.valid)
        self.assertEqual(cons.task_signal, "TASK_FAILURE")


class TestPublicAPI(unittest.TestCase):
    def test_load_domain_is_callable(self):
        from tais_core import load_domain
        self.assertTrue(callable(load_domain))

    def test_unknown_name_raises(self):
        from tais_core import load_domain
        with self.assertRaises(ValueError):
            load_domain("no_such_domain")


class TestCrossDomainMoteStep(unittest.TestCase):
    def test_all_domains_step_with_mote(self):
        from tais_core import load_domain, UniversalMote
        for name, pos in [
            ("gridworld", "mote"),
            ("rules", "rule_ab"),
            ("logic", "ASSIGN"),
            ("chemistry_lite", "atom_c"),
        ]:
            with self.subTest(domain=name):
                world = load_domain(name)
                graph = world.initial_graph()
                mote = UniversalMote(energy=100)
                graph, cons, action = mote.step(world, graph, mote_position=pos, tick=0)
                self.assertIsNotNone(cons)
                self.assertIsInstance(cons.net, float)


if __name__ == "__main__":
    unittest.main()

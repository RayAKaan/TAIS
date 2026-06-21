import unittest
from tais_core.domains.python_ast import PythonASTWorld
from tais_core.mote import UniversalMote


class TestPythonAST(unittest.TestCase):
    def test_ast_parse_and_step(self):
        world = PythonASTWorld(source_code="x = 1")
        graph = world.initial_graph()
        self.assertGreater(len(graph.entities()), 0)

        mote = UniversalMote()
        next_g, cons, action = mote.step(world, graph, mote_position="root", tick=0)
        self.assertTrue(cons.valid)

    def test_evaluate_success(self):
        world = PythonASTWorld(source_code="x = 1")
        graph = world.initial_graph()
        mote = UniversalMote()

        actions = world.valid_actions(graph, {})
        mutate_action = next(a for a in actions if a.name == "mutate_constant")
        next_g, cons = world.act(graph, mutate_action, {})

        self.assertEqual(world.evaluate(next_g, {}), 10.0)


if __name__ == "__main__":
    unittest.main()

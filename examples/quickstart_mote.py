from tais_core import UniversalMote, load_domain


def main():
    world = load_domain("rules")
    graph = world.initial_graph()

    mote = UniversalMote(energy=100)
    graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=0)

    print("action:", action.name if action else None)
    print("net consequence:", cons.net)
    print("metrics:", mote.metrics())


if __name__ == "__main__":
    main()

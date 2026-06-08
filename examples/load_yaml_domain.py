from tais_core import UniversalMote, load_domain


def main():
    world = load_domain("chemistry_lite")
    graph = world.initial_graph()

    mote = UniversalMote(energy=100)
    for tick in range(5):
        graph, cons, action = mote.step(world, graph, mote_position="atom_c", tick=tick)
        print(tick, action.name if action else None, cons.net, cons.task_signal)


if __name__ == "__main__":
    main()

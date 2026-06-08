from pathlib import Path

from tais_core import UniversalMote, load_domain
from tais_core.viz import (
    record_mote_trajectory,
    save_trajectory_html,
    save_trajectory_json,
)


def main():
    out = Path("results/example_figures")
    out.mkdir(parents=True, exist_ok=True)

    world = load_domain("chemistry_lite")
    graph = world.initial_graph()
    mote = UniversalMote(energy=100)

    records = record_mote_trajectory(
        world,
        graph,
        mote,
        mote_position="atom_c",
        ticks=5,
    )

    save_trajectory_json(records, out / "trajectory.json")
    save_trajectory_html(records, out / "trajectory.html")
    print("wrote", out)


if __name__ == "__main__":
    main()

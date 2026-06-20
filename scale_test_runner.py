"""
TAIS Phase 4: Scale Test.
Measuring performance and precision as graph size increases from 10 to 1000 nodes.
"""

import time
import random
import numpy as np
import matplotlib.pyplot as plt
from tais_core.mote import UniversalMote
from tais_core.domains.python_ast import PythonASTWorld


def generate_large_source(num_lines=100):
    lines = [f"x_{i} = {i} + {i+1}" for i in range(num_lines)]
    return "\n".join(lines)


def run_scale_test():
    scales = [5, 20, 50, 100, 200, 500]
    latencies = []
    precisions = []

    print("=== TAIS SCALE TEST (Graph Size vs. Performance) ===")
    print(f"{'Nodes':<10} | {'Time/Tick (ms)':<15} | {'Precision':<10}")
    print("-" * 45)

    for s in scales:
        source = generate_large_source(s)
        world = PythonASTWorld(source_code=source)
        g = world.initial_graph()
        num_nodes = len(list(g.entities()))

        mote = UniversalMote()

        start = time.time()
        for t in range(5):
            g, cons, _ = mote.step(world, g, mote_position="root", tick=t)
        end = time.time()

        avg_time = ((end - start) / 5) * 1000
        metrics = mote.metrics()
        prec = metrics.get("transfer_prior_precision", 0.0)

        print(f"{num_nodes:<10} | {avg_time:<15.2f} | {prec*100:<10.1f}%")
        latencies.append(avg_time)
        precisions.append(prec)


if __name__ == "__main__":
    run_scale_test()

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .common import save_figure


def plot_lexicon_convergence(
    ticks: Sequence[int],
    convergence: Sequence[float],
    title: str = "Lexicon Convergence",
    output: str | Path | None = None,
):
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(list(ticks), list(convergence), marker=".", linestyle="-", linewidth=1.2, markersize=4)
    ax.set_xlabel("Tick", fontsize=9)
    ax.set_ylabel("Convergence Score", fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if output:
        return save_figure(fig, output)
    return fig


def compute_pairwise_lexicon_agreement(lexicons: Sequence[Mapping[str, str]]) -> float:
    if len(lexicons) < 2:
        return 0.0
    shared_tokens: set[str] | None = None
    for lex in lexicons:
        tokens = set(lex.keys())
        if shared_tokens is None:
            shared_tokens = tokens
        else:
            shared_tokens &= tokens
    if not shared_tokens:
        return 0.0
    total_agreements = 0
    total_pairs = 0
    for token in shared_tokens:
        concepts = [lex[token] for lex in lexicons]
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                total_pairs += 1
                if concepts[i] == concepts[j]:
                    total_agreements += 1
    return total_agreements / total_pairs if total_pairs > 0 else 0.0

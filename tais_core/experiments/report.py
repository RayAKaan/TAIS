from __future__ import annotations

from pathlib import Path
from typing import List

from .results import ExperimentResults


class ExperimentReport:
    def __init__(self, results: ExperimentResults):
        self.results = results

    def markdown(self) -> str:
        lines: List[str] = []
        lines.append(f"# Experiment Report: {self.results.name}")
        lines.append("")
        lines.append("## Provenance")
        lines.append("")
        prov = self.results.provenance
        lines.append(f"- **Timestamp (UTC):** {prov.get('timestamp_utc', 'N/A')}")
        lines.append(f"- **Python:** {prov.get('python', 'N/A')}")
        lines.append(f"- **Platform:** {prov.get('platform', 'N/A')}")
        lines.append(f"- **Git SHA:** {prov.get('git_sha', 'N/A')}")
        lines.append(f"- **Git Branch:** {prov.get('git_branch', 'N/A')}")
        lines.append("")
        lines.append(f"Baseline condition: **{self.results.baseline_condition}**")
        lines.append("")
        cond_names = [c for c in self.results.records if c != self.results.baseline_condition]
        lines.append(f"Conditions: {', '.join(cond_names)}")
        n = max((len(v) for v in self.results.records.values()), default=0)
        lines.append(f"Seeds per condition: {n}")
        lines.append("")

        summary = self.results.summary()
        for metric in self.results.metrics:
            lines.append(f"## {metric.name}")
            lines.append("")
            lines.append(f"{metric.description}")
            lines.append("")
            lines.append("| Condition | Baseline | Condition | Delta | 95% CI | p | d |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|")
            for cond_name in cond_names:
                vals = summary["conditions"][cond_name].get(metric.name, {})
                ci = f"[{vals.get('ci_low', 'N/A')}, {vals.get('ci_high', 'N/A')}]"
                p_raw = vals.get("p", 1.0)
                if p_raw < 0.001:
                    p_str = f"{p_raw:.2e} ***"
                elif p_raw < 0.01:
                    p_str = f"{p_raw:.4f} **"
                elif p_raw < 0.05:
                    p_str = f"{p_raw:.4f} *"
                else:
                    p_str = f"{p_raw:.4f}"
                lines.append(
                    f"| {cond_name} | {vals.get('baseline', 'N/A')} | "
                    f"{vals.get('condition', 'N/A')} | {vals.get('delta', 'N/A')} | "
                    f"{ci} | {p_str} | {vals.get('d', 'N/A')} |"
                )
            lines.append("")
        return "\n".join(lines)

    def latex_table(self) -> str:
        lines: List[str] = []
        lines.append(r"\begin{tabular}{lrrrrrr}")
        lines.append(r"\toprule")
        lines.append(r"Condition & Baseline & Condition & Delta & CI Low & CI High & d \\")
        lines.append(r"\midrule")

        summary = self.results.summary()
        cond_names = [c for c in self.results.records if c != self.results.baseline_condition]
        for metric in self.results.metrics:
            lines.append(f"  \\multicolumn{{7}}{{l}}{{\\textit{{{metric.name}}}}} \\\\")
            for cond_name in cond_names:
                vals = summary["conditions"][cond_name].get(metric.name, {})
                lines.append(
                    f"  {cond_name} & {vals.get('baseline', 'N/A')} & "
                    f"{vals.get('condition', 'N/A')} & {vals.get('delta', 'N/A')} & "
                    f"{vals.get('ci_low', 'N/A')} & {vals.get('ci_high', 'N/A')} & "
                    f"{vals.get('d', 'N/A')} \\\\"
                )
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        return "\n".join(lines)

    def save_markdown(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.markdown())

    def save_latex(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.latex_table())

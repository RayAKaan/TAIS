#!/usr/bin/env python3
"""Generate all paper figures from committed result artifacts.

Usage:
    python scripts/generate_paper_figures.py

Output: PNG files in paper/figures/
"""

import json
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'paper', 'figures')
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')

os.makedirs(FIGURES_DIR, exist_ok=True)

plt.rcParams.update({'figure.max_open_warning': 0})

def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_csv(path):
    rows = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ─── Figure 1: Domain Count Scaling ───────────────────────────────────────────
def fig_domain_count_scaling():
    raw = load_json(os.path.join(RESULTS_DIR, 'phase_f2', 'domain_count_scaling.json'))
    data = raw['summary']['conditions']
    conditions = ['one_grid', 'two_grid_rules', 'three_grid_rules_chem',
                  'four_grid_rules_chem_hazard', 'five_grid_rules_chem_hazard_sequences',
                  'same_domain_logic']
    labels = ['1 grid', '2 grid+rules', '3 grid+rules+chem',
              '4 +hazard', '5 +sequences', 'same(logic)']
    tick_deltas = [data[c].get('first_task_success_tick', {}).get('delta', 0) for c in conditions]
    tick_cis = [(data[c].get('first_task_success_tick', {}).get('ci_low', 0),
                 data[c].get('first_task_success_tick', {}).get('ci_high', 0)) for c in conditions]
    ctr_deltas = [data[c].get('task_completion_rate', {}).get('delta', 0) for c in conditions]
    ctr_cis = [(data[c].get('task_completion_rate', {}).get('ci_low', 0),
                data[c].get('task_completion_rate', {}).get('ci_high', 0)) for c in conditions]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    x = np.arange(len(conditions))

    ax1.bar(x, tick_deltas, color='steelblue')
    yerr1 = np.array([[(d - l) for d, (l, u) in zip(tick_deltas, tick_cis)],
                      [(u - d) for d, (l, u) in zip(tick_deltas, tick_cis)]])
    ax1.errorbar(x, tick_deltas,
                 yerr=yerr1,
                 fmt='none', color='black', capsize=3)
    ax1.axhline(0, color='gray', linestyle='--')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha='right')
    ax1.set_ylabel('First Success Tick Delta')
    ax1.set_title('First Task Success Tick')

    ax2.bar(x, ctr_deltas, color='seagreen')
    yerr2 = np.array([[(d - l) for d, (l, u) in zip(ctr_deltas, ctr_cis)],
                      [(u - d) for d, (l, u) in zip(ctr_deltas, ctr_cis)]])
    ax2.errorbar(x, ctr_deltas,
                 yerr=yerr2,
                 fmt='none', color='black', capsize=3)
    ax2.axhline(0, color='gray', linestyle='--')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha='right')
    ax2.set_ylabel('Completion Rate Delta')
    ax2.set_title('Task Completion Rate')

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig_domain_count_scaling.png'), dpi=150)
    plt.close()
    print('  fig_domain_count_scaling.png')


# ─── Figure 2: Role-Balanced Curriculum ───────────────────────────────────────
def fig_role_balanced_curriculum():
    data = load_json(os.path.join(RESULTS_DIR, 'phase_f2', 'role_balanced_curriculum.json'))
    conditions = ['grid_standard', 'danger_only', 'approach_only',
                  'role_balanced', 'logic_same_domain']
    labels = ['grid\nstandard', 'danger\nonly', 'approach\nonly',
              'role\nbalanced', 'logic\nsame-domain']
    tick_deltas = [data[c].get('first_task_success_tick', {}).get('delta', 0) for c in conditions]
    tick_cis = [(data[c].get('first_task_success_tick', {}).get('ci_low', 0),
                 data[c].get('first_task_success_tick', {}).get('ci_high', 0)) for c in conditions]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(conditions))
    colors = ['steelblue' if d < 0 else 'firebrick' for d in tick_deltas]
    ax.bar(x, tick_deltas, color=colors)
    yerr = np.array([[(d - l) for d, (l, u) in zip(tick_deltas, tick_cis)],
                     [(u - d) for d, (l, u) in zip(tick_deltas, tick_cis)]])
    ax.errorbar(x, tick_deltas,
                yerr=yerr,
                fmt='none', color='black', capsize=3)
    ax.axhline(0, color='gray', linestyle='--')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('First Success Tick Delta')
    ax.set_title('Role-Balanced Curriculum (First Task Success Tick)')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig_role_balanced_curriculum.png'), dpi=150)
    plt.close()
    print('  fig_role_balanced_curriculum.png')


# ─── Figure 3: 1000-Seed Replication ──────────────────────────────────────────
def fig_replication():
    data = load_json(os.path.join(RESULTS_DIR, 'phase_f2', 'grid_logic_1000_replication.json'))
    conditions = ['full', 'no_action_role', 'no_pattern_transfer',
                  'no_prediction', 'empty_pretrain', 'random_pretrain', 'logic_pretrain']
    labels = ['Full', 'No action\nrole', 'No pattern\ntransfer',
              'No\nprediction', 'Empty\npretrain', 'Random\npretrain', 'Logic\npretrain']
    tick_deltas = [data[c].get('first_task_success_tick', {}).get('delta', 0) for c in conditions]
    tick_ds = [data[c].get('first_task_success_tick', {}).get('d', 0) for c in conditions]
    ctr_deltas = [data[c].get('task_completion_rate', {}).get('delta', 0) for c in conditions]
    ctr_ds = [data[c].get('task_completion_rate', {}).get('d', 0) for c in conditions]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    x = np.arange(len(conditions))
    width = 0.35

    ax1.bar(x - width/2, tick_deltas, width, color='steelblue', label='Delta')
    ax1_twin = ax1.twinx()
    ax1_twin.bar(x + width/2, tick_ds, width, color='lightcoral', alpha=0.7, label='d')
    ax1.axhline(0, color='gray', linestyle='--')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha='right')
    ax1.set_ylabel('First Success Tick Delta')
    ax1_twin.set_ylabel("Cohen's d")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='lower left')

    ax2.bar(x - width/2, ctr_deltas, width, color='seagreen', label='Delta')
    ax2_twin = ax2.twinx()
    ax2_twin.bar(x + width/2, ctr_ds, width, color='lightcoral', alpha=0.7, label='d')
    ax2.axhline(0, color='gray', linestyle='--')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha='right')
    ax2.set_ylabel('Completion Rate Delta')
    ax2_twin.set_ylabel("Cohen's d")
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='lower left')

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig_grid_logic_replication.png'), dpi=150)
    plt.close()
    print('  fig_grid_logic_replication.png')


# ─── Figure 4: Role-Ontology Robustness ───────────────────────────────────────
def fig_role_ontology_robustness():
    data = load_json(os.path.join(RESULTS_DIR, 'phase_r', 'role_ontology_robustness', 'report.json'))
    conditions = ['canonical_roles', 'shuffled_target_role_hints', 'shuffled_target_universal_ops',
                  'shuffled_source_roles', 'random_compatibility', 'identity_only_compatibility',
                  'no_role_transfer']
    labels = ['Canonical', 'Shuffled\ntarget hints', 'Shuffled\ntarget ops',
              'Shuffled\nsource roles', 'Random\ncompat', 'Identity\ncompat', 'No role']
    tick_deltas = [data[c]['first_task_success_tick']['delta'] for c in conditions]
    tick_cis = [(data[c]['first_task_success_tick']['ci_low'],
                 data[c]['first_task_success_tick']['ci_high']) for c in conditions]
    tick_ds = [data[c]['first_task_success_tick']['d'] for c in conditions]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    x = np.arange(len(conditions))
    width = 0.35

    colors = ['steelblue' if d < 0 else 'firebrick' for d in tick_deltas]
    ax1.bar(x - width/2, tick_deltas, width, color=colors)
    yerr = np.array([[(d - l) for d, (l, u) in zip(tick_deltas, tick_cis)],
                     [(u - d) for d, (l, u) in zip(tick_deltas, tick_cis)]])
    ax1.errorbar(x - width/2, tick_deltas,
                 yerr=yerr,
                 fmt='none', color='black', capsize=3)
    ax1.axhline(0, color='gray', linestyle='--')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha='right')
    ax1.set_ylabel('First Success Tick Delta')

    ax2.bar(x, tick_ds, color='lightcoral')
    ax2.axhline(0, color='gray', linestyle='--')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha='right')
    ax2.set_ylabel("Cohen's d")
    ax2.set_title('Effect Size')

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig_role_ontology_robustness.png'), dpi=150)
    plt.close()
    print('  fig_role_ontology_robustness.png')


# ─── Figure 5: Baseline Comparison ────────────────────────────────────────────
def fig_baseline_comparison():
    data = load_json(os.path.join(RESULTS_DIR, 'phase_r', 'baseline_comparison', 'baseline_comparison.json'))
    agents = ['TAIS_full', 'TAIS_no_pattern_transfer', 'RandomAgent', 'HeuristicAgent', 'TabularQAgent']
    labels = ['TAIS\nfull', 'TAIS\nno pattern', 'Random', 'Heuristic', 'TabularQ']
    ctr = [data[a]['task_completion_rate']['mean'] for a in agents]
    tick = [data[a]['first_task_success_tick']['mean'] for a in agents]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
    x = np.arange(len(agents))

    ax1.bar(x, ctr, color='seagreen')
    ax1.axhline(0.5, color='gray', linestyle='--', label='Chance')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha='right')
    ax1.set_ylabel('Task Completion Rate')

    ax2.bar(x, tick, color='steelblue')
    ax2.axhline(11, color='gray', linestyle='--', label='Chance')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha='right')
    ax2.set_ylabel('First Task Success Tick')

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig_baseline_comparison.png'), dpi=150)
    plt.close()
    print('  fig_baseline_comparison.png')


# ─── Figure 6: Larger-Domain Transfer ─────────────────────────────────────────
def fig_large_domains():
    data = load_json(os.path.join(RESULTS_DIR, 'phase_r', 'large_domain_transfer', 'large_domain_transfer.json'))
    pretrain_conds = ['fresh', 'grid_pretrain', 'rules_pretrain', 'three_domain_pretrain', 'same_domain_pretrain']
    labels = ['Fresh', 'Grid', 'Rules', '3-domain', 'Same-domain']
    targets = ['logic_large', 'hazard_large', 'rules_chain_long']
    target_labels = ['Logic Large', 'Hazard Large', 'Rules Chain Long']

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    x = np.arange(len(pretrain_conds))

    for ax, target, tlabel in zip(axes, targets, target_labels):
        ctr = [data[target][c]['task_completion_rate']['mean'] for c in pretrain_conds]
        ax.bar(x, ctr, color='steelblue')
        ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_title(tlabel)
        ax.set_ylim(0, 1.0)

    axes[0].set_ylabel('Task Completion Rate')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig_large_domains.png'), dpi=150)
    plt.close()
    print('  fig_large_domains.png')


def main():
    print('Generating paper figures...')
    fig_domain_count_scaling()
    fig_role_balanced_curriculum()
    fig_replication()
    fig_role_ontology_robustness()
    fig_baseline_comparison()
    fig_large_domains()
    print('Done. Figures written to paper/figures/')


if __name__ == '__main__':
    main()

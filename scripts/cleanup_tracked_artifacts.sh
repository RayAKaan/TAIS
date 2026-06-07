#!/usr/bin/env bash
# Drop the 31 MB of generated artefacts that the v1 repo accidentally tracked.
# All of these are regenerable from swarm_v5.py or experiments/*.py and are
# now excluded by .gitignore.
#
# Run from the repo root AFTER applying tais_phase0_phase2_phase1.patch.
# This is split out because including the deletions in the patch itself would
# inflate it to 37 MB.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "Removing tracked generated artefacts..."

git rm --quiet --ignore-unmatch \
    colonies/test_v4.json \
    colonies/test_v4b.json \
    colonies/test_v4b_loaded.json \
    colonies/test_v5.json \
    colonies/test_v5_final.json \
    colonies/test_v55_smoke.json

git rm --quiet --ignore-unmatch \
    results/ablation_results.csv \
    results/ablation_results.json \
    results/ablation_results.txt \
    results/ablation_smoke.csv \
    results/ablation_smoke.json \
    results/ablation_smoke.txt \
    results/cross_domain_transfer_results.json \
    results/statistical_replication_results.json

# These are not auto-regenerable but are pure dead weight; history preserves them.
git rm --quiet --ignore-unmatch \
    archive/CODE_DUMP.md \
    archive/tais_lang_v2_results.json

echo
echo "Done. Inspect with: git status"
echo "If satisfied:      git commit -m 'Phase 0 followup: drop tracked generated artefacts'"
echo
echo "Repo size before/after will drop ~31 MB."

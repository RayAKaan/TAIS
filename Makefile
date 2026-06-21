.PHONY: test smoke figures clean import-check

test:
	PYTHONPATH=. python -m unittest discover -s tests -v

import-check:
	PYTHONPATH=. python -c "import experiments.statistical_replication; import experiments.cross_domain_transfer; import experiments.ablation_runner; import experiments.negosim_fused_transfer_runner; import experiments.codesynt_transfer_runner; import experiments.sciex_fused_transfer_runner; import stress_test"

smoke:
	PYTHONPATH=. python experiments/phase_c_logic_transfer_suite.py --seeds 5 --eval 10 --pretrain 5 --output results/smoke_phase_c

figures:
	PYTHONPATH=. python experiments/phase_e/generate_figures.py --phase-d results/phase_d --output results/phase_e/figures

# Unix-friendly cleanup target.
clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +

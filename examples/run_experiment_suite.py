from tais_core.experiments import Condition, ExperimentSuite, Metric


def main():
    suite = ExperimentSuite(
        name="example_grid_to_logic",
        seeds=5,
        conditions=[
            Condition("fresh", pretrain_domains=[]),
            Condition("grid_only", pretrain_domains=["gridworld"]),
        ],
        eval_domain="logic",
        eval_ticks=10,
        pretrain_ticks=5,
        metrics=[
            Metric("first_task_success_tick", lower_is_better=True),
            Metric("task_completion_rate"),
        ],
    )

    results = suite.run(output_dir="results/example_grid_to_logic")
    print(results.summary())


if __name__ == "__main__":
    main()

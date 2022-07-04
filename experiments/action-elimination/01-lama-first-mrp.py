#! /usr/bin/env python

from pathlib import Path

from lab.experiment import Experiment

import project


ATTRIBUTES = [
    "cost",
    "error",
    "plan_length",
    "run_dir",
    "coverage",
    "planner_memory",
    "planner_time",
    "config_times",
]

exp = Experiment()
exp.add_step(
    "remove-combined-properties", project.remove_file, Path(exp.eval_dir) / "properties"
)

for before, after in [("lama-first", None), ("lama-first-mrp-hmax",	None), ("lama-first-mrp-lmcut", None)]:
    project.fetch_algorithm(exp, "2022-07-04-A-lama-first-mrp", before, new_algo=after)
project.fetch_algorithm(exp, "2022-07-04-B-lama-first-mrp-scorpion", "lama-first-mrp-scorpion-sys-scp-goals", new_algo="lama-first-mrp-scorpion")

project.add_absolute_report(
    exp, attributes=ATTRIBUTES, name=f"{exp.name}"
)

exp.add_report(project.PerTaskComparison(attributes=["cost"], sort=True), name=f"{exp.name}-per-task-cost-comparison")

exp.run_steps()

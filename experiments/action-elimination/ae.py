#! /usr/bin/env python

import os

from downward import suites
from downward.cached_revision import CachedFastDownwardRevision
from downward.experiment import (
    _DownwardAlgorithm,
    _get_solver_resource_name,
    FastDownwardRun,
)
from lab.experiment import Experiment
import project


REPO = project.get_repo_base()
# TODO include 2018 ipc problems.
# TODO remove all hardcoded absolute paths.
BENCHMARKS_DIR = "/home/msalerno/dev/docto/action-elimination/experiments/action-elimination/domains/ipc2014/seq-sat"
PLANS_DIR = "/home/msalerno/dev/docto/action-elimination/experiments/action-elimination/plans"
# TODO magadascar, BFWS and yahsp lack plan cost in plan file. Causing problems, need to add cost line.
# PLANNER_NAMES = ["lama-first", "cerberus", "freelunch-magadascar", "LAPKT-BFWS-Preference","yahsp"]
PLANNER_NAMES = ["lama-first", "cerberus",]
# TODO remove all hardcoded absolute paths.
SAS_DIR = "/home/msalerno/dev/docto/action-elimination/experiments/action-elimination/plans/translator"
SUITE = [name for name in os.listdir(BENCHMARKS_DIR)
            if os.path.isdir(os.path.join(BENCHMARKS_DIR, name))]
# TODO single domain for a local test. Remember to change to all the domains
SUITE = ["tetris"]
# If REVISION_CACHE is None, the default ./data/revision-cache is used.
REVISION_CACHE = "./data/revision-cache"
ENV = project.LocalEnvironment(processes=1)

MR_ENHANCED_CONFIG = ["--action-elimination-options", "--reduction", "MR", "--subsequence", "--enhanced"]
CONFIGS = {
    "minimal-reduction-enhanced-astar-blind":
    MR_ENHANCED_CONFIG + ["--action-elimination-planner-config", "--search", "astar(blind)"],
    "minimal-reduction-enhanced-astar-hmax":
    MR_ENHANCED_CONFIG + ["--action-elimination-planner-config", "--search", "astar(hmax)"],
    # TODO add all discussed configs
}
BUILD_OPTIONS = []

DRIVER_OPTIONS = [
    "--eliminate-actions",
    "--overall-time-limit",
    "30m",
    "--overall-memory-limit",
    "8192M",
]
# Pairs of revision identifier and revision nick.
REVS = [
    ("HEAD", "current"),
]
ATTRIBUTES = [
    "error",
    "old_cost",
    "new_cost",
    "search_start_time",
    "search_start_memory",
    "total_time",
    project.EVALUATIONS_PER_TIME,
]

exp = Experiment(environment=ENV)
for rev, rev_nick in REVS:
    cached_rev = CachedFastDownwardRevision(REPO, rev, BUILD_OPTIONS)
    cached_rev.cache(REVISION_CACHE)
    cache_path = os.path.join(REVISION_CACHE, cached_rev.name)
    dest_path = "code-" + cached_rev.name
    exp.add_resource("", cache_path, dest_path)
    # Overwrite the script to set an environment variable.
    exp.add_resource(
        _get_solver_resource_name(cached_rev),
        os.path.join(cache_path, "fast-downward.py"),
        os.path.join(dest_path, "fast-downward.py"),
    )

    for config_nick, config in CONFIGS.items():
        algo_name = f"{rev_nick}-{config_nick}"
        for planner_name in PLANNER_NAMES:
            count = 1
            for task in suites.build_suite(BENCHMARKS_DIR, SUITE):
                plan_file = "{0}/{1}/{2}/{2}{3}{4}.solution".format(PLANS_DIR, planner_name, task.domain, "0" if count < 10 else "", count)
                sas_file = "{0}/{1}/{1}{2}{3}.solution".format(SAS_DIR, task.domain, "0" if count < 10 else "", count)
                if os.path.exists(plan_file) and os.path.exists(sas_file):
                    algo = _DownwardAlgorithm(
                        algo_name,
                        cached_rev,
                        DRIVER_OPTIONS,
                        config,
                    )
                    run = FastDownwardRun(exp, algo, task)
                    # One domain and problem can be used for multiple experiments
                    # Since there are (potentiallty) different plans
                    # Update problem name so reports don't break
                    run.properties['id'][-1] = run.task.problem + "-%s" % planner_name
                    run.properties['problem'] = run.task.problem + "-%s" % planner_name
                    run.add_resource("sas_task", sas_file, "output.sas")
                    run.add_resource("plan", plan_file, "sas_plan.1")
                    exp.add_run(run)
                count += 1

exp.add_parser(project.FastDownwardExperiment.EXITCODE_PARSER)
exp.add_parser(project.DIR / "ae_parser.py")
exp.add_parser(project.FastDownwardExperiment.TRANSLATOR_PARSER)
exp.add_parser(project.FastDownwardExperiment.ANYTIME_SEARCH_PARSER )
exp.add_parser(project.DIR / "parser.py")
exp.add_parser(project.FastDownwardExperiment.PLANNER_PARSER)

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_fetcher(name="fetch")

project.add_absolute_report(
    exp, attributes=ATTRIBUTES, filter=[project.add_evaluations_per_time]
)

exp.run_steps()

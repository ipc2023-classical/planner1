#! /usr/bin/env python

import os
import shutil

import project


SCP_LOGIN = "nsc"
REMOTE_REPOS_DIR = "/proj/dfsplan/users/x_jense/"
REPO = project.get_repo_base()
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
SUITE = project.SUITE_SATISFICING
if project.TetralithEnvironment.is_present():
    #BENCHMARKS_DIR = os.environ["AUTOSCALE_BENCHMARKS_SAT"]
    #SUITE = project.SUITE_AUTOSCALE_SAT
    ENV = project.TetralithEnvironment(email="jendrik.seipp@liu.se", extra_options="#SBATCH --account=snic2022-5-341")
else:
    SUITE = ["depot:p01.pddl", "gripper:prob01.pddl", "miconic:s1-0.pddl"]
    ENV = project.LocalEnvironment(processes=2)

def _get_lama(**kwargs):
    return [
        "--if-unit-cost",
        "--evaluator",
        "hlm=lmcount(lm_reasonable_orders_hps(lm_rhw()),pref={pref})".format(**kwargs),
        "--evaluator", "hff=ff()",
        "--search", """iterated([
                         lazy_greedy([hff,hlm],preferred=[hff,hlm]),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=5),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=3),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=2),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=1)
                         ],repeat_last=true,continue_on_fail=true)""",
        "--if-non-unit-cost",
        "--evaluator",
        "hlm1=lmcount(lm_reasonable_orders_hps(lm_rhw()),transform=adapt_costs(one),pref={pref})".format(**kwargs),
        "--evaluator", "hff1=ff(transform=adapt_costs(one))",
        "--evaluator",
        "hlm2=lmcount(lm_reasonable_orders_hps(lm_rhw()),transform=adapt_costs(plusone),pref={pref})".format(**kwargs),
        "--evaluator", "hff2=ff(transform=adapt_costs(plusone))",
        "--search", """iterated([
                         lazy_greedy([hff1,hlm1],preferred=[hff1,hlm1],
                                     cost_type=one,reopen_closed=false),
                         lazy_greedy([hff2,hlm2],preferred=[hff2,hlm2],
                                     reopen_closed=false),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=5),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=3),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=2),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=1)
                         ],repeat_last=true,continue_on_fail=true)""",
        # Append --always to be on the safe side if we want to append
        # additional options later.
        "--always"]

def _get_action_elimination_lama(**kwargs):
    return [
        "--if-unit-cost",
        "--evaluator",
        "hlm=lmcount(lm_reasonable_orders_hps(lm_rhw()),pref={pref})".format(**kwargs),
        "--evaluator", "hff=ff()",
        "--search", """iterated([
                         lazy_greedy([hff,hlm],preferred=[hff,hlm]),
                         lazy_greedy([hff,hlm],preferred=[hff,hlm], only_use_operators_from_incumbent_plan=true),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=5),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=5, only_use_operators_from_incumbent_plan=true),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=3),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=3, only_use_operators_from_incumbent_plan=true),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=2),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=2, only_use_operators_from_incumbent_plan=true),
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=1)
                         lazy_wastar([hff,hlm],preferred=[hff,hlm],w=1, only_use_operators_from_incumbent_plan=true)
                         ],repeat_last=true,continue_on_fail=true)""",
        "--if-non-unit-cost",
        "--evaluator",
        "hlm1=lmcount(lm_reasonable_orders_hps(lm_rhw()),transform=adapt_costs(one),pref={pref})".format(**kwargs),
        "--evaluator", "hff1=ff(transform=adapt_costs(one))",
        "--evaluator",
        "hlm2=lmcount(lm_reasonable_orders_hps(lm_rhw()),transform=adapt_costs(plusone),pref={pref})".format(**kwargs),
        "--evaluator", "hff2=ff(transform=adapt_costs(plusone))",
        "--search", """iterated([
                         lazy_greedy([hff1,hlm1],preferred=[hff1,hlm1],cost_type=one,reopen_closed=false),
                         lazy_greedy([hff1,hlm1],preferred=[hff1,hlm1],cost_type=one,reopen_closed=false, only_use_operators_from_incumbent_plan=true),
                         lazy_greedy([hff2,hlm2],preferred=[hff2,hlm2],reopen_closed=false),
                         lazy_greedy([hff2,hlm2],preferred=[hff2,hlm2],reopen_closed=false, only_use_operators_from_incumbent_plan=true),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=5),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=5, only_use_operators_from_incumbent_plan=true),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=3),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=3, only_use_operators_from_incumbent_plan=true),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=2),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=2, only_use_operators_from_incumbent_plan=true),
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=1)
                         lazy_wastar([hff2,hlm2],preferred=[hff2,hlm2],w=1, only_use_operators_from_incumbent_plan=true)
                         ],repeat_last=true,continue_on_fail=true)""",
        # Append --always to be on the safe side if we want to append
        # additional options later.
        "--always"]

LAMA = _get_lama(pref="false")
LAMA_AE = _get_action_elimination_lama(pref="false")

CONFIGS = [
    ("lama", LAMA),
    ("lama-ae", LAMA_AE),
]

BUILD_OPTIONS = []
DRIVER_OPTIONS = ["--overall-time-limit", "5m"]
REVS = [
    ("619f5913a", ""),
]
ATTRIBUTES = [
    "cost",
    "error",
    "plan_length",
    "run_dir",
    "coverage",
    #"planner_memory",
    "planner_time",
]

exp = project.FastDownwardExperiment(environment=ENV)
for config_nick, config in CONFIGS:
    for rev, rev_nick in REVS:
        algo_name = f"{rev_nick}:{config_nick}" if rev_nick else config_nick
        exp.add_algorithm(
            algo_name,
            REPO,
            rev,
            config,
            build_options=BUILD_OPTIONS,
            driver_options=DRIVER_OPTIONS,
        )
exp.add_suite(BENCHMARKS_DIR, SUITE)

exp.add_parser(exp.EXITCODE_PARSER)
exp.add_parser(exp.TRANSLATOR_PARSER)
exp.add_parser(exp.ANYTIME_SEARCH_PARSER)
exp.add_parser(project.DIR / "parser.py")
exp.add_parser(exp.PLANNER_PARSER)

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_fetcher(name="fetch")

if not project.TetralithEnvironment.is_present():
     exp.add_step(
         "remove-eval-dir", shutil.rmtree, exp.eval_dir, ignore_errors=True
     )
     project.add_scp_step(exp, SCP_LOGIN, REMOTE_REPOS_DIR)

project.add_absolute_report(
    exp, attributes=ATTRIBUTES, filter=[project.add_evaluations_per_time]
)

attributes = ["cost"]
pairs = [
    ("lama", "lama-ae"),
]
suffix = "-rel" if project.RELATIVE else ""
for algo1, algo2 in pairs:
    for attr in attributes:
        exp.add_report(
            project.ScatterPlotReport(
                relative=project.RELATIVE,
                get_category=None if project.TEX else lambda run1, run2: run1["domain"],
                attributes=[attr],
                filter_algorithm=[algo1, algo2],
                filter=[project.add_evaluations_per_time],
                format="tex" if project.TEX else "png",
            ),
            name=f"{exp.name}-{algo1}-vs-{algo2}-{attr}{suffix}",
        )

exp.run_steps()

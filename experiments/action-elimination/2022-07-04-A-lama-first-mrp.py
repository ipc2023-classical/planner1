#! /usr/bin/env python

import os
import shutil

import project


SCP_LOGIN = "nsc"
REMOTE_REPOS_DIR = "/proj/dfsplan/users/x_jense/"
REPO = project.get_repo_base()
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
SUITE = project.SUITE_SATISFICING_STRIPS
if project.TetralithEnvironment.is_present():
    #BENCHMARKS_DIR = os.environ["AUTOSCALE_BENCHMARKS_SAT"]
    #SUITE = project.SUITE_AUTOSCALE_SAT
    ENV = project.TetralithEnvironment(email="jendrik.seipp@liu.se", extra_options="#SBATCH --account=snic2022-5-341")
else:
    SUITE = ["depot:p01.pddl", "gripper:prob01.pddl", "miconic:s1-0.pddl"]
    ENV = project.LocalEnvironment(processes=2)

LAMA_FIRST = [
    "--evaluator",
    "hlm=lmcount(lm_factory=lm_reasonable_orders_hps(lm_rhw()),transform=adapt_costs(one),pref=false)",
    "--evaluator", "hff=ff(transform=adapt_costs(one))",
    "--search", "lazy_greedy([hff,hlm],preferred=[hff,hlm],cost_type=one,reopen_closed=false)"]

def _get_action_elimination_lama_first(**kwargs):
    return [
        "--evaluator",
        "hlm=lmcount(lm_reasonable_orders_hps(lm_rhw()),transform=adapt_costs(one),pref={pref})".format(**kwargs),
        "--evaluator", "hff=ff(transform=adapt_costs(one))",
        "--evaluator", "h={heuristic}".format(**kwargs),
        "--search", """iterated([
                         lazy_greedy([hff,hlm],preferred=[hff,hlm],cost_type=one,reopen_closed=false),
                         astar(h, only_use_operators_from_incumbent_plan=true),
                         ],repeat_last=false, continue_on_fail=false)""",
    ]

CONFIGS = [
    ("lama-first", LAMA_FIRST),
    ("lama-first-mrp-hmax", _get_action_elimination_lama_first(pref=False, heuristic="hmax()")),
    ("lama-first-mrp-lmcut", _get_action_elimination_lama_first(pref=False, heuristic="lmcut()")),
    ("lama-first-mrp-scorpion", _get_action_elimination_lama_first(pref=False, heuristic="""scp_online([
        projections(sys_scp(max_time=5, max_time_per_restart=1)),
        cartesian(max_time=5)],
        saturator=perimstar, max_time=5, interval=10K)""")),
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
    "planner_memory",
    "planner_time",
    "config_times",
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

#! /usr/bin/env python

import os
from lab.experiment import ARGPARSER
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

# Should be experiments/action/elimination
current_dir = os.path.dirname(os.path.realpath(__file__))

# Define all paths
BENCHMARKS_2014_DIR = os.path.join(current_dir ,"domains/ipc2014/seq-agl")
BENCHMARKS_2018_DIR = os.path.join(current_dir ,"domains/ipc2018/sat")
PLANS_DIR = os.path.join(current_dir,"plans")
SAS_DIR = os.path.join(current_dir, "plans/translator")
PLANNER_NAMES = ["lama-first", "cerberus", "freelunch-madagascar", "LAPKT-BFWS-Preference","yahsp"]

# Define problems to be solved
SUITE_IPC2014 = sorted([name for name in os.listdir(BENCHMARKS_2014_DIR)
            if os.path.isdir(os.path.join(BENCHMARKS_2014_DIR, name))])
SUITE_IPC2018 = sorted([name for name in os.listdir(BENCHMARKS_2018_DIR)
            if os.path.isdir(os.path.join(BENCHMARKS_2018_DIR, name))])

# TODO single domain for a local test. Remember to change to all the domains
# SUITE_IPC2014 = ["parking"]

# If REVISION_CACHE is None, the default ./data/revision-cache is used.
REVISION_CACHE = "./data/revision-cache"
ENV = project.LocalEnvironment(processes=1)

HEURISTICS_MAP = {
    # "astar-blind":
    # ["--action-elimination-planner-config", "--search", "astar(blind())"],
    "astar-hmax":
    ["--action-elimination-planner-config", "--search", "astar(hmax())"],
    # "astar-lmcut":
    # ["--action-elimination-planner-config", "--search", "astar(lmcut())"],
    # "astar-lmc-lazy-eval-lmc":
    # ["--action-elimination-planner-config", "--evaluator", "lmc=lmcount(lm_merged([lm_rhw(), lm_hm(m=1)]), admissible=true, cost_partitioning=suboptimal, reuse_costs=true, greedy=true)", "--search", "astar(lmc, lazy_evaluator=lmc)"],
    # "astar-bjolp":
    # ["--action-elimination-planner-config", "--evaluator", "lmc=lmcount(lm_merged([lm_rhw(),lm_hm(m=1)]),admissible=true)", "--search", "astar(lmc,lazy_evaluator=lmc)"],
    # "sys-scp-cartesian":
    # ["--action-elimination-planner-config", "--search", "astar(scp_online([projections(sys_scp(max_time=1, max_time_per_restart=0.2)), cartesian([goals()], max_time=1)], saturator=perimstar, max_time=1, interval=10K))"],
    # "sys-scp":
    # ["--action-elimination-planner-config", "--seasrch", "astar(scp_online([projections(sys_scp(max_time=1, max_time_per_restart=0.2))], saturator=perimstar, max_time=1, interval=10K))"],
    # "cartesian":
    # ["--action-elimination-planner-config", "--search", "astar(scp_online([cartesian([goals()], max_time=1)], saturator=perimstar, max_time=1, interval=10K))"],
    # "sys2":
    # ["--action-elimination-planner-config", "--search", "astar(scp_online([projections(systematic(2))], saturator=perimstar, max_time=1, interval=10K))"],
    # "sys3exp":
    # ["--action-elimination-planner-config", "--search", "astar(scp_online([projections(systematic(3))], saturator=perimstar, max_time=1, interval=10K))"]
}

MR_ENHANCED_CONFIG = ["--action-elimination-options", "--reduction", "MR", "--subsequence", "--enhanced", "--macro-operators", "--enhanced-fix-point", "--add-pos-to-goal"]
MR_CONFIG = ["--action-elimination-options", "--reduction", "MR", "--subsequence"]

enhanced_configs = {
    "minimal-reduction-enhanced-" + h_name : MR_ENHANCED_CONFIG + h_config for (h_name, h_config) in HEURISTICS_MAP.items()
}
non_enhanced_confings = {
    "minimal-reduction-" + h_name : MR_CONFIG + h_config for (h_name, h_config) in HEURISTICS_MAP.items() if h_name != "astar-blind"
}

CONFIGS = {**enhanced_configs, **non_enhanced_confings}

BUILD_OPTIONS = []

DRIVER_OPTIONS = [
    "--eliminate-actions",
    "--overall-time-limit",
    "30m",
    "--overall-memory-limit",
    "8G",
]
# Pairs of revision identifier and revision nick.
REVS = [
    ("HEAD", "current"),
]
ATTRIBUTES = [
    "error",
    "planner_time",
    "ae_planner_call_time",
    "parse_input_sas_and_plan",
    "ae_total_time",
    "old_cost",
    "new_cost",
    "create_ae_task_time",
    "search_start_time",
    "search_start_memory",
    "search_time",
    "total_time",
    project.EVALUATIONS_PER_TIME,
]

args = ARGPARSER.parse_args()
config_domain = []

if args.process_number != -1:
    # Cluster execution, distribute load following process number
    # Each process will run one config for every instances in one domain of the suites
    # if args.process_number > suite_1_processes:
    config_number = args.process_number // (len(SUITE_IPC2014) + len(SUITE_IPC2018))
    domain_number = args.process_number % (len(SUITE_IPC2014) + len(SUITE_IPC2018))
    # Int div. gets the config while mod gets domain number
    if domain_number >= len(SUITE_IPC2014):
        domain_number = domain_number - len(SUITE_IPC2014)
        SUITE_IPC2014 = []
        SUITE_IPC2018 = [SUITE_IPC2018[domain_number]]
        current_config = sorted(list(CONFIGS.keys()))[config_number]
        CONFIGS = {current_config : CONFIGS[current_config]}
    else:
        SUITE_IPC2018 = []
        SUITE_IPC2014 = [SUITE_IPC2014[domain_number]]
        current_config = sorted(list(CONFIGS.keys()))[config_number]
        CONFIGS = {current_config : CONFIGS[current_config]}

SUITE_IPC2014 = ["visitall"]
SUITE_IPC2018 = []
print("The domains are: ", SUITE_IPC2014, SUITE_IPC2018)
print("The configs are: ", CONFIGS)

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
        algo_name = f"{config_nick}"
        for planner_name in PLANNER_NAMES:
            # Add all experiments for agile ipc2014
            for domain in SUITE_IPC2014:
                count = 1
                # Have to do one domain at a time to keep track of plan number
                for task in suites.build_suite(BENCHMARKS_2014_DIR, [domain]):
                    plan_file = f"{PLANS_DIR}/{planner_name}/{task.domain}/{task.domain}{count:02d}.solution"
                    sas_file = f"{SAS_DIR}/{task.domain}/{task.domain}{count:02d}.solution"
                    if os.path.exists(plan_file) and os.path.exists(sas_file):
                        planning_time_file = f"{PLANS_DIR}/{planner_name}/{task.domain}/{task.domain}{count:02d}.solution.timemilliseconds"
                        with open(planning_time_file, 'r') as time_file:
                            time_micros = int(time_file.readline())

                        if time_micros <= 300000000:
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
                    # Only one instance per domain for testing!
                    # break

            # Add all experiments for agile ipc2018
            for domain in SUITE_IPC2018:
                count = 1
                # Have to do one domain at a time to keep track of plan number
                for task in suites.build_suite(BENCHMARKS_2018_DIR, [domain]):
                    plan_file = f"{PLANS_DIR}/{planner_name}/{task.domain}/{task.domain}{count:02d}.solution"
                    sas_file = f"{SAS_DIR}/{task.domain}/{task.domain}{count:02d}.solution"
                    if os.path.exists(plan_file) and os.path.exists(sas_file):
                        planning_time_file = f"{PLANS_DIR}/{planner_name}/{task.domain}/{task.domain}{count:02d}.solution.timemilliseconds"
                        with open(planning_time_file, 'r') as time_file:
                            time_micros = int(time_file.readline())

                        if time_micros <= 300000000:
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

                    # Only one instance per domain for testing!
                    # break

exp.add_parser(project.FastDownwardExperiment.EXITCODE_PARSER)
exp.add_parser(project.DIR / "ae_parser.py")
exp.add_parser(project.FastDownwardExperiment.TRANSLATOR_PARSER)
exp.add_parser(project.FastDownwardExperiment.SINGLE_SEARCH_PARSER)
exp.add_parser(project.DIR / "parser.py")
exp.add_parser(project.FastDownwardExperiment.PLANNER_PARSER)

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)

exp.add_fetcher(name="fetch")

project.add_absolute_report(
    exp, attributes=ATTRIBUTES, filter=[project.add_evaluations_per_time]
)

exp.run_steps()

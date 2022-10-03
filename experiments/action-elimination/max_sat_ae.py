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

# Remember to Define all paths!!
BENCHMARKS_2014_DIR = "action-elimination/experiments/action-elimination/domains/ipc2014/seq-agl"
BENCHMARKS_2018_DIR = "action-elimination/experiments/action-elimination/domains/ipc2018/sat"
PLANS_DIR = "action-elimination/experiments/action-elimination/plans"
SAS_DIR = "action-elimination/experiments/action-elimination/plans/translator"
PLANNER_NAMES = ["lama-first", "cerberus", "freelunch-madagascar", "LAPKT-BFWS-Preference","yahsp"]
# Make sure that set this variable!
FREE_LUNCH_PATH = "freelunch"

# Java stuff...
JAVA_ARGUMENTS = [
    "java",
    "-Xmn8192m",
    "-jar",
    "aaai23.jar",
    "wpmax"
]

# Define problems to be solved
SUITE_IPC2014 = sorted([name for name in os.listdir(BENCHMARKS_2014_DIR)
            if os.path.isdir(os.path.join(BENCHMARKS_2014_DIR, name))])
SUITE_IPC2018 = sorted([name for name in os.listdir(BENCHMARKS_2018_DIR)
            if os.path.isdir(os.path.join(BENCHMARKS_2018_DIR, name))])

ENV = project.LocalEnvironment(processes=1)
TIME_LIMIT = 1800
MEMORY_LIMIT = 8192

ATTRIBUTES = [
    "error",
    "ae_planner_call_time",
    "ae_total_time",
    "parse_input_sas_and_plan",
    "old_cost",
    "new_cost",
    "create_ae_task_time",
    "search_time",
    project.EVALUATIONS_PER_TIME,
]

args = ARGPARSER.parse_args()
config_domain = []

if args.process_number != -1:
    # Cluster execution, distribute load following process number
    # Each process will run one config for every instances in one domain of the suites
    # if args.process_number > suite_1_processes:
    domain_number = args.process_number % (len(SUITE_IPC2014) + len(SUITE_IPC2018))

    # Int div. gets the config while mod gets domain number
    if domain_number >= len(SUITE_IPC2014):
        domain_number = domain_number - len(SUITE_IPC2014)
        SUITE_IPC2014 = []
        SUITE_IPC2018 = [SUITE_IPC2018[domain_number]]
    else:
        SUITE_IPC2018 = []
        SUITE_IPC2014 = [SUITE_IPC2014[domain_number]]

exp = Experiment(environment=ENV)
# # Add solver
# exp.add_resource(
#     "solver",
#     os.path.join(FREE_LUNCH_PATH, "aaai23.jar")
# )
print(SUITE_IPC2014, SUITE_IPC2018)
for planner_name in PLANNER_NAMES:
    # Add all experiments for agile ipc2014
    for domain in SUITE_IPC2014:
        count = 1
        # Have to do one domain at a time to keep track of plan number
        for task in suites.build_suite(BENCHMARKS_2014_DIR, [domain]):
            plan_file = f"{PLANS_DIR}/{planner_name}/{task.domain}/{task.domain}{count:02d}.solution"
            sas_file = f"{SAS_DIR}/{task.domain}/{task.domain}{count:02d}.solution"
            cnf_file = "max_sat.cnf"
            if os.path.exists(plan_file) and os.path.exists(sas_file):
                planning_time_file = f"{PLANS_DIR}/{planner_name}/{task.domain}/{task.domain}{count:02d}.solution.timemilliseconds"
                with open(planning_time_file, 'r') as time_file:
                    time_micros = int(time_file.readline())

                if time_micros <= 300000000:
                    run = exp.add_run()
                    run.add_command(
                        "solve",
                        JAVA_ARGUMENTS + ["output.sas", "sas_plan.1", cnf_file],
                        time_limit=TIME_LIMIT,
                        memory_limit=MEMORY_LIMIT,
                        hard_stdout_limit=None,
                        soft_stdout_limit=None,
                    )
                    # One domain and problem can be used for multiple experiments
                    # Since there are (potentiallty) different plans
                    # Update problem name so reports don't break
                    run.set_property("time_limit", TIME_LIMIT)
                    run.set_property("memory_limit", MEMORY_LIMIT)
                    run.set_property("domain", task.domain)
                    run.set_property("problem", task.problem)
                    run.set_property("algorithm", "weighted-max-sat")
                    problem = os.path.basename(os.path.dirname(task.problem))
                    run.set_property("id", ["weighted-max-sat", domain, task.problem + "-" + planner_name])
                    run.properties['id'][-1] = task.problem + "-%s" % planner_name
                    run.properties['problem'] = task.problem + "-%s" % planner_name
                    run.add_resource("sas_task", sas_file, "output.sas")
                    run.add_resource("plan", plan_file, "sas_plan.1")
                    run.add_resource(
                        "solver",
                        os.path.join(FREE_LUNCH_PATH, "aaai23.jar")
                    )
            count += 1
            # Only one instance per domain for testing!
            # break
        # break
    # break

    # Add all experiments for agile ipc2018
    for domain in SUITE_IPC2018:
        count = 1
        # Have to do one domain at a time to keep track of plan number
        for task in suites.build_suite(BENCHMARKS_2018_DIR, [domain]):
            plan_file = f"{PLANS_DIR}/{planner_name}/{task.domain}/{task.domain}{count:02d}.solution"
            sas_file = f"{SAS_DIR}/{task.domain}/{task.domain}{count:02d}.solution"
            cnf_file = "max_sat.cnf"
            if os.path.exists(plan_file) and os.path.exists(sas_file):
                planning_time_file = f"{PLANS_DIR}/{planner_name}/{task.domain}/{task.domain}{count:02d}.solution.timemilliseconds"
                with open(planning_time_file, 'r') as time_file:
                    time_micros = int(time_file.readline())

                if time_micros <= 300000000:
                    run = exp.add_run()
                    run.add_command(
                        "solve",
                        JAVA_ARGUMENTS + ["output.sas", "sas_plan.1", cnf_file],
                        time_limit=TIME_LIMIT,
                        memory_limit=MEMORY_LIMIT,
                        hard_stdout_limit=None,
                        soft_stdout_limit=None,
                    )
                    # One domain and problem can be used for multiple experiments
                    # Since there are (potentiallty) different plans
                    # Update problem name so reports don't break
                    run.set_property("time_limit", TIME_LIMIT)
                    run.set_property("memory_limit", MEMORY_LIMIT)
                    run.set_property("domain", task.domain)
                    run.set_property("problem", task.problem)
                    run.set_property("algorithm", "weighted-max-sat")
                    problem = os.path.basename(os.path.dirname(task.problem))
                    run.set_property("id", ["weighted-max-sat", domain, task.problem + "-" + planner_name])
                    run.properties['id'][-1] = task.problem + "-%s" % planner_name
                    run.properties['problem'] = task.problem + "-%s" % planner_name
                    run.add_resource("sas_task", sas_file, "output.sas")
                    run.add_resource("plan", plan_file, "sas_plan.1")
                    run.add_resource(
                        "solver",
                        os.path.join(FREE_LUNCH_PATH, "aaai23.jar")
                    )
            count += 1

            # Only one instance per domain for testing!
            # break

exp.add_parser(project.DIR / "sat_ae_parser.py")
exp.add_parser(project.DIR / "parser.py")
exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_fetcher(name="fetch")

project.add_absolute_report(
    exp, attributes=ATTRIBUTES, filter=[project.add_evaluations_per_time]
)

exp.run_steps()
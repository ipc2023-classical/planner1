#! /usr/bin/env python3

#######################################################################
#
# Author: Raquel Fuentetaja, Mauricio Salerno
# Copyright 2021
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
#######################################################################

from ast import parse
import os
import sys
import re
import options

def python_version_supported():
    return sys.version_info >= (3, 6)

if not python_version_supported():
    sys.exit("Error: Ria only supports Python >= 3.6.")

import sys
import pddl
import pddl_parser
import plan_parser
import timers
import time
from sas_tasks import SASOperator
import sas_parser

DEBUG = False
MINIMAL_LENGTH = False
MINIMAL_COST = True
DOWNWARD_HOME = "../../"
# HEURISTIC = "hmax"
BLIND_HEURISTIC = "blind()"
HMAX_HEURISTIC  = "hmax()"
LMCUT_HEURISTIC = "lmcut(transform=no_transform(), cache_estimates=true)"
CEGAR_HEURISTIC = "cegar(subtasks=[landmarks(),goals()], max_states=infinity, max_transitions=1M, max_time=infinity, pick=MAX_REFINED, use_general_costs=true, debug=false, transform=no_transform(), cache_estimates=true, random_seed=-1)"
HM_HEURISTIC    = "hm(m=1, transform=no_transform(), cache_estimates=true)"
HEURISTICS_MAP = {
    "blind": BLIND_HEURISTIC,
    "hmax": HMAX_HEURISTIC,
}

# With a task and a plan, finds trivially necessary actions in the plan. (related to landmarks)
# When solving MR and MLR (action ordHEURISTIC that achieves a precondition for another triv. nec. action
# NOTE: changed around to find "skippable" actions.
def find_triv_nec_actions(init, goal, variables, plan):
    # Find achievers for each fact
    fact_achievers = [[[] for _ in range(dom_size)] for dom_size in variables.ranges]

    # Facts achieved by the initial state
    for var, val in enumerate(init.values):
        fact_achievers[var][val].append(-1)

    # For each operator what facts they achieve
    for index, op in enumerate(plan):
        for var, _, new_val, _  in op.pre_post:
            fact_achievers[var][new_val].append(index)

    # Add virtual goal action. prevail is goal conditions, used for ease of implementation
    virtual_goal_action = SASOperator(name='virtual_goal', prevail=[(var, val) for var, val in goal.pairs], pre_post=[], cost=0)
    # Copy the operators
    extended_plan = plan[:]
    extended_plan.append(virtual_goal_action)
    triv_nec = [True for _ in extended_plan]
    triv_nec[-1] = False

    # Check, in reverse order, for trivially nec actions
    for op_index in range(len(extended_plan) - 1, -1, -1):
        # If current act is triv. nec, its' preconds are nec.domain
        if not triv_nec[op_index]:
            current_op = extended_plan[op_index]
            for var, val in current_op.prevail:
                # If one pre has only one achiever that is not the initial state, that achiever is nec!
                if sum(1 for achiever in fact_achievers[var][val] if achiever < op_index) < 2:
                    if fact_achievers[var][val][0] > -1:
                        triv_nec[fact_achievers[var][val][0]] = False

            for var, val, _, _ in current_op.pre_post:
                # If one pre has only one achiever that is not the initial state, that achiever is nec!
                if val > -1 and sum(1 for achiever in fact_achievers[var][val] if achiever < op_index) < 2:
                    if fact_achievers[var][val][0] > -1:
                       triv_nec[fact_achievers[var][val][0]] = False

    # TODO This can be done iteratively to identify more nec. actions
    # Once you identify a triv. nec action you can delete achievers from the list.
    # If one action with index i is nec, and changes the value of a variable, all achievers
    # of a value for that variable are no longer achievers for indices > i
    # What's the worst case complexity? Is it worth it?
    return triv_nec

def main():
    # Parse args: messy
    # Order of arguments: pddl domain, pddl problem, plan, sas+ task, use skippable actions
    print(options.domain, options.task, options.plan, options.sas_task, options.enhanced, options.heuristic)
    sas_task, sas_task_map = sas_parser.parse_task(options.sas_task)
    parse_pddl_time = time.time()
    SKIPPABLE_PREDICATES = options.enhanced == "True"
    task = pddl_parser.open(domain_filename=options.domain, task_filename=options.task)
    plan_length, plan, plan_cost = plan_parser.plan_file.parse_plan(options.plan)
    parse_pddl_time = time.time() - parse_pddl_time
    print(f"Parse input SAS task and plan time: {parse_pddl_time:.3f}")
    print(f"Old plan cost: {plan_cost}")

    skippable_actions = find_triv_nec_actions(sas_task.init, sas_task.goal, sas_task.variables, [sas_task.operators[sas_task_map[f"({op.action})"]] for op in plan])

    create_ae_task_time = time.time()
    with timers.timing("Generating follow-plan domain", True):
        # task new types and predicates
        generate_domain_time = time.time()
        task.add_type(pddl.Type("order", "object"))
        task.add_predicate(pddl.Predicate("last", [pddl.TypedObject("?o", "order")] ))
        task.add_predicate(pddl.Predicate("before", [pddl.TypedObject("?o1", "order"), pddl.TypedObject("?o2", "order") ]))
        task.add_predicate(pddl.Predicate("next-action", [pddl.TypedObject("?o1", "order"), pddl.TypedObject("?o2", "order") ]))
        if SKIPPABLE_PREDICATES:
            task.add_predicate(pddl.Predicate("skippable", [pddl.TypedObject("?o1", "order")]))
        for index, action in enumerate(task.actions):
            task.add_predicate(pddl.Predicate("plan-action-" + action.name, [pddl.TypedObject("?o", "order")] + action.parameters))
            new_prec = pddl.conditions.Atom("plan-action-" + action.name, ["?ocurrent"] + action.param_names())
            action.add_precondition(new_prec)

            new_prec = pddl.conditions.Atom("next-action", ["?olast", "?ocurrent"])
            action.add_precondition(new_prec)
            new_prec = pddl.conditions.Atom("last", ["?olast"])
            action.add_precondition(new_prec)

            new_poseff = pddl.conditions.Atom("last", ["?ocurrent"])
            new_negeff = pddl.conditions.NegatedAtom("last", ["?olast"])
            action.add_effect(pddl.effects.Effect(["?ocurrent"], pddl.conditions.Truth(), new_poseff))
            action.add_effect(pddl.effects.Effect(["?olast"], pddl.conditions.Truth(), new_negeff))

            action.add_parameter(pddl.TypedObject("?olast", "order"))
            action.add_parameter(pddl.TypedObject("?ocurrent", "order"))
        generate_domain_time = time.time() - generate_domain_time

    with timers.timing("Generating follow-plan problem", True):
        generate_problem_time = time.time()
        # task new objects
        new_order_objects = []
        new_order_objects.append(task.add_object(pddl.TypedObject("action-number0", "order")))
        for i in range(plan_length):
            new_order_objects.append(task.add_object(pddl.TypedObject("action-number" + str(i+1), "order")))

        # task modified initial state
        for index, elem in enumerate(new_order_objects[:-1]):
            next_elem = new_order_objects[index + 1]
            task.add_init_atom(pddl.conditions.Atom("next-action", [elem.name, next_elem.name]))
            if SKIPPABLE_PREDICATES:
                # try:
                if (skippable_actions[index]):
                    task.add_init_atom(pddl.conditions.Atom("skippable", [elem.name]))
                # except:
                #     print("Current inidex " + str(index) + " size of list... " + str(len(skippable_actions)))
        task.add_init_atom(pddl.conditions.Atom("next-action", [new_order_objects[-1].name, new_order_objects[-1].name]))
        if SKIPPABLE_PREDICATES and (skippable_actions[-1]):
            task.add_init_atom(pddl.conditions.Atom("skippable", [new_order_objects[-1].name]))

        task.add_init_atom(pddl.conditions.Atom("last", ["action-number0"]))

        for action in plan:
            task.add_init_atom(pddl.conditions.Atom("plan-action-" + action.op, ["action-number"+ str(action.step)] + action.args))

        # Action to skip an action
        parameter_list = list()
        condition_list = list()
        effects_list = list()
        last_obj = pddl.TypedObject("?olast", "order")
        current_obj = pddl.TypedObject("?ocurrent", "order")
        parameter_list = [last_obj, current_obj]
        condition_list.append(pddl.conditions.Atom("next-action", ["?olast", "?ocurrent"]))
        condition_list.append(pddl.conditions.Atom("last", ["?olast"]))
        if SKIPPABLE_PREDICATES:
            condition_list.append(pddl.conditions.Atom("skippable", ["?olast"]))
        new_poseff = pddl.conditions.Atom("last", ["?ocurrent"])
        new_negeff = pddl.conditions.NegatedAtom("last", ["?olast"])
        effects_list.append((pddl.effects.Effect([last_obj], pddl.conditions.Truth(), new_poseff)))
        effects_list.append((pddl.effects.Effect([current_obj], pddl.conditions.Truth(), new_negeff)))

        skip_condition = pddl.conditions.Conjunction(condition_list)

        skip_action = pddl.Action("skip-original-action-plan", parameter_list, len(parameter_list), skip_condition, effects_list, 0)
        task.add_action(skip_action)
        generate_problem_time = time.time() - generate_problem_time
        create_ae_task_time = time.time() - create_ae_task_time

    # Save files
    # new_domain_filename = "%s-%s-domain-follow-plan-comp-2-%s.pddl" % (options.domain, options.task, "min-cost" if MINIMAL_COST else "min-length")
    # new_problem_filename = "%s-%s-problem-follow-plan-comp-2-%s.pddl" % (options.domain, options.task, "min-cost" if MINIMAL_COST else "min-length")
    # new_plan_filename = new_problem_filename + ".pddl"
    new_domain_filename = "domain-follow_plan.pddl"
    new_problem_filename = "problem-follow-plan.pddl"
    new_plan_filename = "sas_plan.2"
    outputDir = ""

    with timers.timing("Writing out problem and domain files", True):
        write_files_time = time.time()
        task.save_domain_pddl(outputDir + new_domain_filename)
        task.save_problem_pddl(outputDir + new_problem_filename)
        write_files_time = time.time() - write_files_time
    print(f"Create AE task time: {create_ae_task_time + write_files_time:.3f}")

    # Calling planner
    planner_output_file = outputDir + new_problem_filename + ".output"
    call_string = "%s./fast-downward.py --overall-time-limit 1800 --overall-memory-limit 8G --plan-file %s %s %s --search \"astar(%s)\"" \
                % (DOWNWARD_HOME, outputDir + new_plan_filename,\
                outputDir + new_domain_filename, outputDir + new_problem_filename, HEURISTICS_MAP[options.heuristic])

    with timers.timing("planner-call-time", True):
        planner_call_time = time.time()
        os.system(call_string)
        planner_call_time = time.time() - planner_call_time

    print(f"AE planner call time: {planner_call_time:.3f}")
    _, new_plan, new_plan_cost = plan_parser.plan_file.parse_plan(new_plan_filename)
    print(f"New plan cost: {new_plan_cost}")

#-----------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
    #main(domain, task, plan)


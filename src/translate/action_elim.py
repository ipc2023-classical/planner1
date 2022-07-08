#! /usr/bin/env python3

#######################################################################
#
# Author: Mauricio Salerno
# Copyright 2022
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
#######################################################################

from numpy import var
from sas_tasks import SASTask, SASVariables, SASOperator, SASInit, SASGoal, SASAxiom, SASMutexGroup
from plan_parser import parse_plan
from sas_parser import parse_task
from simplify import filter_unreachable_propositions
from variable_order import find_and_apply_variable_order
import argparse
import os

MR  = 'MR'
MLR = 'MLR'

# Clean domains as proposed by Jendrik (I think)
def create_action_elim_task(sas_task, plan, operator_name_to_index, ordered=False):
    # Process operators. Later on, variable to maintain order of actions will be var_(n + 1) (n=num vars originally)
    new_operators = get_operators_from_plan(sas_task.operators, plan, operator_name_to_index, ordered=True)

    # Find relevant facts for action elim task
    relevant_facts = find_relevant_facts(sas_task, plan, operator_name_to_index)

    # Prune domains of variables to only contain relevant facts
    new_variables, vars_vals_map = prune_irrelevant_domain_values(sas_task.variables, relevant_facts, plan, ordered)

    # Map operators variable values to new domains
    new_operators = process_operators(new_operators, relevant_facts, vars_vals_map, new_variables, ordered, sas_task.metric)

    # Map init values to new domains
    new_init = process_init(sas_task.init, vars_vals_map, relevant_facts, new_variables, ordered)

    # Map mutexes values new domains
    new_mutexes = process_mutex_groups(sas_task.mutexes, vars_vals_map, relevant_facts)

    # Map goal values to new domains
    new_goal = map_goal_vals(sas_task.goal, vars_vals_map)

    # Map axioms
    new_axioms = process_axioms(sas_task.axioms)

    new_task = SASTask(variables=new_variables, mutexes=new_mutexes, \
                   init=new_init, goal=new_goal, operators=new_operators, axioms=new_axioms, metric=True if ordered else sas_task.metric)
    
    # Remove unreachable facts and useless variables using FD code
    filter_unreachable_propositions(new_task)
    find_and_apply_variable_order(new_task, reorder_vars=True, filter_unimportant_vars=True)

    return new_task

def get_operators_from_plan(operators, plan, operator_name_to_index, ordered=False):
    return [operators[operator_name_to_index[op]] for op in plan]

def find_relevant_facts(sas_task, operators, operator_name_to_index):
    is_fact_relevant = [[False] * domain_size for domain_size in sas_task.variables.ranges] 
    # All facts in goal are needed
    for var, val in sas_task.goal.pairs: 
        is_fact_relevant[var][val] = True

    # All facts in operations preconditions are needed
    for op_name in operators:
        op = sas_task.operators[operator_name_to_index[op_name]]
        for var, val in op.prevail:
            is_fact_relevant[var][val] = True
        
        # TODO: Ask: Should we add a 'default' val to all variable domains?
        # Let one action pre_post be 1 -> 9
        # Is 9 relevant? What if 9 is never in the precond part of the effect of an action?
        # If it's not relevant, what do we do with the value of variable? Map it to a default val might reduce dom size (?)
        for var, old_val, new_val, _ in op.pre_post:
            if old_val > -1:
                is_fact_relevant[var][old_val] = True
            # Uncomment Code to make 9 value relevant
            # is_fact_relevant[var][new_val] = True

    # All values of order variable are relevant!
    is_fact_relevant.append([True] * (len(operators) + 1))

    return is_fact_relevant

def prune_irrelevant_domain_values(variables, is_fact_relevant, plan, ordered):
    # For each var, store value mapping to new domain
    vars_new_vals_map = [[-1] * domain_size for domain_size in variables.ranges]
    new_value_names = list()
    new_axiom_layers = list()
    new_ranges = list()

    # For each relevant fact, add to new domain
    for var, rel_facts in enumerate(is_fact_relevant[:-1]):
        next_val = 0
        current_val_names = list()
        for val, is_rel in enumerate(rel_facts):
            if is_rel:
                vars_new_vals_map[var][val] = next_val
                current_val_names.append(variables.value_names[var][val])
                next_val += 1
        # Code to create default 'Some value not in any precond' value of variable
        current_val_names.append('Atom irrelevant-fact()')
        next_val += 1
        # End code for some value not in any precond
        new_ranges.append(next_val)
        new_axiom_layers.append(variables.axiom_layers[var])
        new_value_names.append(current_val_names)

    # Add variable to maintain action order
    if ordered:
        new_ranges.append(len(plan) + 1)
        new_axiom_layers.append(-1)
        new_value_names.append(['Atom plan-pos-%i()' % i for i in range(len(plan) + 1)])
        vars_new_vals_map.append([i for i in range(len(plan) + 1)])
    
    return SASVariables(ranges=new_ranges, axiom_layers=new_axiom_layers, value_names=new_value_names)\
           , vars_new_vals_map

def process_operators(operators, is_fact_relevant, vars_vals_map, variables, ordered, costs_task):
    processed_operators = list()
    # Variable to maintain order is ALWAYS the last variable
    ordered_var = len(variables.ranges) - 1
    for op_index, op in enumerate(operators):
        # Might not need to check if prevail is relevant -- was set as relevant before
        new_prev = [(var, vars_vals_map[var][val]) for var, val in op.prevail if is_fact_relevant[var][val]]
        new_pre_post = [(var, old_val if old_val == -1 else vars_vals_map[var][old_val], \
                        vars_vals_map[var][new_val] if is_fact_relevant[var][new_val] else variables.ranges[var] - 1, cond) \
                        for var, old_val, new_val, cond in op.pre_post]

        # Readable code. Should do the same as the list comprehension. I-ll leave it here so we can choose
        #readable_new_prev = list()
        #for var, val in op.prevail:
        #    if is_fact_relevant[var][val]:
        #        readable_new_prev.append((var, vars_vals_map[var][val]))
        #
        #readable_pre_post = list()
        #for var, old_val, new_val, cond in op.pre_post:
        #    mapped_old = -1 if old_val == -1 else vars_vals_map[var][old_val]
        #    mapped_new = vars_vals_map[var][new_val] if is_fact_relevant[var][new_val] else variables.ranges[var] - 1
        #    readable_pre_post.append((var, mapped_old, mapped_new, cond))

        # Add ordered constraint pre_post
        if ordered:
            new_pre_post.append((ordered_var, op_index, op_index + 1, []))
            # We are assuming the input domain does not have action 'skip-action'. Should we think of a better name for this action?
            processed_operators.append(SASOperator(name='(skip-action plan-pos-%i)' % op_index, prevail=[], pre_post=[(ordered_var, op_index, op_index + 1, [])], cost=0))

        processed_operators.append(SASOperator(name=op.name, prevail=new_prev, pre_post=new_pre_post, cost=op.cost if not ordered or costs_task else 1))

    return processed_operators

def process_init(init, vars_val_map, is_fact_relevant, variables, ordered):
    new_init_values = list()
    for var, val in enumerate(init.values):
        # If fact is relevant add to init. Else add 'some value'
        if is_fact_relevant[var][val]:
            new_init_values.append(vars_val_map[var][val])
        else:
            new_init_values.append(variables.ranges[var] - 1)

    # Order var always last one. Initial plan position 0
    if ordered:
        new_init_values.append(0)
    
    return SASInit(values=new_init_values)

def process_mutex_groups(mutex_groups, vars_val_map, is_fact_relevant):
    new_groups = list()
    for group in mutex_groups:
        new_mutex = [(var, vars_val_map[var][val]) for var, val in group.facts if is_fact_relevant[var][val]]
        if len(new_mutex) > 1:
            new_groups.append(SASMutexGroup(facts=new_mutex))
    
    return new_groups

def process_axioms(axioms):
    # TODO use axioms!
    return list()

# One liner without multiple uses. Might refactor
def map_goal_vals(goal, vars_vals_map):
    return SASGoal(pairs=[(var, vars_vals_map[var][val]) for var, val in goal.pairs])

def main():
    help_string = '''
    Creates an action elimination domain for an automated planning task and a valid plan.
    Currently reduction will always be MR, will include MLR in the future.
    Examples: <param> is a nec. parameter, while [param=val] is an optional parameter with default value = val
    Maintain order of actions in original plan call string: 
        ./action_elim.py  -t <output.sas> -p <sas_plan> -s -r [reduction=MR] -f [file=reformulation.sas] -d [directory=.]
    Allow reorder of actions in original plan call string: 
        ./action_elim.py  -t <output.sas> -p <sas_plan> -r [reduction=MR] -f [file=reformulation.sas] -d [directory=.]
    '''
    parser = argparse.ArgumentParser(description=help_string,formatter_class=argparse.RawTextHelpFormatter)
    required_named = parser.add_argument_group('required named arguments')
    required_named.add_argument('-t', '--task', help='Path to task file in SAS+ format.',type=str, required=True)
    required_named.add_argument('-p', '--plan', help='Path to plan file.', type=str, required=True)
    parser.add_argument('-s', '--subsequence', help='Compiled task must guarantee maintaing order of original actions', action='store_true', default=False)
    parser.add_argument('-r', '--reduction', help='MR or MLR. MR=minimal reduction, MLR=minimal length reduction',type=str, default=MR)
    parser.add_argument('-f', '--file', help='Output file where reformulated SAS+ will be stored',type=str,default='minimal-reduction.sas')
    parser.add_argument('-d', '--directory', help='Output directory',type=str, default='.')
    options = parser.parse_args()
    
    if options.task == None or options.plan == None:
        parser.print_help()
        exit(-1)

    task, operator_name_to_index_map = parse_task(options.task)
    plan_size, plan, plan_cost = parse_plan(options.plan)
    new_task = create_action_elim_task(task, plan, operator_name_to_index_map, options.subsequence)
    
    with open(os.path.join(options.directory, options.file), mode='w') as output_file:
        new_task.output(stream=output_file)
    
if __name__ == '__main__':
    main()
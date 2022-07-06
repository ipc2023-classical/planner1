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

from asyncio.subprocess import STDOUT
import sys
import os

from yaml import parse
from sas_tasks import SASTask, SASVariables, SASOperator, SASInit, SASGoal, SASAxiom, SASMutexGroup
from plan_parser import parse_plan

MR  = 'MR'
MLR = 'MLR'

def parse_task(task_file):
    variables = list()
    domains = list()
    mutex_groups = list()
    init_values = list()
    goal_values = list()
    operators = list()
    axiom_layers = list()
    axioms = list()
    current_line = str()
    ranges = list()
    operator_index = 0
    operator_name_to_index = dict()
    fact_name_to_var_val = dict()

    try:
        with open(task_file, 'r') as sas_task:
            # Read version
            current_line = sas_task.readline().strip()
            assert(current_line == 'begin_version')
            version = int(sas_task.readline().strip())
            if version != 3: sys.exit("Only version 3 supported.")
            current_line = sas_task.readline().strip()
            assert(current_line == 'end_version')

            # Check metric
            current_line = sas_task.readline().strip()
            assert(current_line == 'begin_metric')
            metric = sas_task.readline().strip() != '0'
            current_line = sas_task.readline().strip()
            assert(current_line == 'end_metric')

            # Read variables
            num_vars = int(sas_task.readline().strip())
            for _ in range(num_vars):
                current_line = sas_task.readline().strip()
                assert(current_line == 'begin_variable')

                # Name and axiom
                var_name = sas_task.readline().strip()
                axiom_layer =  int(sas_task.readline().strip())

                # Domain
                dom_size = int(sas_task.readline().strip())
                ranges.append(dom_size)
                domain_vals = list()
                for _ in range(dom_size): domain_vals.append(sas_task.readline().strip())

                current_line = sas_task.readline().strip()
                assert(current_line == 'end_variable')

                # Store var info
                variables.append(var_name)
                axiom_layers.append(axiom_layer)
                domains.append(domain_vals)
            
            variables = SASVariables(ranges=ranges, axiom_layers=axiom_layers,value_names=domains)
            # Read mutex groups
            num_mutex_groups = int(sas_task.readline().strip())
            for _ in range(num_mutex_groups):
                current_line = sas_task.readline().strip()
                assert(current_line == 'begin_mutex_group')
                current_group = list()
                facts_in_group = int(sas_task.readline().strip())
                for _ in range(facts_in_group):
                    var, fact = sas_task.readline().strip().split()
                    current_group.append((int(var), int(fact)))

                current_line = sas_task.readline().strip()
                assert(current_line == 'end_mutex_group')
                mutex_groups.append(SASMutexGroup(facts=current_group))

            # Read initial state
            current_line = sas_task.readline().strip()
            assert(current_line == 'begin_state')
            
            for _ in range(num_vars):
                # Not going to check for domain of each variable, assume input sas is valid
                init_values.append(int(sas_task.readline().strip()))
            init_state = SASInit(init_values)
            
            current_line = sas_task.readline().strip()
            assert(current_line == 'end_state')

            # Read goal
            current_line = sas_task.readline().strip()
            assert(current_line == 'begin_goal')

            num_goals = int(sas_task.readline().strip())
            for _ in range(num_goals):
                var, val = sas_task.readline().strip().split()
                goal_values.append((int(var), int(val)))
            
            goal = SASGoal(pairs=goal_values)

            current_line = sas_task.readline().strip()
            assert(current_line == 'end_goal')

            # Read operators
            num_operators = int(sas_task.readline().strip())
            for _ in range(num_operators):
                current_line = sas_task.readline().strip()
                assert(current_line == 'begin_operator')

                # Name and prevail conditions               
                operator_name = '(%s)' % sas_task.readline().strip()
                prevail_cond = list()
                num_prevail_cond = int(sas_task.readline().strip())
                for _ in range(num_prevail_cond):
                    var, val = sas_task.readline().strip().split()
                    prevail_cond.append((int(var), int(val)))

                # Effects
                effects = list()
                num_effects = int(sas_task.readline().strip())
                for _ in range(num_effects):
                    num_cond_effects, var_number, old_val, new_val = sas_task.readline().strip().split()
                    if int(num_cond_effects) > 0:
                        sys.exit("Conditional effects not supported.")
                    effects.append((int(var_number), int(old_val), int(new_val), []))

                cost = int(sas_task.readline().strip())
                current_line = sas_task.readline().strip()
                assert(current_line == 'end_operator')

                # Create operator with empty prev, pre_post. Done to maintain orignal SAS+ task variable order
                operators.append(SASOperator(name=operator_name, prevail=[], pre_post=[], cost=cost))
                operators[-1].prevail = prevail_cond
                operators[-1].pre_post = effects
                operator_name_to_index[operator_name] = operator_index
                operator_index += 1

            # Axioms...
            num_axioms = int(sas_task.readline().strip())
            for _ in range(num_axioms):
                current_line = sas_task.readline().strip()
                assert(current_line == 'begin_rule')

                num_cond = int(sas_task.readline().strip())
                conditions = list()
                conditions = list()
                for _ in range(num_cond):
                    var, val = sas_task.readline().strip().split()
                    conditions.append(int(var), int(val))
                
                var, old_val, new_val = sas_task.readline().strip().split()
                effect = (int(var), int(old_val), int(new_val))

                current_line = sas_task.readline().strip()
                assert(current_line == 'end_rule')

                axioms.append(SASAxiom(condition=conditions, effect=effect))

    except Exception as e:
        print("Something went wrong!", e)
        exit(-1)

    return SASTask(variables=variables, mutexes=mutex_groups, init=init_state, goal=goal, operators=operators, axioms=axioms, metric=metric), operator_name_to_index
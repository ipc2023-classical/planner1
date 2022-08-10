#! /usr/bin/env python3

#######################################################################
#
# Author: Raquel Fuentetaja 
# Copyright 2021
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
#######################################################################

import re


class PlanAction:
    def __init__(self, step, action):
        self.step = step
        self.op = action[0].lower()
        self.args = list(map(lambda x:x.lower(), action[1:]))
        self.action = " ".join(action)

    def set_instance_mapping(self, op):
        self.op_mapping = dict()
        for param, arg in zip(op.parameters, self.args):
            self.op_mapping[param.name] = arg

    def set_shadow_action(self, shadow_subs, baseop):
        self.shadow_action = [baseop.name]

        for param in baseop.parameters:
            if param.name in self.op_mapping.keys():
                self.shadow_action.append(self.op_mapping[param.name])
            elif param.name in shadow_subs.keys():
                self.shadow_action.append(shadow_subs[param.name])
            else:
                self.shadow_action.append('<NoneOb!>')
            
    def __str__(self):
        return self.action

def parse_plan(planfile):
    plan_actions = []
    
    #action_reader = re.compile("([0-9]*): (\(.*\))\s*\[([0-9]*\.[0-9]*)\]")
    #action_reader = re.compile("\s*([0-9]*): (\(.*\))")
    action_reader = re.compile("(\(.*\))")

    try:
        stream = open(planfile, 'r')
        step = 0
        for line in stream:
            plan_action = action_reader.match(line)
            if plan_action and not "skip-original-action-plan" in line:
                step +=1
                action_args = plan_action.group(1)[1:-1].split()
                #planactions.append(Planaction(plan_action.group(1), action_args))
                plan_actions.append(PlanAction(step, action_args))

        total_cost = int(re.sub("[^0-9]", "", line))
                
        return step, plan_actions, total_cost
    except:
        return -1,-1,-1

def parse_skippable_actions(actions_file):
    skippable_actions = list()
    action_reader = re.compile("(\(.*\))")
    stream = open(actions_file, 'r')
    step = -1
    for line in stream:
        skippable = action_reader.match(line)
        if (skippable is None): continue
        # TODO fix this thing...
        skippable = skippable.group(1).split(",")[1].replace(")","").strip() == "True"
        skippable_actions.append((step, skippable))
        step += 1

    # First and last actions are virtual initial and goal action
    if False:
        for action in skippable_actions[1:-1]:
            print("Action %d is %s" % (action[0], action[1]))

    return skippable_actions[1:-1]

# For printing plans in any format
def print_plan(planactions):
    for i, a in enumerate(planactions):
        print ("%s: (%s)" % (i+1, a.action))


def print_from_list(objectlist):
    res = ""
    for el in objectlist:
        res += " %s" % el
    return res


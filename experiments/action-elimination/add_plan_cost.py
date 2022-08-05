import os
import subprocess
from downward import suites
import sys
SAS_FILE_VERSION = 3

DEBUG = False

class SASTask:
    """Planning task in finite-domain representation.

    The user is responsible for making sure that the data fits a
    number of structural restrictions. For example, conditions should
    generally be sorted and mention each variable at most once. See
    the validate methods for details."""

    def __init__(self, variables, mutexes, init, goal,
                 operators, axioms, metric):
        self.variables = variables
        self.mutexes = mutexes
        self.init = init
        self.goal = goal
        self.operators = sorted(operators, key=lambda op: (
            op.name, op.prevail, op.pre_post))
        self.axioms = sorted(axioms, key=lambda axiom: (
            axiom.condition, axiom.effect))
        self.metric = metric
        if DEBUG:
            self.validate()

    def validate(self):
        """Fail an assertion if the task is invalid.

        A task is valid if all its components are valid. Valid tasks
        are almost in a kind of "canonical form", but not quite. For
        example, operators and axioms are permitted to be listed in
        any order, even though it would be possible to require some
        kind of canonical sorting.

        Note that we require that all derived variables are binary.
        This is stricter than what later parts of the planner are
        supposed to handle, but some parts of the translator rely on
        this. We might want to consider making this a general
        requirement throughout the planner.

        Note also that there is *no* general rule on what the init (=
        fallback) value of a derived variable is. For example, in
        PSR-Large #1, it can be either 0 or 1. While it is "usually"
        1, code should not rely on this.
        """
        self.variables.validate()
        for mutex in self.mutexes:
            mutex.validate(self.variables)
        self.init.validate(self.variables)
        self.goal.validate(self.variables)
        for op in self.operators:
            op.validate(self.variables)
        for axiom in self.axioms:
            axiom.validate(self.variables, self.init)
        assert self.metric is False or self.metric is True, self.metric

    def dump(self):
        print("variables:")
        self.variables.dump()
        print("%d mutex groups:" % len(self.mutexes))
        for mutex in self.mutexes:
            print("group:")
            mutex.dump()
        print("init:")
        self.init.dump()
        print("goal:")
        self.goal.dump()
        print("%d operators:" % len(self.operators))
        for operator in self.operators:
            operator.dump()
        print("%d axioms:" % len(self.axioms))
        for axiom in self.axioms:
            axiom.dump()
        print("metric: %s" % self.metric)

    def output(self, stream):
        print("begin_version", file=stream)
        print(SAS_FILE_VERSION, file=stream)
        print("end_version", file=stream)
        print("begin_metric", file=stream)
        print(int(self.metric), file=stream)
        print("end_metric", file=stream)
        self.variables.output(stream)
        print(len(self.mutexes), file=stream)
        for mutex in self.mutexes:
            mutex.output(stream)
        self.init.output(stream)
        self.goal.output(stream)
        print(len(self.operators), file=stream)
        for op in self.operators:
            op.output(stream)
        print(len(self.axioms), file=stream)
        for axiom in self.axioms:
            axiom.output(stream)

    def get_encoding_size(self):
        task_size = 0
        task_size += self.variables.get_encoding_size()
        for mutex in self.mutexes:
            task_size += mutex.get_encoding_size()
        task_size += self.goal.get_encoding_size()
        for op in self.operators:
            task_size += op.get_encoding_size()
        for axiom in self.axioms:
            task_size += axiom.get_encoding_size()
        return task_size


class SASVariables:
    def __init__(self, ranges, axiom_layers, value_names):
        self.ranges = ranges
        self.axiom_layers = axiom_layers
        self.value_names = value_names

    def validate(self):
        """Validate variables.

        All variables must have range at least 2, and derived
        variables must have range exactly 2. See comment on derived
        variables in the docstring of SASTask.validate.
        """
        assert len(self.ranges) == len(self.axiom_layers) == len(
            self.value_names)
        for (var_range, layer, var_value_names) in zip(
                self.ranges, self.axiom_layers, self.value_names):
            assert var_range == len(var_value_names)
            assert var_range >= 2
            assert layer == -1 or layer >= 0
            if layer != -1:
                assert var_range == 2

    def validate_fact(self, fact):
        """Assert that fact is a valid (var, value) pair."""
        var, value = fact
        assert 0 <= var < len(self.ranges)
        assert 0 <= value < self.ranges[var]

    def validate_condition(self, condition):
        """Assert that the condition (list of facts) is sorted, mentions each
        variable at most once, and only consists of valid facts."""
        last_var = -1
        for (var, value) in condition:
            self.validate_fact((var, value))
            assert var > last_var
            last_var = var

    def dump(self):
        for var, (rang, axiom_layer) in enumerate(
                zip(self.ranges, self.axiom_layers)):
            if axiom_layer != -1:
                axiom_str = " [axiom layer %d]" % axiom_layer
            else:
                axiom_str = ""
            print("v%d in {%s}%s" % (var, list(range(rang)), axiom_str))

    def output(self, stream):
        print(len(self.ranges), file=stream)
        for var, (rang, axiom_layer, values) in enumerate(zip(
                self.ranges, self.axiom_layers, self.value_names)):
            print("begin_variable", file=stream)
            print("var%d" % var, file=stream)
            print(axiom_layer, file=stream)
            print(rang, file=stream)
            assert rang == len(values), (rang, values)
            for value in values:
                print(value, file=stream)
            print("end_variable", file=stream)

    def get_encoding_size(self):
        # A variable with range k has encoding size k + 1 to also give the
        # variable itself some weight.
        return len(self.ranges) + sum(self.ranges)


class SASMutexGroup:
    def __init__(self, facts):
        self.facts = sorted(facts)

    def validate(self, variables):
        """Assert that the facts in the mutex group are sorted and unique
        and that they are all valid."""
        for fact in self.facts:
            variables.validate_fact(fact)
        assert self.facts == sorted(set(self.facts))

    def dump(self):
        for var, val in self.facts:
            print("v%d: %d" % (var, val))

    def output(self, stream):
        print("begin_mutex_group", file=stream)
        print(len(self.facts), file=stream)
        for var, val in self.facts:
            print(var, val, file=stream)
        print("end_mutex_group", file=stream)

    def get_encoding_size(self):
        return len(self.facts)


class SASInit:
    def __init__(self, values):
        self.values = values

    def validate(self, variables):
        """Validate initial state.

        Assert that the initial state contains the correct number of
        values and that all values are in range.
        """

        assert len(self.values) == len(variables.ranges)
        for fact in enumerate(self.values):
            variables.validate_fact(fact)

    def dump(self):
        for var, val in enumerate(self.values):
            print("v%d: %d" % (var, val))

    def output(self, stream):
        print("begin_state", file=stream)
        for val in self.values:
            print(val, file=stream)
        print("end_state", file=stream)


class SASGoal:
    def __init__(self, pairs):
        self.pairs = sorted(pairs)

    def validate(self, variables):
        """Assert that the goal is nonempty and a valid condition."""
        assert self.pairs
        variables.validate_condition(self.pairs)

    def dump(self):
        for var, val in self.pairs:
            print("v%d: %d" % (var, val))

    def output(self, stream):
        print("begin_goal", file=stream)
        print(len(self.pairs), file=stream)
        for var, val in self.pairs:
            print(var, val, file=stream)
        print("end_goal", file=stream)

    def get_encoding_size(self):
        return len(self.pairs)


class SASOperator:
    def __init__(self, name, prevail, pre_post, cost):
        self.name = name
        self.prevail = sorted(prevail)
        self.pre_post = self._canonical_pre_post(pre_post)
        self.cost = cost

    def _canonical_pre_post(self, pre_post):
        # Return a sorted and uniquified version of pre_post. We would
        # like to just use sorted(set(pre_post)), but this fails because
        # the effect conditions are a list and hence not hashable.
        def tuplify(entry):
            var, pre, post, cond = entry
            return var, pre, post, tuple(cond)
        def listify(entry):
            var, pre, post, cond = entry
            return var, pre, post, list(cond)
        pre_post = map(tuplify, pre_post)
        pre_post = sorted(set(pre_post))
        pre_post = list(map(listify, pre_post))
        return pre_post

    def validate(self, variables):
        """Validate the operator.

        Assert that
        1. Prevail conditions are valid conditions (i.e., sorted and
           all referring to different variables)
        2. The pre_post list is sorted by (var, pre, post, cond), and the
           same (var, pre, post, cond) 4-tuple is not repeated.
        3. Effect conditions are valid conditions and do not contain variables
           from the pre- or prevail conditions.
        4. Variables occurring in pre_post rules do not have a prevail
           condition.
        5. Preconditions in pre_post are -1 or valid facts.
        6. Effects are valid facts.
        7. Effect variables are non-derived.
        8. If a variable has multiple pre_post rules, then pre is
           identical in all these rules.
        9. There is at least one effect.
        10. Costs are non-negative integers.

        Odd things that are *not* illegal:
        - The effect in a pre_post rule may be identical to the
          precondition or to an effect condition of that effect.

        TODO/open question:
        - It is currently not very clear what the semantics of operators
          should be when effects "conflict", i.e., when multiple effects
          trigger and want to set a given variable to two different
          values. In the case where both are unconditional effects, we
          should make sure that our representation doesn't actually
          contain two such effects, but when at least one of them is
          conditional, things are not so easy.

          To make our life simpler when generating SAS+ tasks from
          PDDL tasks, it probably makes most sense to generalize the
          PDDL rule in this case: there is a value order where certain
          values "win" over others in this situation. It probably
          makes sense to say the "highest" values should win in this
          case, because that's consistent with the PDDL rules if we
          say false = 0 and true = 1, and also with our sort order of
          effects it means we get the right result if we just apply
          effects in sequence.

          But whatever we end up deciding, we need to be clear about it,
          document it and make sure that all of our code knows the rules
          and follows them.
        """

        variables.validate_condition(self.prevail)
        assert self.pre_post == self._canonical_pre_post(self.pre_post)
        prevail_vars = {var for (var, value) in self.prevail}
        pre_values = {}
        for var, pre, post, cond in self.pre_post:
            variables.validate_condition(cond)
            assert var not in prevail_vars
            if pre != -1:
                variables.validate_fact((var, pre))
            variables.validate_fact((var, post))
            assert variables.axiom_layers[var] == -1
            if var in pre_values:
                assert pre_values[var] == pre
            else:
                pre_values[var] = pre
        for var, pre, post, cond in self.pre_post:
            for cvar, cval in cond:
                assert(cvar not in pre_values or pre_values[cvar] == -1)
                assert(cvar not in prevail_vars)
        assert self.pre_post
        assert self.cost >= 0 and self.cost == int(self.cost)

    def dump(self):
        print(self.name)
        print("Prevail:")
        for var, val in self.prevail:
            print("  v%d: %d" % (var, val))
        print("Pre/Post:")
        for var, pre, post, cond in self.pre_post:
            if cond:
                cond_str = " [%s]" % ", ".join(
                    ["%d: %d" % tuple(c) for c in cond])
            else:
                cond_str = ""
            print("  v%d: %d -> %d%s" % (var, pre, post, cond_str))

    def output(self, stream):
        print("begin_operator", file=stream)
        print(self.name[1:-1], file=stream)
        print(len(self.prevail), file=stream)
        for var, val in self.prevail:
            print(var, val, file=stream)
        print(len(self.pre_post), file=stream)
        for var, pre, post, cond in self.pre_post:
            print(len(cond), end=' ', file=stream)
            for cvar, cval in cond:
                print(cvar, cval, end=' ', file=stream)
            print(var, pre, post, file=stream)
        print(self.cost, file=stream)
        print("end_operator", file=stream)

    def get_encoding_size(self):
        size = 1 + len(self.prevail)
        for var, pre, post, cond in self.pre_post:
            size += 1 + len(cond)
            if pre != -1:
                size += 1
        return size

    def get_applicability_conditions(self):
        """Return the combined applicability conditions
        (prevail conditions and preconditions) of the operator.

        Returns a sorted list of (var, value) pairs. This is
        guaranteed to contain at most one fact per variable and
        must hence be non-contradictory."""
        conditions = {}
        for var, val in self.prevail:
            assert var not in conditions
            conditions[var] = val
        for var, pre, post, cond in self.pre_post:
            if pre != -1:
                assert var not in conditions or conditions[var] == pre
                conditions[var] = pre
        return sorted(conditions.items())


class SASAxiom:
    def __init__(self, condition, effect):
        self.condition = sorted(condition)
        self.effect = effect
        assert self.effect[1] in (0, 1)

        for _, val in condition:
            assert val >= 0, condition

    def validate(self, variables, init):

        """Validate the axiom.

        Assert that the axiom condition is a valid condition, that the
        effect is a valid fact, that the effect variable is a derived
        variable, and that the layering condition is satisfied.

        See the docstring of SASTask.validate for information on the
        restriction on derived variables. The layering condition boils
        down to:

        1. Axioms always set the "non-init" value of the derived
           variable.
        2. Derived variables in the condition must have a lower of
           equal layer to derived variables appearing in the effect.
        3. Conditions with equal layer are only allowed when the
           condition uses the "non-init" value of that variable.

        TODO/bug: rule #1 is currently disabled because we currently
        have axioms that violate it. This is likely due to the
        "extended domain transition graphs" described in the Fast
        Downward paper, Section 5.1. However, we want to eventually
        changes this. See issue454. For cases where rule #1 is violated,
        "non-init" should be "init" in rule #3.
        """

        variables.validate_condition(self.condition)
        variables.validate_fact(self.effect)
        eff_var, eff_value = self.effect
        eff_layer = variables.axiom_layers[eff_var]
        assert eff_layer >= 0
        eff_init_value = init.values[eff_var]
        ## The following rule is currently commented out because of
        ## the TODO/bug mentioned in the docstring.
        # assert eff_value != eff_init_value
        for cond_var, cond_value in self.condition:
            cond_layer = variables.axiom_layers[cond_var]
            if cond_layer != -1:
                assert cond_layer <= eff_layer
                if cond_layer == eff_layer:
                    cond_init_value = init.values[cond_var]
                    ## Once the TODO/bug above is addressed, the
                    ## following four lines can be simplified because
                    ## we are guaranteed to land in the "if" branch.
                    if eff_value != eff_init_value:
                        assert cond_value != cond_init_value
                    else:
                        assert cond_value == cond_init_value

    def dump(self):
        print("Condition:")
        for var, val in self.condition:
            print("  v%d: %d" % (var, val))
        print("Effect:")
        var, val = self.effect
        print("  v%d: %d" % (var, val))

    def output(self, stream):
        print("begin_rule", file=stream)
        print(len(self.condition), file=stream)
        for var, val in self.condition:
            print(var, val, file=stream)
        var, val = self.effect
        print(var, 1 - val, val, file=stream)
        print("end_rule", file=stream)

    def get_encoding_size(self):
        return 1 + len(self.condition)


def parse_plan(planfile):
    with open(planfile) as stream:
        lines = stream.readlines()
    plan = [act.strip() for act in lines[:-1]]
    #total_cost = int(re.match(r"; cost = (\d+) \(.+ cost\)", lines[-1]).group(1))
    return plan


def parse_task(task_file):
    variables = []
    domains = []
    mutex_groups = []
    init_values = []
    goal_values = []
    operators = []
    axiom_layers = []
    axioms = []
    current_line = ""
    ranges = []
    operator_name_to_index = {}

    def get_next_line():
        return sas_task.readline().strip()

    def get_next_int():
        return int(get_next_line())

    def get_next_int_pair():
        p1, p2 = get_next_line().split()
        return int(p1), int(p2)

    with open(task_file, 'r') as sas_task:
        # Read version
        current_line = get_next_line()
        assert(current_line == 'begin_version')
        version = get_next_int()
        if version != 3:
            sys.exit("Only version 3 supported.")
        current_line = get_next_line()
        assert(current_line == 'end_version')

        # Check metric
        current_line = get_next_line()
        assert(current_line == 'begin_metric')
        metric = get_next_line() != '0'
        current_line = get_next_line()
        assert(current_line == 'end_metric')

        # Read variables
        num_vars = get_next_int()
        for _ in range(num_vars):
            current_line = get_next_line()
            assert(current_line == 'begin_variable')

            # Name and axiom
            var_name = get_next_line()
            axiom_layer =  get_next_int()

            # Domain
            dom_size = get_next_int()
            ranges.append(dom_size)
            domain_vals = []
            for _ in range(dom_size):
                domain_vals.append(get_next_line())

            current_line = get_next_line()
            assert(current_line == 'end_variable')

            # Store var info
            variables.append(var_name)
            axiom_layers.append(axiom_layer)
            domains.append(domain_vals)

        variables = SASVariables(ranges=ranges, axiom_layers=axiom_layers,value_names=domains)
        # Read mutex groups
        num_mutex_groups = get_next_int()
        for _ in range(num_mutex_groups):
            current_line = get_next_line()
            assert(current_line == 'begin_mutex_group')
            current_group = []
            facts_in_group = get_next_int()
            for _ in range(facts_in_group):
                var, fact = get_next_int_pair()
                current_group.append((int(var), int(fact)))

            current_line = get_next_line()
            assert(current_line == 'end_mutex_group')

            # Create mutex group with empty facts
            # The constructor of SASMutexGroup reorders the facts.
            # This causes the parsed task to not be exactly equal to the task defined in the input file (diff. order facts in mutexes)
            # Creating the SASMutex and then adding the facts maintains order of the input task file
            mutex_groups.append(SASMutexGroup(facts=[]))
            mutex_groups[-1].facts = current_group

        # Read initial state
        current_line = get_next_line()
        assert(current_line == 'begin_state')

        for _ in range(num_vars):
            # Not going to check for domain of each variable, assume input sas is valid
            init_values.append(get_next_int())
        init_state = SASInit(init_values)

        current_line = get_next_line()
        assert(current_line == 'end_state')

        # Read goal
        current_line = get_next_line()
        assert(current_line == 'begin_goal')

        num_goals = get_next_int()
        for _ in range(num_goals):
            var, val = get_next_int_pair()
            goal_values.append((var,val))

        goal = SASGoal(pairs=goal_values)

        current_line = get_next_line()
        assert(current_line == 'end_goal')

        # Read operators
        num_operators = get_next_int()
        for operator_index in range(num_operators):
            current_line = get_next_line()
            assert(current_line == 'begin_operator')

            # Name and prevail conditions
            operator_name = '(%s)' % sas_task.readline().rstrip('\n')
            prevail_cond = []
            num_prevail_cond = get_next_int()
            for _ in range(num_prevail_cond):
                var, val = get_next_int_pair()
                prevail_cond.append((var,val))

            # Effects
            effects = []
            num_effects = get_next_int()
            for _ in range(num_effects):
                try:
                    num_cond_effects, var_number, old_val, new_val = sas_task.readline().strip().split()
                except:
                    # TODO should we include conditional effects?
                    #print(operator_name)
                    #print("Conditional effects not supported.")
                    return None, None
                if int(num_cond_effects) > 0:
                    sys.exit("Conditional effects not supported.")
                effects.append((int(var_number), int(old_val), int(new_val), []))

            cost = get_next_int()
            current_line = get_next_line()
            assert(current_line == 'end_operator')

            # Create operator with empty prev, pre_post.
            # The constructor of SASOperator reorders the prevail and pre_post.
            # This causes the parsed task to not be exactly equal to the task defined in the input file (diff. order of prevails, pre_posts)
            # Creating the SASOpertor and then adding the prevail, pre_post maintains order of the input task file.
            operators.append(SASOperator(name=operator_name, prevail=[], pre_post=[], cost=cost))
            operators[-1].prevail = prevail_cond
            operators[-1].pre_post = effects
            operator_name_to_index[operator_name] = operator_index

        # Axioms...
        num_axioms = get_next_int()
        for _ in range(num_axioms):
            current_line = get_next_line()
            assert(current_line == 'begin_rule')

            num_cond = get_next_int()
            conditions = []
            for _ in range(num_cond):
                var, val = get_next_int_pair()
                conditions.append(var, val)

            var, old_val, new_val = sas_task.readline().strip().split()
            effect = (int(var), int(old_val), int(new_val))

            current_line = get_next_line()
            assert(current_line == 'end_rule')

            axioms.append(SASAxiom(condition=conditions, effect=effect))

    # Verify that the read task is equal to original file
    task = SASTask(variables=variables, mutexes=mutex_groups, init=init_state, goal=goal, operators=operators, axioms=axioms, metric=metric)
    verify_file = task_file + ".verify-contents.sas"
    with open(verify_file, mode='w') as output_file:
        task.output(stream=output_file)

    # Some trailing whitespaces and empty lines might mess with filecmp, so now using this.
    # Did not find a direct way to use filecmp while ignoring trailing whtiespaces and empty lines.
    are_different = subprocess.check_output(['diff', '-ZB', task_file, verify_file]).decode('utf-8')
    assert not are_different, "Read task is not equal to input task."
    os.remove(verify_file)

    return SASTask(variables=variables, mutexes=mutex_groups, init=init_state, goal=goal, operators=operators, axioms=axioms, metric=metric), operator_name_to_index

def main():
    PLANNER_NAMES = ["freelunch-madagascar", "LAPKT-BFWS-Preference","yahsp"]
    current_dir = os.path.dirname(os.path.realpath(__file__))
    SAS_DIR = os.path.join(current_dir, "plans/translator")
    BENCHMARKS_DIR = os.path.join(current_dir ,"domains/ipc2014/seq-agl")
    BENCHMARKS_DIR1 = os.path.join(current_dir ,"domains/ipc2018/sat")
    PLANS_DIR = os.path.join(current_dir,"plans")

    SUITE = [name for name in os.listdir(BENCHMARKS_DIR)
            if os.path.isdir(os.path.join(BENCHMARKS_DIR, name))]
    SUITE1 = [name for name in os.listdir(BENCHMARKS_DIR1)
            if os.path.isdir(os.path.join(BENCHMARKS_DIR1, name))]
    plans_changed = 0
    for planner_name in PLANNER_NAMES:
        for domain in SUITE:
            count = 1
            for task in suites.build_suite(BENCHMARKS_DIR, [domain]):
                plan_file = "{0}/{1}/{2}/{2}{3}{4}.solution".format(PLANS_DIR, planner_name, task.domain, "0" if count < 10 else "", count)
                sas_file = "{0}/{1}/{1}{2}{3}.solution".format(SAS_DIR, task.domain, "0" if count < 10 else "", count)
                # For each task in the suite, check if plan and sas_file exist
                if os.path.exists(plan_file) and os.path.exists(sas_file):
                    sas_task, operator_name_to_index = parse_task(sas_file)
                    # If succesful parse of sas_task, get plan and plan cost
                    if sas_task:
                        plan = parse_plan(plan_file)
                        plan = [sas_task.operators[operator_name_to_index[op]] for op in plan]
                        plan_cost = sum(op.cost for op in plan)
                        # Add cost line at end if not exists
                        with open(plan_file, 'r+') as f:
                            lines = f.readlines()
                            if not lines[-1]:
                                lines = lines[:-1]
                            elif lines[-1].startswith("; cost = "):
                                lines = lines[:-1]
                            if sas_task.metric:
                                lines.append("; cost = %d (%s)\n" % (plan_cost, "general cost"))
                            else:
                                lines.append("; cost = %d (%s)\n" % (len(plan), "unit cost"))

                            f.seek(0)
                            f.writelines(lines)
                            f.truncate()
                            plans_changed += 1
                            # Could have just used validate... Add it as verification
                            # are_different = subprocess.check_output(['validate', task.domain_file, task.problem_file, plan_file]).decode('utf-8')
                            # if "Value: %d" % plan_cost not in are_different:
                            #     print("Messed up the cost! " + plan_file)
                count += 1

        for domain in SUITE1:
            count = 1
            for task in suites.build_suite(BENCHMARKS_DIR1, [domain]):
                plan_file = "{0}/{1}/{2}/{2}{3}{4}.solution".format(PLANS_DIR, planner_name, task.domain, "0" if count < 10 else "", count)
                sas_file = "{0}/{1}/{1}{2}{3}.solution".format(SAS_DIR, task.domain, "0" if count < 10 else "", count)
                if os.path.exists(plan_file) and os.path.exists(sas_file):
                    sas_task, operator_name_to_index = parse_task(sas_file)
                    if sas_task:
                        plan = parse_plan(plan_file)
                        plan = [sas_task.operators[operator_name_to_index[op]] for op in plan]
                        plan_cost = sum(op.cost for op in plan)
                        with open(plan_file, 'r+') as f:
                            lines = f.readlines()
                            if not lines[-1]:
                                lines = lines[:-1]
                            elif lines[-1].startswith("; cost = "):
                                lines = lines[:-1]
                            if sas_task.metric:
                                lines.append("; cost = %d (%s)\n" % (plan_cost, "general cost"))
                            else:
                                lines.append("; cost = %d (%s)\n" % (plan_cost, "unit cost"))
                            f.seek(0)
                            f.writelines(lines)
                            f.truncate()
                            plans_changed += 1
                            # Could have just used validate... Add it as verification
                            # are_different = subprocess.check_output(['validate', task.domain_file, task.problem_file, plan_file]).decode('utf-8')
                            # if "Value: %d" % plan_cost not in are_different:
                            #     print("Messed up the cost! " + plan_file)
                count += 1
    print("Updated plans: ", plans_changed)
if __name__ == "__main__":
    main()
from pddl.actions import Action
from .conditions import NegatedAtom
from . import axioms
from . import predicates
from . import f_expression

NUMERIC_COMPILATION = False
MINIMAL_COST = True
class Task:
    def __init__(self, domain_name, task_name, requirements,
                 types, objects, predicates, functions, init, goal,
                 actions, axioms, use_metric):
        self.domain_name = domain_name
        self.task_name = task_name
        self.requirements = requirements
        self.types = types
        self.objects = objects
        self.predicates = predicates
        self.functions = functions
        self.init = init
        self.goal = goal
        self.actions = actions
        self.axioms = axioms
        self.axiom_counter = 0
        self.use_min_cost_metric = use_metric

    def add_axiom(self, parameters, condition):
        name = "new-axiom@%d" % self.axiom_counter
        self.axiom_counter += 1
        axiom = axioms.Axiom(name, parameters, len(parameters), condition)
        self.predicates.append(predicates.Predicate(name, parameters))
        self.axioms.append(axiom)
        return axiom

    def dump(self):
        print("Problem %s: %s [%s]" % (
            self.domain_name, self.task_name, self.requirements))
        print("Types:")
        for type in self.types:
            print("  %s" % type)
        print("Objects:")
        for obj in self.objects:
            print("  %s" % obj)
        print("Predicates:")
        for pred in self.predicates:
            print("  %s" % pred)
        print("Functions:")
        for func in self.functions:
            print("  %s" % func)
        print("Init:")
        for fact in self.init:
            print("  %s" % fact)
        print("Goal:")
        self.goal.dump()
        print("Actions:")
        for action in self.actions:
            action.dump()
        if self.axioms:
            print("Axioms:")
            for axiom in self.axioms:
                axiom.dump()


#--------- RIA NEW METHODS -------------------------------------------------------------
# Added 19/11/21 by Raquel Fuentetaja
    def add_type(self, type_name):
        self.types.append(type_name)
        return type_name

    def add_predicate(self, predicate):
        self.predicates.append(predicate)
        return predicate

    def add_object(self, object):
        self.objects.append(object)
        return object

    def add_init_atom(self, atom):
        self.init.append(atom)
        return atom

    def goals(self):
        if not self.goal.parts:
            return [self.goal]
        return list(self.goal.parts)

    def add_action(self, action):
        self.actions.append(action)

    def save_domain_pddl(self, filename):
        indent = "   "
        with open(filename, 'w') as result_file:
            print ("(define (domain %s)" % self.domain_name , file = result_file)
            remove_action_costs = False
            if ":action-costs" not in self.requirements.requirements:
                remove_action_costs = True
                self.requirements.requirements.append(":action-costs")
            print ("(:requirements %s)" % " ".join(self.requirements.requirements), file = result_file)

            if remove_action_costs:
                self.requirements.requirements.remove(":action-costs")

            print(indent, "(:types ", file = result_file)
            for type in self.types:
                if type.basetype_name:
                    print ( indent, indent, type, "-", type.basetype_name, file = result_file)
                else:
                    if type.name != "object":
                        print (indent, indent, type, file = result_file)
            print ( indent, ")", file = result_file)

            print (indent, "(:predicates ", file = result_file)
            for pred in self.predicates:
                if (pred.name != '='):
                    print (indent, indent, "%s" % pred, file = result_file)
            print (indent, ")", file = result_file)

            print (indent, "(:functions " , file = result_file)
            added_total_cost = False
            for fun in self.functions:
                formatted_fun = "(%s %s)" % (fun.name, " - ".join(map(str, fun.arguments)))
                if fun.type_name:
                    added_total_cost = added_total_cost or "total-cost" in formatted_fun
                    formatted_fun += " - %s" % fun.type_name
                print (indent, indent, formatted_fun, file = result_file)

            if not added_total_cost and False:
                print (indent, indent, "(total-cost ) - number", file = result_file)


            #print >> file = result_file, indent, indent, "(total-cost)"
            if NUMERIC_COMPILATION:
                print(indent + indent + " (action-index-in-plan ?o - order)", file = result_file)

            print (indent, ")", file = result_file)


            for action in self.actions:
                action.save_pddl(result_file, indent, self)

            print (")", file = result_file)

    def save_problem_pddl(self, file_name):
        indent = "   "
        stream = open(file_name, "w")

        print ("(define (problem %s) " % self.task_name, file = stream)
        print (indent, "(:domain %s) " % self.domain_name, file = stream)

        print (indent, "(:objects ", file = stream)

        for ob in self.objects:
            print (indent, ob.name + " - " + ob.type_name, file = stream)
        print (")", file = stream)

        discard_preds = ['=']

        print (indent, "(:init ", file = stream)
        for literal in self.init:
            if type(literal) is not f_expression.Assign and literal.predicate not in discard_preds:
                print (indent, "%s" % literal, file = stream)
            elif type(literal) is f_expression.Assign:
                string = str(literal.fluent)
                string = string[len("PNE "):]
                string = string.replace("(", " ")
                string = string.replace(",", " ")
                string = "(= (" + string + " " + literal.expression.__str__()[len("NumericConstant "):] + ")"
                print(indent, string, file = stream)
        print (indent, ")", file = stream)
        print (indent, "(:goal (and ", file = stream)

        blank = " "
        for goal in self.goals():
            if isinstance(goal, NegatedAtom):
                #print (indent, "%s" % goal, file = stream)
                print(f"{indent}(not ({goal.predicate} {blank.join(goal.args)}))", file=stream)
            else:
                print (indent, "%s" % goal, file = stream)
        print ("))", file = stream)

        if MINIMAL_COST or True:
            print("(:metric minimize (total-cost))", file = stream)
        print(")", file=stream)


    def get_action_by_name(self, action_name):
        return next(action for action in self.actions if action.name == action_name)



#--------- END RIA NEW METHODS -------------------------------------------------------------

class Requirements:
    def __init__(self, requirements):
        self.requirements = requirements
        for req in requirements:
            assert req in (
              ":strips", ":adl", ":typing", ":negation", ":equality",
              ":negative-preconditions", ":disjunctive-preconditions",
              ":existential-preconditions", ":universal-preconditions",
              ":quantified-preconditions", ":conditional-effects",
              ":derived-predicates", ":action-costs"), req
    def __str__(self):
        return ", ".join(self.requirements)

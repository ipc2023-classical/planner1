import argparse
import sys

def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "domain", help="path to domain pddl file")
    argparser.add_argument(
        "task", help="path to task pddl file")
    argparser.add_argument(
        "plan", help="path to plan file")
    argparser.add_argument(
        "sas_task", help="The sastask")
    argparser.add_argument(
        "enhanced", help="Use trivilly nec actions")
    argparser.add_argument(
        "heuristic", help="Heuristic to use, blind or hmax")

    return argparser.parse_args()


def copy_args_to_module(args):
    module_dict = sys.modules[__name__].__dict__
    for key, value in vars(args).items():
        module_dict[key] = value


def setup():
    args = parse_args()
    copy_args_to_module(args)


setup()

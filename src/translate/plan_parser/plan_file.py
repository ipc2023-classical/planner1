#! /usr/bin/env python3

import re

def parse_plan(planfile):
    try:
        stream = open(planfile, 'r')
        lines = stream.readlines()
        plan = [act.strip() for act in lines[:-1]]
        total_cost = int(re.sub("[^0-9]", "", lines[-1]))
        return len(plan), plan, total_cost
    except Exception as e:
        print(e)
        return -1,-1,-1
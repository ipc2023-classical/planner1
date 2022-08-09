from lab.parser import Parser

# Parse AE specific values
ae_parser = Parser()
ae_parser.add_pattern("old_cost", r"Old plan cost: (\d+)\n", type=int)
ae_parser.add_pattern("new_cost", r"New plan cost: (\d+)\n", type=int)
ae_parser.add_pattern("create_ae_task_time", r"Create AE task time: (\d+\.\d+)\n", type=float)
ae_parser.add_pattern("parse_input_sas_and_plan", r"Parse input SAS task and plan time: (\d+\.\d+)\n", type=float)
ae_parser.add_pattern("ae_planner_call_time", r"AE planner call time: (\d+\.\d+)\n", type=float)
ae_parser.add_pattern("ae_total_time", r"Total AE time: (\d+\.\d+)\n", type=float)
ae_parser.add_pattern("search_time", r"Search time: (.+)s", type=float)

ae_parser.parse()
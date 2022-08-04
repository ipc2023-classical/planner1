from lab.parser import Parser

# Parse AE specific values
ae_parser = Parser()
ae_parser.add_pattern("old_cost", r"Old plan cost: (\d+)", type=int)
ae_parser.add_pattern("new_cost", r"New plan cost: (\d+)", type=int)
ae_parser.parse()
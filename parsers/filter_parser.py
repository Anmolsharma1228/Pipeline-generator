import re
from parsers.read_parser import generate_id


def parse_filter(prompt):

    pipeline = []

    prompt = prompt.lower()

    patterns = [

        # Filter salary > 40000
        r"filter\s+(\w+)\s*(>=|<=|>|<|==|=|!=)\s*(\d+)",

        # where salary > 40000
        r"where\s+(\w+)\s*(>=|<=|>|<|==|=|!=)\s*(\d+)",

        # salary greater than 40000
        r"(\w+)\s+(greater than|more than|above|over|exceeds)\s+(\d+)",

        # salary less than 40000
        r"(\w+)\s+(less than|below|under)\s+(\d+)"
    ]

    operator_map = {

        "greater than": ">",
        "more than": ">",
        "above": ">",
        "over": ">",
        "exceeds": ">",

        "less than": "<",
        "below": "<",
        "under": "<",

        "=": "=="
    }

    for pattern in patterns:

        match = re.search(pattern, prompt, re.I)

        if match:

            column = match.group(1)

            operator = match.group(2)

            value = int(match.group(3))

            operator = operator_map.get(operator, operator)

            pipeline.append({

                "id": generate_id(),

                "operation": "filter_rows",

                "input": "dataframe",

                "output": "dataframe",

                "column": column,

                "operator": operator,

                "value": value

            })

            break

    return pipeline
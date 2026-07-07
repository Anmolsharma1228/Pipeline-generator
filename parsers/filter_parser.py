import re
from parsers.read_parser import generate_id


def parse_filter(prompt):

    pipeline = []

    match = re.search(
        r"(?:where|filter)\s+(\w+)\s*(?:is\s+)?(greater\s+than|less\s+than|>=|<=|>|<|==|=|!=)?\s*(\d+)",
        prompt,
        re.I
    )

    if match:

        column = match.group(1)
        operator = (
            match.group(2) or "=="
        ).lower()

        value = int(
            match.group(3)
        )

        operator_map = {
            "greater than": ">",
            "less than": "<",
            "=": "=="
        }

        operator = operator_map.get(
            operator,
            operator
        )

        pipeline.append({
            "id": generate_id(),
            "operation": "filter_rows",
            "input": "dataframe",
            "output": "dataframe",
            "column": column,
            "operator": operator,
            "value": value
        })


    filter_match = re.search(
        r"keep\s+\w+\s+whose\s+(\w+)\s+is\s+greater\s+than\s+(\d+)",
        prompt,
        re.I
    )

    if filter_match:

        pipeline.append({

            "operation":"filter_rows",

            "column":filter_match.group(1),

            "operator":">",

            "value":int(filter_match.group(2))

        })


    select_match = re.search(
        r"keep\s+(\w+)\s+whose",
        prompt,
        re.I
    )

    if select_match:

        pipeline.append({

            "operation":"select_columns",

            "cols":[select_match.group(1)]

        })


    return pipeline
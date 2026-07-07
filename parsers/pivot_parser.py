import re
from parsers.read_parser import generate_id


def parse_pivot(prompt):

    pipeline=[]

    match = re.search(
        r"pivot\s+table\s+by\s+(\w+)",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation": "pivot_table",

            "input": "dataframe",

            "output": "dataframe",

            "index": match.group(1),

            "values": "salary",

            "aggfunc": "sum"
        })

    return pipeline
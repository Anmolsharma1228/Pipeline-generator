import re
from parsers.read_parser import generate_id


def parse_use_row_as_header(prompt):

    pipeline=[]

    match = re.search(
        r"use\s+row\s+(\d+)\s+as\s+header",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation": "use_row_as_header",

            "input": "dataframe",

            "output": "dataframe",

            "row": int(
                match.group(1)
            )
        })

    return pipeline
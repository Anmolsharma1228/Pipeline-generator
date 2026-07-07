import re
from parsers.read_parser import generate_id


def parse_transform(prompt):

    pipeline = []

    match = re.search(
        r"transpose\s+(?:data|table)?",
        prompt,
        re.I
    )

    if match:

        pipeline.append({
            "id": generate_id(),
            "operation": "transpose",
            "input": "dataframe",
            "output": "dataframe"
        })

    return pipeline
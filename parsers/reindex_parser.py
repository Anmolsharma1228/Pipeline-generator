import re
from parsers.read_parser import generate_id


def parse_reindex(prompt):

    pipeline = []

    match = re.search(
        r"reindex\s+columns",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation": "reindex_columns",

            "input": "dataframe",

            "output": "dataframe"
        })

    return pipeline
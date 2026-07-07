import re
from parsers.read_parser import generate_id


def parse_sql(prompt):

    pipeline = []

    match = re.search(
        r"write\s+to\s+sql",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "write_sql",

            "input":
            "dataframe",

            "connection":
            "sqlite:///database.db",

            "table":
            "employees",

            "output":
            "dataframe"
        })

    return pipeline   # ← MOVE OUTSIDE if



def parse_read_database(prompt):

    pipeline = []

    match = re.search(
        r"read\s+database",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "read_database",

            "output":
            "dataframe",

            "table":
            "employees"
        })

    return pipeline
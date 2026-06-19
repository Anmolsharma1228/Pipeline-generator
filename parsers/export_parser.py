import re
from parsers.read_parser import generate_id


def parse_export(prompt):

    pipeline=[]

    export_match = re.search(
        r"(?:save|export)?\s*([\w\-]+\.csv)",
        prompt,
        re.IGNORECASE
    )

    if export_match:

        filename = export_match.group(1)

        if not filename.lower().endswith(".xlsx"):

            pipeline.append({

                "id": generate_id(),

                "operation": "write_csv",

                "input": "dataframe",

                "path": filename

            })

    return pipeline
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

 # JSON
    json_match = re.search(
        r"convert\s+to\s+json",
        prompt,
        re.I
    )

    if json_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "to_json",

            "input": "dataframe",

            "path": "output.json"
        })

    # HTML
    html_match = re.search(
        r"convert\s+to\s+html",
        prompt,
        re.I
    )

    if html_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "to_html",

            "input": "dataframe",

            "path": "output.html"
        })



    return pipeline
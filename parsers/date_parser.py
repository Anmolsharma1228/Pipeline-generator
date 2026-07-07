import re
from parsers.read_parser import generate_id


def parse_date(prompt):

    pipeline = []
    
    # extract date parts
    extract_match = re.search(
        r"extract\s+date\s+parts\s+from\s+(\w+)",
        prompt,
        re.I
    )

    if extract_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "extract_date_parts",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            extract_match.group(1)
        })

     # add days
    add_match = re.search(
        r"add\s+(\d+)\s+days?\s+to\s+(\w+)",
        prompt,
        re.I
    )

    if add_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "add_days",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            add_match.group(2),

            "days":
            int(add_match.group(1))
        })

    # subtract days
    subtract_match = re.search(
        r"subtract\s+(\d+)\s+days?\s+from\s+(\w+)",
        prompt,
        re.I
    )

    if subtract_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "subtract_days",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            subtract_match.group(2),

            "days":
            int(
                subtract_match.group(1)
            )
        })

   # format date
    format_match = re.search(
        r"format\s+date\s+column",
        prompt,
        re.I
    )

    if format_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "format_date",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            "joining_date"
        })


 # date difference
    diff_match = re.search(
        r"date\s+difference\s+between\s+(\w+)\s+and\s+(\w+)",
        prompt,
        re.I
    )

    if diff_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "date_diff",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "start_col":
            diff_match.group(1),

            "end_col":
            diff_match.group(2),

            "result":
            "days_difference"
        })    

    return pipeline
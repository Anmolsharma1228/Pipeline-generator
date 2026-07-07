import re
from parsers.read_parser import generate_id


def parse_drop_rows(prompt):

    pipeline = []

    range_match = re.search(
        r"drop\s+rows?\s+(\d+)\s+to\s+(\d+)",
        prompt,
        re.I
    )

    if range_match:

        start = int(
            range_match.group(1)
        )

        end = int(
            range_match.group(2)
        )

        pipeline.append({

            "id": generate_id(),

            "operation":
            "drop_rows_by_index",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "rows":
            list(
                range(
                    start,
                    end + 1
                )
            )
        })

        return pipeline


    single_match = re.search(
        r"drop\s+rows?\s+([\d,\s]+)",
        prompt,
        re.I
    )

    if single_match:

        rows = [

            int(
                x.strip()
            )

            for x in single_match
            .group(1)
            .split(",")

        ]

        pipeline.append({

            "id": generate_id(),

            "operation":
            "drop_rows_by_index",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "rows":
            rows
        })

    return pipeline
import re
from parsers.read_parser import generate_id


def parse_column(prompt):

    pipeline=[]

    current_table="dataframe"

    # Skip if math operation
    if re.search(
        r"multiply|divide|percent",
        prompt,
        re.I
    ):
        return []

    # ==========================
    # ADD COLUMN
    # ==========================

    add_match = re.search(
        r"(?:add|create)\s+(?:new\s+)?column\s+(\w+)(?:\s+with\s+value\s+([^\s]+))?",
        prompt,
        re.I
    )

    if add_match:

        value=""

        if add_match.group(2):

            value=add_match.group(2)

        pipeline.append({

            "id":generate_id(),

            "operation":"add_column",

            "input":current_table,

            "output":current_table,

            "column":add_match.group(1),

            "value":value

        })

    # ==========================
    # RENAME COLUMN
    # ==========================

    rename_match = re.search(
        r"rename\s+(\w+)(?:\s+column)?\s+to\s+(\w+)",
        prompt,
        re.I
    )

    if rename_match:

        pipeline.append({

            "id":generate_id(),

            "operation":"rename_columns",

            "input":current_table,

            "output":current_table,

            "mapping":{

                rename_match.group(1):
                rename_match.group(2)

            }

        })


    # ==========================
    # SORT
    # ==========================

    sort_match = re.search(
        r"sort\s+by\s+(\w+)(?:\s+(ascending|descending))?",
        prompt,
        re.IGNORECASE
    )

    if sort_match:

        column = sort_match.group(1)

        order = sort_match.group(2)

        ascending = True

        if order:

            ascending = (
                order.lower()
                ==
                "ascending"
            )

        pipeline.append({

            "id": generate_id(),

            "operation": "sort_values",

            "input": current_table,

            "output": current_table,

            "by": column,

            "ascending": ascending

        })


    # ==========================
    # DROP COLUMN
    # ==========================

    drop_match = re.search(
        r"(?:remove|drop)\s+(\w+)\s+column",
        prompt,
        re.IGNORECASE
    )

    if drop_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "drop_columns",

            "input": current_table,

            "output": current_table,

            "cols": [

                drop_match.group(1)

            ]

        })

    # ==========================
    # SELECT COLUMNS
    # ==========================
    select_match = re.search(
        r"keep\s+only\s+(.+?)\s+columns",
        prompt,
        re.IGNORECASE
    )

    if select_match:
        cols_text = select_match.group(1)
        cols = re.split(
            r",|and",
            cols_text
        )

        cols = [
            c.strip()
            for c in cols
            if c.strip()
        ]

        pipeline.append({

            "id": generate_id(),
            "operation": "select_columns",
            "input": current_table,
            "output": current_table,
            "cols": cols

        })


    # ==========================
    # COMBINE COLUMNS
    # ==========================
    combine_match = re.search(
        r"combine\s+(\w+)\s+and\s+(\w+)",
        prompt,
        re.I
    )

    if combine_match:

        pipeline.append({
            "id": generate_id(),
            "operation": "combine_columns",
            "input": "dataframe",
            "output": "dataframe",

            "columns": [
                combine_match.group(1),
                combine_match.group(2)
            ],

            "new_column":
            f"{combine_match.group(1)}_{combine_match.group(2)}"
        })


    duplicate_match = re.search(
        r"(remove|drop)\s+duplicate[s]?\s+(\w+)\s+based\s+on\s+(\w+)",
        prompt,
        re.I
    )

    if duplicate_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "drop_duplicates",

            "input": "dataframe",

            "output": "dataframe",

            "subset": [duplicate_match.group(3)]

        })


    fill_match = re.search(
        r"replace\s+missing\s+(\w+)\s+with\s+(.+)",
        prompt,
        re.I
    )

    if fill_match:

        value = fill_match.group(2).strip()

        try:
            value = int(value)
        except:
            pass

        pipeline.append({

            "id": generate_id(),

            "operation": "fill_missing",

            "input": "dataframe",

            "output": "dataframe",

            "column": fill_match.group(1),

            "value": value

        })


    return pipeline
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
        r"(?:rename|change)\s+(\w+)\s+(?:to|as|into)\s+(\w+)",
        prompt,
        re.I
    )

    if rename_match:

        old = rename_match.group(1).lower()
        new = rename_match.group(2).lower()

        pipeline.append({
            "id": generate_id(),
            "operation": "rename_columns",
            "input": current_table,
            "output": current_table,
            "mapping": {
                old: new
            }
        })

        # Replace old column name in remaining prompt
        prompt = re.sub(
            rf"\b{re.escape(old)}\b",
            new,
            prompt,
            flags=re.I
        )


    # ==========================
    # SORT
    # ==========================

    sort_match = re.search(
        r"sort(?:\s+by)?\s+(\w+)(?:\s+(ascending|descending|asc|desc))?",
        prompt,
        re.I
    )

    if sort_match:

        column = sort_match.group(1)
        order = sort_match.group(2) or "ascending"
        ascending = order.lower() in ["ascending", "asc"]
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
        r"(?:keep\s+only|need\s+only|only\s+need|select|retain|include\s+only|show\s+only)\s+(.+?)(?=\s+(?:rename|convert|change|uppercase|lowercase|replace|trim|split|extract|sort|filter|drop|save|export|write|store|finally)\b|$)",
        prompt,
        re.I
    )

    if select_match:

        cols_text = select_match.group(1).lower()

        # Remove everything after sort/order if present
        cols_text = re.sub(
            r"\bsort\b.*",
            "",
            cols_text,
            flags=re.I
        )

        cols_text = re.sub(
            r"\border\b.*",
            "",
            cols_text,
            flags=re.I
        )

        # Remove filter expressions
        cols_text = re.sub(
            r"\b(?:greater\s+than|more\s+than|less\s+than|above|below|over|under)\s+\d+\b",
            "",
            cols_text,
            flags=re.I
        )

        cols_text = re.sub(
            r"[><=!]=?\s*\d+",
            "",
            cols_text
        )

        # Remove unnecessary keywords
        cols_text = re.sub(
            r"\b(column|columns|whose|where|then|with|having|save|export|write|store|download|finally|records|rows|employee|employees|ascending|descending|asc|desc|by)\b",
            "",
            cols_text,
            flags=re.I
        )

        cols_text = cols_text.replace(".", " ")
        cols_text = cols_text.replace("(", " ")
        cols_text = cols_text.replace(")", " ")

        cols_text = re.sub(
            r"\s+",
            " ",
            cols_text
        ).strip()

        # Split by comma or "and"
        raw_cols = re.split(
            r",|\band\b",
            cols_text
        )

        mapping = {
            "name": "fullname",
            "names": "fullname",
            "employee": "fullname",
            "employees": "fullname",
            "employee name": "fullname",
            "full name": "fullname",
            "fullname": "fullname",
            "city": "city",
            "cities": "city",
            "email": "email",
            "emails": "email",
            "department": "department",
            "dept": "department",
            "salary": "salary",
            "bonus": "bonus"
        }

        cols = []

        for col in raw_cols:

            col = col.strip()

            if not col:
                continue

            col = re.sub(r"\d+", "", col).strip()

            # Keep only the first word if extra words remain
            col = col.split()[0]

            col = mapping.get(col, col)

            if col not in cols:
                cols.append(col)

        if cols:

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

    

        #==========================
        # DROP DUPLICATES
        #=========================
    duplicate_match = re.search(
        r"(?:remove|drop)\s+duplicate(?:s)?(?:\s+rows)?(?:\s+based\s+on)?\s+(\w+)",
        prompt,
        re.I
    )

    if duplicate_match:

        column = duplicate_match.group(1).lower()

        mapping = {
            "cities": "city",
            "city": "city",
            "departments": "department",
            "department": "department",
            "emails": "email",
            "email": "email",
            "names": "fullname",
            "name": "fullname"
        }

        column = mapping.get(column, column)

        pipeline.append({

            "id": generate_id(),
            "operation": "drop_duplicates",
            "input": current_table,
            "output": current_table,
            "subset": [column]

        })

    # ==========================
    # FILL MISSING VALUES
    # ==========================

    fill_match = re.search(
        r"replace\s+missing\s+(\w+)(?:\s+values?)?\s+with\s+(.+?)(?=\s+(?:keep|select|retain|sort|save|export|write|store|download|$)|,)",
        prompt,
        re.I
    )

    if fill_match:

        value = fill_match.group(2).strip()

        # Convert numeric values
        if value.isdigit():
            value = int(value)

        elif re.fullmatch(r"\d+\.\d+", value):
            value = float(value)

        pipeline.append({

            "id": generate_id(),
            "operation": "fill_missing",
            "input": current_table,
            "output": current_table,
            "column": fill_match.group(1),
            "value": value

        })


    return pipeline
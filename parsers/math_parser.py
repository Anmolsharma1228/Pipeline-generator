import re
from parsers.read_parser import generate_id


def parse_math(prompt):

    pipeline=[]

    multiply_match = re.search(
        r"multiply\s+(\w+)\s+(?:and|by)\s+(\w+)",
        prompt,
        re.I
    )

    if multiply_match:

        col1 = multiply_match.group(1)
        col2 = multiply_match.group(2)

        result = f"{col1}_x_{col2}"

        result_match = re.search(
            r"create\s+new\s+column\s+(\w+)",
            prompt,
            re.I
        )

        if result_match:

            result = result_match.group(1)

        pipeline.append({

            "id":generate_id(),

            "operation":"multiply_columns",

            "col1":col1,

            "col2":col2,

            "result":result

        })

    add_match = re.search(
        r"add\s+(\d+)\s+to\s+(\w+)",
        prompt,
        re.I
    )

    if add_match:

        pipeline.append({

            "id":generate_id(),

            "operation":"add_constant",

            "col":add_match.group(2),

            "value":int(
                add_match.group(1)
            )

        })

    # ==========================
    # SUBTRACT CONSTANT
    # ==========================

    subtract_match = re.search(
        r"subtract\s+(\d+)\s+from\s+(\w+)",
        prompt,
        re.IGNORECASE
    )

    if subtract_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "subtract_constant",

            "col": subtract_match.group(2),

            "value": int(
                subtract_match.group(1)
            )

        })


    # ==========================
    # DIVIDE COLUMNS
    # ==========================

    divide_match = re.search(
        r"divide\s+(\w+)\s+by\s+(\w+)",
        prompt,
        re.IGNORECASE
    )

    if divide_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "divide_columns",

            "col1": divide_match.group(1),

            "col2": divide_match.group(2),

            "result": (
                f"{divide_match.group(1)}"
                "_per_"
                f"{divide_match.group(2)}"
            )

        })


    # ==========================
    # SUM
    # ==========================

    sum_match = re.search(
        r"sum\s+of\s+(\w+)",
        prompt,
        re.IGNORECASE
    )

    if sum_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "aggregate",

            "column": sum_match.group(1),

            "agg": "sum"

        })


    # ==========================
    # AVG
    # ==========================

    avg_match = re.search(
        r"(?:average|mean)\s+(?:of\s+)?(\w+)",
        prompt,
        re.IGNORECASE
    )

    if avg_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "aggregate",

            "column": avg_match.group(1),

            "agg": "mean"

        })


    # ==========================
    # MAX
    # ==========================

    max_match = re.search(
        r"max\s+(?:of\s+)?(\w+)",
        prompt,
        re.IGNORECASE
    )

    if max_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "aggregate",

            "column": max_match.group(1),

            "agg": "max"

        })

        # ==========================
        # GROUP AGGREGATE
        # ==========================
    aggregate_match = re.search(
        r"(aggregate|sum|total|average|mean|max|min)\s+(\w+)\s+by\s+(\w+)",
        prompt,
        re.I
    )

    if aggregate_match:

        operation = (
            aggregate_match
            .group(1)
            .lower()
        )

        agg_map = {

            "aggregate": "sum",
            "sum": "sum",
            "total": "sum",
            "average": "mean",
            "mean": "mean",
            "max": "max",
            "min": "min"

        }

        pipeline.append({

            "id": generate_id(),

            "operation": "aggregate",

            "input": "dataframe",

            "output": "dataframe",

            "column":
            aggregate_match.group(2),

            "groupby":
            aggregate_match.group(3),

            "agg":
            agg_map[operation]

        })


    return pipeline
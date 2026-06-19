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


    return pipeline
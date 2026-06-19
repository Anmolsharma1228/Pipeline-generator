import re
from parsers.read_parser import generate_id


def parse_string(prompt):

    pipeline=[]

    upper = re.search(
        r"uppercase",
        prompt,
        re.I
    )

    if upper:

        pipeline.append({

            "id":generate_id(),

            "operation":
            "uppercase"

        })

    return pipeline
import json

from parsers.read_parser import parse_read
from parsers.column_parser import parse_column
from parsers.math_parser import parse_math
from parsers.string_parser import parse_string
from parsers.export_parser import parse_export

from parsers.validation import (
    validate_pipeline
)


def generate_pipeline(prompt):

    pipeline=[]

    pipeline.extend(
        parse_read(prompt)
    )

    pipeline.extend(
        parse_column(prompt)
    )

    pipeline.extend(
        parse_math(prompt)
    )

    pipeline.extend(
        parse_string(prompt)
    )

    pipeline.extend(
        parse_export(prompt)
    )

    error = validate_pipeline(
        pipeline
    )

    if error:

        return json.dumps({
            "error": error
        })

    with open(
        "generated/pipeline.json",
        "w"
    ) as file:

        json.dump(
            pipeline,
            file,
            indent=4
        )

    return json.dumps(
        pipeline,
        indent=4
    )
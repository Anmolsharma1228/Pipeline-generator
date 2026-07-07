import json

from parsers.read_parser import parse_read
from parsers.column_parser import parse_column
from parsers.math_parser import parse_math
from parsers.string_parser import parse_string
from parsers.filter_parser import parse_filter
from parsers.export_parser import parse_export
from parsers.transform_parser import parse_transform
from parsers.reindex_parser import parse_reindex
from parsers.drop_parser import parse_drop_rows
from parsers.header_parser import parse_use_row_as_header
from parsers.pivot_parser import parse_pivot
from parsers.date_parser import parse_date
from parsers.sql_parser import (
    parse_sql, parse_read_database
)

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
    parse_filter(prompt)
   )

    pipeline.extend(
         parse_transform(prompt)
        )
    
    pipeline.extend(
     parse_pivot(prompt)
    )

    pipeline.extend(
     parse_reindex(prompt)
   )
    
    pipeline.extend(
     parse_use_row_as_header(prompt)
    )

    pipeline.extend(
     parse_drop_rows(prompt)
   )
    
    pipeline.extend(
    parse_date(prompt)
    )

    pipeline.extend(
    parse_sql(prompt)
   )

    pipeline.extend(
    parse_read_database(prompt)
    )

    pipeline.extend(
        parse_export(prompt)
    )

    print("PIPELINE:", pipeline)

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
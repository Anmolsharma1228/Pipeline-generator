import json

from llm.llm_parser import normalize_prompt

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
    parse_sql,
    parse_read_database
)
from parsers.validation import validate_pipeline


def remove_duplicate_steps(pipeline):

    unique = []
    seen = set()

    for step in pipeline:

        key = (
            step["operation"],
            str(step)
        )

        if key not in seen:
            seen.add(key)
            unique.append(step)

    return unique




def reorder_pipeline(pipeline):

    PRIORITY = {

        # READ
        "read_csv": 1,
        "read_excel_any": 1,
        "read_database": 1,

        # CLEANING
        "drop_duplicates": 5,
        "fill_missing": 6,

        # FILTER
        "filter_rows": 10,

        # SELECT FIRST
        "select_columns": 15,

        # THEN RENAME
        "rename_columns": 20,

        # STRING
        "uppercase": 25,
        "lowercase": 26,
        "replace_str": 27,
        "trim_whitespace": 28,
        "split_column": 29,
        "extract_pattern": 30,

        # MATH
        "add_constant": 35,
        "subtract_constant": 36,
        "multiply_columns": 37,
        "divide_columns": 38,

        # COLUMN
        "combine_columns": 40,
        "add_column": 41,
        "drop_columns": 42,

        # SORT
        "sort_values": 60,

        # OTHER
        "transpose": 80,
        "pivot_table": 81,
        "reindex_columns": 82,
        "use_row_as_header": 83,
        "drop_rows_by_index": 84,

        # DATE
        "extract_date_parts": 90,
        "add_days": 91,
        "subtract_days": 92,
        "format_date": 93,
        "date_diff": 94,

        # DATABASE
        "write_sql": 98,

        # EXPORT
        "write_csv": 100,
        "to_json": 101,
        "to_html": 102
    }

    return sorted(
        pipeline,
        key=lambda step: PRIORITY.get(
            step["operation"],
            999
        )
    )



def build_regex_pipeline(prompt):

    pipeline = []

    pipeline.extend(parse_read(prompt))
    pipeline.extend(parse_column(prompt))
    pipeline.extend(parse_math(prompt))
    pipeline.extend(parse_string(prompt))
    pipeline.extend(parse_filter(prompt))
    pipeline.extend(parse_transform(prompt))
    pipeline.extend(parse_pivot(prompt))
    pipeline.extend(parse_reindex(prompt))
    pipeline.extend(parse_use_row_as_header(prompt))
    pipeline.extend(parse_drop_rows(prompt))
    pipeline.extend(parse_date(prompt))
    pipeline.extend(parse_sql(prompt))
    pipeline.extend(parse_read_database(prompt))
    pipeline.extend(parse_export(prompt))

    return pipeline


def generate_pipeline(prompt):

    print("=" * 60)
    print("Original Prompt")
    print(prompt)

    try:

        normalized_prompt = normalize_prompt(prompt)

        print("=" * 60)
        print("Normalized Prompt")
        print(normalized_prompt)

    except Exception as e:

        print("LLM Error:", e)

        normalized_prompt = prompt

    # Build pipeline (ALWAYS)
    pipeline = build_regex_pipeline(normalized_prompt)

    # Remove duplicate steps
    pipeline = remove_duplicate_steps(pipeline)

    # Reorder steps
    pipeline = reorder_pipeline(pipeline)

    

    print("=" * 60)
    print("Pipeline")
    print(pipeline)

    error = validate_pipeline(pipeline)

    if error:
        return json.dumps(
            {
                "error": error
            },
            indent=4
        )

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
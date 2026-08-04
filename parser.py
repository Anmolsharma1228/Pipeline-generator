import json
import os

# Works whether llm_parser.py lives in a llm/ subfolder (original
# project layout) or flat next to this file (e.g. after uploading
# individual files somewhere new) - tries the package form first.
try:
    from llm.llm_parser import normalize_prompt
except ModuleNotFoundError:
    from llm.llm_parser import normalize_prompt

from column_resolver import remap_pipeline_columns, _OP_COLUMN_SPEC

import re
import time
import random


def generate_id():

    return int(
        f"{int(time.time()*1000)}{random.randint(10,99)}"
    )


def parse_read(prompt):

    pipeline = []
    current_table = "dataframe"

    number_words = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "ten": 10,
        "twenty": 20,
        "fifty": 50
    }

    read_match = re.search(
        r"(?:read|open|load|import)\s+([\w\-.]+)(?:\.(csv|xlsx|json)|\s+(csv|excel|xlsx|json))",
        prompt,
        re.I
    )

    if read_match:

        filename = read_match.group(1)

        # Extension can come from either:
        # Read employee.xlsx
        # or
        # Read employee excel
        ext = read_match.group(2) or read_match.group(3)

        ext = ext.lower()

        if ext == "excel":
            ext = "xlsx"

        # If user wrote "Read employee excel"
        if "." not in filename:
            filename = f"{filename}.{ext}"

        read_op = {

            "id": generate_id(),

            "operation": {
                "csv": "read_csv",
                "xlsx": "read_excel_any",
                "json": "read_json"
            }[ext],

            "output": current_table,

            "path": filename

        }

        # ==========================
        # SHEET SUPPORT
        # ==========================

        sheet_match = re.search(
            r"(?:from\s+)?(sheet\s*\d+)",
            prompt,
            re.I
        )

        if sheet_match:

            read_op["sheet_name"] = (
                sheet_match
                .group(1)
                .replace(" ", "")
                .title()
            )

        else:

            read_op["sheet_name"] = "Sheet1"

        # ==========================
        # ROW PREVIEW
        # ==========================

        rows_match = re.search(
            r"(?:first|top)\s+(\w+)\s+(?:rows|records)",
            prompt,
            re.I
        )

        if rows_match:

            value = rows_match.group(1)

            if value.isdigit():

                read_op["rows"] = int(value)

            elif value.lower() in number_words:

                read_op["rows"] = number_words[value.lower()]

            read_op["preview"] = True

        # Add step with prompt position
        add_step(
            pipeline,
            read_op["operation"],
            position=read_match.start(),
            **{k: v for k, v in read_op.items() if k != "operation"}
        )

    return pipeline



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

        add_step(
         pipeline,
         "add_column",
         position=add_match.start(),
         input=current_table,
         output=current_table,
         column=add_match.group(1),
         value=value
         )


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

        add_step(
         pipeline,
         "rename_columns",
         position=rename_match.start(),
         input=current_table,
         output=current_table,
         mapping={
         old: new
         })



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

        add_step(
            pipeline,
            "sort_values",
            position=sort_match.start(),
            input=current_table,
            output=current_table,
            by=column,
            ascending=ascending
            )



    # ==========================
    # DROP COLUMN
    # ==========================

    drop_match = re.search(
        r"(?:remove|drop)\s+(\w+)\s+column",
        prompt,
        re.IGNORECASE
    )

    if drop_match:

       add_step(
        pipeline,
        "drop_columns",
        position=drop_match.start(),
        input=current_table,
        output=current_table,
        cols=[drop_match.group(1)]
        )

    # ==========================
    # SELECT COLUMNS
    # ==========================

    select_match = re.search(
        r"(?:keep\s+only|keep\s+just|just\s+keep|need\s+only|only\s+need|"
        r"i\s+just\s+need|just\s+need|"
        r"select|retain|include\s+only|show\s+only|display\s+only|"
        r"i\s+want\s+only|only\s+give(?:\s+me)?|give\s+only|"
        r"(?:just\s+)?(?:give|gimme)(?:\s+me)?(?:\s+only)?)\s+(.+?)"
        r"(?=\s+(?:rename|convert|change|uppercase|lowercase|replace|trim|split|extract|sort|filter|drop|save|export|write|store|finally|then|also|and\s+then|now|date\s+difference|extract\s+date|add\s+\d+\s+days?|subtract\s+\d+\s+days?|format\s+date)\b|$)",
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

        mapping = {}

        cols = []

        for col in raw_cols:

            col = col.strip()

            if not col:
                continue

            col = re.sub(r"\d+", "", col).strip()

            if not col:
                continue

            # If more than one space-separated word remains, it's
            # usually several column names typed without a comma or
            # "and" between them (e.g. "fullname diagnosis and X").
            # Treat each word as its own candidate column instead of
            # merging them into one bogus name or dropping any of them.
            _STOPWORDS = {
                "then", "also", "now", "get", "and",
                "the", "a", "an", "please", "next"
            }

            for word in col.split():

                word = normalize_col(word)

                if word and word not in _STOPWORDS and word not in cols:
                    cols.append(word)

        if cols:

            add_step(
             pipeline,
             "select_columns",
             position=select_match.start(),
             input=current_table,
             output=current_table,
             cols=cols
             )
            


    # ==========================
    # COMBINE COLUMNS
    # ==========================
    combine_match = re.search(
        r"combine\s+(\w+)\s+and\s+(\w+)",
        prompt,
        re.I
    )

    if combine_match:

        add_step(
         pipeline,
         "combine_columns",
         position=combine_match.start(),
         input="dataframe",
         output="dataframe",
         columns=[
             combine_match.group(1),
             combine_match.group(2)
         ],
         new_column=f"{combine_match.group(1)}_{combine_match.group(2)}"
         )

    

        #==========================
        # DROP DUPLICATES
        #=========================
    duplicate_match = re.search(
       r"(?:remove|drop)\s+duplicate(?:s)?(?:\s+rows)?(?:\s+based\s+on|using)?\s+(.+?)(?=\s+(?:then|after|if|replace|fill|keep|select|rename|sort|save|export|write|finally|$))",
       prompt,
    re.I
    )

    if duplicate_match:

        column = normalize_col(duplicate_match.group(1))

        add_step(
         pipeline,
         "drop_duplicates",
         position=duplicate_match.start(),
         input=current_table,
         output=current_table,
         subset=[column]
         )



    # ==========================
    # FILL MISSING VALUES
    # ==========================

    fill_patterns = [

        # replace missing salary with 0
       r"replace\s+missing\s+(.+?)(?:\s+values?)?\s+with\s+([^\s]+)",

        # salary blank put 0
       r"(.+?)\s+blank\s+put\s+([^\s]+)",

        # salary blank replace with 0
        r"(.+?)\s+blank\s+replace\s+with\s+([^\s]+)",

        # fill missing salary with 0
        r"fill\s+missing\s+(.+?)\s+with\s+([^\s]+)"
    ]

    for pattern in fill_patterns:

        for fill_match in re.finditer(pattern, prompt, re.I):

            value = fill_match.group(2).strip()

            if value.isdigit():
                value = int(value)

            elif re.fullmatch(r"\d+\.\d+", value):
                value = float(value)

            add_step(
                pipeline,
                "fill_missing",
                position=fill_match.start(),
                input=current_table,
                output=current_table,
                column=normalize_col(fill_match.group(1)),
                value=value
                )

    return pipeline



def parse_math(prompt):

    pipeline = []
    current_table = "dataframe"

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

        add_step(
            pipeline,
            "multiply_columns",
            position=multiply_match.start(),
            input=current_table,
            output=current_table,
            col1=col1,
            col2=col2,
            result=result
        )

    add_match = re.search(
        r"add\s+(\d+)\s+to\s+(\w+)",
        prompt,
        re.I
    )

    if add_match:

        add_step(
            pipeline,
            "add_constant",
            position=add_match.start(),
            input=current_table,
            output=current_table,
            col=add_match.group(2),
            value=int(add_match.group(1))
        )

    # ==========================
    # SUBTRACT CONSTANT
    # ==========================

    subtract_match = re.search(
        r"subtract\s+(\d+)\s+from\s+(\w+)",
        prompt,
        re.IGNORECASE
    )

    if subtract_match:

        add_step(
            pipeline,
            "subtract_constant",
            position=subtract_match.start(),
            input=current_table,
            output=current_table,
            col=subtract_match.group(2),
            value=int(subtract_match.group(1))
        )

    # ==========================
    # DIVIDE COLUMNS
    # ==========================

    divide_match = re.search(
        r"divide\s+(\w+)\s+by\s+(\w+)",
        prompt,
        re.IGNORECASE
    )

    if divide_match:

        add_step(
            pipeline,
            "divide_columns",
            position=divide_match.start(),
            input=current_table,
            output=current_table,
            col1=divide_match.group(1),
            col2=divide_match.group(2),
            result=(
                f"{divide_match.group(1)}"
                "_per_"
                f"{divide_match.group(2)}"
            )
        )

    # ==========================
    # SUM
    # ==========================

    sum_match = re.search(
        r"sum\s+of\s+(\w+)",
        prompt,
        re.IGNORECASE
    )

    if sum_match:

        add_step(
            pipeline,
            "aggregate",
            position=sum_match.start(),
            input=current_table,
            output=current_table,
            column=sum_match.group(1),
            agg="sum"
        )

    # ==========================
    # AVG
    # ==========================

    avg_match = re.search(
        r"(?:average|mean)\s+(?:of\s+)?(\w+)",
        prompt,
        re.IGNORECASE
    )

    if avg_match:

        add_step(
            pipeline,
            "aggregate",
            position=avg_match.start(),
            input=current_table,
            output=current_table,
            column=avg_match.group(1),
            agg="mean"
        )

    # ==========================
    # MAX
    # ==========================

    max_match = re.search(
        r"max\s+(?:of\s+)?(\w+)",
        prompt,
        re.IGNORECASE
    )

    if max_match:

        add_step(
            pipeline,
            "aggregate",
            position=max_match.start(),
            input=current_table,
            output=current_table,
            column=max_match.group(1),
            agg="max"
        )

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

        add_step(
            pipeline,
            "aggregate",
            position=aggregate_match.start(),
            input=current_table,
            output=current_table,
            column=aggregate_match.group(2),
            groupby=aggregate_match.group(3),
            agg=agg_map[operation]
        )

    return pipeline


def add_step(pipeline, operation, position=None, **kwargs):
    """
    Add a pipeline step and remember where it appeared
    in the user's prompt.
    """

    step = {
        "id": generate_id(),
        "operation": operation,
        "__pos": position if position is not None else 999999
    }

    step.update(kwargs)

    pipeline.append(step)


def find_match(prompt, patterns):

    for pattern in patterns:

        m = re.search(
            pattern,
            prompt,
            re.I
        )

        if m:
            return m

    return None


def normalize_col(col):

    col = col.strip().lower()
    col = re.sub(r"\s+", "_", col)

    return col

def parse_columns(text):
    """
    Convert:
    city
    city, department
    city and department

    into

    ["city", "department"]
    """

    text = text.replace(" and ", ",")

    columns = [
        normalize_col(col.strip())
        for col in text.split(",")
        if col.strip()
    ]

    return columns


def parse_string(prompt):

    pipeline = []

    if not isinstance(prompt, str):
        return pipeline
    
    prompt = prompt.lower().strip()

    NEXT_OP = (
            r"(?=\s+(?:"
            r"replace|uppercase|lowercase|rename|sort|trim|split|extract|"
            r"save|export|write|filter|keep|select|drop|"
            r"subtract|add|multiply|divide|compute|date|finally|$))"
        )

    try:

        # ==========================
        # UPPERCASE
        # ==========================

        upper_patterns = [
          r"(?:convert|change)\s+(.+?)\s+to\s+uppercase",
          r"(?:convert|change)\s+(.+?)\s+uppercase",
          r"\b(.+?)\s+(?:convert|change)\s+uppercase\b",
          r"(.+?)\s+should\s+be\s+uppercase",
          r"make\s+(.+?)\s+uppercase",
          r"\buppercase\s+(.+?)(?=\s+(?:lowercase|replace|rename|sort|trim|split|extract|save|export|write|$))"
        ]

        for pattern in upper_patterns:

            for match in re.finditer(pattern, prompt, re.I):

                col = normalize_col(match.group(1))

                add_step(
                    pipeline,
                    "uppercase",
                    position=match.start(),
                    input="dataframe",
                    output="dataframe",
                    col=col,
                    output_col=col
                    )



        # ==========================
        # LOWERCASE
        # ==========================

        lower_patterns = [
           r"(?:convert|change)\s+(\w+)\s+to\s+lowercase",
           r"(?:convert|change)\s+(\w+)\s+lowercase",
           r"\b(\w+)\s+(?:convert|change)\s+lowercase\b",
           r"(\w+)\s+should\s+be\s+lowercase",
           r"make\s+(\w+)\s+lowercase",
           r"\blowercase\s+(\w+)"
        ]

        for pattern in lower_patterns:

            for match in re.finditer(pattern, prompt, re.I):

                col = normalize_col(match.group(1))

                add_step(
                  pipeline,
                  "lowercase",
                  position=match.start(),
                  input="dataframe",
                  output="dataframe",
                  col=col,
                  output_col=col
                  )


        # ==========================
        # REPLACE
        # ==========================

        # --------------------------
        # Column specific replacement
        # Example:
        # replace Delhi with Mumbai in city
        # --------------------------
        for match in re.finditer(
            rf"replace\s+(.+?)\s+with\s+(.+?)\s+in\s+(\w+){NEXT_OP}",
            prompt,
            re.I
        ):

            if match.group(1).lower() == "missing":
                continue

            add_step(
                pipeline,
                "replace_str",
                position=match.start(),
                input="dataframe",
                output="dataframe",
                old=match.group(1).strip(),
                new=match.group(2).strip(),
                col=normalize_col(match.group(3))
                )

            
        # --------------------------
        # Global replacement
        # --------------------------
        for match in re.finditer(
           rf"replace\s+(?!missing\b)(.+?)\s+with\s+(.+?){NEXT_OP}",
           prompt,
           re.I
        ):

            old_value = match.group(1).strip()
            new_value = match.group(2).strip()

            # Skip if this is actually a column-specific replace
            # Example: replace mumbai with bombay in city
            if re.search(r"\bin\s+\w+$", new_value, re.I):
                continue

            step = {
                "input": "dataframe",
                "output": "dataframe",
                "old": old_value,
                "new": new_value
            }

            add_step(
                pipeline,
                "replace_str",
                position=match.start(),
                **step
            )


        # ==========================
        # TRIM
        # ==========================

        trim = re.search(
            r"trim\s+whitespace(?:\s+from\s+(\w+))?",
            prompt,
            re.I
        )

        if trim:

            col = trim.group(1)

            if col:

                add_step(
                 pipeline,
                 "trim_whitespace",
                 position=trim.start(),
                 input="dataframe",
                 output="dataframe",
                 col=col,
                 output_col=col
                 )

        # ==========================
        # SPLIT
        # ==========================

        split = re.search(
            r"split\s+(\w+)(?=\s+(?:extract|save|export|uppercase|lowercase|replace|trim|$))",
            prompt,
            re.I
        )

        if split:

          add_step(
           pipeline,
           "split_column",
           position=split.start(),
           input="dataframe",
           output="dataframe",
           col=split.group(1),
           separator=" "
            )


        # ==========================
        # EXTRACT
        # ==========================

        extract = find_match(
            prompt,
            [
                r"extract\s+pattern\s+from\s+(\w+)",
                r"extract\s+email\s+from\s+(\w+)",
               r"extract\s+(\w+)(?=\s+(?:save|export|uppercase|lowercase|replace|split|trim|$))"
            ]
        )

        if extract:

            col = extract.group(1)

            add_step(
              pipeline,
              "extract_pattern",
              position=extract.start(),
              input="dataframe",
              output="dataframe",
              col=col,
              pattern=r"([^@]+)",
              output_col=f"{col}_pattern"
               )

    except Exception as e:

        print(
            "Parser Error:",
            str(e)
        )

        return []

    return pipeline



def parse_filter(prompt):

    pipeline = []

    prompt = prompt.lower()

    patterns = [

        # Filter salary > 40000
        r"filter\s+(\w+)\s*(>=|<=|>|<|==|=|!=)\s*(\d+)",

        # where salary > 40000
        r"where\s+(\w+)\s*(>=|<=|>|<|==|=|!=)\s*(\d+)",

        # salary greater than 40000
        r"(\w+)\s+(greater than|more than|above|over|exceeds)\s+(\d+)",

        # salary less than 40000
        r"(\w+)\s+(less than|below|under)\s+(\d+)"
    ]

    operator_map = {

        "greater than": ">",
        "more than": ">",
        "above": ">",
        "over": ">",
        "exceeds": ">",

        "less than": "<",
        "below": "<",
        "under": "<",

        "=": "=="
    }

    for pattern in patterns:

        match = re.search(pattern, prompt, re.I)

        if match:

            column = match.group(1)

            operator = match.group(2)

            value = int(match.group(3))

            operator = operator_map.get(operator, operator)

            add_step(
                pipeline,
                "filter_rows",
                position=match.start(),
                input="dataframe",
                output="dataframe",
                column=column,
                operator=operator,
                value=value
            )

            break

    return pipeline



def parse_export(prompt):

    pipeline=[]
    current_table = "dataframe"

    export_match = re.search(
        r"(?:save|export)?\s*([\w\-]+\.csv)",
        prompt,
        re.IGNORECASE
    )

    if export_match:

        filename = export_match.group(1)

        if not filename.lower().endswith(".xlsx"):

                add_step(
                    pipeline,
                    "write_csv",
                    position=export_match.start(),
                    input=current_table,
                    path=filename
                    )

 # JSON
    json_match = re.search(
        r"convert\s+to\s+json",
        prompt,
        re.I
    )

    if json_match:

        add_step(
            pipeline,
            "to_json",
            position=json_match.start(),
            input="dataframe",
            path="output.json"
        )

    # HTML
    html_match = re.search(
        r"convert\s+to\s+html",
        prompt,
        re.I
    )

    if html_match:

        add_step(
            pipeline,
            "to_html",
            position=html_match.start(),
            input="dataframe",
            path="output.html"
        )


    return pipeline


def parse_transform(prompt):

    pipeline = []

    match = re.search(
        r"transpose\s+(?:data|table)?",
        prompt,
        re.I
    )

    if match:

        add_step(
            pipeline,
            "transpose",
            position=match.start(),
            input="dataframe",
            output="dataframe"
        )

    return pipeline


def parse_reindex(prompt):

    pipeline = []

    match = re.search(
        r"reindex\s+columns",
        prompt,
        re.I
    )

    if match:

        add_step(
            pipeline,
            "reindex_columns",
            position=match.start(),
            input="dataframe",
            output="dataframe"
        )

    return pipeline



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

        add_step(
            pipeline,
            "drop_rows_by_index",
            position=range_match.start(),
            input="dataframe",
            output="dataframe",
            rows=list(range(start, end + 1))
        )

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

        add_step(
            pipeline,
            "drop_rows_by_index",
            position=single_match.start(),
            input="dataframe",
            output="dataframe",
            rows=rows
        )

    return pipeline


def parse_use_row_as_header(prompt):

    pipeline=[]

    match = re.search(
        r"use\s+row\s+(\d+)\s+as\s+header",
        prompt,
        re.I
    )

    if match:

        add_step(
            pipeline,
            "use_row_as_header",
            position=match.start(),
            input="dataframe",
            output="dataframe",
            row=int(match.group(1))
        )

    return pipeline


def parse_pivot(prompt):

    pipeline=[]

    match = re.search(
        r"pivot\s+table\s+by\s+(\w+)"
        r"(?:\s+values?\s+(\w+))?"
        r"(?:\s+(?:aggfunc|using|agg)\s+(\w+))?",
        prompt,
        re.I
    )

    if match:

        index_col = match.group(1)

        # values column: use whatever the user named; if they didn't
        # name one, fall back to the index column itself rather than
        # guessing an unrelated business field.
        values_col = match.group(2) or index_col

        agg_map = {
            "sum": "sum", "total": "sum",
            "average": "mean", "mean": "mean",
            "max": "max", "min": "min", "count": "count"
        }

        aggfunc = agg_map.get(
            (match.group(3) or "sum").lower(),
            "sum"
        )

        add_step(
            pipeline,
            "pivot_table",
            position=match.start(),
            input="dataframe",
            output="dataframe",
            index=index_col,
            values=values_col,
            aggfunc=aggfunc
        )

    return pipeline



def parse_date(prompt):

    pipeline = []
    current_table = "dataframe"

    # -----------------------------
    # Extract date parts
    # -----------------------------
    extract_match = re.search(
        r"extract\s+date\s+parts\s+from\s+(\w+)",
        prompt,
        re.I
    )

    if extract_match:

        add_step(
            pipeline,
            "extract_date_parts",
            position=extract_match.start(),
            input=current_table,
            output=current_table,
            column=extract_match.group(1)
        )

    # -----------------------------
    # Add days
    # -----------------------------
    add_match = re.search(
        r"add\s+(\d+)\s+days?\s+to\s+(\w+)",
        prompt,
        re.I
    )

    if add_match:

        add_step(
            pipeline,
            "add_days",
            position=add_match.start(),
            input=current_table,
            output=current_table,
            column=add_match.group(2),
            days=int(add_match.group(1))
        )

    # -----------------------------
    # Subtract days
    # -----------------------------
    subtract_match = re.search(
        r"subtract\s+(\d+)\s+days?\s+from\s+(\w+)",
        prompt,
        re.I
    )

    if subtract_match:

        add_step(
            pipeline,
            "subtract_days",
            position=subtract_match.start(),
            input=current_table,
            output=current_table,
            column=subtract_match.group(2),
            days=int(subtract_match.group(1))
        )

    # -----------------------------
    # Format date
    # -----------------------------
    format_match = re.search(
        r"format\s+(?:date\s+column\s+(\w+)|(\w+)\s+as\s+date|(\w+)\s+date\s+column)",
        prompt,
        re.I
    )

    if format_match:

        date_col = (
            format_match.group(1)
            or format_match.group(2)
            or format_match.group(3)
        )

        add_step(
            pipeline,
            "format_date",
            position=format_match.start(),
            input=current_table,
            output=current_table,
            column=date_col
        )

    # -----------------------------
    # Date Difference
    # Supports:
    # date difference between start and end
    # date difference between start and end as delivery_days
    # date difference between start and end into delivery_days
    # date difference between start and end called delivery_days
    # -----------------------------
    diff_match = re.search(
        r"""
        date\s+difference\s+between\s+
        (\w+)\s+
        and\s+
        (\w+)
        (?:\s+
            (?:as|into|called|named)
            \s+
            (\w+)
        )?
        """,
        prompt,
        re.I | re.X
    )

    if diff_match:

        result_col = diff_match.group(3) or "days_difference"

        add_step(
            pipeline,
            "date_diff",
            position=diff_match.start(),
            input=current_table,
            output=current_table,
            start_col=diff_match.group(1),
            end_col=diff_match.group(2),
            result=result_col
        )

    return pipeline


def parse_sql(prompt):

    pipeline = []

    match = re.search(
        r"write\s+to\s+sql(?:\s+table\s+(\w+))?",
        prompt,
        re.I
    )

    if match:

        table = match.group(1)

        if not table:
            # No table name given - fall back to the source
            # filename (e.g. "sales.xlsx" -> "sales") rather than
            # guessing an unrelated business table name.
            file_match = re.search(
                r"([\w\-]+)\.(csv|xlsx|json)",
                prompt,
                re.I
            )
            table = file_match.group(1) if file_match else "output_table"

        add_step(
            pipeline,
            "write_sql",
            position=match.start(),
            input="dataframe",
            connection="sqlite:///database.db",
            table=table,
            output="dataframe"
        )

    return pipeline



def parse_read_database(prompt):

    pipeline = []

    match = re.search(
        r"read\s+database(?:\s+table\s+(\w+))?",
        prompt,
        re.I
    )

    if match:

        table = match.group(1) or "source_table"

        add_step(
            pipeline,
            "read_database",
            position=match.start(),
            output="dataframe",
            table=table
        )

    return pipeline


def validate_pipeline(pipeline):

    if not pipeline:
        return "No valid operations found!"

    read_ops = {
        "read_csv",
        "read_excel_any",
        "read_json",
        "read_database"
    }

    has_read = any(
        step["operation"] in read_ops
        for step in pipeline
    )

    if not has_read:
        return "Please specify an input source."

    return None



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
        "filter_rows": 48,

        # RENAME
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

        # DATE - must run BEFORE select_columns/drop_columns, since
        # these read source columns (e.g. admitdate, dischargedate)
        # that the user's final column selection may not keep.
        "extract_date_parts": 39,
        "add_days": 40,
        "subtract_days": 41,
        "format_date": 42,
        "date_diff": 43,

        # COLUMN - runs AFTER all derived-value computations above,
        # so it's safe to narrow down to just the requested output
        # columns without breaking a later step that needed the
        # original source columns.
        "combine_columns": 44,
        "add_column": 45,
        "drop_columns": 46,
        "select_columns": 50,

        # SORT
        "sort_values": 49,

        # OTHER
        "transpose": 80,
        "pivot_table": 81,
        "reindex_columns": 82,
        "use_row_as_header": 83,
        "drop_rows_by_index": 84,

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



def _step_requires_and_produces(step):
    """
    Return (requires, produces) sets of column names for a step,
    reusing the same operation spec used for column resolution
    (_OP_COLUMN_SPEC) so this logic never drifts out of sync with it.
    """

    op = step.get("operation")
    requires = set()
    produces = set()

    if op == "rename_columns" and "mapping" in step:
        for old, new in step["mapping"].items():
            if isinstance(old, str):
                requires.add(old)
            if isinstance(new, str):
                produces.add(new)
        return requires, produces

    spec = _OP_COLUMN_SPEC.get(op)

    if not spec:
        return requires, produces

    for key in spec.get("resolve", []):
        val = step.get(key)
        if isinstance(val, str):
            requires.add(val)

    for key in spec.get("resolve_list", []):
        val = step.get(key)
        if isinstance(val, list):
            requires.update(v for v in val if isinstance(v, str))

    for key in spec.get("define", []):
        val = step.get(key)
        if isinstance(val, str):
            produces.add(val)

    return requires, produces


def enforce_dependency_order(pipeline):
    """
    Move any step that depends on a column created later.
    Export operations are always kept at the end.
    """

    EXPORT_OPS = {
        "write_csv",
        "write_sql",
        "to_json",
        "to_html"
    }

    changed = True

    while changed:

        changed = False

        for i in range(len(pipeline)):

            step = pipeline[i]

            requires, _ = _step_requires_and_produces(step)

            if not requires:
                continue

            producer = None

            for j in range(i + 1, len(pipeline)):

                _, produces = _step_requires_and_produces(pipeline[j])

                if requires.intersection(produces):
                    producer = j

            if producer is not None:

                item = pipeline.pop(i)

                if producer > i:
                    producer -= 1

                pipeline.insert(producer + 1, item)

                changed = True
                break

    exports = [
        s for s in pipeline
        if s.get("operation") in EXPORT_OPS
    ]

    others = [
        s for s in pipeline
        if s.get("operation") not in EXPORT_OPS
    ]

    return others + exports


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


def generate_pipeline(prompt, file_path=None):

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

    pipeline.sort(key=lambda step: step.get("__pos", 999999))
    pipeline = reorder_pipeline(pipeline)
    pipeline = enforce_dependency_order(pipeline)

    for step in pipeline:
        step.pop("__pos", None)

    # Resolve/correct column references against the REAL uploaded
    # file's headers, whatever the schema is. If no file is
    # available or reading fails, this is a safe no-op - it never
    # raises, so the user never sees an error from this step.
    if file_path:
        pipeline = remap_pipeline_columns(pipeline, file_path)

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

    os.makedirs("generated", exist_ok=True)

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
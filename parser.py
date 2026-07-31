import json
from llm.llm_parser import normalize_prompt

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

        "one": 1,
        "two": 2,
        "three": 3,
        "five": 5,
        "ten": 10,
        "twenty": 20,
        "fifty": 50

    }

    read_match = re.search(
        r"([\w\-.]+\.(csv|xlsx|json))",
        prompt,
        re.I
    )

    if read_match:

        read_op = {

            "id": generate_id(),

            "operation": {

                "csv": "read_csv",
                "xlsx": "read_excel_any",
                "json": "read_json"

            }[
                read_match.group(2)
            ],

            "output": current_table,

            "path": read_match.group(1)

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
         # Default sheet if user doesn't mention one
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

                read_op["rows"] = number_words[
                    value.lower()
                ]

            read_op["preview"] = True

        pipeline.append(
            read_op
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

    for fill_match in re.finditer(
         r"replace\s+missing\s+(\w+)(?:\s+values?)?\s+with\s+(.+?)(?=\s+(?:replace|keep|select|rename|sort|save|export|write|finally|$))",
         prompt,
         re.I
    ):

        value = fill_match.group(2).strip()

        if value.isdigit():
            value = int(value)

        elif re.fullmatch(r"\d+\.\d+", value):
            value = float(value)

        pipeline.append({

            "id": generate_id(),

            "operation": "fill_missing",

            "input": current_table,

            "output": current_table,

            "column": fill_match.group(1).lower(),

            "value": value

        })

    return pipeline



def parse_date(prompt):

    pipeline = []
    
    # extract date parts
    extract_match = re.search(
        r"extract\s+date\s+parts\s+from\s+(\w+)",
        prompt,
        re.I
    )

    if extract_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "extract_date_parts",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            extract_match.group(1)
        })

     # add days
    add_match = re.search(
        r"add\s+(\d+)\s+days?\s+to\s+(\w+)",
        prompt,
        re.I
    )

    if add_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "add_days",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            add_match.group(2),

            "days":
            int(add_match.group(1))
        })

    # subtract days
    subtract_match = re.search(
        r"subtract\s+(\d+)\s+days?\s+from\s+(\w+)",
        prompt,
        re.I
    )

    if subtract_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "subtract_days",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            subtract_match.group(2),

            "days":
            int(
                subtract_match.group(1)
            )
        })

   # format date
    format_match = re.search(
        r"format\s+date\s+column",
        prompt,
        re.I
    )

    if format_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "format_date",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            "joining_date"
        })


 # date difference
    diff_match = re.search(
        r"date\s+difference\s+between\s+(\w+)\s+and\s+(\w+)",
        prompt,
        re.I
    )

    if diff_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "date_diff",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "start_col":
            diff_match.group(1),

            "end_col":
            diff_match.group(2),

            "result":
            "days_difference"
        })    

    return pipeline


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


def add_step(pipeline, operation, **kwargs):

    step = {
        "id": generate_id(),
        "operation": operation
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

    COLUMN_MAP = {

   
    "employee":"fullname",
    "employees":"fullname",

    "name":"fullname",
    "names":"fullname",

    "full name":"fullname",
    "employee name":"fullname",

    "city":"city",
    "cities":"city",

    "mail":"email",
    "mails":"email",

    "email":"email",
    "emails":"email",

    "dept":"department",
    "team":"department",
    "department":"department",

    "salary":"salary"

}

    return COLUMN_MAP.get(
        col.strip(),
        col.strip()
    )

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

    try:

        # ==========================
        # UPPERCASE
        # ==========================

        upper_patterns = [
            r"(?:convert|change)\s+(\w+)\s+to\s+uppercase",
            r"(?:convert|change)\s+(\w+)\s+uppercase",
            r"\b(\w+)\s+(?:convert|change)\s+uppercase\b",
            r"(\w+)\s+should\s+be\s+uppercase",
            r"make\s+(\w+)\s+uppercase",
            r"\buppercase\s+(\w+)"
        ]

        for pattern in upper_patterns:

            for match in re.finditer(pattern, prompt, re.I):

                col = normalize_col(match.group(1))

                add_step(
                    pipeline,
                    "uppercase",
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
           r"\b(\w+)\s+(?:convert|change)\s+lowercase\b"
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
                    input="dataframe",
                    output="dataframe",
                    col=col,
                    output_col=col
                )
                  
                  
        # ==========================
        # REPLACE
        # ==========================

        # Column specific replacement
        for match in re.finditer(
             r"replace\s+(.+?)\s+with\s+(.+?)\s+in\s+(\w+)",
             prompt,
             re.I
        ):

            # Ignore "replace missing salary..."
            if match.group(1).lower() == "missing":
                continue

            add_step(
                pipeline,
                "replace_str",
                old=match.group(1).strip(),
                new=match.group(2).strip(),
                col=normalize_col(match.group(3))
            )


        # Global replacement
        for match in re.finditer(
            r"replace\s+(?!missing\b)(.+?)\s+with\s+(.+?)(?=\s+(?:replace|uppercase|lowercase|rename|sort|save|export|write|$))",
            prompt,
            re.I
        ):

            # Skip if already parsed as column replacement
            if re.search(
                rf"replace\s+{re.escape(match.group(1))}\s+with\s+{re.escape(match.group(2))}\s+in\s+\w+",
                prompt,
                re.I
            ):
                continue

            add_step(
               pipeline,
               "replace_str",
               input="dataframe",
               output="dataframe",
               old=match.group(1).strip(),
               new=match.group(2).strip(),
               col="city"
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

            pipeline.append({

                "id": generate_id(),

                "operation": "filter_rows",

                "input": "dataframe",

                "output": "dataframe",

                "column": column,

                "operator": operator,

                "value": value

            })

            break

    return pipeline



def parse_export(prompt):

    pipeline=[]

    export_match = re.search(
        r"(?:save|export)?\s*([\w\-]+\.csv)",
        prompt,
        re.IGNORECASE
    )

    if export_match:

        filename = export_match.group(1)

        if not filename.lower().endswith(".xlsx"):

            pipeline.append({

                "id": generate_id(),

                "operation": "write_csv",

                "input": "dataframe",

                "path": filename

            })

 # JSON
    json_match = re.search(
        r"convert\s+to\s+json",
        prompt,
        re.I
    )

    if json_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "to_json",

            "input": "dataframe",

            "path": "output.json"
        })

    # HTML
    html_match = re.search(
        r"convert\s+to\s+html",
        prompt,
        re.I
    )

    if html_match:

        pipeline.append({

            "id": generate_id(),

            "operation": "to_html",

            "input": "dataframe",

            "path": "output.html"
        })



    return pipeline


def parse_transform(prompt):

    pipeline = []

    match = re.search(
        r"transpose\s+(?:data|table)?",
        prompt,
        re.I
    )

    if match:

        pipeline.append({
            "id": generate_id(),
            "operation": "transpose",
            "input": "dataframe",
            "output": "dataframe"
        })

    return pipeline


def parse_reindex(prompt):

    pipeline = []

    match = re.search(
        r"reindex\s+columns",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation": "reindex_columns",

            "input": "dataframe",

            "output": "dataframe"
        })

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


def parse_use_row_as_header(prompt):

    pipeline=[]

    match = re.search(
        r"use\s+row\s+(\d+)\s+as\s+header",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation": "use_row_as_header",

            "input": "dataframe",

            "output": "dataframe",

            "row": int(
                match.group(1)
            )
        })

    return pipeline


def parse_pivot(prompt):

    pipeline=[]

    match = re.search(
        r"pivot\s+table\s+by\s+(\w+)",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation": "pivot_table",

            "input": "dataframe",

            "output": "dataframe",

            "index": match.group(1),

            "values": "salary",

            "aggfunc": "sum"
        })

    return pipeline



def parse_date(prompt):

    pipeline = []
    
    # extract date parts
    extract_match = re.search(
        r"extract\s+date\s+parts\s+from\s+(\w+)",
        prompt,
        re.I
    )

    if extract_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "extract_date_parts",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            extract_match.group(1)
        })

     # add days
    add_match = re.search(
        r"add\s+(\d+)\s+days?\s+to\s+(\w+)",
        prompt,
        re.I
    )

    if add_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "add_days",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            add_match.group(2),

            "days":
            int(add_match.group(1))
        })

    # subtract days
    subtract_match = re.search(
        r"subtract\s+(\d+)\s+days?\s+from\s+(\w+)",
        prompt,
        re.I
    )

    if subtract_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "subtract_days",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            subtract_match.group(2),

            "days":
            int(
                subtract_match.group(1)
            )
        })

   # format date
    format_match = re.search(
        r"format\s+date\s+column",
        prompt,
        re.I
    )

    if format_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "format_date",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "column":
            "joining_date"
        })


 # date difference
    diff_match = re.search(
        r"date\s+difference\s+between\s+(\w+)\s+and\s+(\w+)",
        prompt,
        re.I
    )

    if diff_match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "date_diff",

            "input":
            "dataframe",

            "output":
            "dataframe",

            "start_col":
            diff_match.group(1),

            "end_col":
            diff_match.group(2),

            "result":
            "days_difference"
        })    

    return pipeline


def parse_sql(prompt):

    pipeline = []

    match = re.search(
        r"write\s+to\s+sql",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "write_sql",

            "input":
            "dataframe",

            "connection":
            "sqlite:///database.db",

            "table":
            "employees",

            "output":
            "dataframe"
        })

    return pipeline   # ← MOVE OUTSIDE if



def parse_read_database(prompt):

    pipeline = []

    match = re.search(
        r"read\s+database",
        prompt,
        re.I
    )

    if match:

        pipeline.append({

            "id": generate_id(),

            "operation":
            "read_database",

            "output":
            "dataframe",

            "table":
            "employees"
        })

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
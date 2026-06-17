import json
import re
import time
import random
import os

os.makedirs("generated", exist_ok=True)


# =====================================================
# GENERATE UNIQUE ID
# =====================================================

def generate_id():
    return int(
        f"{int(time.time() * 1000)}{random.randint(10,99)}"
    )


# =====================================================
# GENERATE PIPELINE
# =====================================================

def generate_pipeline(prompt):

    pipeline = []

    current_table = "dataframe"

    # detect dataframe name
    df_match = re.search(
        r"into\s+dataframe\s+(\w+)",
        prompt,
        re.IGNORECASE
    )

    if df_match:
        current_table = df_match.group(1)

    # Keep original prompt for column names
    original_prompt = prompt

    # Lowercase only for regex matching
    prompt = prompt.lower()

     # =====================================================
    # READ FILE
    # =====================================================

    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "twenty": 20,
        "fifty": 50,
        "hundred": 100
    }

    read_match = re.search(
        r"([\w\-.]+\.(csv|xlsx|json))",
        original_prompt,
        re.IGNORECASE
    )


    if read_match:
            filename = read_match.group(1)
            extension = read_match.group(2).lower()

            operation_map = {
                "csv": "read_csv",
                "xlsx": "read_excel_any",
                "json": "read_json"
            }

            read_op = {
                "id": generate_id(),
                "operation": operation_map[extension],
                "output": current_table,
                "path": filename
            }

            if extension == "xlsx":

                sheet_match = re.search(
                    r"sheet\s+([a-zA-Z0-9_]+)",
                    original_prompt,
                    re.IGNORECASE
                )

                if sheet_match:
                    read_op["sheet"] = sheet_match.group(1)

            rows_match = re.search(
        r"(?:first|top)\s+(\w+)\s+(?:rows|records)",
        original_prompt,
        re.IGNORECASE
    )

            if rows_match:

                rows_value = rows_match.group(1).lower()

                if rows_value.isdigit():
                    read_op["rows"] = int(rows_value)
                    read_op["preview"] = True

                elif rows_value in number_words:
                    read_op["rows"] = number_words[rows_value]
                    read_op["preview"] = True

            print("GENERATED READ OP:")
            print(read_op)
            pipeline.append(read_op)


# =====================================================
# ADD NEW COLUMN
# =====================================================

    add_col_match = re.search(
        r"(?:add|create)\s+(?:new\s+)?column\s+(\w+)(?:\s+with\s+value\s+([^\s,]+))?",
        original_prompt,
        re.IGNORECASE
    )

    if add_col_match:

        column = add_col_match.group(1)

        value = ""

        if add_col_match.group(2):
            value = add_col_match.group(2)

            # convert numeric values
            if value.isdigit():
                value = int(value)

        pipeline.append({
            "id": generate_id(),
            "operation": "add_column",
            "input": current_table,
            "output": current_table,
            "column": column,
            "value": value
        })


    # =====================================================
    # ADD CONSTANT
    # =====================================================

    add_match = re.search(
        r"add\s+(\d+)\s+to\s+(\w+)",
        original_prompt,
        re.IGNORECASE
    )

    if add_match:

        value = int(add_match.group(1))
        column = add_match.group(2)

        pipeline.append({
            "id": generate_id(),
            "operation": "add_constant",
            "input": current_table,
            "output": current_table,
            "col": column,
            "value": value
        })

    # =====================================================
    # UPPERCASE
    # =====================================================

    uppercase_match = re.search(
        r"(?:convert|change)\s+(\w+)\s+column\s+to\s+uppercase",
        original_prompt,
        re.IGNORECASE
    )

    if uppercase_match:

        col = uppercase_match.group(1)

        pipeline.append({
            "id": generate_id(),
            "operation": "uppercase",
            "input": current_table,
            "output": current_table,
            "col": col,
            "output_col": col
        })


# =====================================================
# LOWERCASE
# =====================================================

    lowercase_match = re.search(
        r"(?:convert|change)\s+(\w+)\s+column\s+to\s+lowercase",
        original_prompt,
        re.IGNORECASE
    )

    if lowercase_match:

        col = lowercase_match.group(1)

        pipeline.append({
            "id": generate_id(),
            "operation": "lowercase",
            "input": current_table,
            "output": current_table,
            "col": col,
            "output_col": col
        })

    # =====================================================
    # SUBTRACT CONSTANT
    # =====================================================

    subtract_match = re.search(
        r"subtract\s+(\d+)\s+from\s+(\w+)",
        original_prompt,
        re.IGNORECASE
    )

    if subtract_match:

        value = int(subtract_match.group(1))
        col = subtract_match.group(2)

        pipeline.append({
            "id": generate_id(),
            "operation": "subtract_constant",
            "input": current_table,
            "output": current_table,
            "col": col,
            "value": value
        })

    # =====================================================
    # MULTIPLY COLUMNS
    # =====================================================

    multiply_match = re.search(
    r"multiply\s+(\w+)\s+(?:column\s+)?(?:and|by)\s+(\w+)",
    original_prompt,
    re.IGNORECASE
)

    if multiply_match:

        col1 = multiply_match.group(1)
        col2 = multiply_match.group(2)

        pipeline.append({
            "id": generate_id(),
            "operation": "multiply_columns",
            "input": current_table,
            "output": current_table,
            "col1": col1,
            "col2": col2,
            "result": f"{col1}_x_{col2}"
        })


        percent_match = re.search(
         r"percent change between (\w+) and (\w+)",
         original_prompt,
         re.IGNORECASE
    )

# =====================================================
# PERCENT CHANGE
# =====================================================

    percent_match = re.search(
        r"percent change between (\w+) and (\w+)",
        original_prompt,
        re.IGNORECASE
    )

    if percent_match:

        col1 = percent_match.group(1)
        col2 = percent_match.group(2)

        pipeline.append({
            "id": generate_id(),
            "operation": "percent_change",
            "input": current_table,
            "output": current_table,
            "col1": col1,
            "col2": col2,
            "result": f"{col1}_{col2}_percent"
        })


        sum_match = re.search(
            r"sum of (\w+)",
            original_prompt,
            re.IGNORECASE
            )

        if sum_match:

            pipeline.append({
            "id":generate_id(),
            "operation":"aggregate",
            "column":sum_match.group(1),
            "agg":"sum"
            })


    avg_match = re.search(
        r"(?:average|mean)\s+(\w+)",
        original_prompt,
        re.IGNORECASE
    )

    if avg_match:

        pipeline.append({
        "operation":"aggregate",
        "column":avg_match.group(1),
        "agg":"mean"
        })


    max_match = re.search(
        r"max\s+(\w+)",
        original_prompt,
        re.IGNORECASE
        )

    if max_match:

        pipeline.append({
        "operation":"aggregate",
        "column":max_match.group(1),
        "agg":"max"
        })


    # =====================================================
    # DIVIDE COLUMNS
    # =====================================================

    divide_match = re.search(
        r"divide\s+(\w+)\s+by\s+(\w+)",
        original_prompt,
        re.IGNORECASE
    )

    if divide_match:

        col1 = divide_match.group(1)
        col2 = divide_match.group(2)

        pipeline.append({
            "id": generate_id(),
            "operation": "divide_columns",
            "input": current_table,
            "output": current_table,
            "col1": col1,
            "col2": col2,
            "result": f"{col1}_per_{col2}"
        })

    # =====================================================
    # RENAME COLUMN
    # =====================================================

    rename_match = re.search(
        r"rename\s+(\w+)\s+column\s+to\s+(\w+)",
        original_prompt,
        re.IGNORECASE
    )

    if rename_match:

        old_col = rename_match.group(1).strip()
        new_col = rename_match.group(2).strip()

        print("RENAME DETECTED:", old_col, "->", new_col)

        pipeline.append({
            "id": generate_id(),
            "operation": "rename_columns",
            "input": current_table,
            "output": current_table,
            "mapping": {
                old_col: new_col
            }
        })

    # =====================================================
    # DROP COLUMN
    # =====================================================

    drop_match = re.search(
        r"(?:drop|remove)\s+(\w+)\s+column",
        original_prompt,
        re.IGNORECASE
    )

    if drop_match:

        col = drop_match.group(1)

        pipeline.append({
            "id": generate_id(),
            "operation": "drop_columns",
            "input": current_table,
            "output": current_table,
            "cols": [col]
        })

    # ==========================================
# SELECT COLUMNS
# ==========================================

    select_match = re.search(
        r"keep only (.+?) columns",
        original_prompt,
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
    # =====================================================
    # FILTER ROWS
    # =====================================================

    filter_match = re.search(
        r"where\s+(\w+)\s*(>|<|>=|<=|=|!=)\s*(\d+)",
        original_prompt,
        re.IGNORECASE
    )

    if not filter_match:

        filter_match = re.search(
            r"where\s+(\w+)\s+is\s+(less than|greater than|equal to)\s+(\d+)",
            original_prompt,
            re.IGNORECASE
        )

        if filter_match:

            col = filter_match.group(1)
            operator_text = filter_match.group(2).lower()
            value = int(filter_match.group(3))

            operator_map = {
                "less than": "<",
                "greater than": ">",
                "equal to": "=="
            }

            pipeline.append({
                "id": generate_id(),
                "operation": "filter_rows",
                "input": current_table,
                "output": current_table,
                "condition": f"{col} {operator_map[operator_text]} {value}"
            })

    elif filter_match:

        col = filter_match.group(1)
        operator = filter_match.group(2)
        value = int(filter_match.group(3))

        if operator == "=":
            operator = "=="

        pipeline.append({
            "id": generate_id(),
            "operation": "filter_rows",
            "input": current_table,
            "output": current_table,
            "condition": f"{col} {operator} {value}"
        })


# =====================================================
# SORT VALUES
# =====================================================
    sort_match = re.search(
        r"sort\s+by\s+(\w+)(?:\s+(ascending|descending))?",
        original_prompt,
        re.IGNORECASE
    )

    if sort_match:
        col = sort_match.group(1)
        order = sort_match.group(2)
        ascending = True

        if order and order.lower() == "descending":
            ascending = False

        pipeline.append({
            "id": generate_id(),
            "operation": "sort_values",
            "input": current_table,
            "output": current_table,
            "by": col,
            "ascending": ascending
        })


    # =====================================================
    # EXPORT CSV
    # =====================================================

    export_match = re.search(
    r"(?:save|export).*?([\w\-]+\.csv)",
    original_prompt,
    re.IGNORECASE
)
    if export_match:

        pipeline.append({
            "id": generate_id(),
            "operation": "write_csv",
            "input": current_table,
            "path": export_match.group(1)
        })


    has_read = any(
        step["operation"] in [
            "read_csv",
            "read_excel_any",
            "read_json"
        ]
        for step in pipeline
    )

    if not has_read:

        return json.dumps(
            {
                "error": "Please specify a file. Example: Add column age in book2.xlsx"
            },
            indent=4
        )


    # =====================================================
    # VALIDATION
    # =====================================================

    if not pipeline:
       return json.dumps(
              {
                "error": "No valid operations found!"
              },
            indent=4
        )

    # =====================================================
    # SAVE JSON
    # =====================================================

    with open("generated/pipeline.json", "w") as file:
        json.dump(
            pipeline,
            file,
            indent=4
        )

    return json.dumps(
        pipeline,
        indent=4
    )
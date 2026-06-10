import pandas as pd
import os

os.makedirs("generated", exist_ok=True)


def execute_pipeline(pipeline):

    df = None

    for step in pipeline:

        operation = step["operation"]

        # ==========================================
        # READ CSV
        # ==========================================

        if operation == "read_csv":

            path = f"uploads/{step['path']}"
            df = pd.read_csv(path)

            if "rows" in step:
                df = df.head(step["rows"])

        # ==========================================
        # READ EXCEL
        # ==========================================

        elif operation == "read_excel_any":

            path = f"uploads/{step['path']}"
            df = pd.read_excel(path)

            if "rows" in step:
                df = df.head(step["rows"])

        # ==========================================
        # READ JSON
        # ==========================================

        elif operation == "read_json":

            path = f"uploads/{step['path']}"
            df = pd.read_json(path)

            if "rows" in step:
                df = df.head(step["rows"])

        # ==========================================
        # ADD COLUMN
        # ==========================================

        elif operation == "add_column":

            df[step["column"]] = step["value"]

        # ==========================================
        # ADD CONSTANT
        # ==========================================

        elif operation == "add_constant":

            col = step["col"]
            value = step["value"]

            if col in df.columns:
                df[col] = df[col] + value

        # ==========================================
        # SUBTRACT CONSTANT
        # ==========================================

        elif operation == "subtract_constant":

            col = step["col"]
            value = step["value"]

            if col in df.columns:
                df[col] = df[col] - value

        # ==========================================
        # UPPERCASE
        # ==========================================

        elif operation == "uppercase":

            col = step["col"]
            output_col = step["output_col"]

            if col in df.columns:
                df[output_col] = df[col].astype(str).str.upper()

        # ==========================================
        # LOWERCASE
        # ==========================================

        elif operation == "lowercase":

            col = step["col"]
            output_col = step["output_col"]

            if col in df.columns:
                df[output_col] = df[col].astype(str).str.lower()

        # ==========================================
        # FILTER ROWS
        # ==========================================

        elif operation == "filter_rows":

            condition = step["condition"]
            df = df.query(condition)

        # ==========================================
        # MULTIPLY COLUMNS
        # ==========================================

        elif operation == "multiply_columns":

            col1 = step["col1"]
            col2 = step["col2"]
            result = step["result"]

            if col1 not in df.columns:
                return {
                    "type": "error",
                    "message": f"Column '{col1}' not found"
                }

            if col2 not in df.columns:
                return {
                    "type": "error",
                    "message": f"Column '{col2}' not found"
                }

            df[result] = df[col1] * df[col2]

        # ==========================================
        # DIVIDE COLUMNS
        # ==========================================

        elif operation == "divide_columns":

            col1 = step["col1"]
            col2 = step["col2"]
            result = step["result"]

            if col1 in df.columns and col2 in df.columns:
                df[result] = df[col1] / df[col2]

        # ==========================================
        # RENAME COLUMNS
        # ==========================================

        elif operation == "rename_columns":

            mapping = step["mapping"]

            df.rename(
                columns=mapping,
                inplace=True
            )

        # ==========================================
        # SELECT COLUMNS
        # ==========================================

        elif operation == "select_columns":

            cols = step["cols"]

            valid_cols = [
                col for col in cols
                if col in df.columns
            ]

            df = df[valid_cols]

        # ==========================================
        # DROP COLUMNS
        # ==========================================

        elif operation == "drop_columns":

            df = df.drop(
                columns=step["cols"],
                errors="ignore"
            )

        # ==========================================
        # SORT VALUES
        # ==========================================

        elif operation == "sort_values":

            df = df.sort_values(
                by=step["by"],
                ascending=step["ascending"]
            )

    # ==========================================
    # CHECK IF DATA EXISTS
    # ==========================================

    if df is None:

        return {
            "type": "error",
            "message": "No data loaded. Please add a read operation first."
        }

    # ==========================================
    # SAVE OUTPUT
    # ==========================================

    output_excel = "generated/output.xlsx"

    df.to_excel(
        output_excel,
        index=False
    )

    # ==========================================
    # RETURN DATA
    # ==========================================

    return {
        "type": "success",
        "total_rows": len(df),
        "data": df.head(20).to_dict(orient="records"),
        "file": output_excel
    }
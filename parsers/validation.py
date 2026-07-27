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
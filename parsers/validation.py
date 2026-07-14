def validate_pipeline(pipeline):

    if not pipeline:
        return "No valid operations found!"

    read_ops = {
        "read_csv",
        "read_excel_any",
        "read_json",
        "read_database"
    }

    export_ops = {
        "write_csv",
        "to_json",
        "to_html",
        "write_sql"
    }

    has_read = any(
        step["operation"] in read_ops
        for step in pipeline
    )

    if not has_read:
        return "Please specify an input file."

    has_export = any(
        step["operation"] in export_ops
        for step in pipeline
    )

    if not has_export:
        return "Please specify an output file."

    return None
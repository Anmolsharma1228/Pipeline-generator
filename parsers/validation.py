def validate_pipeline(pipeline):

    if not pipeline:
        return "No valid operations found!"

    has_read = any(

        x["operation"]

        in [

            "read_csv",

            "read_excel_any",

            "read_json"

        ]

        for x in pipeline
    )

    if not has_read:

        return (
            "Please specify file"
        )

    return None
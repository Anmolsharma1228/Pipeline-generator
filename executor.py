from operations import OPERATIONS


def execute_pipeline(pipeline):

    df = None

    show_preview = False

    for step in pipeline:

        if step.get("preview"):
            show_preview = True

        operation = step["operation"]

        if operation not in OPERATIONS:

            return {
                "type": "error",
                "message": f"Unknown operation {operation}"
            }

        df = OPERATIONS[
            operation
        ](
            step,
            df
        )

    if df is None:

        return {
            "type": "error",
            "message": "No data loaded"
        }

    return {

        "type": "success",

        "show_preview": show_preview,

        "total_rows": len(df),

        "data": (
            df
            .head(20)
            .to_dict(
                orient="records"
            )
        )
    }
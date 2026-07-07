from flask import Flask, render_template, request, send_file
from parser import generate_pipeline
from executor import execute_pipeline

import json
import os

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    message = None
    preview = None

    if request.method == "POST":
        try:
            prompt = request.form["prompt"]

            # Generate JSON pipeline
            result = generate_pipeline(prompt)

            pipeline = json.loads(result)

            # Parser error
            if isinstance(pipeline, dict):
                message = pipeline.get(
                    "error",
                    "Unknown error occurred"
                )

            elif len(pipeline) == 0:
                message = "No valid operations found!"

            else:
                # Execute pipeline
                execution_result = execute_pipeline(
                    pipeline
                )

                if (
                    execution_result
                    and
                    execution_result.get("type")
                    == "error"
                ):
                    message = execution_result.get(
                        "message",
                        "Execution failed"
                    )

                else:
                    preview = None

            if execution_result:

                preview = execution_result.get(
                    "data",
                    None
                )

            result = json.dumps(
                pipeline,
                indent=4
            )

            if preview:

                message = (
                    "Pipeline Executed Successfully"
                )

            else:

                message = (
                    "JSON Generated Successfully"
                )

        except Exception as e:
            message = str(e)

    return render_template(
        "index.html",
        result=result,
        message=message,
        preview=preview
    )

# ==========================================
# VIEW JSON
# ==========================================

@app.route("/view")
def view():

    file_path = "generated/pipeline.json"

    if not os.path.exists(file_path):

        return {
            "error": "pipeline.json not found"
        }

    with open(file_path) as file:

        data = json.load(file)

    return data


# ==========================================
# DOWNLOAD JSON
# ==========================================

@app.route("/download")
def download():

    file_path = "generated/pipeline.json"

    if os.path.exists(file_path):

        return send_file(
            file_path,
            as_attachment=True
        )

    return "No JSON file found"


if __name__ == "__main__":

    app.run(
        debug=True
    )
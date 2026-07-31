from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from parser import generate_pipeline

import json
import os

app = Flask(__name__)
CORS(app)


@app.route("/generate", methods=["POST"])
def generate():

    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        result = generate_pipeline(prompt)
        pipeline = json.loads(result)
        return jsonify(pipeline)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/download", methods=["GET"])
def download():

    file_path = "generated/pipeline.json"

    if os.path.exists(file_path):

        return send_file(
            file_path,
            as_attachment=True
        )

    return jsonify({
        "error": "pipeline.json not found"
    }), 404


if __name__ == "__main__":

    app.run(debug=True)
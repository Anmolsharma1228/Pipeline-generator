from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS
from parser import generate_pipeline

import json
import os

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


@app.route("/generate", methods=["POST"])
def generate():

    try:
        file_path = None

        # Case 1: multipart/form-data - prompt text + an actual
        # uploaded file (csv/xlsx/json), so column names can be
        # checked against the real headers.
        if request.content_type and "multipart/form-data" in request.content_type:

            prompt = request.form.get("prompt", "")
            uploaded = request.files.get("file")

            if uploaded and uploaded.filename:

                ext = os.path.splitext(uploaded.filename)[1].lower()

                if ext not in ALLOWED_EXTENSIONS:
                    return jsonify({
                        "error": f"Unsupported file type '{ext}'. "
                                 f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                    }), 400

                os.makedirs(UPLOAD_DIR, exist_ok=True)

                safe_name = secure_filename(uploaded.filename)
                file_path = os.path.join(UPLOAD_DIR, safe_name)
                uploaded.save(file_path)

        # Case 2: plain JSON body - just a prompt, no file (still
        # works exactly as before; column names are used as-is).
        else:
            data = request.get_json(silent=True) or {}
            prompt = data.get("prompt", "")

        result = generate_pipeline(prompt, file_path=file_path)
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
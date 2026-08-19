"""
app.py
------
Thin local web server wrapping the EXISTING extract.py / avr.py / saaf.py
unchanged. Run this instead of main.py when you want the Chrome extension
to call your machine directly.

Usage:
    pip install flask flask-cors pypdf
    python app.py
    -> serves on http://localhost:5000

Endpoint:
    POST /generate
        multipart/form-data:
            proposal        = the PDF file
            applicantProfile = JSON string (same shape as main.py's
                                APPLICANT_PROFILE dict)
    Response (JSON):
        {
          "avr":    "<base64 PDF>",
          "saaf":   "<base64 PDF>",
          "master": "<base64 PDF>"   # Proposal + SAAF + AVR combined
        }
    On a strict-format failure from extract.py:
        HTTP 400, { "error": "...", "strict_errors": [...] }
"""

import base64
import io
import json
import os
import tempfile

from flask import Flask, request, jsonify
from flask_cors import CORS
from pypdf import PdfWriter

import extract
import avr
import saaf

app = Flask(__name__)
# Allow calls from your unpacked/published Chrome extension.
CORS(app, resources={r"/generate": {"origins": "*"}})

# Same constant as main.py — adviser doesn't come from the PDF anymore.
ORGANIZATION_ADVISER = {
    "name": "Renilda S. Layno",
    "position": "Organization Adviser",
    "organizationName": "AWS Student Builder Group - Arcus",
}


@app.route("/generate", methods=["POST"])
def generate():
    if "proposal" not in request.files:
        return jsonify(error="No 'proposal' file uploaded."), 400

    profile_raw = request.form.get("applicantProfile")
    if not profile_raw:
        return jsonify(error="Missing 'applicantProfile' field."), 400
    applicant_profile = json.loads(profile_raw)

    with tempfile.TemporaryDirectory() as tmp:
        proposal_path = os.path.join(tmp, "proposal.pdf")
        request.files["proposal"].save(proposal_path)

        # ---- Same calls main.py already makes, unchanged ----
        try:
            event = extract.extract_proposal(proposal_path)  # strict=True by default
        except extract.ProposalFormatError as e:
            return jsonify(
                error="Proposal failed strict format validation.",
                strict_errors=str(e).split("\n- ")[1:],
            ), 400

        event["adviserName"] = ORGANIZATION_ADVISER["name"]

        avr_path = avr.fill(event, applicant_profile)     # returns output path, per main.py
        saaf_path = saaf.fill(event, applicant_profile)

        # ---- Merge Proposal + SAAF + AVR into one master PDF ----
        master_path = os.path.join(tmp, "Master.pdf")
        writer = PdfWriter()
        for path in [proposal_path, saaf_path, avr_path]:
            writer.append(path)
        with open(master_path, "wb") as f:
            writer.write(f)

        def to_b64(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")

        return jsonify(
            avr=to_b64(avr_path),
            saaf=to_b64(saaf_path),
            master=to_b64(master_path),
        )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
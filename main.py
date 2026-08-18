"""
main.py
-------
Entry point for the SAAF/AVR automation.

Usage:
    python main.py

Reads input/proposal.pdf, extracts the structured event data, and fills
both templates/AVR.pdf and templates/SAAF.pdf, writing results to output/.

Applicant profile and org-level defaults are kept as plain constants below
rather than a separate config file — edit them directly when the applicant
or standard equipment/room defaults change.
"""

import json
import os

import extract
import avr
import saaf

# ---- Constants: fixed per-applicant / per-org, reused every run ----

APPLICANT_PROFILE = {
    "name": "Mico Angelo C. Tazarte",
    "studentNumber": "2024109156",
    "programAndYear": "BSCS - 3",
    "position": "Corporate Secretary",
    "department": "SOIT",
    "courseSection": "BSCS - 3",
    "contactNo": "09457786367",
    "organizationName": "AWS Student Builder Group - Arcus",
}

ORG_DEFAULTS = {
    "defaultAvEquipment": [
        {"item": "Television", "quantity": 1},
        {"item": "Speaker", "quantity": 1},
        {"item": "Microphone", "quantity": 1},
    ],
    "defaultAvRoom": "AV Room 1",
    "individualContribution": "0",
}


def main():
    os.makedirs("output", exist_ok=True)

    print("Extracting proposal...")
    event = extract.extract_proposal("input/proposal.pdf")
    with open("output/_extracted.json", "w") as f:
        json.dump(event, f, indent=2, ensure_ascii=False)
    print(f"  -> extracted {sum(1 for v in event.values() if v not in (None, [], ''))} non-empty fields")

    print("Filling AVR...")
    avr_out = avr.fill(event, APPLICANT_PROFILE, ORG_DEFAULTS)
    print(f"  -> {avr_out}")

    print("Filling SAAF...")
    try:
        saaf_out = saaf.fill(event, APPLICANT_PROFILE, ORG_DEFAULTS)
        print(f"  -> {saaf_out}")
    except NotImplementedError as e:
        print(f"  -> skipped: {e}")

    print("Done.")


if __name__ == "__main__":
    main()

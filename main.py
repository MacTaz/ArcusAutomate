"""
main.py
-------
Entry point for the SAAF/AVR automation.
 
Usage:
    python main.py
 
Reads input/proposal.pdf, extracts the structured event data, and fills
both templates/AVR.pdf and templates/SAAF.pdf, writing results to output/.
 
APPLICANT_PROFILE is kept as a plain constant below rather than a separate
config file — edit it directly when the applicant changes. AV Equipment,
AV Room, and every other event-specific value now come straight from the
proposal itself (see the Official Event Proposal Template's "AV Equipment
& Room Request" section) — there are no org-level fallback defaults left,
since those fields are expected to always be filled in on the proposal.
"""
 
import argparse
import json
import os
 
import extract
import avr
import saaf
 
# ---- Constant: fixed per-applicant, reused every run ----
 
APPLICANT_PROFILE = {
    "name": "Mico Angelo C. Tazarte",
    "studentNumber": "2024109156",
    "programAndYear": "BSCS - 3",
    "position": "Corporate Secretary",
    "department": "SOIT",
    "courseSection": "BSCS - 3",
    "contactNo": "09770232108",
    "organizationName": "AWS Student Builder Group - Arcus",
}
 
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug-saaf",
        action="store_true",
        help="Draw field/checkbox outlines on the SAAF output for box "
             "placement testing, and write to output/SAAF_debug.pdf "
             "instead of overwriting the real output.",
    )
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)
 
    print("Extracting proposal...")
    event = extract.extract_proposal("input/proposal.pdf")
    with open("output/_extracted.json", "w") as f:
        json.dump(event, f, indent=2, ensure_ascii=False)
    print(f"  -> extracted {sum(1 for v in event.values() if v not in (None, [], ''))} non-empty fields")
 
    print("Filling AVR...")
    avr_out = avr.fill(event, APPLICANT_PROFILE)
    print(f"  -> {avr_out}")
 
    print("Filling SAAF...")
    if args.debug_saaf:
        saaf_out = saaf.fill(
            event,
            APPLICANT_PROFILE,
            debug=True,
            output_path="output/SAAF_debug.pdf",
        )
    else:
        saaf_out = saaf.fill(event, APPLICANT_PROFILE)
    print(f"  -> {saaf_out}")
 
    print("Done.")
 
 
if __name__ == "__main__":
    main()
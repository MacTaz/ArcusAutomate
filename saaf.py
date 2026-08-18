"""
saaf.py
-------
Fills templates/SAAF.pdf (FM-SA-14-01) using the extracted proposal data
plus constant config passed in from main.py.

STATUS: scaffold only — not yet implemented.

Unlike AVR.pdf, SAAF.pdf has NO fillable AcroForm fields (confirmed via
`python /mnt/skills/public/pdf/scripts/check_fillable_fields.py templates/SAAF.pdf`).
It's a flat form, so text has to be drawn onto the page at specific
coordinates (an "overlay") rather than set via form field values.

Build plan (see /mnt/skills/public/pdf/FORMS.md, "Non-fillable fields"):
  1. Run extract_form_structure.py on templates/SAAF.pdf to pull label
     coordinates, lines, and checkbox positions.
  2. Build a fields.json mapping each SAAF field to an entry_bounding_box,
     using the label positions as anchors (entry x0 = label x1 + gap).
  3. Validate with check_bounding_boxes.py (catches overlaps / too-small entries).
  4. Fill with fill_pdf_form_with_annotations.py.
  5. Convert to image and visually verify before trusting the output.

Field -> data source, per the mapping worked out earlier in the project:
  Dynamic (from proposal):
    - Title and Nature of Activity   <- event["eventTitle"]
    - Objectives of the Activity     <- event["objectives"]
    - Venue                          <- event["venue"]
    - Date / Day / Time              <- event["date"] / computed / event["startTime"]
    - Number of Expected Participants<- event["participants"]
    - Proposed Budget                <- event["totalBudget"]
    - Faculty Adviser/Organizer      <- event["adviserName"]
    - Co-Curricular/Extra-Curricular checkbox <- event["activityType"]
    - Major/Minor checkbox           <- event["activityLevel"]
    - Total Number of Class/Org Members <- event["totalOrgMembers"]
    - Mapua Core Values write-up     <- event["coreValuesWriteup"]
    - PEO/PO write-up                <- event["peoWriteup"]
  Constant (from profile/defaults):
    - Name of Applicant & Student #, Program and Year, Position,
      Name of Organization/Course and Section, Class Officer name <- profile
    - Amount of Individual Contribution                            <- defaults["individualContribution"] (fixed at 0)
  Auto-generated:
    - Date of Submission of Form     <- datetime.date.today()
  Manual only (left blank):
    - All signature fields
"""


def fill(event: dict, profile: dict, defaults: dict,
         template_path: str = "templates/SAAF.pdf",
         output_path: str = "output/SAAF_filled.pdf") -> str:
    raise NotImplementedError(
        "saaf.py is a scaffold — the coordinate-overlay fill logic hasn't been "
        "built yet. See the module docstring for the build plan. "
        "avr.py can be used as a working reference for the overall function shape."
    )


if __name__ == "__main__":
    print("saaf.py is a module used by main.py — run `python main.py` instead.")

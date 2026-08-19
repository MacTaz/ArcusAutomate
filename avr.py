"""
avr.py
------
Fills templates/AVR.pdf (FM-AO-08-01) using extracted proposal data and applicant profile constants.
This template contains native AcroForm fields, so filling is performed directly via pypdf form field values.

Contains mappings for:
- ROOM_FIELD_MAP: Room selection checkboxes, dates, times, and remarks fields.
- EQUIPMENT_FIELD_MAP: Audio-Visual equipment checkboxes, dates, and times fields.
"""

import datetime
import json
import sys

ROOM_FIELD_MAP = {
    "AV Room 1": {"checkbox": "Check Box1", "date": "Date NeededRow1", "time": "Time NeededRow1", "remarks": "Remarks  AV Room 1"},
    "AV Room 2": {"checkbox": "Check Box2", "date": "Date NeededRow2", "time": "Time NeededRow2", "remarks": "Remarks  AV Room 2"},
    "Conference Room": {"checkbox": "Check Box3", "date": "Date NeededRow3", "time": "Time NeededRow3", "remarks": "Remarks  Conference Room"},
    "Others": {"checkbox": "Check Box4", "date": "Date NeededRow4", "time": "Time NeededRow4", "remarks": "Remarks  Others"},
}

EQUIPMENT_FIELD_MAP = {
    "LCD":               {"checkbox": "Check Box5", "date": "Date NeededRow1_2", "time": "Time NeededRow1_2"},
    "CPU":               {"checkbox": "Check Box6", "date": "Date NeededRow2_2", "time": "Time NeededRow2_2"},
    "Laptop":            {"checkbox": "Check Box7", "date": "Date NeededRow3_2", "time": "Time NeededRow3_2"},
    "Computer Speaker":  {"checkbox": "Check Box8", "date": "Date NeededRow4_2", "time": "Time NeededRow4_2"},
    "Laser Pointer":     {"checkbox": "Check Box9", "date": "Date NeededRow5",   "time": "Time NeededRow5"},
    "Television":        {"checkbox": "Check Box",  "date": "Date NeededRow6",   "time": "Time NeededRow6"},
    "DVD":                {"checkbox": "Check Bo1", "date": "Date NeededRow7",   "time": "Time NeededRow7"},
    "Doc. Cam.":          {"checkbox": "Check Bo2", "date": "Date NeededRow8",   "time": "Time NeededRow8"},
    "Amplifier":          {"checkbox": "Check Bo3", "date": "Date NeededRow9",   "time": "Time NeededRow9"},
    "Mixer":              {"checkbox": "Check Bo4", "date": "Date NeededRow10",  "time": "Time NeededRow10"},
    "Speaker":            {"checkbox": "Check Bo5", "date": "Date NeededRow11",  "time": "Time NeededRow11"},
    "Microphone":         {"checkbox": "Check Bo6", "date": "Date NeededRow12",  "time": "Time NeededRow12"},
}


def build_field_values(event: dict, profile: dict) -> list:
    """
    Constructs the list of AcroForm field ID and value mappings required to populate the AVR form.
    """
    values = []

    def text(field_id, value):
        if value is not None:
            values.append({"field_id": field_id, "value": str(value)})

    def check(field_id):
        values.append({"field_id": field_id, "value": "/Yes"})

    # Applicant profile constants
    text("Name of Applicant", profile["name"])
    text("DepartmentCompany of Applicant", profile["department"])
    text("CourseSection", profile["courseSection"])
    text("Contact No", profile["contactNo"])
    text("Date Applied", datetime.date.today().strftime("%m/%d/%Y"))
    text("Signature of Applicant", profile["name"])

    # Event details from extracted proposal
    text("No of Participants", event.get("participants"))
    text("Purpose of Activity", event.get("eventTitle"))

    date_needed = event.get("date")
    start_time = event.get("startTime")
    end_time = event.get("endTime")

    if not start_time or not end_time:
        raise ValueError("Proposal has no valid start/end time.")

    time_needed = f"{start_time} - {end_time}"
    room = event.get("avRoom")
    if not room:
        raise ValueError("Proposal has no AV Room specified — add a Room to the proposal's AV Equipment & Room Request section.")
    room_key = room if room in ROOM_FIELD_MAP else "Others"
    room_map = ROOM_FIELD_MAP[room_key]
    check(room_map["checkbox"])
    text(room_map["date"], date_needed)
    text(room_map["time"], time_needed)
    if room_key == "Others":
        text(room_map["remarks"], room)

    equipment = event.get("avEquipment")
    if not equipment:
        raise ValueError("Proposal has no AV Equipment listed — add items to the proposal's AV Equipment table.")
    for eq in equipment:
        item_name = eq["item"]
        if item_name in EQUIPMENT_FIELD_MAP:
            m = EQUIPMENT_FIELD_MAP[item_name]
            check(m["checkbox"])
            text(m["date"], date_needed)
            text(m["time"], time_needed)
        else:
            print(f"  [warn] '{item_name}' has no known field mapping on the AVR form — skipped.", file=sys.stderr)

    return values


def fill(event: dict, profile: dict,
          template_path: str = "templates/AVR.pdf",
          output_path: str = "output/AVR_filled.pdf") -> str:
    """
    Fills the AVR PDF template with event and profile data, saving the result to output_path.
    """
    from pypdf import PdfReader, PdfWriter

    field_values = build_field_values(event, profile)

    # Save extracted values for debugging audit
    tmp_values_path = "output/_avr_field_values.json"
    with open(tmp_values_path, "w", encoding="utf-8") as f:
        json.dump(field_values, f, indent=2, ensure_ascii=False)

    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    values = {
        item["field_id"]: item["value"]
        for item in field_values
    }

    for page in writer.pages:
        writer.update_page_form_field_values(
            page,
            values,
            auto_regenerate=False
        )

    with open(output_path, "wb") as f:
        writer.write(f)

    # Render applicant signature name onto signature field overlay
    import fitz
    doc = fitz.open(output_path)
    page = doc[0]
    applicant_name = str(profile.get("name", "")).strip()
    if applicant_name:
        center_x = (41.4 + 243.36) / 2.0
        text_len = fitz.get_text_length(applicant_name, fontname="helv", fontsize=10.5)
        x = center_x - (text_len / 2.0)
        page.insert_text(
            fitz.Point(x, 588.5),
            applicant_name,
            fontsize=10.5,
            fontname="helv",
            color=(0, 0, 0)
        )
    doc.save(output_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.close()

    return output_path


if __name__ == "__main__":
    print("avr.py is a module used by main.py — run `python main.py` instead.")
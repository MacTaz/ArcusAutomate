"""
extract.py
----------
Parses the AWS-SBG Arcus Event Proposal (input/proposal.pdf) into a single
structured dict. This is the shared "source of truth" consumed by both
avr.py and saaf.py.

Extraction strategy: the proposal template has fixed, predictable headings
("Date:", "Time:", "Target Proponents", "AV Equipment", "Room", etc.), so we
use straightforward label-based text parsing via pdfplumber rather than a
heavy AI/NLP step. Fast, free, deterministic.
"""

import pdfplumber
import re
import sys


def extract_proposal(pdf_path: str) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        tables_by_page = [page.extract_tables() for page in pdf.pages]

    data = {}

    # ---- Event Title ----
    title_match = re.search(r"^(.*?)\nDate:", full_text, re.DOTALL)
    data["eventTitle"] = title_match.group(1).strip().replace("\n", " ") if title_match else None

    # ---- Date / Time ----
    date_match = re.search(r"Date:\s*(.+)", full_text)
    time_match = re.search(r"Time:\s*(.+)", full_text)
    data["date"] = date_match.group(1).strip() if date_match else None
    data["time_raw"] = time_match.group(1).strip() if time_match else None

    if data["time_raw"]:
        times = re.findall(r"\d{1,2}:\d{2}\s*[APMapm]{2}", data["time_raw"])
        data["startTime"] = times[0] if len(times) > 0 else None
        data["endTime"] = times[1] if len(times) > 1 else None
    else:
        data["startTime"] = data["endTime"] = None

    # ---- Activity Classification ----
    level_match = re.search(r"Activity Level:\s*(.+)", full_text)
    type_match = re.search(r"Activity Type:\s*(.+)", full_text)
    data["activityLevel"] = level_match.group(1).strip() if level_match else None
    data["activityType"] = type_match.group(1).strip() if type_match else None

    # ---- Total Org Members / Participants ----
    total_members_match = re.search(r"Total Number of Members:\s*(\d+)", full_text)
    data["totalOrgMembers"] = int(total_members_match.group(1)) if total_members_match else None

    participants_match = re.search(r"cater\s+(\d+)\s+participants", full_text)
    data["participants"] = int(participants_match.group(1)) if participants_match else None

    # ---- Venue ----
    venue_match = re.search(r"\|\s*([^|\n]+?university[^|\n]*)", full_text, re.IGNORECASE)
    data["venue"] = venue_match.group(1).strip() if venue_match else None

    # ---- Total Allocated Budget ----
    budget_match = re.search(r"Total Allocated Budget:\s*[₱P]?\s*([\d,]+)", full_text)
    data["totalBudget"] = budget_match.group(1).replace(",", "") if budget_match else None

    # ---- Organization Adviser ----
    # NOTE: COO and Adviser names currently sit side-by-side on one PDF line
    # with no clear delimiter. This regex grabs a "First M. Last" shaped name
    # at the END of that line. Fragile if names don't fit that exact shape —
    # recommend adding an explicit "Adviser Name:" label to the template for
    # a fully reliable long-term fix.
    noted_by_match = re.search(r"Noted by:\s*\n(.+)\n", full_text)
    data["adviserName"] = None
    if noted_by_match:
        name_match = re.search(r"([A-Z][a-z]+\s[A-Z]\.\s[A-Z][a-z]+)$", noted_by_match.group(1))
        data["adviserName"] = name_match.group(1).strip() if name_match else None

    # ---- Objectives ----
    obj_match = re.search(r"core objectives:\s*(.+?)Program Education", full_text, re.DOTALL)
    if obj_match:
        bullets = re.split(r"●|•", obj_match.group(1))
        data["objectives"] = [b.strip().replace("\n", " ") for b in bullets if b.strip()]
    else:
        data["objectives"] = []

    # ---- PEO write-up ----
    # Heading wording can vary slightly ("Program Education Objective (PEO)"
    # vs "Program Education Objective/s (PEO) Satisfied"), so match loosely
    # up to end-of-line rather than the exact heading text.
    peo_match = re.search(
        r"Program Education Objective.*?\(PEO\).*?\n(.+?)\n\s*Mapúa Core Values",
        full_text, re.DOTALL
    )
    data["peoWriteup"] = re.sub(r"\s+", " ", peo_match.group(1)).strip() if peo_match else None

    # ---- Core Values write-up ----
    core_values_match = re.search(
        r"Mapúa Core Values Alignment\s*(.+?)\n\s*Guidelines",
        full_text, re.DOTALL
    )
    data["coreValuesWriteup"] = re.sub(r"\s+", " ", core_values_match.group(1)).strip() if core_values_match else None

    # ---- AV Equipment table + Room ----
    # The table has a merged title row above the real header (e.g.
    # ['AV Equipment', None] before ['Item', 'Quantity']), and the Room
    # value lives as extra rows in this SAME table (a ['Room', None] marker
    # row followed by a row whose first cell is the room name) rather than
    # as a separate table or plain text. We scan every row rather than
    # assuming table[0] is the header, since that title row shifts things
    # down by one.
    equipment = []
    room = None
    for page_tables in tables_by_page:
        for table in page_tables:
            if not table:
                continue
            header_idx = None
            for i, row in enumerate(table):
                cells = [c.strip() if c else "" for c in row]
                if "Item" in cells and "Quantity" in cells:
                    header_idx = i
                    break
            if header_idx is None:
                continue  # not the AV Equipment table

            reading_room = False
            for row in table[header_idx + 1:]:
                if not row or not row[0]:
                    continue
                first_cell = row[0].strip()
                second_cell = (row[1] or "").strip() if len(row) > 1 else ""

                if first_cell == "Room":
                    reading_room = True
                    continue
                if reading_room:
                    room = first_cell
                    reading_room = False
                    continue
                if second_cell.isdigit():
                    equipment.append({"item": first_cell, "quantity": int(second_cell)})

    data["avEquipment"] = equipment
    data["avRoom"] = room

    return data


if __name__ == "__main__":
    import json

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "input/proposal.pdf"
    result = extract_proposal(pdf_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
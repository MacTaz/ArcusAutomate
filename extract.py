"""
extract.py
----------
Parses the AWS-SBG Arcus Event Proposal PDF (input/proposal.pdf) into a structured dictionary.
This data is the source of truth consumed by avr.py and saaf.py.

Extraction Rules:
- Matches exact expected field labels and formats.
- Enforces numeric validation for participants, budget, and equipment quantities.
- Collects format errors into strict_errors to report validation issues cleanly.
"""

import pdfplumber
import re


class ProposalFormatError(Exception):
    """Raised when a required, exactly-labeled field cannot be found."""


def _require_match(pattern: str, text: str, field_name: str, flags=0,
                    strict_errors: list = None, required: bool = True):
    """
    Executes an anchored regex match. On failure:
      - Appends an error message to strict_errors if required and provided.
      - Raises ProposalFormatError if required and strict_errors is None.
    """
    m = re.search(pattern, text, flags)
    if m is None:
        msg = f"Required field '{field_name}' not found or not in exact expected format."
        if required:
            if strict_errors is not None:
                strict_errors.append(msg)
            else:
                raise ProposalFormatError(msg)
        return None
    return m


def extract_proposal(pdf_path: str, strict: bool = True) -> dict:
    """
    Parses the event proposal PDF and returns a structured dictionary of event details.
    """
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        tables_by_page = [page.extract_tables() for page in pdf.pages]

    data = {}
    strict_errors = []

    # ---- Event Title ----
    # Title appears directly above the 'Date:' line
    title_match = _require_match(
        r"^(.+?)\n\s*Date:\s", full_text, "Event Title (before 'Date:')",
        flags=re.DOTALL | re.MULTILINE, strict_errors=strict_errors
    )
    data["eventTitle"] = title_match.group(1).strip().replace("\n", " ") if title_match else None

    # ---- Date ----
    date_match = _require_match(
        r"^Date:[ \t]+(.+)$", full_text, "Date:",
        flags=re.MULTILINE, strict_errors=strict_errors
    )
    data["date"] = date_match.group(1).strip() if date_match else None

    # ---- Time ----
    time_match = _require_match(
        r"^Time:[ \t]+(.+)$", full_text, "Time:",
        flags=re.MULTILINE, strict_errors=strict_errors
    )
    data["time_raw"] = time_match.group(1).strip() if time_match else None

    data["startTime"] = data["endTime"] = None
    if data["time_raw"]:
        # Extract H:MM AM/PM times
        times = re.findall(r"\b\d{1,2}:\d{2}\s*[AaPp][Mm]\b", data["time_raw"])
        if len(times) < 2:
            strict_errors.append(
                f"Time: field does not contain two valid H:MM AM/PM times "
                f"(found: {data['time_raw']!r})"
            )
        data["startTime"] = times[0] if len(times) > 0 else None
        data["endTime"] = times[1] if len(times) > 1 else None

    # ---- Activity Classification ----
    level_match = _require_match(
        r"^Activity Level:[ \t]+(.+)$", full_text, "Activity Level:",
        flags=re.MULTILINE, strict_errors=strict_errors
    )
    data["activityLevel"] = level_match.group(1).strip() if level_match else None
    if data["activityLevel"] and re.search(r"[,/;]| and ", data["activityLevel"]):
        strict_errors.append("Activity Level: appears to contain multiple values.")

    type_match = _require_match(
        r"^Activity Type:[ \t]+(.+)$", full_text, "Activity Type:",
        flags=re.MULTILINE, strict_errors=strict_errors
    )
    data["activityType"] = type_match.group(1).strip() if type_match else None
    if data["activityType"] and re.search(r"[,/;]| and ", data["activityType"]):
        strict_errors.append("Activity Type: appears to contain multiple values.")

    # ---- Total Org Members ----
    total_members_match = _require_match(
        r"^Total Number of Members:[ \t]+(\d+)\b", full_text,
        "Total Number of Members:", flags=re.MULTILINE, strict_errors=strict_errors
    )
    data["totalOrgMembers"] = int(total_members_match.group(1)) if total_members_match else None

    # ---- Participants ----
    participants_match = _require_match(
        r"\bcater\s+(\d+)\s+participants\b", full_text, "'cater [NUMBER] participants' statement",
        strict_errors=strict_errors
    )
    data["participants"] = int(participants_match.group(1)) if participants_match else None

    # ---- Venue ----
    venue_match = _require_match(
        r"\|\s*([^|\n]*\bUniversity\b[^|\n]*)\|", full_text, "Venue (must contain 'University')",
        flags=re.IGNORECASE, strict_errors=strict_errors, required=False
    )
    if venue_match is None:
        venue_match = re.search(r"^(.*\bUniversity\b.*)$", full_text, re.IGNORECASE | re.MULTILINE)
        if venue_match is None:
            strict_errors.append("Venue containing 'University' not found.")
    data["venue"] = venue_match.group(1).strip() if venue_match else None

    # ---- Total Allocated Budget ----
    budget_match = _require_match(
        r"^Total Allocated Budget:[ \t]*[₱P]?\s*([\d,]+(?:\.\d+)?)\b", full_text,
        "Total Allocated Budget:", flags=re.MULTILINE, strict_errors=strict_errors
    )
    data["totalBudget"] = budget_match.group(1).replace(",", "") if budget_match else None

    # ---- Objectives ----
    main_obj_match = _require_match(
        r"^Main Objective\s*\n(.+?)(?=^Project Proponents|^Target Proponents|^Description)",
        full_text, "Main Objective",
        flags=re.DOTALL | re.MULTILINE | re.IGNORECASE, strict_errors=strict_errors
    )
    if main_obj_match:
        raw_obj_text = re.sub(r"\s+", " ", main_obj_match.group(1)).strip()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_obj_text) if s.strip()]
        data["objectives"] = sentences[:2]
        if not data["objectives"]:
            strict_errors.append("'Main Objective' section found, but no sentences extracted.")
    else:
        obj_match = re.search(
            r"^(?:.*\b)?core objectives:\s*\n(.+?)(?=^Program Education Objective)",
            full_text, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE
        )
        if obj_match:
            bullets = re.split(r"●|•", obj_match.group(1))
            data["objectives"] = [b.strip().replace("\n", " ") for b in bullets if b.strip()][:2]
        else:
            data["objectives"] = []

    # ---- PEO Write-up ----
    peo_match = _require_match(
        r"^Program Education Objective.*?\(PEO\).*?$\s*\n(.+?)(?=^\s*Mapúa Core Values)",
        full_text, "Program Education Objective ... (PEO)",
        flags=re.DOTALL | re.MULTILINE, strict_errors=strict_errors
    )
    data["peoWriteup"] = re.sub(r"\s+", " ", peo_match.group(1)).strip() if peo_match else None

    # ---- Core Values Write-up ----
    core_values_match = _require_match(
        r"^Mapúa Core Values Alignment\s*\n?(.+?)(?=^Guidelines)", full_text,
        "Mapúa Core Values Alignment", flags=re.DOTALL | re.MULTILINE, strict_errors=strict_errors
    )
    data["coreValuesWriteup"] = re.sub(r"\s+", " ", core_values_match.group(1)).strip() if core_values_match else None

    # ---- AV Equipment Table + Room ----
    equipment = []
    room = None
    found_table = False

    for page_tables in tables_by_page:
        for table in page_tables:
            if not table:
                continue
            header_idx = None
            for i, row in enumerate(table):
                cells = [c.strip() if c else "" for c in row]
                non_empty = [c for c in cells if c]
                if len(non_empty) >= 2 and non_empty[0] == "Item" and non_empty[1] == "Quantity":
                    header_idx = i
                    break
            if header_idx is None:
                continue

            found_table = True
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
                if not second_cell:
                    continue
                if not second_cell.isdigit():
                    strict_errors.append(
                        f"AV Equipment row '{first_cell}' has a non-numeric "
                        f"Quantity value: {second_cell!r}."
                    )
                    continue
                equipment.append({"item": first_cell, "quantity": int(second_cell)})

    if not found_table:
        strict_errors.append("AV Equipment table with exact 'Item' / 'Quantity' headers not found.")
    if room is None:
        strict_errors.append("Room label/value not found in the AV Equipment table.")

    data["avEquipment"] = equipment
    data["avRoom"] = room

    data["strict_errors"] = strict_errors
    data["is_valid"] = len(strict_errors) == 0

    if strict and strict_errors:
        raise ProposalFormatError(
            "Proposal failed strict format validation:\n- " + "\n- ".join(strict_errors)
        )

    return data


if __name__ == "__main__":
    import json
    import sys

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "input/proposal.pdf"
    result = extract_proposal(pdf_path, strict=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
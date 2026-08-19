"""
saaf.py
-------
Populates templates/SAAF.pdf directly using PyMuPDF (fitz).

Inserts text and checkboxes onto specific coordinates extracted from the SAAF form template,
handling multiline text wrapping, font scaling, and signature line placement.
"""

import datetime
import os
import fitz

FONT_SIZE = 9

# Shared font size for multiline text blocks (Objectives, Core Values, and PEO)
# to maintain visual consistency across sections.
MULTILINE_FONT_SIZE = 7.5

INDIVIDUAL_CONTRIBUTION = "0"


# ---------------------------------------------------------------------------
# Form Coordinates (Point rectangles: [x0, top, x1, bottom])
# ---------------------------------------------------------------------------

CHECKBOXES = {
    "Co-Curricular": [46.2, 108.0, 55.8, 115.8],
    "Extra-Curricular": [46.2, 118.8, 55.8, 126.6],
    "Major": [256.8, 108.0, 266.4, 115.8],
    "Minor": [256.8, 118.8, 266.4, 126.6],

    # Institutional Vision, Mission, and Formation Goals checkboxes
    "MissionStatement1": [46.5, 352.6, 56.1, 360.4],
    "MissionStatement2": [46.5, 363.4, 56.1, 371.2],
    "MissionStatement3": [46.5, 374.2, 56.1, 382.0],
}


FIELDS = {
    "totalOrgMembers": [459.0, 118.8, 567.0, 127.9],
    "applicantNameStudentNo": [157.6, 161.7, 329.0, 169.7],
    "programAndYear": [393.0, 161.7, 540.2, 169.7],
    "dateOfSubmission": [148.6, 170.7, 323.0, 178.7],
    "positionOfApplicant": [414.2, 170.7, 540.1, 178.7],
    "orgCourseSection": [202.6, 180.0, 540.1, 188.0],
    "titleAndNature": [184.6, 218.0, 540.1, 226.0],
    "objectivesLine1": [153.1, 235.8, 540.1, 243.8],
    "objectivesLine2": [153.1, 245.0, 540.1, 253.0],
    "venue": [72.0, 254.0, 540.1, 262.0],
    "date": [66.5, 271.8, 222.1, 279.8],
    "day": [243.3, 271.8, 385.4, 279.8],
    "time": [410.1, 271.8, 539.0, 279.8],
    "participants": [166.6, 281.0, 540.1, 289.0],
    "individualContribution": [167.4, 290.3, 332.0, 298.3],
    "proposedBudget": [484.5, 290.3, 573.4, 298.3],
    "coreValuesLine1": [45.0, 410.8, 539.0, 418.8],
    "coreValuesLine2": [45.0, 420.0, 539.1, 428.1],
    "coreValuesLine3": [45.0, 429.3, 539.0, 437.3],
    "peoLine1": [45.0, 456.1, 539.0, 464.1],
    "peoLine2": [45.0, 465.3, 539.0, 473.3],
    "peoLine3": [45.0, 474.6, 539.0, 482.6],
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _compute_day(date_str):
    """
    Parses a date string (e.g., 'August 28, 2026') and returns the day of the week.
    """
    if not date_str:
        return ""

    cleaned = date_str.split("(")[0].strip()

    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.datetime.strptime(cleaned, fmt).strftime("%A")
        except ValueError:
            pass

    return ""


def _wrap_at_size(text, box_width_pts, font_size):
    """
    Word-wraps `text` into lines fitting within `box_width_pts` using actual glyph widths at `font_size`.
    """
    words = str(text).split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if fitz.get_text_length(candidate, fontname="helv", fontsize=font_size) <= box_width_pts:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    return lines


def _wrap_to_lines(text, n_lines, box_width_pts, font_size=FONT_SIZE, min_font_size=5.0):
    """
    Fits `text` into exactly `n_lines` lines of width `box_width_pts`.
    Dynamically scales down font size if text exceeds line limits, adding an ellipsis if truncated.
    """
    if not text:
        return [""] * n_lines, font_size

    size = font_size
    wrapped = _wrap_at_size(text, box_width_pts, size)

    while len(wrapped) > n_lines and size > min_font_size:
        size = round(size - 0.25, 2)
        wrapped = _wrap_at_size(text, box_width_pts, size)

    if len(wrapped) > n_lines:
        print(
            f"  [warn] Text still didn't fit at {size}pt, truncating with ellipsis: "
            f"{str(text)[:80]}..."
        )
        lines = wrapped[:n_lines]
        last = lines[-1]
        while fitz.get_text_length(last + "…", fontname="helv", fontsize=size) > box_width_pts and len(last) > 1:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    else:
        lines = wrapped
        print(f"  [info] Fit text into {len(lines)}/{n_lines} lines at {size}pt")

    while len(lines) < n_lines:
        lines.append("")

    return lines, size


def _insert_text(page, box, text, font_size=FONT_SIZE, align=fitz.TEXT_ALIGN_LEFT, top_pad=2, bottom_pad=6, label=None, debug=False):
    """
    Inserts formatted text into a PDF bounding box rectangle.
    If debug=True, draws the box outline and field label on the page for box placement testing.
    """
    x0, top, x1, bottom = box

    rect = fitz.Rect(x0, top - top_pad, x1, bottom + bottom_pad)

    if debug:
        page.draw_rect(rect, color=(1, 0, 0), width=0.4)
        if label:
            page.insert_text(fitz.Point(x0, top - 3), label, fontsize=4, fontname="helv", color=(1, 0, 0))

    if text is None:
        return

    text = str(text).strip()
    if not text:
        return

    result = page.insert_textbox(
        rect,
        text,
        fontsize=font_size,
        fontname="helv",
        color=(0, 0, 0),
        align=align,
        lineheight=1.15,
    )

    verify = page.get_text("text", clip=rect).strip()
    print(f"    [text] '{text[:50]}' box={rect} result={result} verify_readback={verify[:50]!r}")

    if result < 0:
        print(f"    [ERROR] Text did not fit in box: '{text}'")

    if not verify:
        print(f"    [ERROR] Nothing was actually written to the page for box={rect} (intended text: '{text}')")


def _insert_signature_name(page, line_x0, line_x1, line_y, name, font_size=10.5):
    """
    Renders text centered horizontally over a signature line [line_x0, line_x1]
    with its baseline sitting 1.5pt above line_y.
    """
    if not name:
        return
    text = str(name).strip()
    center_x = (line_x0 + line_x1) / 2.0
    text_len = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
    x = center_x - (text_len / 2.0)
    baseline_y = line_y - 1.5
    page.insert_text(fitz.Point(x, baseline_y), text, fontsize=font_size, fontname="helv", color=(0, 0, 0))


def _insert_checkbox(page, box, label=None, debug=False):
    """
    Draws an 'X' mark inside a specified checkbox bounding box.
    """
    x0, top, x1, bottom = box

    if debug:
        page.draw_rect(fitz.Rect(x0, top, x1, bottom), color=(0, 0, 1), width=0.4)
        if label:
            page.insert_text(fitz.Point(x0, top - 2), label, fontsize=4, fontname="helv", color=(0, 0, 1))

    margin = 1.5
    p1 = fitz.Point(x0 + margin, top + margin)
    p2 = fitz.Point(x1 - margin, bottom - margin)
    p3 = fitz.Point(x1 - margin, top + margin)
    p4 = fitz.Point(x0 + margin, bottom - margin)

    page.draw_line(p1, p2, color=(0, 0, 0), width=0.8)
    page.draw_line(p3, p4, color=(0, 0, 0), width=0.8)


# ---------------------------------------------------------------------------
# Main Filling Logic
# ---------------------------------------------------------------------------

def fill(
    event,
    profile,
    template_path="templates/SAAF.pdf",
    output_path="output/SAAF_filled.pdf",
    debug=False,
):
    """
    Populates the SAAF PDF template with extracted event data and applicant profile information.
    """
    print("  -> Opening SAAF template...")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"SAAF template not found: {template_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    doc = fitz.open(template_path)
    if len(doc) < 1:
        doc.close()
        raise RuntimeError("SAAF.pdf contains no pages.")

    page = doc[0]

    print("  -> Filling applicant information...")

    # Applicant information
    _insert_text(
        page,
        FIELDS["applicantNameStudentNo"],
        f"{profile['name']} {profile.get('studentNumber', '')}".strip(),
        label="applicantNameStudentNo",
        debug=debug,
    )
    prog_yr = profile.get("programAndYear") or profile.get("courseSection")
    _insert_text(page, FIELDS["programAndYear"], prog_yr, label="programAndYear", debug=debug)
    _insert_text(page, FIELDS["positionOfApplicant"], profile["position"], label="positionOfApplicant", debug=debug)
    _insert_text(page, FIELDS["orgCourseSection"], profile["organizationName"], label="orgCourseSection", debug=debug)

    # Submission date
    _insert_text(
        page,
        FIELDS["dateOfSubmission"],
        datetime.date.today().strftime("%m/%d/%Y"),
        label="dateOfSubmission",
        debug=debug,
    )

    # Event information
    _insert_text(page, FIELDS["titleAndNature"], event.get("eventTitle"), label="titleAndNature", debug=debug)

    # Objectives
    objs = event.get("objectives") or []
    if isinstance(objs, str):
        obj_text = objs
    else:
        if any(item.endswith((".", "!", "?")) for item in objs):
            obj_text = " ".join(objs)
        else:
            obj_text = "; ".join(objs)

    obj_width = FIELDS["objectivesLine1"][2] - FIELDS["objectivesLine1"][0]
    obj_lines, obj_font_size = _wrap_to_lines(
        obj_text,
        2,
        obj_width,
        font_size=MULTILINE_FONT_SIZE,
        min_font_size=MULTILINE_FONT_SIZE,
    )

    _insert_text(page, FIELDS["objectivesLine1"], obj_lines[0], font_size=obj_font_size, label="objectivesLine1", debug=debug)
    _insert_text(page, FIELDS["objectivesLine2"], obj_lines[1], font_size=obj_font_size, label="objectivesLine2", debug=debug)

    # Venue, Date, Day, Time, Participants, Budget, Org Members, Contribution
    _insert_text(page, FIELDS["venue"], event.get("venue"), label="venue", debug=debug)
    _insert_text(page, FIELDS["date"], event.get("date"), label="date", debug=debug)
    _insert_text(page, FIELDS["day"], _compute_day(event.get("date")), label="day", debug=debug)
    _insert_text(
        page,
        FIELDS["time"],
        event.get("time_raw") or event.get("startTime"),
        label="time",
        debug=debug,
    )
    _insert_text(page, FIELDS["participants"], event.get("participants"), label="participants", debug=debug)
    _insert_text(page, FIELDS["proposedBudget"], event.get("totalBudget"), label="proposedBudget", debug=debug)
    _insert_text(page, FIELDS["totalOrgMembers"], event.get("totalOrgMembers"), label="totalOrgMembers", debug=debug)
    _insert_text(
        page,
        FIELDS["individualContribution"],
        INDIVIDUAL_CONTRIBUTION,
        label="individualContribution",
        debug=debug,
    )

    # Core Values
    cv_text = event.get("coreValuesWriteup") or ""
    cv_width = FIELDS["coreValuesLine1"][2] - FIELDS["coreValuesLine1"][0]
    cv_lines, cv_font_size = _wrap_to_lines(
        cv_text,
        3,
        cv_width,
        font_size=MULTILINE_FONT_SIZE,
        min_font_size=MULTILINE_FONT_SIZE,
    )

    _insert_text(page, FIELDS["coreValuesLine1"], cv_lines[0], font_size=cv_font_size, label="coreValuesLine1", debug=debug)
    _insert_text(page, FIELDS["coreValuesLine2"], cv_lines[1], font_size=cv_font_size, label="coreValuesLine2", debug=debug)
    _insert_text(page, FIELDS["coreValuesLine3"], cv_lines[2], font_size=cv_font_size, label="coreValuesLine3", debug=debug)

    # PEO / PO
    peo_text = event.get("peoWriteup") or ""
    peo_width = FIELDS["peoLine1"][2] - FIELDS["peoLine1"][0]
    peo_lines, peo_font_size = _wrap_to_lines(
        peo_text,
        3,
        peo_width,
        font_size=MULTILINE_FONT_SIZE,
        min_font_size=MULTILINE_FONT_SIZE,
    )

    _insert_text(page, FIELDS["peoLine1"], peo_lines[0], font_size=peo_font_size, label="peoLine1", debug=debug)
    _insert_text(page, FIELDS["peoLine2"], peo_lines[1], font_size=peo_font_size, label="peoLine2", debug=debug)
    _insert_text(page, FIELDS["peoLine3"], peo_lines[2], font_size=peo_font_size, label="peoLine3", debug=debug)

    # Organizers & Adviser Signature Names
    _insert_signature_name(page, 48.525, 266.95, 566.5, profile.get("name"), font_size=10.5)
    _insert_signature_name(page, 303.13, 521.50, 566.5, event.get("adviserName"), font_size=10.5)

    # Activity Type Checkbox
    activity_type = (event.get("activityType") or "").strip().lower()
    if "extra" in activity_type:
        print("  -> Marking Extra-Curricular")
        _insert_checkbox(page, CHECKBOXES["Extra-Curricular"], label="Extra-Curricular", debug=debug)
    elif "co-curricular" in activity_type or activity_type == "co":
        print("  -> Marking Co-Curricular")
        _insert_checkbox(page, CHECKBOXES["Co-Curricular"], label="Co-Curricular", debug=debug)
    else:
        print(f"  [warn] Unknown activity type: {event.get('activityType')}")

    # Activity Level Checkbox
    activity_level = (event.get("activityLevel") or "").strip().lower()
    if activity_level == "major":
        print("  -> Marking Major")
        _insert_checkbox(page, CHECKBOXES["Major"], label="Major", debug=debug)
    elif activity_level == "minor":
        print("  -> Marking Minor")
        _insert_checkbox(page, CHECKBOXES["Minor"], label="Minor", debug=debug)
    else:
        print(f"  [warn] Unknown activity level: {event.get('activityLevel')}")

    # Institutional Vision / Mission / Formation Goals (All 3 checked)
    print("  -> Marking all 3 mission statement checkboxes")
    _insert_checkbox(page, CHECKBOXES["MissionStatement1"], label="MissionStatement1", debug=debug)
    _insert_checkbox(page, CHECKBOXES["MissionStatement2"], label="MissionStatement2", debug=debug)
    _insert_checkbox(page, CHECKBOXES["MissionStatement3"], label="MissionStatement3", debug=debug)

    # Save output PDF
    print("  -> Saving SAAF...")
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    print(f"  -> SAAF created: {output_path}")
    return output_path


if __name__ == "__main__":
    print("saaf.py is a module used by main.py — run `python main.py` instead.")
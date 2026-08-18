"""
saaf.py
-------
Fills templates/SAAF.pdf directly using PyMuPDF.

No dependency on /mnt/skills or external PDF skill scripts.
"""

import fitz
import datetime
import textwrap
import os


PAGE_WIDTH = 612.0
PAGE_HEIGHT = 936.0
FONT_SIZE = 8

INDIVIDUAL_CONTRIBUTION = "0"


# ---------------------------------------------------------------------------
# Coordinates from SAAF.pdf
# ---------------------------------------------------------------------------

CHECKBOXES = {
    "Co-Curricular": [46.2, 108.0, 55.8, 115.8],
    "Extra-Curricular": [46.2, 118.8, 55.8, 126.6],
    "Major": [256.8, 108.0, 266.4, 115.8],
    "Minor": [256.8, 118.8, 266.4, 126.6],
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
# Helpers
# ---------------------------------------------------------------------------

def _compute_day(date_str):
    if not date_str:
        return ""

    cleaned = date_str.split("(")[0].strip()

    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.datetime.strptime(
                cleaned, fmt
            ).strftime("%A")
        except ValueError:
            pass

    return ""


def _wrap_to_lines(text, n_lines, box_width_pts, font_size=FONT_SIZE):
    if not text:
        return [""] * n_lines

    # Approximate number of characters that fit.
    chars_per_line = max(
        1,
        int(box_width_pts / (font_size * 0.52))
    )

    wrapped = textwrap.wrap(
        str(text),
        width=chars_per_line,
        break_long_words=False,
        break_on_hyphens=False,
    )

    if len(wrapped) > n_lines:
        print(
            f"  [warn] Text truncated to {n_lines} lines: "
            f"{str(text)[:80]}..."
        )

    lines = wrapped[:n_lines]

    while len(lines) < n_lines:
        lines.append("")

    return lines


def _insert_text(page, box, text, font_size=FONT_SIZE):
    """
    Inserts text inside a PDF-coordinate rectangle.

    The original coordinates use:
        x0, top, x1, bottom

    PyMuPDF also uses top-left based coordinates,
    so they can be used directly.
    """

    if text is None:
        return

    text = str(text).strip()

    if not text:
        return

    x0, top, x1, bottom = box

    rect = fitz.Rect(
        x0,
        top,
        x1,
        bottom
    )

    # Position text vertically inside the box.
    page.insert_textbox(
        rect,
        text,
        fontsize=font_size,
        fontname="helv",
        color=(0, 0, 0),
        align=fitz.TEXT_ALIGN_LEFT,
    )


def _insert_checkbox(page, box):
    """
    Draw an X inside the checkbox.
    """

    x0, top, x1, bottom = box

    margin = 1.5

    p1 = fitz.Point(
        x0 + margin,
        top + margin
    )

    p2 = fitz.Point(
        x1 - margin,
        bottom - margin
    )

    p3 = fitz.Point(
        x1 - margin,
        top + margin
    )

    p4 = fitz.Point(
        x0 + margin,
        bottom - margin
    )

    page.draw_line(
        p1,
        p2,
        color=(0, 0, 0),
        width=0.8,
    )

    page.draw_line(
        p3,
        p4,
        color=(0, 0, 0),
        width=0.8,
    )


# ---------------------------------------------------------------------------
# Main filling logic
# ---------------------------------------------------------------------------

def fill(
    event,
    profile,
    template_path="templates/SAAF.pdf",
    output_path="output/SAAF_filled.pdf",
):

    print("  -> Opening SAAF template...")

    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"SAAF template not found: {template_path}"
        )

    os.makedirs(
        os.path.dirname(output_path) or ".",
        exist_ok=True
    )

    # Open template.
    doc = fitz.open(template_path)

    if len(doc) < 1:
        doc.close()
        raise RuntimeError("SAAF.pdf contains no pages.")

    page = doc[0]

    print("  -> Filling applicant information...")

    # -----------------------------------------------------------------------
    # Applicant information
    # -----------------------------------------------------------------------

    _insert_text(
        page,
        FIELDS["applicantNameStudentNo"],
        f"{profile['name']} {profile.get('studentNumber', '')}".strip()
    )

    _insert_text(
        page,
        FIELDS["programAndYear"],
        profile["programAndYear"]
    )

    _insert_text(
        page,
        FIELDS["positionOfApplicant"],
        profile["position"]
    )

    _insert_text(
        page,
        FIELDS["orgCourseSection"],
        profile["organizationName"]
    )

    # -----------------------------------------------------------------------
    # Submission date
    # -----------------------------------------------------------------------

    _insert_text(
        page,
        FIELDS["dateOfSubmission"],
        datetime.date.today().strftime("%m/%d/%Y")
    )

    # -----------------------------------------------------------------------
    # Event information
    # -----------------------------------------------------------------------

    _insert_text(
        page,
        FIELDS["titleAndNature"],
        event.get("eventTitle")
    )

    # Objectives
    obj_text = "; ".join(
        event.get("objectives") or []
    )

    obj_width = (
        FIELDS["objectivesLine1"][2]
        - FIELDS["objectivesLine1"][0]
    )

    obj_lines = _wrap_to_lines(
        obj_text,
        2,
        obj_width
    )

    _insert_text(
        page,
        FIELDS["objectivesLine1"],
        obj_lines[0]
    )

    _insert_text(
        page,
        FIELDS["objectivesLine2"],
        obj_lines[1]
    )

    # Venue
    _insert_text(
        page,
        FIELDS["venue"],
        event.get("venue")
    )

    # Date
    _insert_text(
        page,
        FIELDS["date"],
        event.get("date")
    )

    # Day
    _insert_text(
        page,
        FIELDS["day"],
        _compute_day(event.get("date"))
    )

    # Time
    _insert_text(
        page,
        FIELDS["time"],
        event.get("time_raw")
        or event.get("startTime")
    )

    # Participants
    _insert_text(
        page,
        FIELDS["participants"],
        event.get("participants")
    )

    # Budget
    _insert_text(
        page,
        FIELDS["proposedBudget"],
        event.get("totalBudget")
    )

    # Organization members
    _insert_text(
        page,
        FIELDS["totalOrgMembers"],
        event.get("totalOrgMembers")
    )

    # Individual contribution
    _insert_text(
        page,
        FIELDS["individualContribution"],
        INDIVIDUAL_CONTRIBUTION
    )

    # -----------------------------------------------------------------------
    # Core Values
    # -----------------------------------------------------------------------

    cv_text = event.get("coreValuesWriteup") or ""

    cv_width = (
        FIELDS["coreValuesLine1"][2]
        - FIELDS["coreValuesLine1"][0]
    )

    cv_lines = _wrap_to_lines(
        cv_text,
        3,
        cv_width
    )

    _insert_text(
        page,
        FIELDS["coreValuesLine1"],
        cv_lines[0]
    )

    _insert_text(
        page,
        FIELDS["coreValuesLine2"],
        cv_lines[1]
    )

    _insert_text(
        page,
        FIELDS["coreValuesLine3"],
        cv_lines[2]
    )

    # -----------------------------------------------------------------------
    # PEO / PO
    # -----------------------------------------------------------------------

    peo_text = event.get("peoWriteup") or ""

    peo_width = (
        FIELDS["peoLine1"][2]
        - FIELDS["peoLine1"][0]
    )

    peo_lines = _wrap_to_lines(
        peo_text,
        3,
        peo_width
    )

    _insert_text(
        page,
        FIELDS["peoLine1"],
        peo_lines[0]
    )

    _insert_text(
        page,
        FIELDS["peoLine2"],
        peo_lines[1]
    )

    _insert_text(
        page,
        FIELDS["peoLine3"],
        peo_lines[2]
    )

    # -----------------------------------------------------------------------
    # Activity type checkbox
    # -----------------------------------------------------------------------

    activity_type = (
        event.get("activityType") or ""
    ).strip().lower()

    if "extra" in activity_type:

        print("  -> Marking Extra-Curricular")

        _insert_checkbox(
            page,
            CHECKBOXES["Extra-Curricular"]
        )

    elif (
        "co-curricular" in activity_type
        or activity_type == "co"
    ):

        print("  -> Marking Co-Curricular")

        _insert_checkbox(
            page,
            CHECKBOXES["Co-Curricular"]
        )

    else:

        print(
            f"  [warn] Unknown activity type: "
            f"{event.get('activityType')}"
        )

    # -----------------------------------------------------------------------
    # Activity level checkbox
    # -----------------------------------------------------------------------

    activity_level = (
        event.get("activityLevel") or ""
    ).strip().lower()

    if activity_level == "major":

        print("  -> Marking Major")

        _insert_checkbox(
            page,
            CHECKBOXES["Major"]
        )

    elif activity_level == "minor":

        print("  -> Marking Minor")

        _insert_checkbox(
            page,
            CHECKBOXES["Minor"]
        )

    else:

        print(
            f"  [warn] Unknown activity level: "
            f"{event.get('activityLevel')}"
        )

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------

    print("  -> Saving SAAF...")

    # Use garbage=4 to clean unused objects.
    doc.save(
        output_path,
        garbage=4,
        deflate=True
    )

    doc.close()

    print(f"  -> SAAF created: {output_path}")

    return output_path


if __name__ == "__main__":
    print(
        "saaf.py is a module used by main.py — "
        "run `python main.py` instead."
    )
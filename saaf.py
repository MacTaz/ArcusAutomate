"""
saaf.py
-------
Fills templates/SAAF.pdf directly using PyMuPDF.

No dependency on /mnt/skills or external PDF skill scripts.
"""

import fitz
import datetime
import os


FONT_SIZE = 8

# Fixed font size shared by Objectives, Core Values, and PEO so they all
# render visually consistently instead of each independently shrinking to
# fit its own text. Anything that doesn't fit at this size within its
# field's line count gets truncated with an ellipsis rather than shrunk
# further — see _wrap_to_lines(min_font_size=font_size).
MULTILINE_FONT_SIZE = 7.5

INDIVIDUAL_CONTRIBUTION = "0"


# ---------------------------------------------------------------------------
# Coordinates from SAAF.pdf
# ---------------------------------------------------------------------------

CHECKBOXES = {
    "Co-Curricular": [46.2, 108.0, 55.8, 115.8],
    "Extra-Curricular": [46.2, 118.8, 55.8, 126.6],
    "Major": [256.8, 108.0, 266.4, 115.8],
    "Minor": [256.8, 118.8, 266.4, 126.6],

    # "ALIGNMENT WITH INSTITUTIONAL VISION, MISSION AND FORMATION GOALS"
    # section — the 3 mission-statement checkboxes, always checked per
    # request (this SAAF is always filed under all 3 institutional goals).
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


def _wrap_at_size(text, box_width_pts, font_size):
    """
    Word-wrap `text` to `box_width_pts` using the ACTUAL rendered width of
    each candidate line at `font_size` (via fitz.get_text_length), rather
    than a crude chars-per-line guess. Returns a list of lines.
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
    Fit `text` into exactly `n_lines` lines of width `box_width_pts`.

    Rather than truncating at a fixed font size (which silently drops
    everything past line n_lines), this shrinks the font size step-by-step
    until the full text actually fits in the available lines. Only if it
    still doesn't fit at min_font_size do we truncate, and in that case we
    add an ellipsis so the cut is visible on the page instead of silent.

    Returns (lines, font_size_used).
    """
    if not text:
        return [""] * n_lines, font_size

    size = font_size
    wrapped = _wrap_at_size(text, box_width_pts, size)

    while len(wrapped) > n_lines and size > min_font_size:
        size = round(size - 0.25, 2)
        wrapped = _wrap_at_size(text, box_width_pts, size)

    if len(wrapped) > n_lines:
        # Even at the smallest allowed font size it doesn't fit.
        # Truncate visibly (with an ellipsis) instead of silently.
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


def _insert_text(page, box, text, font_size=FONT_SIZE, label=None, debug=False):
    """
    Insert text into a PDF rectangle and report whether it actually fit.

    If debug=True, draws the rect's outline and a small label (the FIELDS
    key) on the page regardless of whether text was supplied — this is
    for visually checking box placement/size against the template.
    """

    x0, top, x1, bottom = box

    # Give the text more vertical room than the raw coordinate box.
    # NOTE: PyMuPDF's insert_textbox() needs slightly more than
    # 1.2x-1.7x the font size in height to fit even a single line
    # (exact factor depends on font metrics). The old "-1 / +4" padding
    # (only 5pt total) was cutting it by a hair for 8pt text — every
    # single-line field with an 8pt-tall template box was landing at
    # 13.0pt available vs. ~13.38pt needed, so insert_textbox silently
    # wrote NOTHING. Padding is bumped here, and lineheight is pinned
    # explicitly so this doesn't depend on PyMuPDF's internal font-metric
    # calculation (which is what caused the razor-thin, version-fragile
    # shortfall in the first place).
    rect = fitz.Rect(
        x0,
        top - 2,
        x1,
        bottom + 6
    )

    if debug:
        page.draw_rect(rect, color=(1, 0, 0), width=0.4)
        if label:
            page.insert_text(
                fitz.Point(x0, top - 3),
                label,
                fontsize=4,
                fontname="helv",
                color=(1, 0, 0),
            )

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
        align=fitz.TEXT_ALIGN_LEFT,
        lineheight=1.15,
    )

    # Read the rect back to confirm the glyphs actually landed on the page,
    # rather than just trusting insert_textbox's return code.
    verify = page.get_text("text", clip=rect).strip()

    print(
        f"    [text] '{text[:50]}' "
        f"box={rect} result={result} verify_readback={verify[:50]!r}"
    )

    if result < 0:
        print(
            f"    [ERROR] Text did not fit in box: "
            f"'{text}'"
        )

    if not verify:
        print(
            f"    [ERROR] Nothing was actually written to the page for "
            f"box={rect} (intended text: '{text}')"
        )


def _insert_checkbox(page, box, label=None, debug=False):
    """
    Draw an X inside the checkbox.
    """

    x0, top, x1, bottom = box

    if debug:
        page.draw_rect(
            fitz.Rect(x0, top, x1, bottom),
            color=(0, 0, 1),
            width=0.4,
        )
        if label:
            page.insert_text(
                fitz.Point(x0, top - 2),
                label,
                fontsize=4,
                fontname="helv",
                color=(0, 0, 1),
            )

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
    debug=False,
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
        f"{profile['name']} {profile.get('studentNumber', '')}".strip(),
        label="applicantNameStudentNo",
        debug=debug
    )

    _insert_text(
        page,
        FIELDS["programAndYear"],
        profile["programAndYear"],
        label="programAndYear",
        debug=debug
    )

    _insert_text(
        page,
        FIELDS["positionOfApplicant"],
        profile["position"],
        label="positionOfApplicant",
        debug=debug
    )

    _insert_text(
        page,
        FIELDS["orgCourseSection"],
        profile["organizationName"],
        label="orgCourseSection",
        debug=debug
    )

    # -----------------------------------------------------------------------
    # Submission date
    # -----------------------------------------------------------------------

    _insert_text(
        page,
        FIELDS["dateOfSubmission"],
        datetime.date.today().strftime("%m/%d/%Y"),
        label="dateOfSubmission",
        debug=debug
    )

    # -----------------------------------------------------------------------
    # Event information
    # -----------------------------------------------------------------------

    _insert_text(
        page,
        FIELDS["titleAndNature"],
        event.get("eventTitle"),
        label="titleAndNature",
        debug=debug
    )

    # Objectives
    obj_text = "; ".join(
        event.get("objectives") or []
    )

    obj_width = (
        FIELDS["objectivesLine1"][2]
        - FIELDS["objectivesLine1"][0]
    )

    obj_lines, obj_font_size = _wrap_to_lines(
        obj_text,
        2,
        obj_width,
        font_size=MULTILINE_FONT_SIZE,
        min_font_size=MULTILINE_FONT_SIZE,
    )

    _insert_text(
        page,
        FIELDS["objectivesLine1"],
        obj_lines[0],
        font_size=obj_font_size,
        label="objectivesLine1",
        debug=debug
    )

    _insert_text(
        page,
        FIELDS["objectivesLine2"],
        obj_lines[1],
        font_size=obj_font_size,
        label="objectivesLine2",
        debug=debug
    )

    # Venue
    _insert_text(
        page,
        FIELDS["venue"],
        event.get("venue"),
        label="venue",
        debug=debug
    )

    # Date
    _insert_text(
        page,
        FIELDS["date"],
        event.get("date"),
        label="date",
        debug=debug
    )

    # Day
    _insert_text(
        page,
        FIELDS["day"],
        _compute_day(event.get("date")),
        label="day",
        debug=debug
    )

    # Time
    _insert_text(
        page,
        FIELDS["time"],
        event.get("time_raw")
        or event.get("startTime"),
        label="time",
        debug=debug
    )

    # Participants
    _insert_text(
        page,
        FIELDS["participants"],
        event.get("participants"),
        label="participants",
        debug=debug
    )

    # Budget
    _insert_text(
        page,
        FIELDS["proposedBudget"],
        event.get("totalBudget"),
        label="proposedBudget",
        debug=debug
    )

    # Organization members
    _insert_text(
        page,
        FIELDS["totalOrgMembers"],
        event.get("totalOrgMembers"),
        label="totalOrgMembers",
        debug=debug
    )

    # Individual contribution
    _insert_text(
        page,
        FIELDS["individualContribution"],
        INDIVIDUAL_CONTRIBUTION,
        label="individualContribution",
        debug=debug
    )

    # -----------------------------------------------------------------------
    # Core Values
    # -----------------------------------------------------------------------

    cv_text = event.get("coreValuesWriteup") or ""

    cv_width = (
        FIELDS["coreValuesLine1"][2]
        - FIELDS["coreValuesLine1"][0]
    )

    cv_lines, cv_font_size = _wrap_to_lines(
        cv_text,
        3,
        cv_width,
        font_size=MULTILINE_FONT_SIZE,
        min_font_size=MULTILINE_FONT_SIZE,
    )

    _insert_text(
        page,
        FIELDS["coreValuesLine1"],
        cv_lines[0],
        font_size=cv_font_size,
        label="coreValuesLine1",
        debug=debug
    )

    _insert_text(
        page,
        FIELDS["coreValuesLine2"],
        cv_lines[1],
        font_size=cv_font_size,
        label="coreValuesLine2",
        debug=debug
    )

    _insert_text(
        page,
        FIELDS["coreValuesLine3"],
        cv_lines[2],
        font_size=cv_font_size,
        label="coreValuesLine3",
        debug=debug
    )

    # -----------------------------------------------------------------------
    # PEO / PO
    # -----------------------------------------------------------------------

    peo_text = event.get("peoWriteup") or ""

    peo_width = (
        FIELDS["peoLine1"][2]
        - FIELDS["peoLine1"][0]
    )

    peo_lines, peo_font_size = _wrap_to_lines(
        peo_text,
        3,
        peo_width,
        font_size=MULTILINE_FONT_SIZE,
        min_font_size=MULTILINE_FONT_SIZE,
    )

    _insert_text(
        page,
        FIELDS["peoLine1"],
        peo_lines[0],
        font_size=peo_font_size,
        label="peoLine1",
        debug=debug
    )

    _insert_text(
        page,
        FIELDS["peoLine2"],
        peo_lines[1],
        font_size=peo_font_size,
        label="peoLine2",
        debug=debug
    )

    _insert_text(
        page,
        FIELDS["peoLine3"],
        peo_lines[2],
        font_size=peo_font_size,
        label="peoLine3",
        debug=debug
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
            CHECKBOXES["Extra-Curricular"],
            label="Extra-Curricular",
            debug=debug
        )

    elif (
        "co-curricular" in activity_type
        or activity_type == "co"
    ):

        print("  -> Marking Co-Curricular")

        _insert_checkbox(
            page,
            CHECKBOXES["Co-Curricular"],
            label="Co-Curricular",
            debug=debug
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
            CHECKBOXES["Major"],
            label="Major",
            debug=debug
        )

    elif activity_level == "minor":

        print("  -> Marking Minor")

        _insert_checkbox(
            page,
            CHECKBOXES["Minor"],
            label="Minor",
            debug=debug
        )

    else:

        print(
            f"  [warn] Unknown activity level: "
            f"{event.get('activityLevel')}"
        )

    # -----------------------------------------------------------------------
    # Institutional Vision/Mission/Formation Goals — all 3 always checked
    # -----------------------------------------------------------------------

    print("  -> Marking all 3 mission statement checkboxes")

    _insert_checkbox(page, CHECKBOXES["MissionStatement1"],
            label="MissionStatement1",
            debug=debug
        )
    _insert_checkbox(page, CHECKBOXES["MissionStatement2"],
            label="MissionStatement2",
            debug=debug
        )
    _insert_checkbox(page, CHECKBOXES["MissionStatement3"],
            label="MissionStatement3",
            debug=debug
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
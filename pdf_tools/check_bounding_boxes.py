"""
check_bounding_boxes.py
-----------------------
Validates the fields JSON used by ArcusAutomate.

Usage:
    python check_bounding_boxes.py output/_saaf_fields.json
"""

import json
import sys
from pathlib import Path


def validate_box(box, page_width, page_height, name):
    if not isinstance(box, list) or len(box) != 4:
        return f"{name}: must contain [x0, top, x1, bottom]"

    try:
        x0, top, x1, bottom = map(float, box)
    except (TypeError, ValueError):
        return f"{name}: coordinates must be numbers"

    if x0 >= x1:
        return f"{name}: x0 must be less than x1"

    if top >= bottom:
        return f"{name}: top must be less than bottom"

    if x0 < 0 or x1 > page_width:
        return f"{name}: outside horizontal page bounds"

    if top < 0 or bottom > page_height:
        return f"{name}: outside vertical page bounds"

    return None


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_bounding_boxes.py <fields.json>")
        return 2

    fields_path = Path(sys.argv[1])

    if not fields_path.exists():
        print(f"Fields file not found: {fields_path}", file=sys.stderr)
        return 2

    try:
        with fields_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Could not read JSON: {e}", file=sys.stderr)
        return 2

    pages = data.get("pages", [])
    fields = data.get("form_fields", [])

    if not pages:
        print("No pages found.", file=sys.stderr)
        return 2

    page_sizes = {
        int(page["page_number"]): (
            float(page["pdf_width"]),
            float(page["pdf_height"])
        )
        for page in pages
    }

    errors = []

    for index, field in enumerate(fields):
        description = (
            field.get("description")
            or field.get("field_label")
            or f"Field {index}"
        )

        page_number = int(field.get("page_number", 1))

        if page_number not in page_sizes:
            errors.append(
                f"{description}: page {page_number} does not exist"
            )
            continue

        page_width, page_height = page_sizes[page_number]

        for box_name in ("label_bounding_box", "entry_bounding_box"):
            error = validate_box(
                field.get(box_name),
                page_width,
                page_height,
                f"{description} -> {box_name}"
            )

            if error:
                errors.append(error)

        # Check that label and entry boxes don't overlap.
        label = field.get("label_bounding_box")
        entry = field.get("entry_bounding_box")

        if (
            isinstance(label, list)
            and len(label) == 4
            and isinstance(entry, list)
            and len(entry) == 4
        ):
            lx0, lt, lx1, lb = map(float, label)
            ex0, et, ex1, eb = map(float, entry)

            overlaps = (
                lx0 < ex1
                and lx1 > ex0
                and lt < eb
                and lb > et
            )

            if overlaps:
                errors.append(
                    f"{description}: label and entry boxes overlap"
                )

    if errors:
        print("Bounding-box validation FAILED:")

        for error in errors:
            print(f"  - {error}")

        return 2

    print(
        f"Bounding-box validation passed for "
        f"{len(fields)} field(s)."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
fill_pdf_form_with_annotations.py
---------------------------------
Fills a flat PDF by drawing text into the supplied bounding boxes.

Usage:
    python fill_pdf_form_with_annotations.py \
        template.pdf fields.json output.pdf
"""

import json
import sys
from pathlib import Path

import fitz


def fill_pdf(template_path, fields_path, output_path):
    template = Path(template_path)
    fields_file = Path(fields_path)
    output = Path(output_path)

    if not template.exists():
        raise FileNotFoundError(
            f"Template PDF not found: {template}"
        )

    if not fields_file.exists():
        raise FileNotFoundError(
            f"Fields JSON not found: {fields_file}"
        )

    with fields_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    doc = fitz.open(str(template))

    try:
        for field in data.get("form_fields", []):
            page_number = int(
                field.get("page_number", 1)
            )

            page = doc[page_number - 1]

            x0, top, x1, bottom = map(
                float,
                field["entry_bounding_box"]
            )

            text_info = field.get("entry_text", {})

            text = str(
                text_info.get("text", "")
            )

            if not text:
                continue

            font_size = float(
                text_info.get("font_size", 8)
            )

            rect = fitz.Rect(
                x0,
                top,
                x1,
                bottom
            )

            page.insert_textbox(
                rect,
                text,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0),
                align=fitz.TEXT_ALIGN_LEFT,
                overlay=True,
            )

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temp_output = output.with_name(
            output.stem + "_tmp.pdf"
        )

        if temp_output.exists():
            temp_output.unlink()

        doc.save(
            str(temp_output),
            garbage=4,
            deflate=True
        )

        doc.close()

        if output.exists():
            output.unlink()

        temp_output.replace(output)

    except Exception:
        doc.close()
        raise


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python "
            "fill_pdf_form_with_annotations.py "
            "<template.pdf> <fields.json> <output.pdf>"
        )

        return 2

    try:
        fill_pdf(
            sys.argv[1],
            sys.argv[2],
            sys.argv[3]
        )

        print(
            f"Filled PDF written to: {sys.argv[3]}"
        )

        return 0

    except Exception as e:
        print(
            f"PDF filling error: {e}",
            file=sys.stderr
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
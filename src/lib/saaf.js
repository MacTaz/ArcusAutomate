/**
 * saaf.js
 * -------
 * Port of saaf.py using pdf-lib for coordinate-based text/checkbox drawing.
 * Fills the SAAF PDF template by drawing text and X marks at exact coordinates.
 *
 * NOTE on coordinate systems:
 *   PyMuPDF uses top-left origin (y increases downward).
 *   pdf-lib uses bottom-left origin (y increases upward).
 *   Conversion: pdfLibY = pageHeight - pymupdfY
 *
 *   For the SAAF template (Letter: 612 x 792 pt or A4-ish), we use the page
 *   height reported by pdf-lib. All coordinates below are stored as
 *   [x0, top, x1, bottom] in PyMuPDF space and converted at draw time.
 */

import { PDFDocument, rgb, StandardFonts } from "pdf-lib";
import { SAAF_PDF_B64 } from "./templates.js";

const FONT_SIZE = 9;
const MULTILINE_FONT_SIZE = 7.5;
const INDIVIDUAL_CONTRIBUTION = "0";

// [x0, topY, x1, bottomY] — PyMuPDF coordinate space (top-left origin)
const CHECKBOXES = {
  "Co-Curricular": [46.2, 108.0, 55.8, 115.8],
  "Extra-Curricular": [46.2, 118.8, 55.8, 126.6],
  Major: [256.8, 108.0, 266.4, 115.8],
  Minor: [256.8, 118.8, 266.4, 126.6],
  MissionStatement1: [46.5, 352.6, 56.1, 360.4],
  MissionStatement2: [46.5, 363.4, 56.1, 371.2],
  MissionStatement3: [46.5, 374.2, 56.1, 382.0],
};

const FIELDS = {
  totalOrgMembers: [459.0, 118.8, 567.0, 127.9],
  applicantNameStudentNo: [157.6, 161.7, 329.0, 169.7],
  programAndYear: [393.0, 161.7, 540.2, 169.7],
  dateOfSubmission: [148.6, 170.7, 323.0, 178.7],
  positionOfApplicant: [414.2, 170.7, 540.1, 178.7],
  orgCourseSection: [202.6, 180.0, 540.1, 188.0],
  titleAndNature: [184.6, 218.0, 540.1, 226.0],
  objectivesLine1: [153.1, 235.8, 540.1, 243.8],
  objectivesLine2: [153.1, 245.0, 540.1, 253.0],
  venue: [72.0, 254.0, 540.1, 262.0],
  date: [66.5, 271.8, 222.1, 279.8],
  day: [243.3, 271.8, 385.4, 279.8],
  time: [410.1, 271.8, 539.0, 279.8],
  participants: [166.6, 281.0, 540.1, 289.0],
  individualContribution: [167.4, 290.3, 332.0, 298.3],
  proposedBudget: [484.5, 290.3, 573.4, 298.3],
  coreValuesLine1: [45.0, 410.8, 539.0, 418.8],
  coreValuesLine2: [45.0, 420.0, 539.1, 428.1],
  coreValuesLine3: [45.0, 429.3, 539.0, 437.3],
  peoLine1: [45.0, 456.1, 539.0, 464.1],
  peoLine2: [45.0, 465.3, 539.0, 473.3],
  peoLine3: [45.0, 474.6, 539.0, 482.6],
};

// Signature lines: [line_x0, line_x1, line_y] in PyMuPDF space
const SIG_APPLICANT = [48.525, 266.95, 566.5];
const SIG_ADVISER = [303.13, 521.50, 566.5];

function computeDay(dateStr) {
  if (!dateStr) return "";
  const cleaned = dateStr.split("(")[0].trim();
  const date = new Date(cleaned);
  if (isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-US", { weekday: "long" });
}

/**
 * Simple word-wrap: returns array of lines that fit within maxWidth characters
 * (approximated by character count * avgCharWidth at given font size).
 * For pdf-lib we can't measure glyph widths without embedding font,
 * so we use an approximation: avgCharWidth ≈ fontSize * 0.55 for Helvetica.
 */
function wrapText(text, boxWidthPt, fontSize) {
  if (!text) return [""];
  const avgCharWidth = fontSize * 0.55;
  const maxChars = Math.floor(boxWidthPt / avgCharWidth);
  const words = String(text).split(/\s+/);
  const lines = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxChars) {
      current = candidate;
    } else {
      if (current) lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return lines;
}

function wrapToLines(text, nLines, boxWidthPt, fontSize = FONT_SIZE) {
  if (!text) return Array(nLines).fill("");
  let size = fontSize;
  let lines = wrapText(text, boxWidthPt, size);
  const minSize = 4.5;

  while (lines.length > nLines && size > minSize) {
    size = Math.round((size - 0.25) * 100) / 100;
    lines = wrapText(text, boxWidthPt, size);
  }

  if (lines.length > nLines) {
    // 1. Try sentence-aware fitting: drop trailing sentences if text has multiple sentences
    const sentences = text.split(/(?<=[.!?])\s+/);
    let fittedBySentence = false;
    if (sentences.length > 1) {
      for (let i = sentences.length - 1; i >= 1; i--) {
        const candidateText = sentences.slice(0, i).join(" ");
        const candLines = wrapText(candidateText, boxWidthPt, size);
        if (candLines.length <= nLines) {
          lines = candLines;
          fittedBySentence = true;
          break;
        }
      }
    }

    // 2. If a single sentence is still too long, truncate cleanly and end with a period
    if (!fittedBySentence) {
      lines = lines.slice(0, nLines);
      const maxLen = Math.floor(boxWidthPt / (size * 0.55));
      let lastLine = lines[nLines - 1];
      if (lastLine.length > maxLen) {
        lastLine = lastLine.slice(0, maxLen).trimEnd();
      }
      lastLine = lastLine.replace(/[.…]+$/, "").trimEnd();
      if (!/[.!?]$/.test(lastLine)) {
        lastLine += ".";
      }
      lines[nLines - 1] = lastLine;
    }
  }

  while (lines.length < nLines) lines.push("");
  return lines;
}

/**
 * Fills the SAAF PDF template and returns a Uint8Array of the filled PDF.
 * @param {object} event
 * @param {object} profile
 * @returns {Promise<Uint8Array>}
 */
export async function fillSaaf(event, profile) {
  const saafBytes = Uint8Array.from(atob(SAAF_PDF_B64), (c) => c.charCodeAt(0));
  const pdfDoc = await PDFDocument.load(saafBytes, { ignoreEncryption: true });

  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const page = pdfDoc.getPages()[0];
  const { height: pageHeight } = page.getSize();

  /**
   * Convert PyMuPDF top-origin y to a pdf-lib baseline y.
   *
   * `bottom` is where the printed underline actually sits (verified against
   * the rendered template), so the baseline must be placed a small gap
   * ABOVE `bottom` — not derived from `top` — or the underline stroke cuts
   * straight through the middle of the glyphs instead of sitting under them.
   */
  function pymupdfToBaseline(top, bottom, fSize) {
    const BASELINE_GAP = 1.5; // pt of clearance between baseline and the underline
    return pageHeight - bottom + BASELINE_GAP;
  }

  function drawText(fieldCoords, text, fSize = FONT_SIZE) {
    if (!text && text !== 0) return;
    const [x0, top, x1, bottom] = fieldCoords;
    const y = pymupdfToBaseline(top, bottom, fSize);
    const maxWidth = x1 - x0;
    let str = String(text).trim();
    if (!str) return;

    // Clip text to box width
    while (str.length > 1 && font.widthOfTextAtSize(str, fSize) > maxWidth) {
      str = str.slice(0, -1).trimEnd();
    }

    page.drawText(str, {
      x: x0,
      y,
      size: fSize,
      font,
      color: rgb(0, 0, 0),
    });
  }

  function drawCheckbox(boxCoords) {
    const [x0, top, x1, bottom] = boxCoords;
    const margin = 1.5;
    // Convert to pdf-lib coords
    const px0 = x0 + margin;
    const py0 = pageHeight - top - margin;
    const px1 = x1 - margin;
    const py1 = pageHeight - bottom + margin;

    // Draw X: two diagonal lines
    page.drawLine({
      start: { x: px0, y: py0 },
      end: { x: px1, y: py1 },
      thickness: 0.8,
      color: rgb(0, 0, 0),
    });
    page.drawLine({
      start: { x: px1, y: py0 },
      end: { x: px0, y: py1 },
      thickness: 0.8,
      color: rgb(0, 0, 0),
    });
  }

  function drawSignatureName(lineX0, lineX1, lineY, name, fSize = 10.5) {
    if (!name) return;
    const str = String(name).trim();
    const textWidth = font.widthOfTextAtSize(str, fSize);
    const centerX = (lineX0 + lineX1) / 2;
    const x = centerX - textWidth / 2;
    // lineY is in PyMuPDF space (top-origin), baseline is 1.5pt above the line
    const y = pageHeight - lineY + 1.5;
    page.drawText(str, { x, y, size: fSize, font, color: rgb(0, 0, 0) });
  }

  // ---- Fill applicant info ----
  const today = new Date();
  const submissionDate = `${String(today.getMonth() + 1).padStart(2, "0")}/${String(today.getDate()).padStart(2, "0")}/${today.getFullYear()}`;

  drawText(
    FIELDS.applicantNameStudentNo,
    `${profile.name || ""} ${profile.studentNumber || ""}`.trim()
  );
  drawText(FIELDS.programAndYear, profile.programAndYear || profile.courseSection);
  drawText(FIELDS.positionOfApplicant, profile.position);
  drawText(FIELDS.orgCourseSection, profile.organizationName);
  drawText(FIELDS.dateOfSubmission, submissionDate);

  // ---- Event info ----
  drawText(FIELDS.titleAndNature, event.eventTitle);

  // Objectives (2 lines)
  const objs = event.objectives || [];
  const objText =
    typeof objs === "string"
      ? objs
      : objs.some((s) => /[.!?]$/.test(s))
        ? objs.join(" ")
        : objs.join("; ");
  const objWidth = FIELDS.objectivesLine1[2] - FIELDS.objectivesLine1[0];
  const objLines = wrapToLines(objText, 2, objWidth, MULTILINE_FONT_SIZE);
  drawText(FIELDS.objectivesLine1, objLines[0], MULTILINE_FONT_SIZE);
  drawText(FIELDS.objectivesLine2, objLines[1], MULTILINE_FONT_SIZE);

  // Venue, date, day, time, participants, budget, members, contribution
  drawText(FIELDS.venue, profile.venue);
  drawText(FIELDS.date, event.date);
  drawText(FIELDS.day, computeDay(event.date));
  drawText(FIELDS.time, event.time_raw || event.startTime);
  drawText(FIELDS.participants, event.participants);
  drawText(FIELDS.proposedBudget, event.totalBudget);
  drawText(FIELDS.totalOrgMembers, event.totalOrgMembers);
  drawText(FIELDS.individualContribution, INDIVIDUAL_CONTRIBUTION);

  // Core Values (3 lines)
  const cvText = event.coreValuesWriteup || "";
  const cvWidth = FIELDS.coreValuesLine1[2] - FIELDS.coreValuesLine1[0];
  const cvLines = wrapToLines(cvText, 3, cvWidth, MULTILINE_FONT_SIZE);
  drawText(FIELDS.coreValuesLine1, cvLines[0], MULTILINE_FONT_SIZE);
  drawText(FIELDS.coreValuesLine2, cvLines[1], MULTILINE_FONT_SIZE);
  drawText(FIELDS.coreValuesLine3, cvLines[2], MULTILINE_FONT_SIZE);

  // PEO (3 lines)
  const peoText = event.peoWriteup || "";
  const peoWidth = FIELDS.peoLine1[2] - FIELDS.peoLine1[0];
  const peoLines = wrapToLines(peoText, 3, peoWidth, MULTILINE_FONT_SIZE);
  drawText(FIELDS.peoLine1, peoLines[0], MULTILINE_FONT_SIZE);
  drawText(FIELDS.peoLine2, peoLines[1], MULTILINE_FONT_SIZE);
  drawText(FIELDS.peoLine3, peoLines[2], MULTILINE_FONT_SIZE);

  // ---- Signature names ----
  drawSignatureName(SIG_APPLICANT[0], SIG_APPLICANT[1], SIG_APPLICANT[2], profile.name);
  drawSignatureName(SIG_ADVISER[0], SIG_ADVISER[1], SIG_ADVISER[2], event.adviserName);

  // ---- Checkboxes ----
  const activityType = (event.activityType || "").trim().toLowerCase();
  if (activityType.includes("extra")) {
    drawCheckbox(CHECKBOXES["Extra-Curricular"]);
  } else if (activityType.includes("co")) {
    drawCheckbox(CHECKBOXES["Co-Curricular"]);
  }

  const activityLevel = (event.activityLevel || "").trim().toLowerCase();
  if (activityLevel === "major") {
    drawCheckbox(CHECKBOXES["Major"]);
  } else if (activityLevel === "minor") {
    drawCheckbox(CHECKBOXES["Minor"]);
  }

  // Mission statements (all 3 always checked)
  drawCheckbox(CHECKBOXES["MissionStatement1"]);
  drawCheckbox(CHECKBOXES["MissionStatement2"]);
  drawCheckbox(CHECKBOXES["MissionStatement3"]);

  const filledBytes = await pdfDoc.save();
  return filledBytes;
}
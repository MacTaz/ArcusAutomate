/**
 * extract.js
 * ----------
 * Port of extract.py using PDF.js for in-browser PDF text extraction.
 * Parses the AWS-SBG Arcus Event Proposal PDF into a structured dictionary.
 *
 * Table detection strategy:
 *   PDF.js returns individual text spans with (x, y) coordinates.
 *   We group spans by their Y position (within a 4pt tolerance) to reconstruct
 *   rows, then sort cells in each row by X to get left-to-right column order.
 *   This mimics what pdfplumber does with bounding boxes.
 */

import * as pdfjsLib from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

export class ProposalFormatError extends Error {
  constructor(message, strictErrors = []) {
    super(message);
    this.name = "ProposalFormatError";
    this.strictErrors = strictErrors;
  }
}

function requireMatch(pattern, text, fieldName, flags = "", strictErrors = null, required = true) {
  const re = new RegExp(pattern, flags);
  const m = text.match(re);
  if (!m) {
    const msg = `Required field '${fieldName}' not found or not in exact expected format.`;
    if (required) {
      if (strictErrors !== null) {
        strictErrors.push(msg);
      } else {
        throw new ProposalFormatError(msg);
      }
    }
    return null;
  }
  return m;
}

/**
 * Extract all text from a PDF File object.
 * Returns:
 *   fullText  — all pages joined as a single string (line-per-visual-row)
 *   pageItems — array of per-page arrays of { str, x, y } objects
 */
async function extractPdfContent(file) {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  let fullText = "";
  const pageItems = [];

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const textContent = await page.getTextContent();

    // Collect all items with position info
    const items = [];
    for (const item of textContent.items) {
      if (!("str" in item) || !item.str.trim()) continue;
      items.push({
        str: item.str,
        x: Math.round(item.transform[4]),
        y: Math.round(item.transform[5]),
      });
    }
    pageItems.push(items);

    // Build line-by-line text by grouping same-Y items (tolerance ±3pt)
    const rowMap = new Map();
    for (const it of items) {
      // Find existing row bucket within ±3pt
      let key = null;
      for (const k of rowMap.keys()) {
        if (Math.abs(k - it.y) <= 3) { key = k; break; }
      }
      if (key === null) { key = it.y; rowMap.set(key, []); }
      rowMap.get(key).push(it);
    }

    // Sort rows top-to-bottom (PDF.js y=0 is bottom of page, so descending)
    const sortedYs = [...rowMap.keys()].sort((a, b) => b - a);
    for (const y of sortedYs) {
      // Sort cells left-to-right by x
      const cells = rowMap.get(y).sort((a, b) => a.x - b.x);
      const line = cells.map((c) => c.str).join(" ").trim();
      if (line) fullText += line + "\n";
    }
  }

  return { fullText, pageItems };
}

/**
 * Reconstruct table rows from raw PDF.js items using position clustering.
 * Groups items into rows (same Y ±4pt), sorts cells left-to-right.
 * Returns array of row arrays, where each row is an array of cell strings.
 */
function buildTableRows(pageItems) {
  const allRows = [];
  for (const items of pageItems) {
    const rowMap = new Map();
    for (const it of items) {
      let key = null;
      for (const k of rowMap.keys()) {
        if (Math.abs(k - it.y) <= 4) { key = k; break; }
      }
      if (key === null) { key = it.y; rowMap.set(key, []); }
      rowMap.get(key).push(it);
    }
    const sortedYs = [...rowMap.keys()].sort((a, b) => b - a);
    for (const y of sortedYs) {
      const cells = rowMap.get(y)
        .sort((a, b) => a.x - b.x)
        .map((c) => c.str.trim())
        .filter(Boolean);
      if (cells.length) allRows.push(cells);
    }
  }
  return allRows;
}

/**
 * Parse AV Equipment table and Room from position-reconstructed table rows.
 * Looks for a header row containing "Item" and "Quantity" (anywhere in row),
 * then collects data rows until an unrelated section starts.
 */
function parseAvTable(tableRows, strictErrors) {
  let equipment = [];
  let avRoom = null;
  let foundTable = false;
  let headerIdx = -1;

  // Find header row: any row that contains both "Item" and "Quantity"
  for (let i = 0; i < tableRows.length; i++) {
    const row = tableRows[i];
    const hasItem = row.some((c) => c === "Item" || c.toLowerCase() === "item");
    const hasQty = row.some((c) =>
      c === "Quantity" || c.toLowerCase() === "quantity" || c.toLowerCase() === "qty"
    );
    if (hasItem && hasQty) {
      headerIdx = i;
      foundTable = true;
      break;
    }
  }

  // Fallback: find header in a wider scan (cells may be joined)
  if (!foundTable) {
    for (let i = 0; i < tableRows.length; i++) {
      const joined = tableRows[i].join(" ").toLowerCase();
      if (joined.includes("item") && (joined.includes("quantity") || joined.includes("qty"))) {
        headerIdx = i;
        foundTable = true;
        break;
      }
    }
  }

  if (!foundTable) {
    strictErrors.push("AV Equipment table with exact 'Item' / 'Quantity' headers not found.");
    strictErrors.push("Room label/value not found in the AV Equipment table.");
    return { equipment, avRoom };
  }

  // Parse rows after header until we hit something unrelated
  // Known section terminators
  const STOP_KEYWORDS = [
    "budget", "objectives", "signat", "approved", "recommending",
    "total allocated", "guidelines", "submitted", "prepared",
  ];
  let readingRoom = false;
  let roomRowPending = false;

  for (let i = headerIdx + 1; i < tableRows.length; i++) {
    const row = tableRows[i];
    if (!row.length) continue;

    const firstCell = row[0].trim();
    const rowText = row.join(" ").trim().toLowerCase();

    // Stop if we hit a known section boundary
    if (STOP_KEYWORDS.some((kw) => rowText.startsWith(kw))) break;

    // Detect "Room" header cell
    if (firstCell === "Room" || firstCell.toLowerCase() === "room") {
      readingRoom = true;
      // Room value might be in the same row (second cell) or the next row
      if (row.length >= 2 && row[1].trim()) {
        avRoom = row[1].trim();
        readingRoom = false;
        // The "Room" row is always the final row of the AV Equipment table,
        // so stop scanning here instead of continuing into unrelated content
        // (e.g. the signature/closing text on the next page).
        break;
      } else {
        roomRowPending = true;
      }
      continue;
    }

    // If waiting for room value on next row
    if (roomRowPending) {
      avRoom = firstCell;
      roomRowPending = false;
      readingRoom = false;
      // Same reasoning as above: the room value is the last piece of the
      // AV Equipment table, so we're done once it's captured.
      break;
    }

    // Equipment row: first cell = item name, second cell = numeric quantity
    if (row.length >= 2) {
      const itemName = firstCell;
      const qtyCell = row[1].trim();
      if (/^\d+$/.test(qtyCell)) {
        equipment.push({ item: itemName, quantity: parseInt(qtyCell) });
      } else if (qtyCell) {
        // Non-numeric quantity
        strictErrors.push(
          `AV Equipment row '${itemName}' has a non-numeric Quantity value: ${JSON.stringify(qtyCell)}.`
        );
      }
    } else if (row.length === 1) {
      // Single-cell row after header could be a room name if readingRoom
      if (readingRoom) {
        avRoom = firstCell;
        readingRoom = false;
        roomRowPending = false;
        break;
      }
    }
  }

  if (!avRoom) {
    strictErrors.push("Room label/value not found in the AV Equipment table.");
  }

  return { equipment, avRoom };
}

/**
 * Main extraction function — ported 1:1 from extract.py.
 * @param {File} file - The proposal PDF file
 * @param {boolean} strict - If true, throws on validation errors
 * @returns {object} Structured event data
 */
export async function extractProposal(file, strict = true) {
  const { fullText, pageItems } = await extractPdfContent(file);
  const tableRows = buildTableRows(pageItems);

  const data = {};
  const strictErrors = [];

  // ---- Event Title ----
  const titleMatch = requireMatch(
    "[\\s\\S]+?(?=\\nDate:)",
    fullText,
    "Event Title (before 'Date:')",
    "",
    strictErrors
  );
  data.eventTitle = titleMatch ? titleMatch[0].trim().replace(/\n/g, " ") : null;

  // ---- Date ----
  const dateMatch = requireMatch("^Date:\\s+(.+)$", fullText, "Date:", "m", strictErrors);
  data.date = dateMatch ? dateMatch[1].trim() : null;

  // ---- Time ----
  const timeMatch = requireMatch("^Time:\\s+(.+)$", fullText, "Time:", "m", strictErrors);
  data.time_raw = timeMatch ? timeMatch[1].trim() : null;

  data.startTime = null;
  data.endTime = null;
  if (data.time_raw) {
    const times = [...data.time_raw.matchAll(/\b\d{1,2}:\d{2}\s*[AaPp][Mm]\b/g)].map((m) => m[0]);
    if (times.length < 2) {
      strictErrors.push(
        `Time: field does not contain two valid H:MM AM/PM times (found: ${JSON.stringify(data.time_raw)})`
      );
    }
    data.startTime = times[0] || null;
    data.endTime = times[1] || null;
  }

  // ---- Activity Classification ----
  const levelMatch = requireMatch("^Activity Level:\\s+(.+)$", fullText, "Activity Level:", "m", strictErrors);
  data.activityLevel = levelMatch ? levelMatch[1].trim() : null;
  if (data.activityLevel && /[,/;]| and /.test(data.activityLevel)) {
    strictErrors.push("Activity Level: appears to contain multiple values.");
  }

  const typeMatch = requireMatch("^Activity Type:\\s+(.+)$", fullText, "Activity Type:", "m", strictErrors);
  data.activityType = typeMatch ? typeMatch[1].trim() : null;
  if (data.activityType && /[,/;]| and /.test(data.activityType)) {
    strictErrors.push("Activity Type: appears to contain multiple values.");
  }

  // ---- Total Org Members ----
  const totalMembersMatch = requireMatch(
    "^Total Number of Members:\\s+(\\d+)\\b",
    fullText,
    "Total Number of Members:",
    "m",
    strictErrors
  );
  data.totalOrgMembers = totalMembersMatch ? parseInt(totalMembersMatch[1]) : null;

  // ---- Participants ----
  const participantsMatch = requireMatch(
    "\\bcater\\s+(\\d+)\\s+participants\\b",
    fullText,
    "'cater [NUMBER] participants' statement",
    "",
    strictErrors
  );
  data.participants = participantsMatch ? parseInt(participantsMatch[1]) : null;

  // ---- Venue ----
  let venueMatch = fullText.match(/\|\s*([^|\n]*\bUniversity\b[^|\n]*)\|/i);
  if (!venueMatch) {
    venueMatch = fullText.match(/^(.*\bUniversity\b.*)$/im);
    if (!venueMatch) {
      strictErrors.push("Venue containing 'University' not found.");
    }
  }
  data.venue = venueMatch ? venueMatch[1].trim() : null;

  // ---- Total Allocated Budget ----
  const budgetMatch = requireMatch(
    "^Total Allocated Budget:\\s*[₱P]?\\s*([\\d,]+(?:\\.\\d+)?)\\b",
    fullText,
    "Total Allocated Budget:",
    "m",
    strictErrors
  );
  data.totalBudget = budgetMatch ? budgetMatch[1].replace(/,/g, "") : null;

  // ---- Objectives ----
  const mainObjMatch = fullText.match(
    /^Main Objective\s*\n([\s\S]+?)(?=^Project Proponents|^Target Proponents|^Description)/m
  );
  if (mainObjMatch) {
    const rawObjText = mainObjMatch[1].replace(/\s+/g, " ").trim();
    const sentences = rawObjText
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter(Boolean);
    data.objectives = sentences.slice(0, 2);
    if (!data.objectives.length) {
      strictErrors.push("'Main Objective' section found, but no sentences extracted.");
    }
  } else {
    const altObjMatch = fullText.match(
      /^(?:.*\b)?core objectives:\s*\n([\s\S]+?)(?=^Program Education Objective)/im
    );
    if (altObjMatch) {
      const bullets = altObjMatch[1].split(/●|•/);
      data.objectives = bullets
        .map((b) => b.trim().replace(/\n/g, " "))
        .filter(Boolean)
        .slice(0, 2);
    } else {
      data.objectives = [];
    }
  }

  // ---- PEO Write-up ----
  const peoMatch = fullText.match(
    /^Program Education Objective.*?\(PEO\).*?$\s*\n([\s\S]+?)(?=^\s*Map[uú]a Core Values)/m
  );
  data.peoWriteup = peoMatch ? peoMatch[1].replace(/\s+/g, " ").trim() : null;
  if (!peoMatch) {
    strictErrors.push("Required field 'Program Education Objective ... (PEO)' not found or not in exact expected format.");
  }

  // ---- Core Values Write-up ----
  const coreValuesMatch = fullText.match(
    /^Map[uú]a Core Values Alignment\s*\n?([\s\S]+?)(?=^Guidelines)/m
  );
  data.coreValuesWriteup = coreValuesMatch
    ? coreValuesMatch[1].replace(/\s+/g, " ").trim()
    : null;
  if (!coreValuesMatch) {
    strictErrors.push("Required field 'Mapúa Core Values Alignment' not found or not in exact expected format.");
  }

  // ---- AV Equipment Table + Room ----
  const { equipment, avRoom } = parseAvTable(tableRows, strictErrors);
  data.avEquipment = equipment;
  data.avRoom = avRoom;

  data.strictErrors = strictErrors;
  data.isValid = strictErrors.length === 0;

  if (strict && strictErrors.length > 0) {
    throw new ProposalFormatError(
      "Proposal failed strict format validation:\n- " + strictErrors.join("\n- "),
      strictErrors
    );
  }

  return data;
}
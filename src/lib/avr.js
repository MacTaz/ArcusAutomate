/**
 * avr.js
 * ------
 * Port of avr.py using pdf-lib for AcroForm field filling.
 * Fills the AVR PDF template (FM-AO-08-01) with event and applicant data.
 */

import { PDFDocument, PDFName } from "pdf-lib";
import { AVR_PDF_B64 } from "./templates.js";

const ROOM_FIELD_MAP = {
  "AV Room 1": {
    checkbox: "Check Box1",
    date: "Date NeededRow1",
    time: "Time NeededRow1",
    remarks: "Remarks  AV Room 1",
  },
  "AV Room 2": {
    checkbox: "Check Box2",
    date: "Date NeededRow2",
    time: "Time NeededRow2",
    remarks: "Remarks  AV Room 2",
  },
  "Conference Room": {
    checkbox: "Check Box3",
    date: "Date NeededRow3",
    time: "Time NeededRow3",
    remarks: "Remarks  Conference Room",
  },
  Others: {
    checkbox: "Check Box4",
    date: "Date NeededRow4",
    time: "Time NeededRow4",
    remarks: "Remarks  Others",
  },
};

const EQUIPMENT_FIELD_MAP = {
  LCD: { checkbox: "Check Box5", date: "Date NeededRow1_2", time: "Time NeededRow1_2" },
  CPU: { checkbox: "Check Box6", date: "Date NeededRow2_2", time: "Time NeededRow2_2" },
  Laptop: { checkbox: "Check Box7", date: "Date NeededRow3_2", time: "Time NeededRow3_2" },
  "Computer Speaker": { checkbox: "Check Box8", date: "Date NeededRow4_2", time: "Time NeededRow4_2" },
  "Laser Pointer": { checkbox: "Check Box9", date: "Date NeededRow5", time: "Time NeededRow5" },
  Television: { checkbox: "Check Box", date: "Date NeededRow6", time: "Time NeededRow6" },
  DVD: { checkbox: "Check Bo1", date: "Date NeededRow7", time: "Time NeededRow7" },
  "Doc. Cam.": { checkbox: "Check Bo2", date: "Date NeededRow8", time: "Time NeededRow8" },
  Amplifier: { checkbox: "Check Bo3", date: "Date NeededRow9", time: "Time NeededRow9" },
  Mixer: { checkbox: "Check Bo4", date: "Date NeededRow10", time: "Time NeededRow10" },
  Speaker: { checkbox: "Check Bo5", date: "Date NeededRow11", time: "Time NeededRow11" },
  Microphone: { checkbox: "Check Bo6", date: "Date NeededRow12", time: "Time NeededRow12" },
};

function todayMMDDYYYY() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${mm}/${dd}/${yyyy}`;
}

/**
 * Fills the AVR PDF template and returns a Uint8Array of the filled PDF.
 * @param {object} event - Extracted event data
 * @param {object} profile - Applicant profile from chrome.storage
 * @returns {Promise<Uint8Array>}
 */
export async function fillAvr(event, profile) {
  const avrBytes = Uint8Array.from(atob(AVR_PDF_B64), (c) => c.charCodeAt(0));
  const pdfDoc = await PDFDocument.load(avrBytes, { ignoreEncryption: true });

  const form = pdfDoc.getForm();

  function setText(fieldName, value) {
    if (value == null) return;
    try {
      const field = form.getTextField(fieldName);
      field.setText(String(value));
    } catch (e) {
      console.warn(`[AVR] TextField '${fieldName}' not found:`, e.message);
    }
  }

  function checkBox(fieldName) {
    try {
      const field = form.getCheckBox(fieldName);
      field.check();
    } catch (e) {
      // Some AVR checkboxes are implemented as text fields with /Yes values
      try {
        const field = form.getField(fieldName);
        field.acroField.dict.set(PDFName.of("V"), PDFName.of("Yes"));
        field.acroField.dict.set(PDFName.of("AS"), PDFName.of("Yes"));
      } catch (e2) {
        console.warn(`[AVR] Checkbox '${fieldName}' not found:`, e2.message);
      }
    }
  }

  // Applicant profile fields
  setText("Name of Applicant", profile.name);
  setText("DepartmentCompany of Applicant", profile.department);
  setText("CourseSection", profile.courseSection || profile.programAndYear);
  setText("Contact No", profile.contactNo);
  setText("Date Applied", todayMMDDYYYY());
  setText("Signature of Applicant", profile.name);

  // Event details
  setText("No of Participants", event.participants);
  setText("Purpose of Activity", event.eventTitle);

  const dateNeeded = event.date;
  const startTime = event.startTime;
  const endTime = event.endTime;

  if (!startTime || !endTime) {
    throw new Error("Proposal has no valid start/end time.");
  }
  const timeNeeded = `${startTime} - ${endTime}`;

  // Room
  const room = event.avRoom;
  if (room) {
    const roomKey = room in ROOM_FIELD_MAP ? room : "Others";
    const roomMap = ROOM_FIELD_MAP[roomKey];
    checkBox(roomMap.checkbox);
    setText(roomMap.date, dateNeeded);
    setText(roomMap.time, timeNeeded);
    if (roomKey === "Others") {
      setText(roomMap.remarks, room);
    }
  }

  // Equipment
  const equipment = event.avEquipment;
  if (equipment && equipment.length > 0) {
    for (const eq of equipment) {
      const m = EQUIPMENT_FIELD_MAP[eq.item];
      if (m) {
        checkBox(m.checkbox);
        setText(m.date, dateNeeded);
        setText(m.time, timeNeeded);
      } else {
        console.warn(`[AVR] '${eq.item}' has no known field mapping — skipped.`);
      }
    }
  }

  // Flatten so fields are rendered visibly
  form.flatten();

  // Draw applicant signature name over signature line
  const pages = pdfDoc.getPages();
  const page = pages[0];
  const { height } = page.getSize();

  // Signature coords from avr.py: center_x = (41.4 + 243.36) / 2 = 142.38, y = 588.5
  // pdf-lib y is from bottom, PyMuPDF y from top (page height ~841.89 for A4)
  // PyMuPDF baseline_y = 588.5 → pdf-lib y = height - 588.5
  const sigY = height - 588.5;
  const sigText = String(profile.name || "").trim();
  if (sigText) {
    page.drawText(sigText, {
      x: 90, // approximate center of the signature line
      y: sigY,
      size: 10.5,
    });
  }

  const filledBytes = await pdfDoc.save();
  return filledBytes;
}

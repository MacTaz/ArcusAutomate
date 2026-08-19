// ---- CONFIG ----
const API_ENDPOINT = "http://localhost:5000/generate";

// ---- Elements ----
const dropZone = document.getElementById("dropZone");
const dropZoneText = document.getElementById("dropZoneText");
const fileInput = document.getElementById("fileInput");
const fileInfo = document.getElementById("fileInfo");
const fileNameEl = document.getElementById("fileName");
const clearFileBtn = document.getElementById("clearFile");
const generateBtn = document.getElementById("generateBtn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const openSettingsBtn = document.getElementById("openSettings");
const autofillBtn = document.getElementById("autofillBtn");

let selectedFile = null;
let generatedUrls = { avr: null, saaf: null, master: null };

// ---- File selection (click to browse) ----
dropZone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (e) => {
  if (e.target.files.length) handleFile(e.target.files[0]);
});

// ---- Drag and drop ----
["dragenter", "dragover"].forEach((evt) =>
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  })
);

["dragleave", "drop"].forEach((evt) =>
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
  })
);

dropZone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

function handleFile(file) {
  if (file.type !== "application/pdf") {
    setStatus("Please select a PDF file.", true);
    return;
  }
  selectedFile = file;
  fileNameEl.textContent = file.name;
  fileInfo.hidden = false;
  dropZoneText.textContent = "PDF selected — drop another to replace";
  generateBtn.disabled = false;
  resultsEl.hidden = true;
  setStatus("");
}

clearFileBtn.addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  fileInfo.hidden = true;
  dropZoneText.textContent = "Drag & drop your proposal PDF here\nor click to browse";
  generateBtn.disabled = true;
  resultsEl.hidden = true;
});

// ---- Generate ----
generateBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  const profile = await getApplicantProfile();
  if (!profile) {
    setStatus("Please fill in your Applicant Settings first.", true);
    return;
  }

  generateBtn.disabled = true;
  setStatus("Uploading & generating documents...");
  resultsEl.hidden = true;

  try {
    const profileJson = JSON.stringify(profile);
    const formData = new FormData();
    formData.append("proposal", selectedFile);
    formData.append("applicantProfile", profileJson);

    const response = await fetch(API_ENDPOINT, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Request failed (${response.status})`);
    }

    const data = await response.json();
    // Expected response shape: { avr, saaf, master } — base64 PDF strings
    generatedUrls = {
      avr: base64ToObjectUrl(data.avr),
      saaf: base64ToObjectUrl(data.saaf),
      master: base64ToObjectUrl(data.master),
    };

    setStatus("Done. Download your documents below.");
    resultsEl.hidden = false;
  } catch (err) {
    console.error(err);
    setStatus(`Error: ${err.message}`, true);
  } finally {
    generateBtn.disabled = false;
  }
});

document.getElementById("downloadAvr").addEventListener("click", () => downloadFile(generatedUrls.avr, "AVR.pdf"));
document.getElementById("downloadSaaf").addEventListener("click", () => downloadFile(generatedUrls.saaf, "SAAF.pdf"));
document.getElementById("downloadMaster").addEventListener("click", () => downloadFile(generatedUrls.master, "Master.pdf"));

function downloadFile(url, filename) {
  if (!url) {
    setStatus("File not ready yet.", true);
    return;
  }
  chrome.downloads.download({ url, filename, saveAs: false });
}

// ---- Settings navigation ----
openSettingsBtn.addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

// autofillBtn intentionally left disabled — reserved for the future
// "Engage form auto-fill" feature (content-script based).

// ---- Helpers ----
function base64ToObjectUrl(base64, mime = "application/pdf") {
  const byteChars = atob(base64);
  const byteNumbers = new Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i);
  const byteArray = new Uint8Array(byteNumbers);
  const blob = new Blob([byteArray], { type: mime });
  return URL.createObjectURL(blob);
}

function getApplicantProfile() {
  return new Promise((resolve) => {
    chrome.storage.sync.get("applicantProfile", (data) => {
      resolve(data.applicantProfile || null);
    });
  });
}

function setStatus(msg, isError = false) {
  statusEl.hidden = !msg;
  statusEl.textContent = msg;
  statusEl.style.color = isError ? "#c0392b" : "#555";
}

import { useState, useRef, useCallback } from "react";
import { extractProposal, ProposalFormatError } from "../lib/extract.js";
import { fillAvr } from "../lib/avr.js";
import { fillSaaf } from "../lib/saaf.js";
import { PDFDocument } from "pdf-lib";

function getApplicantProfile() {
  return new Promise((resolve) => {
    if (typeof chrome !== "undefined" && chrome.storage) {
      chrome.storage.sync.get("applicantProfile", (data) => {
        resolve(data.applicantProfile || null);
      });
    } else {
      // Fallback for dev mode
      const stored = localStorage.getItem("applicantProfile");
      resolve(stored ? JSON.parse(stored) : null);
    }
  });
}

function downloadBlob(bytes, filename) {
  const blob = new Blob([bytes], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  if (typeof chrome !== "undefined" && chrome.downloads) {
    chrome.downloads.download({ url, filename, saveAs: false });
  } else {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}

export default function Popup() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState(null); // { msg, isError }
  const [isGenerating, setIsGenerating] = useState(false);
  const [results, setResults] = useState(null); // { avr, saaf, master }
  const fileInputRef = useRef(null);

  function handleFile(file) {
    if (file.type !== "application/pdf") {
      setStatus({ msg: "Please select a PDF file.", isError: true });
      return;
    }
    setSelectedFile(file);
    setResults(null);
    setStatus(null);
  }

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, []);

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback(() => setIsDragging(false), []);

  function clearFile(e) {
    e.stopPropagation();
    setSelectedFile(null);
    setResults(null);
    setStatus(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function generate() {
    if (!selectedFile || isGenerating) return;

    const profile = await getApplicantProfile();
    if (!profile) {
      setStatus({ msg: "Please fill in your Applicant Settings first.", isError: true });
      return;
    }

    setIsGenerating(true);
    setResults(null);
    setStatus({ msg: "Extracting proposal data…", isError: false });

    try {
      // Step 1: Extract
      let event;
      try {
        event = await extractProposal(selectedFile, true);
      } catch (err) {
        if (err instanceof ProposalFormatError) {
          const errList = err.strictErrors.map((e) => `• ${e}`).join("\n");
          throw new Error(`Proposal format errors:\n${errList}`);
        }
        throw err;
      }

      event.adviserName = profile.adviserName || "";

      const hasAvr = Boolean(
        (event.avRoom && event.avRoom.trim()) ||
        (event.avEquipment && event.avEquipment.length > 0)
      );

      // Step 2: Fill AVR
      let avrBytes = null;
      if (hasAvr) {
        setStatus({ msg: "Filling AVR form…", isError: false });
        avrBytes = await fillAvr(event, profile);
      }

      // Step 3: Fill SAAF
      setStatus({ msg: "Filling SAAF form…", isError: false });
      const saafBytes = await fillSaaf(event, profile);

      // Step 4: Merge Proposal + SAAF (+ AVR if present) into master
      setStatus({ msg: "Merging master PDF…", isError: false });
      const masterDoc = await PDFDocument.create();

      const proposalBytes = await selectedFile.arrayBuffer();
      const docsToMerge = [
        await PDFDocument.load(proposalBytes),
        await PDFDocument.load(saafBytes),
      ];
      if (avrBytes) {
        docsToMerge.push(await PDFDocument.load(avrBytes));
      }

      for (const doc of docsToMerge) {
        const pages = await masterDoc.copyPages(doc, doc.getPageIndices());
        pages.forEach((p) => masterDoc.addPage(p));
      }
      const masterBytes = await masterDoc.save();

      setResults({ avr: avrBytes, saaf: saafBytes, master: masterBytes });
      setStatus({ msg: "✓ Done. Download your documents below.", isError: false });
    } catch (err) {
      console.error(err);
      setStatus({ msg: err.message, isError: true });
    } finally {
      setIsGenerating(false);
    }
  }

  function openSettings() {
    if (typeof chrome !== "undefined" && chrome.runtime) {
      chrome.runtime.openOptionsPage();
    } else {
      window.open("options.html", "_blank");
    }
  }

  const dropZoneClass = [
    "drop-zone",
    isDragging ? "dragover" : "",
    selectedFile ? "has-file" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="container">
      <h1>ARCUS Secretary</h1>

      <a
        href="https://docs.google.com/document/d/1R5BpxvDhrA3iJBWGMe90AgIGAKBuPUC6GjyVhwxqMWY/edit?usp=sharing"
        target="_blank"
        rel="noopener noreferrer"
        className="guidelines-link"
      >
        📄 Proposal Guidelines ↗
      </a>

      <div className="drop-zone-wrapper">
        <div
          className={dropZoneClass}
          onClick={() => fileInputRef.current?.click()}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
        >
          <p>
            {selectedFile
              ? "PDF selected — drop another to replace"
              : "Drag & drop your proposal PDF here\nor click to browse"}
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            style={{ display: "none" }}
            onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
          />
        </div>
        <img src="assets/ARCUS_DOG.png" alt="Arcus Dog" className="drop-zone-dog" />
        {selectedFile && (
          <button className="remove-btn" onClick={clearFile}>
            ✕ Remove
          </button>
        )}
      </div>

      {selectedFile && (
        <div className="file-info">
          <span>{selectedFile.name}</span>
        </div>
      )}

      <button
        className="primary-btn"
        disabled={!selectedFile || isGenerating}
        onClick={generate}
      >
        {isGenerating ? "Generating…" : "Generate Documents"}
      </button>

      {status && (
        <div
          className="status"
          style={{ color: status.isError ? "#c0392b" : "#7fbb6e", whiteSpace: "pre-wrap" }}
        >
          {status.msg}
        </div>
      )}

      {results && (
        <div className="results">
          {results.avr && (
            <button className="secondary-btn" onClick={() => downloadBlob(results.avr, "AVR.pdf")}>
              ⬇ Download AVR
            </button>
          )}
          <button className="secondary-btn" onClick={() => downloadBlob(results.saaf, "SAAF.pdf")}>
            ⬇ Download SAAF
          </button>
          <button
            className="secondary-btn"
            onClick={() => downloadBlob(results.master, "Master.pdf")}
          >
            ⬇ Download Master ({results.avr ? "Proposal + SAAF + AVR" : "Proposal + SAAF"})
          </button>
        </div>
      )}

      <div className="footer-row">
        <button className="link-btn" onClick={openSettings}>
          ⚙ Applicant Settings
        </button>
      </div>
    </div>
  );
}

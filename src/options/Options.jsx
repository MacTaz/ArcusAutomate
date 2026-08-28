import { useState, useEffect, useRef } from "react";
import { computeSignatureDimensions } from "../lib/signaturePlacement.js";

const FIELDS = [
  { name: "name", label: "Full Name", placeholder: "" },
  { name: "studentNumber", label: "Student Number", placeholder: "" },
  { name: "programAndYear", label: "Program-Year", placeholder: "e.g. BSCS - 3" },
  { name: "position", label: "Position", placeholder: "e.g. Corporate Secretary" },
  { name: "department", label: "Department", placeholder: "e.g. SOIT" },
  { name: "contactNo", label: "Contact No.", placeholder: "" },
  { name: "organizationName", label: "Organization Name", placeholder: "" },
  { name: "venue", label: "Default Venue", placeholder: "" },
  { name: "adviserName", label: "Organization Adviser", placeholder: "" },
];

function getStorage(key) {
  return new Promise((resolve) => {
    if (typeof chrome !== "undefined" && chrome.storage) {
      chrome.storage.local.get(key, (localData) => {
        if (localData && localData[key]) {
          resolve(localData[key]);
        } else {
          chrome.storage.sync.get(key, (syncData) => resolve(syncData ? syncData[key] : null));
        }
      });
    } else {
      const val = localStorage.getItem(key);
      resolve(val ? JSON.parse(val) : null);
    }
  });
}

function setStorage(key, value) {
  return new Promise((resolve) => {
    if (typeof chrome !== "undefined" && chrome.storage) {
      chrome.storage.local.set({ [key]: value }, resolve);
    } else {
      localStorage.setItem(key, JSON.stringify(value));
      resolve();
    }
  });
}

export default function Options() {
  const [values, setValues] = useState(
    Object.fromEntries(FIELDS.map((f) => [f.name, ""]))
  );
  const [signatureImage, setSignatureImage] = useState("");
  const [signatureSize, setSignatureSize] = useState(180);
  const [signatureOffsetY, setSignatureOffsetY] = useState(0);
  const [saved, setSaved] = useState(false);
  const signatureInputRef = useRef(null);
  // naturalDims holds the pixel dimensions of the uploaded signature image.
  // Populated via the <img> onLoad handler so we can feed the exact same
  // computeSignatureDimensions() call that the PDF embedders use.
  const [naturalDims, setNaturalDims] = useState({ w: 1, h: 1 });

  // The SAAF applicant signature line spans from x0=48.525 to x1=266.95 (pt).
  // The preview container is 260 px wide, so this scale maps PDF pt → preview px.
  const PDF_SIG_LINE_WIDTH_PT = 266.95 - 48.525; // 218.425 pt
  const PREVIEW_CONTAINER_PX = 260;
  const previewScale = PREVIEW_CONTAINER_PX / PDF_SIG_LINE_WIDTH_PT;

  // Signature line sits at top=55px inside the 120px-tall preview container.
  const PREVIEW_LINE_TOP_PX = 55;

  useEffect(() => {
    getStorage("applicantProfile").then((profile) => {
      if (!profile) return;
      setValues((prev) => ({ ...prev, ...profile }));
      if (profile.signatureImage) setSignatureImage(profile.signatureImage);
      if (profile.signatureSize) setSignatureSize(profile.signatureSize);
      else if (profile.signatureWidth) setSignatureSize(profile.signatureWidth);
      if (profile.signatureOffsetY !== undefined) setSignatureOffsetY(profile.signatureOffsetY);
    });
  }, []);

  function onChange(e) {
    const { name, value } = e.target;
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  function handleSignatureUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setSignatureImage(reader.result);
      }
    };
    reader.readAsDataURL(file);
  }

  function clearSignature() {
    setSignatureImage("");
    if (signatureInputRef.current) {
      signatureInputRef.current.value = "";
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    const profile = {
      ...values,
      signatureImage,
      signatureSize: Number(signatureSize),
      signatureOffsetY: Number(signatureOffsetY),
    };
    // Mirror programAndYear to courseSection for compatibility
    profile.courseSection = profile.programAndYear;
    await setStorage("applicantProfile", profile);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="container">
      <h1>Applicant Profile</h1>
      <p className="hint">
        This information is filled into the AVR and SAAF automatically. It&apos;s saved in your
        browser and reused every time.
      </p>

      <form onSubmit={onSubmit}>
        {FIELDS.map((f) => (
          <label key={f.name}>
            {f.label}
            <input
              type="text"
              name={f.name}
              value={values[f.name]}
              placeholder={f.placeholder}
              onChange={onChange}
              required
            />
          </label>
        ))}

        <div className="signature-section" style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
          <label style={{ fontSize: "13px", fontWeight: 600, color: "#cfd8e3" }}>
            Signature Image (PNG / JPG)
          </label>
          <span style={{ fontSize: "12px", color: "#7a8ba3" }}>
            Upload your signature image to automatically embed it on the SAAF and AVR signature lines.
          </span>
          <input
            ref={signatureInputRef}
            type="file"
            accept="image/png, image/jpeg, image/webp"
            onChange={handleSignatureUpload}
            style={{ display: "none" }}
          />
          {signatureImage ? (
            <div
              style={{
                marginTop: "8px",
                display: "flex",
                flexDirection: "column",
                gap: "14px",
                background: "rgba(255, 255, 255, 0.05)",
                padding: "14px",
                borderRadius: "8px",
                border: "1px solid rgba(231, 131, 20, 0.35)",
              }}
            >
              {/* Centered Remove Signature Button */}
              <div style={{ display: "flex", justifyContent: "center", width: "100%" }}>
                <button
                  type="button"
                  className="remove-btn"
                  style={{
                    position: "static",
                    width: "100%",
                    padding: "8px 16px",
                    fontSize: "12.5px",
                    fontWeight: 600,
                    textAlign: "center",
                    borderRadius: "6px",
                  }}
                  onClick={clearSignature}
                >
                  ✕ Remove Signature
                </button>
              </div>

              {/* Sliders for Size & Vertical Shift */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  borderTop: "1px solid rgba(255, 255, 255, 0.1)",
                  paddingTop: "12px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "12px", color: "#cfd8e3" }}>Signature Size: {signatureSize}pt</span>
                  <input
                    type="range"
                    min="80"
                    max="320"
                    step="5"
                    value={signatureSize}
                    onChange={(e) => setSignatureSize(e.target.value)}
                    style={{ width: "150px" }}
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "12px", color: "#cfd8e3" }}>Vertical Shift (Y): {signatureOffsetY}pt</span>
                  <input
                    type="range"
                    min="-100"
                    max="100"
                    step="1"
                    value={signatureOffsetY}
                    onChange={(e) => setSignatureOffsetY(e.target.value)}
                    style={{ width: "150px" }}
                  />
                </div>
              </div>

              {/* Live PDF Signature Preview Card */}
              <div
                style={{
                  marginTop: "4px",
                  background: "#ffffff",
                  borderRadius: "8px",
                  padding: "16px 12px 14px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    position: "relative",
                    width: "260px",
                    height: "120px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {/* Anchor for Signature Line & Text */}
                  <div
                    style={{
                      position: "absolute",
                      top: "55px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      width: "220px",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                    }}
                  >
                    {/* Printed Name in exact PDF font (10.5pt Helvetica) */}
                    <div
                      style={{
                        fontFamily: "Helvetica, Arial, sans-serif",
                        fontSize: "10.5pt",
                        color: "#000000",
                        textAlign: "center",
                        lineHeight: "1.2",
                        marginBottom: "2px",
                        userSelect: "none",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {values.name ? values.name.trim() : "APPLICANT NAME"}
                    </div>

                    {/* Signature Line */}
                    <div
                      style={{
                        width: "100%",
                        height: "1px",
                        backgroundColor: "#000000",
                      }}
                    />

                    <div
                      style={{
                        fontFamily: "Helvetica, Arial, sans-serif",
                        fontSize: "8.5pt",
                        fontWeight: "bold",
                        color: "#222222",
                        marginTop: "3px",
                        textAlign: "center",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {values.position ? values.position.trim() : "Class Officer / Organizer"} (Name and Signature)
                    </div>
                  </div>

                  {/* Signature Image Overlay — dimensions derived from the same
                      computeSignatureDimensions() formula used by the PDF embedders,
                      scaled into preview-pixel space via previewScale. */}
                  {signatureImage && (() => {
                    const { width: pdfW, height: pdfH } = computeSignatureDimensions(
                      signatureSize,
                      naturalDims.w,
                      naturalDims.h
                    );
                    const previewW = pdfW * previewScale;
                    const previewH = pdfH * previewScale;
                    // offsetY in PDF pts → preview px; positive = up (same sign as PDF)
                    const previewOffsetY = Number(signatureOffsetY) * previewScale;
                    return (
                      <img
                        src={signatureImage}
                        alt="Live Signature Overlay"
                        onLoad={(e) => setNaturalDims({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
                        style={{
                          position: "absolute",
                          // Centre vertically on the signature line, shifted by offsetY
                          top: `${PREVIEW_LINE_TOP_PX - previewH / 2 - previewOffsetY}px`,
                          left: "50%",
                          transform: "translateX(-50%)",
                          width: `${previewW}px`,
                          height: `${previewH}px`,
                          objectFit: "contain",
                          pointerEvents: "none",
                          zIndex: 3,
                        }}
                      />
                    );
                  })()}
                </div>
              </div>
            </div>
          ) : (
            <button
              type="button"
              className="secondary-btn"
              style={{ textAlign: "center", marginTop: "6px" }}
              onClick={() => signatureInputRef.current?.click()}
            >
              Upload Signature Image
            </button>
          )}
        </div>

        <button type="submit" className="primary-btn">
          Save
        </button>
        {saved && <div className="saved-msg">Saved ✓</div>}
      </form>
    </div>
  );
}

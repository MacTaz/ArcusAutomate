import { useState, useEffect } from "react";

const FIELDS = [
  { name: "name", label: "Full Name", placeholder: "" },
  { name: "studentNumber", label: "Student Number", placeholder: "" },
  { name: "programAndYear", label: "Program, Year & Section", placeholder: "e.g. BSCS - 3" },
  { name: "position", label: "Position", placeholder: "e.g. Corporate Secretary" },
  { name: "department", label: "Department", placeholder: "e.g. SOIT" },
  { name: "contactNo", label: "Contact No.", placeholder: "" },
  { name: "organizationName", label: "Organization Name", placeholder: "" },
];

function getStorage(key) {
  return new Promise((resolve) => {
    if (typeof chrome !== "undefined" && chrome.storage) {
      chrome.storage.sync.get(key, (data) => resolve(data[key] || null));
    } else {
      const val = localStorage.getItem(key);
      resolve(val ? JSON.parse(val) : null);
    }
  });
}

function setStorage(key, value) {
  return new Promise((resolve) => {
    if (typeof chrome !== "undefined" && chrome.storage) {
      chrome.storage.sync.set({ [key]: value }, resolve);
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
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getStorage("applicantProfile").then((profile) => {
      if (!profile) return;
      setValues((prev) => ({ ...prev, ...profile }));
    });
  }, []);

  function onChange(e) {
    const { name, value } = e.target;
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    const profile = { ...values };
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

        <button type="submit" className="primary-btn">
          Save
        </button>
        {saved && <div className="saved-msg">Saved ✓</div>}
      </form>
    </div>
  );
}

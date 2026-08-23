# Arcus Secretary — Chrome Extension (v2.0)

Fully self-contained Chrome extension. **No local Python server required.**
All PDF parsing and filling happens directly in-browser.

## Folder Structure

```
ext/
├── src/
│   ├── lib/
│   │   ├── extract.js      ← PDF proposal parser (PDF.js)
│   │   ├── avr.js          ← AVR AcroForm filler (pdf-lib)
│   │   ├── saaf.js         ← SAAF coordinate filler (pdf-lib)
│   │   └── templates.js    ← AVR + SAAF PDFs bundled as base64
│   ├── popup/
│   │   ├── Popup.jsx       ← Main popup UI (React)
│   │   └── main.jsx
│   ├── options/
│   │   ├── Options.jsx     ← Applicant settings UI (React)
│   │   └── main.jsx
│   └── index.css
├── public/
│   ├── assets/ARCUS_DOG.png
│   └── icons/
├── scripts/
│   └── copy-assets.js      ← Post-build asset copier
├── dist/                   ← Built output → load this in Chrome
├── manifest.json
├── popup.html
├── options.html
├── vite.config.js
└── package.json
```

## One-time Setup

```bash
cd ext
npm install
npm run build
```

## Loading in Chrome

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the **`ext/dist/`** folder

## After Updating Templates

If `templates/AVR.pdf` or `templates/SAAF.pdf` change, regenerate `templates.js` from the project root:

```powershell
# From ArcusAutomate\ root:
$avr  = [Convert]::ToBase64String([IO.File]::ReadAllBytes("templates\AVR.pdf"))
$saaf = [Convert]::ToBase64String([IO.File]::ReadAllBytes("templates\SAAF.pdf"))
"export const AVR_PDF_B64 = `"$avr`";`nexport const SAAF_PDF_B64 = `"$saaf`";" | Out-File ext\src\lib\templates.js -Encoding utf8
```

Then rebuild:
```bash
cd ext && npm run build
```

And reload the extension in Chrome (`chrome://extensions` → click 🔄).

## Development (Hot Reload)

```bash
cd ext
npm run dev
```
Opens at `http://localhost:5173/popup.html` — you can test the UI in the browser.
Note: `chrome.storage` and `chrome.downloads` won't work in dev mode (localStorage fallback is used instead).

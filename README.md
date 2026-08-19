# Arcus Proposal Automation

Generates AVR, SAAF, and a merged Master PDF (Proposal + SAAF + AVR) from an
Arcus event proposal PDF, via a Chrome extension talking to a small local
server on your own computer. No AWS account, no cloud hosting, no cost —
each person runs their own copy.

---

## 1. Requirements

- Python 3.10+ installed (check with `python --version` or `python3 --version`)
- Google Chrome

## 2. Set up the local server

1. Download/clone this folder. It should contain:
   ```
   app.py
   extract.py
   avr.py
   saaf.py
   requirements.txt
   templates/        (AVR.pdf, SAAF.pdf blank templates — whatever avr.py/saaf.py expect)
   extension/         (the Chrome extension folder)
   ```
2. Open a terminal in this folder and install dependencies:
   ```
   pip install -r requirements.txt
   ```
   (On some systems use `pip3` instead of `pip`.)
3. Start the server:
   ```
   python app.py
   ```
   You should see something like:
   ```
    * Running on http://127.0.0.1:5000
   ```
   **Leave this terminal window open** — the server needs to keep running
   while you use the extension. Closing the terminal stops it.

## 3. Install the Chrome extension

1. Open Chrome and go to `chrome://extensions`.
2. Turn on **Developer mode** (top-right toggle).
3. Click **Load unpacked**.
4. Select the `extension/` folder from this project.
5. The extension icon should now appear in your Chrome toolbar. Pin it for
   easy access (puzzle-piece icon → pin).

## 4. Fill in your Applicant Profile (one-time)

1. Click the extension icon → **⚙ Applicant Settings**.
2. Fill in your name, student number, program/year, position, department,
   section, contact number, and organization name.
3. Click **Save**. This is stored in your own Chrome profile only — it is
   never sent anywhere except to your own local server when you generate
   documents.

## 5. Generate documents

1. Make sure `python app.py` is still running in your terminal.
2. Click the extension icon.
3. Drag & drop your proposal PDF onto the upload box (or click to browse).
4. Click **Generate Documents**.
5. Download the AVR, SAAF, and Master PDF using the buttons that appear.

If the proposal doesn't follow the required format (see the **Proposal
Guidelines** link in the extension), you'll get an error listing exactly
which fields failed validation instead of a generated file.

---

## For other people you're sharing this with

Each person needs their own copy of this whole folder and runs steps 2–3
themselves, on their own computer. Nothing here is shared or centralized —
your local server only talks to your own browser (`localhost`), so there's
nothing to configure differently between people; everyone's setup is
identical and independent.

## Troubleshooting

- **"Failed to fetch" / extension can't reach the server** — make sure
  `python app.py` is running and the terminal shows no errors.
- **Port 5000 already in use** — another program is using that port. Either
  close it, or change the port in the last line of `app.py`
  (`app.run(..., port=5000)`) and update `API_ENDPOINT` in
  `extension/popup.js` to match, then reload the extension.
- **CORS error in the browser console** — confirm `flask-cors` installed
  correctly (`pip install flask-cors`) and restart `app.py`.

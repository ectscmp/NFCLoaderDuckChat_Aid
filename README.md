# Duck Portal Browser

This project listens to the NFC portal service and automatically opens a browser to a duck’s URL when a duck is placed on the reader.

- Duck placed → loads duck URL
- Duck removed → shows default message
- Reuses a single browser window (no spam tabs)

---

## Requirements

- Python 3.9+
- NFC reader (PC/SC compatible)
- Duck tags with NDEF URL records

---

## Setup Instructions

### 1. Clone or Download Project

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

---

### 2. Create a Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Mac / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Install Dependencies

If you have a `requirements.txt`:

```bash
pip install -r requirements.txt
```

If not, use:

```bash
pip install pyscard pywebview
```

---

## Running the Program

```bash
python portal_duck_browser_fixed.py
```

---

## Simulation Mode (No NFC Reader Required)

```bash
python portal_duck_browser_fixed.py --sim
```

---

## How It Works

- Listens to NFC readers using your portal system
- Reads NDEF records from duck tags:
    - URL → used to load browser

- Tracks current state:
    - Prevents duplicate reloads
    - Detects removal and resets UI

- Uses a **single browser window** that updates instead of opening new tabs

---

## Default Screen

When no duck is present, the browser shows:

> **"Please place a duck on the portal"**

This is loaded from:

```bash
default.html
```

You can customize this file to change the UI.

---

## Project Structure (Typical)

```
project/
│
├── portal_duck_browser_fixed.py
├── nfc_portal.py
├── reader_service.py
├── default.html
├── requirements.txt
└── README.md
```

---

## Troubleshooting

### pywebview must be run on main thread

Make sure:

- `webview.start()` runs in the main thread
- portal/NFC runs in a background thread

---

### No attribute load_html

Your browser must be:

- a `pywebview` window, OR
- your custom browser must implement `load_html()`

---

### Duck not loading after removal

Ensure you:

- clear `_last_loaded_url`
- remove reader entry from `_last_reader_url`

---

## Future Improvements

- Split screen for 2 readers (left/right portals) - Allow ducks to chat?
- Show duck name before page loads
- Add loading animation
- Offline mode using JSON record

# ZeroLag — PC Performance Diagnostic for Gamers (Windows)

ZeroLag is a **local** (no-telemetry) diagnostics tool that scans a Windows PC, detects common performance killers,
and generates a clean report (**Markdown + PDF**) with a **Performance Score**.

✅ Runs locally  
✅ No system changes (analysis only)  
✅ Gamer-focused mode (FPS/latency killers)  

---

## What you get

- **Performance Score** (0–100) + breakdown
- System snapshot (CPU / RAM / Disk)
- Startup items scan (common “boot slow / background bloat” culprit)
- Top processes snapshot (CPU/RAM hogs)
- Prioritized recommendations (High / Medium / Low)
- Export:
  - `scan.json`
  - `report.md`
  - `report.pdf`

---

## Quick start

### 1) Install Python (Windows)
Install **Python 3.10+** from python.org (check “Add Python to PATH”).

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Run (GUI)
```bash
python run_gui.py
```

### 4) Run (CLI)
```bash
python run_cli.py --mode gaming --out reports
```

Modes:
- `general` (default)
- `gaming` (stricter thresholds + gamer-oriented tips)

---

## Screenshots (add after first run)

- `docs/screenshot-gui.png`
- `docs/screenshot-report.png`

---

## Design principles

- **Privacy-first**: local only, no network calls
- **Readable output**: short, prioritized actions
- **Safe by default**: recommends actions; never applies changes

---

## License
MIT

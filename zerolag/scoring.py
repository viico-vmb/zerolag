from __future__ import annotations

from typing import Any, Dict, Tuple, List

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}

def clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))

def score_system(data: Dict[str, Any], mode: str = "general") -> Dict[str, Any]:
    """Return a performance score (0-100) with breakdown and notes.

    This is a heuristic score (not a benchmark). It rewards healthy headroom:
    - free disk space
    - low RAM pressure
    - reasonable startup items count
    - low CPU load at scan time
    """
    mode = (mode or "general").lower().strip()
    gaming = mode == "gaming"

    cpu = data.get("cpu") or {}
    ram = data.get("ram") or {}
    disks = data.get("disks") or []
    startup = data.get("startup_items") or []

    cpu_pct = float(cpu.get("cpu_pct") or 0.0)
    ram_used = float(ram.get("used_pct") or 0.0)
    startup_n = len(startup)

    # Consider the system drive primarily; if unknown, take worst free%
    free_pcts = [d.get("free_pct") for d in disks if d.get("free_pct") is not None]
    disk_free_pct = float(min(free_pcts)) if free_pcts else 100.0

    # Thresholds
    # Gaming expects more headroom.
    ram_warn = 70 if not gaming else 60
    ram_bad  = 85 if not gaming else 75

    cpu_warn = 60 if not gaming else 50
    cpu_bad  = 85 if not gaming else 75

    disk_warn = 25 if not gaming else 30
    disk_bad  = 15 if not gaming else 20

    startup_warn = 7 if not gaming else 6
    startup_bad  = 12 if not gaming else 10

    # Start at 100, subtract penalties (bounded)
    score = 100.0
    breakdown: List[Dict[str, Any]] = []

    def penalize(tag: str, penalty: float, reason: str):
        nonlocal score
        penalty = float(clamp(penalty, 0, 40))
        score -= penalty
        breakdown.append({"tag": tag, "penalty": round(penalty, 1), "reason": reason})

    # RAM penalty
    if ram_used >= ram_bad:
        penalize("RAM", 25 + (ram_used - ram_bad) * 0.6, f"High RAM pressure ({ram_used:.0f}%).")
    elif ram_used >= ram_warn:
        penalize("RAM", 10 + (ram_used - ram_warn) * 0.4, f"Moderate RAM pressure ({ram_used:.0f}%).")

    # Disk penalty
    if disk_free_pct <= disk_bad:
        penalize("Disk", 25 + (disk_bad - disk_free_pct) * 0.8, f"Very low free disk space ({disk_free_pct:.0f}%).")
    elif disk_free_pct <= disk_warn:
        penalize("Disk", 10 + (disk_warn - disk_free_pct) * 0.5, f"Low free disk space ({disk_free_pct:.0f}%).")

    # Startup penalty
    if startup_n >= startup_bad:
        penalize("Startup", 18 + (startup_n - startup_bad) * 0.7, f"Too many startup items ({startup_n}).")
    elif startup_n >= startup_warn:
        penalize("Startup", 8 + (startup_n - startup_warn) * 0.8, f"Several startup items ({startup_n}).")

    # CPU penalty
    if cpu_pct >= cpu_bad:
        penalize("CPU", 18 + (cpu_pct - cpu_bad) * 0.5, f"High CPU load at scan time ({cpu_pct:.0f}%).")
    elif cpu_pct >= cpu_warn:
        penalize("CPU", 7 + (cpu_pct - cpu_warn) * 0.4, f"CPU moderately loaded ({cpu_pct:.0f}%).")

    score = clamp(score, 0, 100)

    band = "Excellent" if score >= 85 else "Good" if score >= 70 else "Fair" if score >= 55 else "Poor"
    return {
        "mode": mode,
        "score": int(round(score)),
        "band": band,
        "inputs": {
            "cpu_pct": round(cpu_pct, 1),
            "ram_used_pct": round(ram_used, 1),
            "disk_free_pct_min": round(disk_free_pct, 1),
            "startup_items": startup_n,
        },
        "breakdown": breakdown,
    }

from __future__ import annotations

import os
import sys
import platform
import time
import json
from typing import Any, Dict, List

import psutil

from .scoring import score_system

IS_WINDOWS = os.name == "nt"


def _bytes_gb(n: float) -> float:
    return round(n / (1024 ** 3), 2)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _safe_get(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _read_startup_items_windows() -> List[Dict[str, str]]:
    """Read common Windows startup entries from registry."""
    items: List[Dict[str, str]] = []
    if not IS_WINDOWS:
        return items

    try:
        import winreg  # type: ignore
    except Exception:
        return items

    locations = [
        ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Run"),
    ]

    for scope, root, path in locations:
        try:
            with winreg.OpenKey(root, path) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        items.append({"scope": scope, "name": str(name), "command": str(value)})
                        i += 1
                    except OSError:
                        break
        except Exception:
            continue
    return items


def _disk_summary() -> List[Dict[str, Any]]:
    disks: List[Dict[str, Any]] = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts.lower():
            continue
        usage = _safe_get(lambda: psutil.disk_usage(part.mountpoint))
        if not usage:
            continue
        disks.append(
            {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": _bytes_gb(usage.total),
                "used_gb": _bytes_gb(usage.used),
                "free_gb": _bytes_gb(usage.free),
                "free_pct": round(usage.free / usage.total * 100, 1) if usage.total else None,
            }
        )
    return disks


def _top_processes(limit: int = 10) -> List[Dict[str, Any]]:
    procs: List[Dict[str, Any]] = []
    for p in psutil.process_iter(attrs=["pid", "name"]):
        try:
            with p.oneshot():
                cpu = p.cpu_percent(interval=0.0)
                mem = p.memory_info().rss
                procs.append(
                    {
                        "pid": p.info.get("pid"),
                        "name": p.info.get("name"),
                        "cpu_pct": cpu,
                        "ram_gb": _bytes_gb(mem),
                    }
                )
        except Exception:
            continue
    procs.sort(key=lambda x: (x.get("cpu_pct") or 0, x.get("ram_gb") or 0), reverse=True)
    return procs[:limit]


def _cpu_snapshot() -> Dict[str, Any]:
    cpu_pct = psutil.cpu_percent(interval=0.6)
    freq = _safe_get(lambda: psutil.cpu_freq())
    return {
        "cpu_pct": cpu_pct,
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "max_mhz": round(freq.max, 0) if freq else None,
        "current_mhz": round(freq.current, 0) if freq else None,
    }


def _ram_snapshot() -> Dict[str, Any]:
    vm = psutil.virtual_memory()
    return {
        "total_gb": _bytes_gb(vm.total),
        "available_gb": _bytes_gb(vm.available),
        "used_pct": round(vm.percent, 1),
    }


def _system_info() -> Dict[str, Any]:
    uname = platform.uname()
    return {
        "timestamp": _now_iso(),
        "os": f"{uname.system} {uname.release}",
        "os_version": uname.version,
        "machine": uname.machine,
        "processor": uname.processor,
        "python": sys.version.split()[0],
    }


def _recommendations(data: Dict[str, Any], mode: str) -> List[Dict[str, Any]]:
    recs: List[Dict[str, Any]] = []
    gaming = (mode or "general").lower() == "gaming"

    # Disk free space warnings (gaming expects more space)
    warn = 25 if not gaming else 30
    bad = 15 if not gaming else 20

    for d in data.get("disks", []):
        free_pct = d.get("free_pct")
        mp = d.get("mountpoint")
        if free_pct is not None and free_pct < bad:
            recs.append(
                {
                    "priority": "High",
                    "title": f"Low free space on {mp}",
                    "why": "Low disk free space can slow down Windows, updates, and games.",
                    "action": "Uninstall unused apps/games, move large files, empty Recycle Bin, clear temp files.",
                }
            )
        elif free_pct is not None and free_pct < warn:
            recs.append(
                {
                    "priority": "Medium",
                    "title": f"Free space getting tight on {mp}",
                    "why": "Keeping comfortable free space helps performance and stability.",
                    "action": "Plan cleanup: remove large downloads, clear temp files, move archives.",
                }
            )

    # RAM usage (gaming stricter)
    used_pct = (data.get("ram") or {}).get("used_pct")
    ram_warn = 70 if not gaming else 60
    ram_bad = 85 if not gaming else 75
    if used_pct is not None and used_pct >= ram_bad:
        recs.append(
            {
                "priority": "High",
                "title": "High RAM usage",
                "why": "When RAM is near full, Windows swaps to disk, causing stutter and slowdowns.",
                "action": "Close heavy apps/tabs, disable background apps, consider RAM upgrade if persistent.",
            }
        )
    elif used_pct is not None and used_pct >= ram_warn:
        recs.append(
            {
                "priority": "Medium",
                "title": "RAM pressure",
                "why": "Background apps and browsers can degrade gaming/productivity over time.",
                "action": "Reduce startup apps, keep fewer browser tabs, monitor RAM-hungry processes.",
            }
        )

    # Startup items count (gaming slightly stricter)
    startup = data.get("startup_items", [])
    s_warn = 7 if not gaming else 6
    s_bad = 12 if not gaming else 10
    if len(startup) >= s_bad:
        recs.append(
            {
                "priority": "High",
                "title": "Many startup items",
                "why": "Too many startup apps slow boot and keep background CPU/RAM usage high.",
                "action": "Disable non-essential items in Task Manager → Startup, or uninstall unused software.",
            }
        )
    elif len(startup) >= s_warn:
        recs.append(
            {
                "priority": "Medium",
                "title": "Several startup items",
                "why": "Startup apps can silently reduce performance.",
                "action": "Review startup list and keep only essentials (GPU driver, audio, security).",
            }
        )

    # CPU load (gaming stricter)
    cpu_pct = (data.get("cpu") or {}).get("cpu_pct")
    c_warn = 60 if not gaming else 50
    c_bad = 85 if not gaming else 75
    if cpu_pct is not None and cpu_pct >= c_bad:
        recs.append(
            {
                "priority": "High",
                "title": "High CPU usage at scan time",
                "why": "High CPU load can cause FPS drops and system lag.",
                "action": "Check top processes list; close runaway apps; scan for unwanted background tools.",
            }
        )
    elif cpu_pct is not None and cpu_pct >= c_warn:
        recs.append(
            {
                "priority": "Low",
                "title": "CPU moderately loaded",
                "why": "Could be normal, but worth monitoring during gaming or heavy work.",
                "action": "If performance issues exist, review top processes and background tasks.",
            }
        )

    # Gamer tips (safe)
    if gaming:
        recs.append(
            {
                "priority": "Low",
                "title": "Gaming mode checklist",
                "why": "Small settings can reduce stutter/latency.",
                "action": "Use exclusive fullscreen where applicable, disable overlays you don't need, keep GPU driver updated.",
            }
        )

    # Safe defaults
    recs.append(
        {
            "priority": "Low",
            "title": "Keep drivers and Windows updated",
            "why": "GPU drivers and system updates often improve stability and performance.",
            "action": "Update GPU drivers from official vendor, and run Windows Update regularly.",
        }
    )
    recs.append(
        {
            "priority": "Low",
            "title": "Storage hygiene",
            "why": "Large temp folders and downloads build up over time.",
            "action": "Run Windows Storage Sense, clear temp files, and keep downloads organized.",
        }
    )

    order = {"High": 0, "Medium": 1, "Low": 2}
    recs.sort(key=lambda r: order.get(r.get("priority", "Low"), 9))
    return recs


def run_scan(mode: str = "general") -> Dict[str, Any]:
    """Runs a diagnostics scan and returns a structured dict."""
    data: Dict[str, Any] = {}
    data["mode"] = (mode or "general").lower().strip()
    data["system"] = _system_info()
    data["cpu"] = _cpu_snapshot()
    data["ram"] = _ram_snapshot()
    data["disks"] = _disk_summary()

    # seed CPU% then snapshot
    _ = _top_processes(limit=16)
    time.sleep(0.6)
    data["top_processes"] = _top_processes(limit=10)

    data["startup_items"] = _read_startup_items_windows()
    data["score"] = score_system(data, mode=data["mode"])
    data["recommendations"] = _recommendations(data, mode=data["mode"])
    return data


def save_json(data: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

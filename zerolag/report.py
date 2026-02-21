from __future__ import annotations

import os
from typing import Any, Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def _md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def render_markdown(data: Dict[str, Any]) -> str:
    sys = data.get("system", {})
    cpu = data.get("cpu", {})
    ram = data.get("ram", {})
    disks = data.get("disks", [])
    procs = data.get("top_processes", [])
    startup = data.get("startup_items", [])
    recs = data.get("recommendations", [])
    score = (data.get("score") or {})

    lines: List[str] = []
    lines.append("# ZeroLag Diagnostic Report")
    lines.append("")
    lines.append(f"**Mode:** {data.get('mode','general')}  ")
    lines.append(f"**Performance Score:** **{score.get('score','?')} / 100** ({score.get('band','')})  ")
    lines.append("")
    lines.append(f"**Generated:** {sys.get('timestamp','')}  ")
    lines.append(f"**OS:** {sys.get('os','')}  ")
    lines.append(f"**Machine:** {sys.get('machine','')}  ")
    proc = sys.get("processor") or "Unknown"
    lines.append(f"**CPU:** {_md_escape(proc)}  ")
    lines.append("")

    lines.append("## Score breakdown")
    lines.append("")
    bd = score.get("breakdown") or []
    if bd:
        lines.append("| Area | Penalty | Reason |")
        lines.append("|---|---:|---|")
        for b in bd:
            lines.append(f"| {b.get('tag','')} | {b.get('penalty','')} | {_md_escape(b.get('reason',''))} |")
    else:
        lines.append("_No major issues detected by the heuristic scoring._")
    lines.append("")

    lines.append("## Snapshot")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| CPU load (scan time) | {cpu.get('cpu_pct','?')}% |")
    lines.append(f"| RAM used | {ram.get('used_pct','?')}% |")
    lines.append(f"| RAM total | {ram.get('total_gb','?')} GB |")
    lines.append(f"| Cores | {cpu.get('physical_cores','?')} physical / {cpu.get('logical_cores','?')} logical |")
    mhz = cpu.get("current_mhz")
    if mhz:
        lines.append(f"| CPU freq | {mhz} MHz (current) |")
    lines.append("")

    lines.append("## Storage")
    lines.append("")
    if disks:
        lines.append("| Mount | Total (GB) | Free (GB) | Free (%) | FS |")
        lines.append("|---|---:|---:|---:|---|")
        for d in disks:
            lines.append(
                f"| {d.get('mountpoint','')} | {d.get('total_gb','')} | {d.get('free_gb','')} | {d.get('free_pct','')} | {d.get('fstype','')} |"
            )
        lines.append("")
    else:
        lines.append("_No disk info available._\n")

    lines.append("## Startup items (common registry locations)")
    lines.append("")
    lines.append(f"Total items found: **{len(startup)}**")
    if startup:
        lines.append("")
        lines.append("| Scope | Name | Command |")
        lines.append("|---|---|---|")
        for s in startup[:20]:
            lines.append(f"| {s.get('scope','')} | {_md_escape(s.get('name',''))} | {_md_escape(s.get('command',''))} |")
        if len(startup) > 20:
            lines.append("")
            lines.append(f"_Showing first 20 of {len(startup)} items._")
    lines.append("")

    lines.append("## Top processes (snapshot)")
    lines.append("")
    if procs:
        lines.append("| Process | CPU (%) | RAM (GB) | PID |")
        lines.append("|---|---:|---:|---:|")
        for p in procs:
            lines.append(f"| {_md_escape(str(p.get('name','')))} | {p.get('cpu_pct','')} | {p.get('ram_gb','')} | {p.get('pid','')} |")
    else:
        lines.append("_No process info available._")
    lines.append("")

    lines.append("## Recommendations")
    lines.append("")
    for r in recs:
        lines.append(f"### [{r.get('priority','Low')}] {r.get('title','')}")
        lines.append(f"- **Why:** {r.get('why','')}")
        lines.append(f"- **Action:** {r.get('action','')}")
        lines.append("")
    return "\n".join(lines)


def save_markdown(md: str, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)


def _priority_color(priority: str):
    p = (priority or "low").lower()
    if p == "high":
        return colors.HexColor("#D64541")  # red-ish
    if p == "medium":
        return colors.HexColor("#E67E22")  # orange-ish
    return colors.HexColor("#2E86C1")      # blue-ish


def render_pdf(data: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    x = 2 * cm
    y = h - 2 * cm

    sys = data.get("system", {})
    cpu = data.get("cpu", {})
    ram = data.get("ram", {})
    disks = data.get("disks", [])
    recs = data.get("recommendations", [])
    procs = data.get("top_processes", [])
    score = data.get("score") or {}

    def newpage_if_needed(min_y=2*cm):
        nonlocal y
        if y < min_y:
            c.showPage()
            y = h - 2 * cm

    def line(txt: str, dy: float = 14, font="Helvetica", size=10):
        nonlocal y
        c.setFont(font, size)
        c.drawString(x, y, txt)
        y -= dy
        newpage_if_needed()

    def badge(text: str, color):
        nonlocal y
        bw = 7.0 * cm
        bh = 0.6 * cm
        c.setFillColor(color)
        c.roundRect(x, y - bh + 3, bw, bh, 6, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 8, y - bh + 8, text)
        c.setFillColor(colors.black)
        y -= (bh + 10)
        newpage_if_needed()

    # Header
    line("ZeroLag Diagnostic Report", dy=20, font="Helvetica-Bold", size=16)
    line(f"Mode: {data.get('mode','general')}", dy=14)
    badge(f"Performance Score: {score.get('score','?')} / 100  —  {score.get('band','')}", colors.HexColor("#111111"))

    line(f"Generated: {sys.get('timestamp','')}", dy=14)
    line(f"OS: {sys.get('os','')}", dy=14)
    line(f"Machine: {sys.get('machine','')}", dy=14)
    line(f"CPU: {sys.get('processor') or 'Unknown'}", dy=18)

    # Snapshot
    line("Snapshot", dy=18, font="Helvetica-Bold", size=12)
    line(f"CPU load (scan time): {cpu.get('cpu_pct','?')}%", dy=14)
    line(f"RAM used: {ram.get('used_pct','?')}% (Total: {ram.get('total_gb','?')} GB)", dy=14)
    line(f"Cores: {cpu.get('physical_cores','?')} physical / {cpu.get('logical_cores','?')} logical", dy=14)
    if cpu.get("current_mhz"):
        line(f"CPU freq (current): {cpu.get('current_mhz')} MHz", dy=18)

    # Storage
    line("Storage", dy=18, font="Helvetica-Bold", size=12)
    if disks:
        for d in disks:
            line(f"{d.get('mountpoint','')}: {d.get('free_gb','?')} GB free ({d.get('free_pct','?')}%) of {d.get('total_gb','?')} GB [{d.get('fstype','')}]")
    else:
        line("No disk info available.")
    y -= 8
    newpage_if_needed()

    # Top processes
    line("Top processes (snapshot)", dy=18, font="Helvetica-Bold", size=12)
    if procs:
        for p in procs[:12]:
            line(f"{p.get('name','')}: CPU {p.get('cpu_pct','?')}% | RAM {p.get('ram_gb','?')} GB | PID {p.get('pid','')}")
    else:
        line("No process info available.")
    y -= 8
    newpage_if_needed()

    # Recommendations
    line("Recommendations", dy=18, font="Helvetica-Bold", size=12)
    for r in recs:
        pr = r.get("priority","Low")
        badge(f"{pr.upper()} — {r.get('title','')}", _priority_color(pr))
        line(f"Why: {r.get('why','')}", dy=14)
        line(f"Action: {r.get('action','')}", dy=16)
    c.showPage()
    c.save()

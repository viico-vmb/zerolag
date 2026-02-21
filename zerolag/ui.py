from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .core import run_scan, save_json
from .report import render_markdown, save_markdown, render_pdf


class ZeroLagApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZeroLag — PC Performance Diagnostic")
        self.geometry("900x560")
        self.minsize(900, 560)

        self.data = None
        self.mode = tk.StringVar(value="gaming")

        self._build()

    def _build(self):
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(top, text="ZeroLag", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(top, text="PC Performance Diagnostic", font=("Segoe UI", 11)).pack(side="left", padx=(10, 0))

        right = ttk.Frame(top)
        right.pack(side="right")
        ttk.Label(right, text="Mode:").pack(side="left")
        ttk.OptionMenu(right, self.mode, self.mode.get(), "gaming", "general").pack(side="left", padx=(6, 10))
        ttk.Label(right, textvariable=self.status).pack(side="left")

        mid = ttk.Frame(self, padding=12)
        mid.pack(fill="both", expand=True)

        left = ttk.Frame(mid)
        left.pack(side="left", fill="y")

        self.btn_scan = ttk.Button(left, text="Run Scan", command=self.run_scan_async)
        self.btn_scan.pack(fill="x", pady=(0, 8))

        self.btn_export = ttk.Button(left, text="Export Report…", command=self.export_report, state="disabled")
        self.btn_export.pack(fill="x")

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=12)

        self.score_label = tk.StringVar(value="Performance Score: —")
        ttk.Label(left, textvariable=self.score_label, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        ttk.Label(left, text="Principles:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(
            left,
            text="• Local only (no telemetry)\n"
                 "• Analysis only (no system changes)\n"
                 "• Prioritized, actionable recommendations",
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        right = ttk.Frame(mid)
        right.pack(side="left", fill="both", expand=True, padx=(16, 0))

        ttk.Label(right, text="Summary", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.text = tk.Text(right, wrap="word", height=24)
        self.text.pack(fill="both", expand=True)
        self._write("Select a mode and click 'Run Scan'.\n")

    def _write(self, s: str):
        self.text.insert("end", s)
        self.text.see("end")

    def run_scan_async(self):
        self.btn_scan.config(state="disabled")
        self.btn_export.config(state="disabled")
        self.text.delete("1.0", "end")
        self.score_label.set("Performance Score: —")
        self.status.set("Scanning…")

        mode = self.mode.get()

        def task():
            try:
                data = run_scan(mode=mode)
                self.data = data
                self.after(0, lambda: self.show_results(data))
            except Exception as e:
                self.after(0, lambda: self.on_error(e))

        threading.Thread(target=task, daemon=True).start()

    def on_error(self, e: Exception):
        self.status.set("Error.")
        self.btn_scan.config(state="normal")
        messagebox.showerror("ZeroLag", f"Scan failed: {e}")

    def show_results(self, data):
        sys = data.get("system", {})
        cpu = data.get("cpu", {})
        ram = data.get("ram", {})
        disks = data.get("disks", [])
        startup = data.get("startup_items", [])
        recs = data.get("recommendations", [])
        procs = data.get("top_processes", [])
        score = data.get("score") or {}

        self.score_label.set(f"Performance Score: {score.get('score','?')} / 100  ({score.get('band','')})")
        self._write("=== Score ===\n")
        self._write(f"Mode: {data.get('mode','general')}\n")
        self._write(f"Performance Score: {score.get('score','?')} / 100  ({score.get('band','')})\n\n")

        bd = score.get("breakdown") or []
        if bd:
            self._write("Breakdown:\n")
            for b in bd:
                self._write(f"- {b.get('tag','')}: -{b.get('penalty','')}  ({b.get('reason','')})\n")
            self._write("\n")

        self._write("=== System ===\n")
        self._write(f"Generated: {sys.get('timestamp','')}\n")
        self._write(f"OS: {sys.get('os','')}\n")
        self._write(f"Machine: {sys.get('machine','')}\n")
        self._write(f"CPU: {sys.get('processor') or 'Unknown'}\n\n")

        self._write("=== Snapshot ===\n")
        self._write(f"CPU load: {cpu.get('cpu_pct','?')}%\n")
        self._write(f"RAM used: {ram.get('used_pct','?')}% (Total {ram.get('total_gb','?')} GB)\n")
        self._write(f"Cores: {cpu.get('physical_cores','?')} physical / {cpu.get('logical_cores','?')} logical\n\n")

        self._write("=== Storage ===\n")
        if disks:
            for d in disks:
                self._write(
                    f"{d.get('mountpoint','')}: {d.get('free_gb','?')} GB free "
                    f"({d.get('free_pct','?')}%) of {d.get('total_gb','?')} GB\n"
                )
        else:
            self._write("No disk info available.\n")
        self._write("\n")

        self._write("=== Startup items ===\n")
        self._write(f"Found: {len(startup)} items (common registry locations)\n\n")

        self._write("=== Top processes ===\n")
        for p in procs[:8]:
            self._write(
                f"{p.get('name','')}: CPU {p.get('cpu_pct','?')}% | "
                f"RAM {p.get('ram_gb','?')} GB | PID {p.get('pid','')}\n"
            )
        self._write("\n")

        self._write("=== Recommendations ===\n")
        for r in recs[:12]:
            self._write(f"[{r.get('priority','Low')}] {r.get('title','')}\n")
            self._write(f"  Why: {r.get('why','')}\n")
            self._write(f"  Action: {r.get('action','')}\n\n")

        self.status.set("Scan complete.")
        self.btn_scan.config(state="normal")
        self.btn_export.config(state="normal")

    def export_report(self):
        if not self.data:
            messagebox.showinfo("ZeroLag", "Run a scan first.")
            return

        out_dir = filedialog.askdirectory(title="Choose export folder")
        if not out_dir:
            return

        try:
            json_path = os.path.join(out_dir, "scan.json")
            md_path = os.path.join(out_dir, "report.md")
            pdf_path = os.path.join(out_dir, "report.pdf")

            save_json(self.data, json_path)
            md = render_markdown(self.data)
            save_markdown(md, md_path)
            render_pdf(self.data, pdf_path)

            messagebox.showinfo("ZeroLag", f"Exported:\n- {json_path}\n- {md_path}\n- {pdf_path}")
        except Exception as e:
            messagebox.showerror("ZeroLag", f"Export failed: {e}")


def main():
    app = ZeroLagApp()
    app.mainloop()


if __name__ == "__main__":
    main()

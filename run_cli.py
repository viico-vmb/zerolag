import argparse
import os
from zerolag.core import run_scan, save_json
from zerolag.report import render_markdown, save_markdown, render_pdf

def main():
    p = argparse.ArgumentParser(description="ZeroLag — PC Performance Diagnostic")
    p.add_argument("--out", default="reports", help="Output directory for reports")
    p.add_argument("--mode", default="general", choices=["general", "gaming"], help="Scan mode")
    args = p.parse_args()

    data = run_scan(mode=args.mode)
    os.makedirs(args.out, exist_ok=True)

    json_path = os.path.join(args.out, "scan.json")
    md_path = os.path.join(args.out, "report.md")
    pdf_path = os.path.join(args.out, "report.pdf")

    save_json(data, json_path)
    md = render_markdown(data)
    save_markdown(md, md_path)
    render_pdf(data, pdf_path)

    s = data.get("score") or {}
    print("✅ ZeroLag scan complete")
    print(f"Mode: {data.get('mode','general')} | Score: {s.get('score','?')}/100 ({s.get('band','')})")
    print(f"- JSON: {json_path}")
    print(f"- MD:   {md_path}")
    print(f"- PDF:  {pdf_path}")

if __name__ == "__main__":
    main()

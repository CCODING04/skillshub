#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic PDF inspection: render pages to PNG and extract table structures.

Replaces any vendor-specific PDF tool. Backends (auto-detected, in order):
  1. PyMuPDF (`pip install pymupdf`)  — full support: page PNG + table JSON
  2. poppler CLI (`pdftoppm`/`pdftotext`) — page PNG + text only, no table cells
If neither is available, prints install instructions and exits non-zero.

Usage:
  python inspect_pdf.py paper.pdf --out temp/pdfcheck
  python inspect_pdf.py paper.pdf --out temp/pdfcheck --dpi 150 --pages 1-10
"""
import argparse, json, os, shutil, subprocess, sys


def parse_pages(spec, total):
    if not spec or spec.lower() == "all":
        return list(range(1, total + 1))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part.strip().isdigit():
            out.append(int(part))
    return [p for p in out if 1 <= p <= total]


def backend_pymupdf():
    try:
        import fitz
        return fitz
    except ImportError:
        return None


def run_pymupdf(pdf, out, dpi, pages):
    fitz = backend_pymupdf()
    if fitz is None:
        return False
    os.makedirs(out, exist_ok=True)
    doc = fitz.open(pdf)
    todo = parse_pages(pages, doc.page_count)
    for pno in todo:
        page = doc[pno - 1]
        pix = page.get_pixmap(dpi=dpi)
        pix.save(os.path.join(out, "page-%04d.png" % pno))
    # table extraction (PyMuPDF >= 1.23)
    tables = {}
    tdir = os.path.join(out, "tables")
    os.makedirs(tdir, exist_ok=True)
    for pno in todo:
        page = doc[pno - 1]
        try:
            tf = page.find_tables()
            found = tf.tables
        except Exception:
            found = []
        for idx, t in enumerate(found, 1):
            data = {"page": pno, "rows": t.row_count, "columns": t.col_count,
                    "cells": []}
            for r in range(t.row_count):
                for c in range(t.col_count):
                    val = t.cell(r, c)
                    data["cells"].append({"row": r, "column": c,
                                          "row_span": 1, "column_span": 1,
                                          "text": (val or "").replace("\n", " ")})
            with open(os.path.join(tdir, "page_%03d_table_%03d.json" % (pno, idx)),
                      "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tables["%d-%d" % (pno, idx)] = len(data["cells"])
    doc.close()
    print("PyMuPDF: rendered %d page(s), extracted %d table(s) -> %s" %
          (len(todo), len(tables), out))
    return True


def run_poppler(pdf, out, dpi, pages):
    if not (shutil.which("pdftoppm") and shutil.which("pdfinfo")):
        return False
    os.makedirs(out, exist_ok=True)
    info = subprocess.check_output(["pdfinfo", pdf], text=True, errors="ignore")
    total = 0
    for line in info.splitlines():
        if line.startswith("Pages:"):
            total = int(line.split(":", 1)[1].strip())
            break
    todo = parse_pages(pages, total)
    for pno in todo:
        subprocess.run(["pdftoppm", "-f", str(pno), "-l", str(pno), "-r", str(dpi),
                        "-png", "-singlefile", pdf,
                        os.path.join(out, "page-%04d" % pno)], check=True)
    print("poppler: rendered %d page(s) -> %s (no table cells; install pymupdf for tables)" %
          (len(todo), out))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", help="input PDF path")
    ap.add_argument("--out", default="temp/pdfcheck", help="output directory")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--pages", default="all", help="e.g. '1-10,15' (default: all)")
    args = ap.parse_args()
    if not os.path.exists(args.pdf):
        ap.error("PDF not found: %s" % args.pdf)
    for fn in (run_pymupdf, run_poppler):
        try:
            if fn(args.pdf, args.out, args.dpi, args.pages):
                return
        except Exception as e:
            print("%s failed: %s: %s" % (fn.__name__, type(e).__name__, str(e)[:200]),
                  file=sys.stderr)
    sys.exit("No PDF backend available. Install one:\n"
             "  pip install pymupdf\n"
             "  (or install poppler-utils: apt install poppler-utils / brew install poppler)")


if __name__ == "__main__":
    main()

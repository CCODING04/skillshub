#!/usr/bin/env python3
"""Render vector-style HTML/CSS figure templates into 2x PNG via a headless browser.

No image-generation model is used. Chinese labels are rendered by the DOM.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser(explicit=None):
    if explicit:
        return explicit if os.path.exists(explicit) else None
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    for name in ["google-chrome", "chromium", "chromium-browser"]:
        p = shutil.which(name)
        if p:
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="JSON: {figures:[{html,out,width,height}]}")
    ap.add_argument("--dir", default=".", help="directory containing the HTML files and PNG outputs")
    ap.add_argument("--scale", type=int, default=2, help="device scale factor (2 = high-DPI)")
    ap.add_argument("--browser", default="", help="explicit browser executable")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    browser = find_browser(args.browser)
    if not browser:
        print("ERROR: no Chrome/Edge/Chromium found; pass --browser", file=sys.stderr)
        return 2

    with open(args.manifest, encoding="utf-8") as f:
        items = json.load(f)["figures"]
    base = Path(args.dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    failures = 0

    for i, item in enumerate(items):
        html = (base / item["html"]).resolve()
        out = (base / item["out"]).resolve()
        if not html.exists():
            print(f"MISSING {html}")
            failures += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        profile = tempfile.mkdtemp(prefix="figrender_")
        cmd = [
            browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
            "--disable-extensions", "--hide-scrollbars",
            f"--force-device-scale-factor={args.scale}",
            f"--user-data-dir={profile}",
            f"--window-size={item['width']},{item['height']}",
            f"--screenshot={out}", html.as_uri(),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
            ok = out.exists() and out.stat().st_size > 1000
            print(f"[{'OK' if ok else 'FAIL'}] {item['out']} "
                  f"{out.stat().st_size if out.exists() else 0} bytes  {item['width']}x{item['height']} @{args.scale}x")
            if not ok:
                print((r.stderr or r.stdout)[-400:], file=sys.stderr)
                failures += 1
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT {item['out']}", file=sys.stderr)
            failures += 1
        finally:
            shutil.rmtree(profile, ignore_errors=True)

    print(f"rendered {len(items) - failures}/{len(items)}; browser={browser}")
    print("NEXT: 逐张看图检查溢出/压字，修正 HTML 后重跑本脚本，再交给 build_article.py")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

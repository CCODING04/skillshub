#!/usr/bin/env python3
"""Render vector-style HTML/CSS figure templates into 2x PNG via a headless browser.

No image-generation model is used. Chinese labels are rendered by the DOM.
"""
import argparse
import glob
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


def playwright_candidates():
    """Chrome-for-Testing shells installed by Playwright.

    Desktop Chrome/Edge can be present but produce no screenshot at all on some
    Windows hosts (exit 0, no file). Those shells are a reliable third option.
    """
    roots = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright"),
        os.path.expanduser("~/.cache/ms-playwright"),
        os.path.expanduser("~/Library/Caches/ms-playwright"),
    ]
    pats = [
        "chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell*",
        "chromium-*/chrome-win/chrome.exe",
        "chromium-*/chrome-linux/chrome",
        "chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
    ]
    found = []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for pat in pats:
            for p in sorted(glob.glob(os.path.join(root, pat)), reverse=True):
                if os.path.isfile(p) and p not in found:
                    found.append(p)
    return found


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


def browser_candidates(explicit=None):
    """Ordered list to try: explicit → PATH/known installs → Playwright shells."""
    if explicit:
        return [explicit] if os.path.exists(explicit) else []
    out = []
    first = find_browser()
    if first:
        out.append(first)
    for p in CANDIDATES:
        if os.path.exists(p) and p not in out:
            out.append(p)
    for p in playwright_candidates():
        if p not in out:
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="JSON: {figures:[{html,out,width,height}]}")
    ap.add_argument("--dir", default=".", help="directory containing the HTML files and PNG outputs")
    ap.add_argument("--scale", type=int, default=2, help="device scale factor (2 = high-DPI)")
    ap.add_argument("--browser", default="", help="explicit browser executable")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    browsers = browser_candidates(args.browser)
    if not browsers:
        print("ERROR: no Chrome/Edge/Chromium/Playwright shell found; pass --browser", file=sys.stderr)
        return 2

    with open(args.manifest, encoding="utf-8") as f:
        items = json.load(f)["figures"]
    base = Path(args.dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    failures = 0
    used = browsers[0]

    for i, item in enumerate(items):
        html = (base / item["html"]).resolve()
        out = (base / item["out"]).resolve()
        if not html.exists():
            print(f"MISSING {html}")
            failures += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)

        ok = False
        tried = []
        for browser in [used] + [b for b in browsers if b != used]:
            tried.append(os.path.basename(browser))
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
                if ok:
                    used = browser
                    print(f"[OK] {item['out']} {out.stat().st_size} bytes  "
                          f"{item['width']}x{item['height']} @{args.scale}x  via {os.path.basename(browser)}")
                    break
                print(f"[retry] {os.path.basename(browser)} produced nothing for {item['out']}",
                      file=sys.stderr)
            except subprocess.TimeoutExpired:
                print(f"[retry] timeout with {os.path.basename(browser)}", file=sys.stderr)
            finally:
                shutil.rmtree(profile, ignore_errors=True)
        if not ok:
            print(f"[FAIL] {item['out']}  tried: {', '.join(tried)}", file=sys.stderr)
            failures += 1

    print(f"rendered {len(items) - failures}/{len(items)}; browser={os.path.basename(used)}")
    print("NEXT: 逐张看图检查溢出/压字，修正 HTML 后重跑本脚本，再交给 build_article.py")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

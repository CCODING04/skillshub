#!/usr/bin/env python3
"""Render vector-style HTML/CSS figure templates into 2x PNG via a headless browser.

No image-generation model is used. Chinese labels are rendered by the DOM.
"""
import argparse
import glob
import html
import json
import os
import re
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


def pronoun_hits(html_text):
    """图会被单独转发，图里不能只用「她/他」——脱离正文就没有指代对象。

    只查人物代称，不查「它」（指物，图里自足）；「其他/其它」不算。
    想保留原话里的代词，在 HTML 里写 <!-- allow-pronoun: 理由 -->。
    """
    if re.search(r"<!--\s*allow-pronoun", html_text):
        return []
    body = re.sub(r"<!--[\s\S]*?-->", " ", html_text)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body)
    body = re.sub(r"<title[\s\S]*?</title>", " ", body)
    plain = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return re.findall(r"(?<!其)[她他][们]?", plain)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="JSON: {figures:[{html,out,width,height}]}")
    ap.add_argument("--dir", default=".", help="directory containing the HTML files and PNG outputs")
    ap.add_argument("--scale", type=int, default=2, help="device scale factor (2 = high-DPI)")
    ap.add_argument("--browser", default="", help="explicit browser executable")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--allow-pronouns", action="store_true",
                    help="skip the F01 check (figure text must name the subject, not use 她/他)")
    args = ap.parse_args()

    browsers = browser_candidates(args.browser)
    if not browsers:
        print("ERROR: no Chrome/Edge/Chromium/Playwright shell found; pass --browser", file=sys.stderr)
        return 2

    with open(args.manifest, encoding="utf-8") as f:
        items = json.load(f)["figures"]
    base = Path(args.dir).resolve()
    base.mkdir(parents=True, exist_ok=True)

    if not args.allow_pronouns:
        bad = 0
        for item in items:
            src = (base / item["html"])
            if not src.exists():
                continue
            hits = pronoun_hits(src.read_text(encoding="utf-8"))
            if hits:
                bad += 1
                print(f"[F01] {item['html']} 用了人物代称 {hits}：图会被单独转发，"
                      f"标题与图内文字要写出具体主体（人名/团队/产品名）", file=sys.stderr)
        if bad:
            print(f"F01 FAILED on {bad} figure(s); 改完再渲染（确属引语可写 <!-- allow-pronoun: 理由 -->）",
                  file=sys.stderr)
            return 1

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
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.stem + ".tmp.png")
        for browser in [used] + [b for b in browsers if b != used]:
            tried.append(os.path.basename(browser))
            # 先写临时文件再改名：桌面版 Chrome/Edge 会「退出码 0、不写文件」，
            # 直接写 out 会让旧图冒充新图（曾因此误判成功），直接删 out 又会
            # 在全失败时毁掉上一版。临时文件两头都不占。
            if tmp.exists():
                tmp.unlink()
            profile = tempfile.mkdtemp(prefix="figrender_")
            cmd = [
                browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
                "--disable-extensions", "--hide-scrollbars",
                f"--force-device-scale-factor={args.scale}",
                f"--user-data-dir={profile}",
                f"--window-size={item['width']},{item['height']}",
                f"--screenshot={tmp}", html.as_uri(),
            ]
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
                ok = tmp.exists() and tmp.stat().st_size > 1000
                if ok:
                    os.replace(tmp, out)
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
                if tmp.exists():
                    tmp.unlink()
        if not ok:
            print(f"[FAIL] {item['out']}  tried: {', '.join(tried)}", file=sys.stderr)
            failures += 1

    print(f"rendered {len(items) - failures}/{len(items)}; browser={os.path.basename(used)}")
    print("NEXT: 逐张看图检查溢出/压字，修正 HTML 后重跑本脚本，再交给 build_article.py")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

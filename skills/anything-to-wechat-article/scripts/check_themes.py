#!/usr/bin/env python3
"""Validate theme.json files: schema, template placeholders, six code slots, contrast.

Checks what the theme spec requires (code slots, contrast floors) instead of leaving it to prose.
Exit 0 = all themes pass, 1 = any failure, 2 = input error.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_TOP = ["id", "name_zh", "tokens", "page", "styles", "code", "html"]
REQUIRED_TOKENS = ["primary", "accent", "ink", "body", "muted", "muted_dark",
                   "surface", "border", "page_bg", "radius", "font_stack"]
REQUIRED_STYLES = ["kicker", "title", "subtitle", "meta", "paragraph", "quote",
                   "card", "aside", "aside_title", "caption", "source", "h3", "list_item", "highlight"]
REQUIRED_CODE = ["bg", "text", "keyword", "comment", "border", "accent", "label"]
REQUIRED_CODE_STYLES = ["frame_style", "header_style", "label_style", "body_style",
                        "line_style", "comment_style", "keyword_style"]
REQUIRED_HTML = ["head", "takeaways_head", "takeaway_item", "closing", "source",
                 "figure", "table", "code"]


def luminance(color):
    rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def check_one(path):
    errors, warnings, info = [], [], {}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"theme": path.parent.name, "passed": False, "errors": ["invalid JSON: " + str(e)], "warnings": []}
    for k in REQUIRED_TOP:
        if k not in d:
            errors.append("missing top-level " + k)
    t = d.get("tokens", {})
    for k in REQUIRED_TOKENS:
        if k not in t:
            errors.append("missing tokens." + k)
    for k in REQUIRED_STYLES:
        if k not in d.get("styles", {}):
            errors.append("missing styles." + k)
    code = d.get("code", {})
    for k in REQUIRED_CODE:
        if k not in code:
            errors.append("missing code." + k)
    for k in REQUIRED_CODE_STYLES:
        if k not in code:
            errors.append("missing code." + k)
    for k in REQUIRED_HTML:
        if k not in d.get("html", {}):
            errors.append("missing html." + k)

    # template placeholders must resolve from tokens or code_* aliases
    known = set(t.keys()) | {"code_" + k for k in code.keys()}
    known |= {"no", "heading", "text", "n", "items", "img", "caption", "lines",
              "lang", "dots", "head", "rows", "source_style", "source_heading_style",
              "caption_style", "code_frame", "code_header", "code_label", "code_body",
              "kicker", "sub_html", "sub_inline"}  # runtime fields supplied by build_article.py fill()
    blob = json.dumps(d.get("styles", {})) + json.dumps(d.get("html", {})) + json.dumps(code)
    placeholders = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", blob))
    unknown = sorted(placeholders - known)
    if unknown:
        errors.append("unresolved template tokens: " + ", ".join(unknown))

    # contrast gates (G16 / G15 basics); label-vs-dark-header is audited by derive_palette.py
    def ratio(fg, bg):
        try:
            return round(contrast(fg, bg), 2)
        except Exception:
            return None
    pairs = [
        ("body/page_bg", t.get("body"), t.get("page_bg"), 7.0),
        ("code.text/code.bg", code.get("text"), code.get("bg"), 12.0),
        ("code.keyword/code.bg", code.get("keyword"), code.get("bg"), 4.5),
        ("code.comment/code.bg", code.get("comment"), code.get("bg"), 4.5),
    ]
    info["contrast"] = {}
    conflicts = []
    for name, fg, bg, gate in pairs:
        if not fg or not bg:
            continue
        r = ratio(fg, bg)
        info["contrast"][name] = {"ratio": r, "gate": gate, "status": "PASS" if r and r >= gate else "FAIL"}
        if not r or r < gate:
            errors.append(f"contrast {name} = {r} < {gate}")
    info["theme_id"] = d.get("id")
    info["name_zh"] = d.get("name_zh")
    return {"theme": path.parent.name, "passed": not errors,
            "errors": errors, "warnings": warnings, "conflicts": conflicts, "info": info}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--themes-dir", default="assets/themes")
    ap.add_argument("--skill-root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    root = Path(args.skill_root) / args.themes_dir
    if not root.exists():
        print(json.dumps({"error": "themes dir not found", "path": str(root)}, ensure_ascii=False))
        return 2
    paths = sorted(root.glob("*/theme.json"))
    if not paths:
        print(json.dumps({"error": "no theme.json found", "path": str(root)}, ensure_ascii=False))
        return 2
    results = [check_one(p) for p in paths]
    report = {
        "valid": all(r["passed"] for r in results),
        "themes_checked": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "results": results,
        "note": "label-vs-header contrast is audited by derive_palette.py --audit-themes",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    if not report["valid"]:
        print("THEME CHECK FAILED:", [r["theme"] for r in results if not r["passed"]], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Derive a complete, contrast-checked palette from one primary colour.

Input: a primary HEX + a style skeleton (which visual language to keep).
Output: semantic tokens (paper / surface / border / ink / body / muted / accent),
the six code-box slots (bg / text / keyword / comment / border / accent),
the label + header colours, and a WCAG contrast report.

`keyword` is drawn on the light code background (inline `**keyword**`), while
`label` is drawn on the code header (which can be dark, e.g. olive's ink strip),
so the two are derived and gated separately.

The skeleton keeps its structure (radius, section-head rhythm, ticket dashes,
serif titles...) and only the hue + semantic colours are re-derived, so a
user-supplied green / blue / ochre / gray still lands on a coherent design
instead of a recoloured copy.

Examples:
  python scripts/derive_palette.py --primary "#A8551F" --skeleton olive --name "赭石手记"
  python scripts/derive_palette.py --primary "#2F6B5F" --skeleton zen --name "松烟青"
  python scripts/derive_palette.py --primary "#4B5563" --skeleton graphite --name "铅灰"
  python scripts/derive_palette.py --primary "#B45309" --skeleton olive --name "赭石手记" \
      --write-theme dist/themes/zheshi-journal/theme.json
"""
import argparse
import colorsys
import json
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
THEMES_DIR = SKILL_ROOT / "assets" / "themes"

SKELETONS = {
    "ink": {
        "name": "墨蓝橘笺",
        "recipe": "沉稳 / 杂志感 / 正式汇报",
        "surface_l": 0.972, "surface_s": 0.10,
        "paper": "white", "code_bg_l": 0.945, "code_bg_s": 0.12,
        "accent": "complement", "accent_l": 0.55, "accent_s": 0.82,
        "code_border_l": 0.80,
    },
    "green": {
        "name": "摸鱼绿",
        "recipe": "清爽 / 活力 / 团队手册",
        "surface_l": 0.975, "surface_s": 0.18,
        "paper": "white", "code_bg_l": 0.90, "code_bg_s": 0.42,
        "accent": "warm_tint", "accent_l": 0.82, "accent_s": 0.75,
        "code_border_l": 0.76,
    },
    "ticket": {
        "name": "摸鱼票据风",
        "recipe": "纸质 / 票据 / 复古印刷",
        "surface_l": 0.985, "surface_s": 0.08,
        "paper": "white", "code_bg_l": 0.965, "code_bg_s": 0.18,
        "accent": "tint", "accent_l": 0.84, "accent_s": 0.45,
        "code_border_l": 0.80,
    },
    "olive": {
        "name": "橄榄手记",
        "recipe": "手账 / 暖调 / 编辑感",
        "surface_l": 0.945, "surface_s": 0.10,
        "paper": "tinted", "code_bg_l": 0.988, "code_bg_s": 0.10,
        "accent": "complement", "accent_l": 0.55, "accent_s": 0.85,
        "code_border_l": 0.78,
    },
    "zen": {
        "name": "留白禅意风",
        "recipe": "留白 / 学术 / 克制",
        "surface_l": 0.968, "surface_s": 0.05,
        "paper": "white", "code_bg_l": 0.93, "code_bg_s": 0.06,
        "accent": "tint", "accent_l": 0.76, "accent_s": 0.22,
        "code_border_l": 0.91,
    },
    "graphite": {
        "name": "石墨极简风",
        "recipe": "冷峻 / 极简 / 技术文档",
        "surface_l": 0.96, "surface_s": 0.02,
        "paper": "white", "code_bg_l": 0.958, "code_bg_s": 0.015,
        "accent": "fixed", "accent_l": 0.55, "accent_s": 0.90,
        "code_border_l": 0.89,
    },
}


def hex_to_rgb(value):
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", v):
        raise SystemExit(f"ERROR invalid hex colour: {value}")
    return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02X}" for c in rgb)


def hx(h, s, l):
    return rgb_to_hex(colorsys.hls_to_rgb(h % 1.0, max(0, min(1, l)), max(0, min(1, s))))


def hls(color):
    return colorsys.rgb_to_hls(*hex_to_rgb(color))


def luminance(color):
    rgb = hex_to_rgb(color)
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def darken_to(color, bg, gate):
    """Lower lightness until the colour reaches the contrast gate on bg."""
    if contrast(color, bg) >= gate:
        return color
    h, l, s = hls(color)
    for _ in range(240):
        l -= 0.005
        candidate = hx(h, s, l)
        if contrast(candidate, bg) >= gate or l <= 0.04:
            return candidate
    return hx(h, s, 0.04)


def lighten_to(color, bg, gate):
    """Raise lightness until the colour reaches the contrast gate on bg."""
    if contrast(color, bg) >= gate:
        return color
    h, l, s = hls(color)
    for _ in range(240):
        l += 0.005
        candidate = hx(h, s, l)
        if contrast(candidate, bg) >= gate or l >= 0.95:
            return candidate
    return hx(h, s, 0.95)


def derive(primary, skeleton):
    sk = SKELETONS[skeleton]
    h, l, s = hls(primary)
    neutral = s < 0.05
    if neutral:
        s = 0.0
    tint = min(1.0, s * 2.2)

    page = hx(h, sk["surface_s"] * 0.35 * tint, 0.987) if sk["paper"] == "tinted" else "#FFFFFF"
    surface = hx(h, sk["surface_s"] * (0.35 + 0.65 * tint), sk["surface_l"])
    surface_alt = hx(h, sk["surface_s"] * (0.25 + 0.55 * tint), min(0.995, sk["surface_l"] + 0.022))
    ink = hx(h, 0.16 if not neutral else 0, 0.13)
    body = hx(h, 0.08 if not neutral else 0, 0.16)
    muted = hx(h, 0.06 if not neutral else 0, 0.62)
    muted_dark = hx(h, 0.07 if not neutral else 0, 0.44)
    border = hx(h, min(0.30, max(0.10, s * 0.35)) if not neutral else 0.02, 0.82)
    border_accent = hx(h, min(0.55, max(0.25, s * 0.8)) if not neutral else 0.03, 0.76)

    primary_out = darken_to(hx(h, max(0.45, s), l), page, 4.5)

    # Accent hue follows the style identity, not the complement:
    # ink / olive / graphite keep a warm orange anchor, green keeps a yellow highlighter,
    # ticket / zen keep a desaturated tint of the user's primary hue.
    if sk["accent"] in ("fixed", "warm_tint"):
        accent = hx(0.075 if sk["accent"] == "fixed" else 0.13, sk["accent_s"], sk["accent_l"])
    else:
        accent = hx(h, sk["accent_s"], sk["accent_l"])
    if sk["accent"] != "warm_tint":
        accent = darken_to(accent, page, 4.5)

    code_bg = hx(h, sk["code_bg_s"] * (0.5 + 0.5 * tint), sk["code_bg_l"])
    code_text = darken_to(hx(h, 0.10 if not neutral else 0, 0.12), code_bg, 12.0)
    if skeleton in ("olive", "ink"):
        key_hue, key_sat = 0.075, 0.80
    else:
        key_hue, key_sat = h, max(0.55, s)
    code_keyword = darken_to(hx(key_hue, key_sat, 0.42), code_bg, 4.5)
    code_comment = darken_to(hx(h, 0.08 if not neutral else 0, 0.40), code_bg, 4.5)
    code_border = hx(h, min(0.22, max(0.06, s * 0.28)) if not neutral else 0.02, sk["code_border_l"])
    code_accent = darken_to(primary_out, code_bg, 3.0)
    # 深色代码头（橄榄手记的墨条）上放语言标签，浅底上放行内关键字 —— 两个槽分开派生：
    # keyword 必须对 code_bg ≥ 4.5（它画在浅底上）；label 必须对 header_bg ≥ 4.5。
    header_bg = "#1E1F23" if skeleton == "olive" else code_bg
    code_label = code_keyword
    if header_bg != code_bg:
        code_label = lighten_to(hx(0.075, 0.80, 0.55), header_bg, 4.5)
        if contrast(code_label, header_bg) < 4.5:
            header_bg = code_bg
            code_label = code_keyword

    tokens = {
        "primary": primary_out,
        "accent": accent,
        "ink": ink,
        "body": body,
        "muted": muted,
        "muted_dark": muted_dark,
        "surface": surface,
        "surface_alt": surface_alt,
        "border": border,
        "border_accent": border_accent,
        "page_bg": page,
    }
    code = {
        "bg": code_bg,
        "text": code_text,
        "keyword": code_keyword,
        "comment": code_comment,
        "border": code_border,
        "accent": code_accent,
        "label": code_label,
        "header_bg": header_bg,
    }
    checks = [
        ("正文 body / 纸底 page_bg", body, page, 7.0),
        ("墨色 ink / 纸底 page_bg", ink, page, 7.0),
        ("主色 primary / 纸底 page_bg", primary_out, page, 4.5),
        ("辅助色 accent / 纸底 page_bg", accent, page, 3.0 if skeleton == "green" else 4.5),
        ("代码字 text / 代码底 bg", code_text, code_bg, 12.0),
        ("关键字 keyword / 代码底 bg", code_keyword, code_bg, 4.5),
        ("注释 comment / 代码底 bg", code_comment, code_bg, 4.5),
        ("语言标签 label / 代码头 header", code_label, header_bg, 4.5),
        ("弱化字 muted_dark / 纸底", muted_dark, page, 4.5),
    ]
    report = [{
        "pair": name,
        "fg": fg,
        "bg": bg,
        "ratio": round(contrast(fg, bg), 2),
        "gate": gate,
        "status": "PASS" if contrast(fg, bg) >= gate else "FAIL",
    } for name, fg, bg, gate in checks]
    return tokens, code, report


SKELETON_THEME_ID = {
    "ink": "ink-tangerine",
    "green": "moyu-green",
    "ticket": "moyu-ticket",
    "olive": "olive-journal",
    "zen": "zen-whitespace",
    "graphite": "graphite-minimal",
}


def write_theme(skeleton, tokens, code, path, name, style_desc, theme_id):
    skeleton_path = THEMES_DIR / SKELETON_THEME_ID[skeleton] / "theme.json"
    data = json.loads(skeleton_path.read_text(encoding="utf-8"))
    data["tokens"].update(tokens)
    for key in code:
        data["code"][key] = code[key]
    if "background:" in data["code"].get("header_style", ""):
        data["code"]["header_style"] = re.sub(
            r"background:#[0-9A-Fa-f]{3,6}", "background:" + code["header_bg"],
            data["code"]["header_style"], count=1)
        if code["header_bg"] != code["bg"] and "border-bottom" not in data["code"]["header_style"]:
            data["code"]["header_style"] += "border-bottom:1px solid " + code["border"] + ";"
    data["id"] = theme_id
    data["name_zh"] = name
    data["style_desc"] = style_desc
    data["derived_from"] = skeleton
    data["recipe"] = SKELETONS[skeleton]["recipe"]
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def resolve_code(text, code):
    """Resolve {code_x} placeholders inside a code style string."""
    def repl(m):
        return str(code.get(m.group(1), m.group(0)))
    return re.sub(r"\{code_([a-z_]+)\}", repl, text)


def audit_themes():
    """Audit code slots AND body/ink contrast against the shipped theme palettes.

    Gate for body & ink is 7:1 (WCAG AAA body text), matching the six built-in themes.
    """
    rows, ok = [], True
    for p in sorted(THEMES_DIR.glob("*/theme.json")):
        theme = json.loads(p.read_text(encoding="utf-8"))
        c = theme["code"]
        header_style = resolve_code(c.get("header_style", ""), c)
        m = re.search(r"background:\s*(#[0-9A-Fa-f]{3,6})", header_style)
        header_bg = m.group(1) if m else c["bg"]
        label = c.get("label", c["keyword"])
        t = theme["tokens"]
        pairs = [
            ("keyword", c["keyword"], c["bg"], 4.5),
            ("comment", c["comment"], c["bg"], 4.5),
            ("label", label, header_bg, 4.5),
            ("text", c["text"], c["bg"], 12.0),
            ("body", t["body"], t["page_bg"], 7.0),
            ("ink", t["ink"], t["page_bg"], 7.0),
        ]
        line = f"{theme['id']:<18}"
        for name, fg, bg, gate in pairs:
            ratio = contrast(fg, bg)
            status = "PASS" if ratio >= gate else "FAIL"
            ok = ok and status == "PASS"
            line += f" {name:<8} {fg} on {bg} {ratio:>5.2f} {status} |"
        rows.append(line)
        rows.append(f"{'':<18} label_style → {label} / header {header_bg}"
                    f"{' (dark header)' if header_bg != c['bg'] else ''}")
    print("THEME AUDIT · 六套内置主题")
    print("\n".join(rows))
    print("\nRESULT   " + ("ALL PASS" if ok else "FAILED — fix the slots above"))
    return ok


def main():
    ap = argparse.ArgumentParser(description="Derive a wechat article palette from a primary colour.")
    ap.add_argument("--primary", help="primary colour, e.g. #A8551F")
    ap.add_argument("--skeleton", choices=sorted(SKELETONS), help="style skeleton to keep")
    ap.add_argument("--name", default="", help="Chinese theme name for --write-theme")
    ap.add_argument("--style", default="", help="one-line style description")
    ap.add_argument("--id", default="", help="theme id for --write-theme (default custom-<skeleton>)")
    ap.add_argument("--write-theme", default="", help="write a ready-to-use theme.json to this path")
    ap.add_argument("--list-skeletons", action="store_true")
    ap.add_argument("--audit-themes", action="store_true", help="print keyword/label contrast for built-in themes")
    ap.add_argument("--json", action="store_true", help="print the palette as JSON only")
    args = ap.parse_args()

    if args.audit_themes:
        return 0 if audit_themes() else 1
    if args.list_skeletons:
        print(json.dumps([
            {"skeleton": k, "default_name": v["name"], "recipe": v["recipe"]}
            for k, v in sorted(SKELETONS.items())
        ], ensure_ascii=False, indent=2))
        return 0
    if not args.primary or not args.skeleton:
        ap.error("--primary and --skeleton are required")

    tokens, code, report = derive(args.primary, args.skeleton)
    payload = {
        "primary_input": args.primary,
        "skeleton": args.skeleton,
        "skeleton_name": SKELETONS[args.skeleton]["name"],
        "tokens": tokens,
        "code": code,
        "contrast": report,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"SKELETON  {args.skeleton}  ({SKELETONS[args.skeleton]['name']} · {SKELETONS[args.skeleton]['recipe']})")
        print(f"PRIMARY   {args.primary} → {tokens['primary']}")
        print("\nPALETTE")
        for k, v in tokens.items():
            print(f"  {k:<14} {v}")
        print("\nCODE BOX · 六槽位（底 / 字 / 关键字 / 注释 / 边框 / 左条）")
        labels = [("底 bg", "bg"), ("代码字 text", "text"), ("关键字 keyword", "keyword"),
                  ("注释 comment", "comment"), ("边框 border", "border"), ("左侧强调 accent", "accent"),
                  ("语言标签 label", "label"), ("代码头 header", "header_bg")]
        for label, key in labels:
            print(f"  {label:<20} {code[key]}")
        print("\nCONTRAST")
        ok = True
        for row in report:
            ok = ok and row["status"] == "PASS"
            print(f"  {row['pair']:<34} {row['ratio']:>5}:1  ≥{row['gate']:<4} {row['status']}")
        print("\nRESULT   " + ("ALL PASS" if ok else "FAILED — darken the failing slots"))

        if args.write_theme:
            theme_id = args.id or ("custom-" + args.skeleton)
            name = args.name or (SKELETONS[args.skeleton]["name"] + "（自定义）")
            desc = args.style or f"由主色 {args.primary} 按「{SKELETONS[args.skeleton]['name']}」骨架派生。"
            out = write_theme(args.skeleton, tokens, code, args.write_theme, name, desc, theme_id)
            print(f"\nTHEME    {out}")
    return 0 if all(r["status"] == "PASS" for r in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())

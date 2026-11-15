#!/usr/bin/env python3
"""Render content.json (IR) into a WeChat-ready fully-inline-style HTML + Markdown.

Theme-driven: every visual decision comes from assets/themes/<id>/theme.json
(semantic tokens + component skeletons). Six built-in themes ship with the skill;
a palette derived by scripts/derive_palette.py can be passed with --theme-path.

All styles are inline, images are embedded as base64 AND copied as standalone PNGs.
No external CSS/JS/fonts, no <style>, no class attributes, no image-generation model.
"""
import argparse
import base64
import html
import json
import re
from pathlib import Path

THEMES_DIR = "assets/themes"


def esc(s):
    # Escape braces too: body text may literally contain {{ }} (e.g. GitHub Actions
    # expressions), and the validator treats any "{{" as an unresolved placeholder.
    return (html.escape(str(s), quote=False)
            .replace("{", "&#123;").replace("}", "&#125;"))


def attr(s):
    return html.escape(str(s), quote=True)


def list_themes(root):
    base = Path(root) / THEMES_DIR
    rows = []
    for p in sorted(base.glob("*/theme.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        rows.append({"id": t["id"], "name_zh": t["name_zh"], "style": t.get("style_desc", "")})
    return rows


def load_theme(root, theme_id, theme_path=None):
    path = Path(theme_path) if theme_path else Path(root) / THEMES_DIR / theme_id / "theme.json"
    if not path.exists():
        raise SystemExit(f"ERROR theme not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class Theme:
    def __init__(self, data):
        self.data = data
        self.id = data["id"]
        self.name = data["name_zh"]
        self.tokens = dict(data["tokens"])
        self.tokens.update(data["page"])
        for key, val in data.get("code", {}).items():
            self.tokens["code_" + key] = val
        # code style templates reference the colour slots; resolve them once here
        # so nested {code_text}/{code_comment} placeholders never reach the output.
        for _ in range(2):
            for key, val in list(self.tokens.items()):
                if isinstance(val, str) and "{" in val:
                    self.tokens[key] = self.fmt(val)
        # short aliases used by the code/figure templates
        for short in ("frame", "header", "label", "body", "line"):
            self.tokens["code_" + short] = self.tokens["code_" + short + "_style"]
        self.styles = data["styles"]
        self.html_parts = data["html"]

    def fmt(self, text):
        """Replace {token} placeholders; leave {{field}} placeholders untouched."""
        def repl(m):
            key = m.group(1)
            return str(self.tokens[key]) if key in self.tokens else m.group(0)
        return re.sub(r"\{([a-z_][a-z0-9_]*)\}", repl, text)

    def style(self, name):
        return self.fmt(self.styles[name])

    def part(self, name):
        return self.fmt(self.html_parts[name])


def fill(template, **fields):
    for key, val in fields.items():
        template = template.replace("{{" + key + "}}", str(val))
    return template


class Renderer:
    def __init__(self, theme, b64_map):
        self.t = theme
        self.b64 = b64_map

    def rich(self, s):
        txt = esc(s)
        hl = self.t.style("highlight")
        return re.sub(r"\*\*(.+?)\*\*",
                      lambda m: '<strong style="' + hl + '">' + m.group(1) + "</strong>", txt)

    def para(self, text, style_name="paragraph"):
        return '<p style="' + self.t.style(style_name) + '">' + self.rich(text).replace("\n", "<br>") + "</p>"

    def quote(self, text):
        return '<blockquote style="' + self.t.style("quote") + '">' + self.rich(text).replace("\n", "<br>") + "</blockquote>"

    def card(self, text):
        return '<div style="' + self.t.style("card") + '">' + self.rich(text).replace("\n", "<br>") + "</div>"

    def tip(self, text):
        return '<div style="' + self.t.style("tip") + '">' + self.rich(text).replace("\n", "<br>") + "</div>"

    def divider(self):
        style = self.t.style("divider")
        if "height:0" in style.replace(" ", ""):
            return '<div style="' + style + '"></div>'
        return '<p style="' + style + '">● ● ●</p>'

    def head(self, sec, index):
        no = str(sec.get("no") or f"{index:02d}")
        heading = esc(sec.get("heading", ""))
        sub = sec.get("sub", "")
        kicker = esc(f"{no} · {sub}") if sub else esc(no)
        sub_html = ('<p style="margin:2px 0 0;font-size:11px;font-weight:600;color:'
                    + self.t.tokens["muted"] + ';letter-spacing:1.5px;">' + esc(sub) + "</p>") if sub else ""
        sub_inline = ('<span style="margin-left:8px;font-size:12px;color:' + self.t.tokens["muted"]
                      + ';">/ ' + esc(sub) + "</span>") if sub else ""
        return fill(self.t.part("head"), no=no, heading=heading, kicker=kicker,
                    sub_html=sub_html, sub_inline=sub_inline)

    def code(self, block):
        lang = esc(block.get("lang", ""))
        lines = block.get("lines", [])
        out = []
        line_style = self.t.tokens["code_line_style"]
        comment_style = self.t.tokens["code_comment_style"]
        keyword_style = self.t.tokens["code_keyword_style"]
        for line in lines:
            raw = line.replace("\t", "    ")
            text = esc(raw) if raw.strip() else "&nbsp;"
            text = re.sub(r"\*\*(.+?)\*\*",
                          lambda m: '<span style="' + keyword_style + '">' + m.group(1) + "</span>",
                          text)
            if line.strip().startswith("#") or line.strip().startswith("//"):
                out.append('<p style="' + comment_style + '">' + text + "</p>")
            else:
                out.append('<p style="' + line_style + '">' + text + "</p>")
        dots = ""
        if self.t.data.get("code", {}).get("dots", False):
            for color in ("#FF5F56", "#FFBD2E", "#27C93F"):
                dots += ('<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
                         'background:' + color + ';margin-right:4px;"></span>')
        body_lines = "".join(out) if out else '<p style="' + line_style + '">&nbsp;</p>'
        if not dots and not lang:
            return ('<div style="' + self.t.tokens["code_frame"] + '"><div style="'
                    + self.t.tokens["code_body"] + '">' + body_lines + "</div></div>")
        return fill(self.t.part("code"), dots=dots, lang=lang, lines=body_lines)

    def table(self, block):
        headers = block.get("headers", [])
        rows = block.get("rows", [])
        th = self.t.style("th")
        td = self.t.style("td")
        td_alt = self.t.style("td_alt")
        head = "".join('<td style="' + th + '">' + self.rich(h) + "</td>" for h in headers)
        body = []
        for i, row in enumerate(rows):
            style = td_alt if i % 2 == 1 else td
            body.append("<tr>" + "".join('<td style="' + style + '">' + self.rich(c) + "</td>" for c in row) + "</tr>")
        return fill(self.t.part("table"), head=head, rows="".join(body))

    def figure(self, fig):
        b64 = self.b64.get(fig["id"])
        if not b64:
            return ""
        cap = fig.get("caption", "")
        img = ('<img src="data:image/png;base64,' + b64 + '" alt="' + attr(cap)
               + '" style="width:100%;height:auto;display:block;border-radius:' + self.t.tokens["radius"] + ';">')
        return fill(self.t.part("figure"), img=img, caption=esc(cap),
                    caption_style=self.t.style("caption"))

    def takeaways(self, ir):
        items = ir["takeaways"]
        heading = esc(ir.get("takeaways_title", "如果只带走三件事"))
        out = [fill(self.t.part("takeaways_head"), heading=heading)]
        for i, text in enumerate(items, 1):
            out.append(fill(self.t.part("takeaway_item"), n=str(i), text=self.rich(text)))
        return out

    def source(self, ir):
        heading = esc("资料来源与整理说明")
        reader = ir.get("reader_notes")
        if reader:
            items = reader
        else:
            items = list(ir.get("sources", [])) + list(ir.get("caveats", []))
        item_html = "<br>".join('<span style="' + self.t.style("source_item") + '">· ' + esc(s) + "</span>"
                                for s in items)
        return fill(self.t.part("source"), heading=heading, items=item_html,
                    source_style=self.t.style("source"),
                    source_heading_style=self.t.style("source_heading"))

    def shell(self, title, content):
        page = self.t.data["page"]
        tokens = self.t.tokens
        style = ("max-width:" + page["max_width"] + ";margin:0 auto;padding:" + page["padding"]
                 + ";background:" + tokens["page_bg"] + ";color:" + tokens["body"]
                 + ";font-family:" + tokens["font_stack"] + ";font-size:" + page["font_size"]
                 + ";line-height:" + page["line_height"] + ";letter-spacing:" + page["letter_spacing"]
                 + ";word-wrap:break-word;")
        return ('<!doctype html><html><head><meta charset="utf-8"><title>' + attr(title) + "</title></head>"
                '<body style="margin:0;padding:0;background:' + tokens["page_bg"] + ';">'
                '<div style="' + style + '">' + content + "</div></body></html>")


def emit_figures(parts, figs, rnd, position):
    for f in figs:
        if f.get("position", "") == position:
            parts.append(rnd.figure(f))


def build_html(ir, theme, b64_map):
    rnd = Renderer(theme, b64_map)
    parts = []
    figs = ir.get("figures", [])
    emit_figures(parts, figs, rnd, "top")

    # G17: the cover image may already carry the headline / kicker / subtitle.
    # In that case the visual replaces that text; do not repeat it in the body.
    compact_head = bool(ir.get("cover_carries_title") or
                        (ir.get("decisions") or {}).get("cover_carries_title"))
    if not compact_head:
        if ir.get("kicker"):
            parts.append('<p style="' + theme.style("kicker") + '"><strong>' + esc(ir["kicker"]) + "</strong></p>")
        parts.append('<h1 style="' + theme.style("title") + '">' + esc(ir["title"]).replace("\n", "<br>") + "</h1>")
        if ir.get("subtitle"):
            parts.append('<p style="' + theme.style("subtitle") + '">' + esc(ir["subtitle"]) + "</p>")
    if ir.get("meta"):
        rows = ["<strong style=\"" + theme.style("meta_label") + "\">" + esc(m["label"]) + "</strong>　"
                + esc(m["value"]) for m in ir["meta"]]
        parts.append('<div style="' + theme.style("meta") + '">' + "<br>".join(rows) + "</div>")
    for item in ir.get("lead", []):
        # lead accepts plain strings or block objects (tip/card/quote) for emphasis
        if isinstance(item, dict):
            kind, text = item.get("type", "p"), item.get("text", "")
            if kind == "tip":
                parts.append(rnd.tip(text))
            elif kind == "card":
                parts.append(rnd.card(text))
            elif kind == "quote":
                parts.append(rnd.quote(text))
            else:
                parts.append(rnd.para(text, "lead"))
        else:
            parts.append(rnd.para(item, "lead"))
    parts.append(rnd.divider())

    for index, sec in enumerate(ir.get("sections", []), 1):
        parts.append(rnd.head(sec, index))
        blocks = sec.get("blocks")
        if blocks:
            for b in blocks:
                kind = b.get("type", "p")
                if kind == "p":
                    parts.append(rnd.para(b.get("text", "")))
                elif kind == "h3":
                    parts.append('<p style="' + theme.style("h3") + '">' + esc(b.get("text", "")) + "</p>")
                elif kind == "list":
                    ordered = b.get("ordered", False)
                    indent = float(b.get("indent", 0) or 0)
                    extra = f"margin-left:{indent:g}em;" if indent > 0 else ""
                    items = b.get("items", [])
                    for i, item in enumerate(items, 1):
                        # 编号单独占一列（宽度 = 主题里的悬挂缩进），不与正文挤在同一行；
                        # 末条补足段后间距，列表才不会和下一段粘成一片。
                        prefix = f"{i:02d}" if ordered else "·"
                        tail = "margin-bottom:22px;" if i == len(items) else ""
                        num = ('<span style="display:inline-block;width:30px;text-indent:0;'
                               'color:' + theme.tokens["accent"] + ';font-size:13px;'
                               'font-weight:700;letter-spacing:.5px;">' + prefix + "</span>")
                        parts.append('<p style="' + theme.style("list_item") + extra + tail + '">'
                                     + num + rnd.rich(item) + "</p>")
                elif kind == "quote":
                    parts.append(rnd.quote(b.get("text", "")))
                elif kind == "card":
                    parts.append(rnd.card(b.get("text", "")))
                elif kind == "tip":
                    parts.append(rnd.tip(b.get("text", "")))
                elif kind == "code":
                    parts.append(rnd.code(b))
                elif kind == "table":
                    parts.append(rnd.table(b))
                elif kind == "figure":
                    for f in figs:
                        if f["id"] == b.get("id"):
                            parts.append(rnd.figure(f))
        else:
            for text in sec.get("paragraphs", []):
                parts.append(rnd.para(text))
            if sec.get("quote"):
                parts.append(rnd.quote(sec["quote"]))
            for text in sec.get("cards", []):
                parts.append(rnd.card(text))
            if sec.get("tip"):
                parts.append(rnd.tip(sec["tip"]))
            for code in sec.get("code", []) if isinstance(sec.get("code"), list) else (
                    [sec["code"]] if sec.get("code") else []):
                parts.append(rnd.code(code))
            if sec.get("table"):
                parts.append(rnd.table(sec["table"]))
        tag = "after_section:" + str(sec.get("no", ""))
        emit_figures(parts, figs, rnd, tag)
        for fid in sec.get("figures", []):
            for f in figs:
                if f["id"] == fid and f.get("position") != tag:
                    parts.append(rnd.figure(f))

    emit_figures(parts, figs, rnd, "before_takeaways")
    for f in figs:
        if f.get("position") in (None, ""):
            parts.append(rnd.figure(f))

    if ir.get("takeaways"):
        parts.extend(rnd.takeaways(ir))
    if ir.get("closing_quote"):
        parts.append(fill(theme.part("closing"), text=rnd.rich(ir["closing_quote"])))
    parts.append(rnd.divider())
    parts.append(rnd.source(ir))
    return rnd.shell(ir["title"], "\n".join(parts))


def build_md(ir, fig_files):
    L = ["# " + ir["title"].replace("\n", " "), "", "> " + ir.get("subtitle", ""), ""]
    if ir.get("meta"):
        for m in ir["meta"]:
            L.append("- **" + m["label"] + "**　" + m["value"])
        L.append("")
    for f in ir.get("figures", []):
        if f.get("position") == "top" and f["id"] in fig_files:
            L += ["![" + f.get("caption", "图示") + "](" + fig_files[f["id"]] + ")", ""]
    lead_lines = [(x.get("text", "") if isinstance(x, dict) else x)
                  for x in ir.get("lead", [])]
    L += lead_lines + [""]
    for sec in ir.get("sections", []):
        L += ["## " + str(sec.get("no", "")) + " " + sec.get("heading", ""), ""]
        if sec.get("blocks"):
            for b in sec["blocks"]:
                kind = b.get("type", "p")
                if kind in ("p", "quote", "card", "tip"):
                    prefix = "> " if kind == "quote" else ("- " if kind == "card" else "")
                    L += [prefix + b.get("text", ""), ""]
                elif kind == "h3":
                    L += ["### " + b.get("text", ""), ""]
                elif kind == "list":
                    ordered = b.get("ordered", False)
                    for i, item in enumerate(b.get("items", []), 1):
                        L.append((f"{i}. " if ordered else "- ") + item)
                    L.append("")
                elif kind == "code":
                    L += ["```" + b.get("lang", "")] + list(b.get("lines", [])) + ["```", ""]
                elif kind == "table":
                    L += ["| " + " | ".join(b.get("headers", [])) + " |"]
                    L += ["| " + " | ".join("---" for _ in b.get("headers", [])) + " |"]
                    for row in b.get("rows", []):
                        L += ["| " + " | ".join(row) + " |"]
                    L.append("")
                elif kind == "figure":
                    fid = b.get("id")
                    for f in ir.get("figures", []):
                        if f["id"] == fid and fid in fig_files:
                            L += ["![" + f.get("caption", "图示") + "](" + fig_files[fid] + ")",
                                  f.get("caption", ""), ""]
        else:
            L += list(sec.get("paragraphs", [])) + [""]
            if sec.get("quote"):
                L += ["> " + sec["quote"].replace("\n", " "), ""]
            for c in sec.get("cards", []):
                L += ["- " + c]
            L.append("")
        for f in ir.get("figures", []):
            if f.get("position") == "after_section:" + str(sec.get("no", "")) and f["id"] in fig_files:
                L += ["![" + f.get("caption", "图示") + "](" + fig_files[f["id"]] + ")",
                      f.get("caption", ""), ""]
    if ir.get("takeaways"):
        L += ["## " + ir.get("takeaways_title", "如果只带走三件事"), ""]
        L += [str(i) + ". " + t for i, t in enumerate(ir["takeaways"], 1)] + [""]
    if ir.get("closing_quote"):
        L += ["> " + ir["closing_quote"], ""]
    L += ["---", "", "## 资料来源与整理说明", ""]
    L += ["- " + s for s in ir.get("sources", [])]
    L += ["- " + s for s in ir.get("caveats", [])]
    dec = ir.get("decisions", {})
    if dec:
        L += ["", "### 口径与决定项", ""]
        L += ["- " + s for s in dec.get("user_decisions_verbatim", [])]
        if dec.get("fact_discrepancy_policy"):
            L += ["- 事实口径：" + dec["fact_discrepancy_policy"]]
        L += ["- 编辑反馈：" + s for s in dec.get("editorial_revisions", [])]
        L.append("")
    appendix = ir.get("process_appendix")
    if appendix:
        L += ["---", ""] + list(appendix)
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", help="content.json (IR)")
    ap.add_argument("--theme", default="ink-tangerine", help="theme id under assets/themes (default: ink-tangerine)")
    ap.add_argument("--theme-path", default="", help="explicit theme.json path (e.g. derived palette)")
    ap.add_argument("--list-themes", action="store_true", help="print available themes and exit")
    ap.add_argument("--figures-dir", default="figures", help="directory with the PNG files")
    ap.add_argument("--out", default="dist", help="output directory")
    ap.add_argument("--skill-root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()

    root = Path(args.skill_root)
    if args.list_themes:
        print(json.dumps(list_themes(root), ensure_ascii=False, indent=2))
        return 0
    if not args.content:
        print("ERROR --content is required")
        return 2

    theme = Theme(load_theme(root, args.theme, args.theme_path or None))
    with open(args.content, encoding="utf-8") as f:
        ir = json.load(f)
    out = Path(args.out).resolve()
    img_dir = out / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    b64_map, fig_files, missing = {}, {}, []
    for f in ir.get("figures", []):
        src = Path(args.figures_dir) / f["file"]
        if not src.exists():
            missing.append(str(src))
            continue
        data = src.read_bytes()
        (img_dir / f["file"]).write_bytes(data)
        b64_map[f["id"]] = base64.b64encode(data).decode("ascii")
        fig_files[f["id"]] = "images/" + f["file"]
    if missing:
        print("ERROR missing figure PNGs:", *missing, sep="\n  ")
        return 2

    html_text = build_html(ir, theme, b64_map)
    (out / "wechat-article.html").write_text(html_text, encoding="utf-8")
    (out / "article.md").write_text(build_md(ir, fig_files), encoding="utf-8")
    print(json.dumps({
        "theme": theme.id,
        "theme_name": theme.name,
        "html": str(out / "wechat-article.html"),
        "md": str(out / "article.md"),
        "html_bytes": len(html_text.encode("utf-8")),
        "figures_embedded": len(b64_map),
        "standalone_pngs": str(img_dir),
        "unresolved_placeholders": html_text.count("{{"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

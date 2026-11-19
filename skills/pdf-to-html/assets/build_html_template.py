# -*- coding: utf-8 -*-
"""Build a self-contained bilingual (EN/ZH) HTML reader from blocks + translations."""
import json, os, re, html

# ============================================================
# PAPER_CONFIG — 每篇论文必须按实际情况改写这一段
# ============================================================
PAPER = "AI_Agents_that_matter"          # 资料目录名（英文，空格用下划线）
CHAPTER = "chapter01_foundations_and_landscape"  # 章节目录名
# 工作目录（含 temp/ 与 courses/）默认取 cwd；可显式指定
WORKDIR = os.getcwd()
BLOCKS = os.path.join(WORKDIR, "temp", "blocks.json")
TRANS = os.path.join(WORKDIR, "temp", "translate_tasks", "translations_merged.json")
OUTDIR = os.path.join(WORKDIR, "courses", CHAPTER, "CourseMaterial", PAPER)
OUTHTML = os.path.join(OUTDIR, PAPER + "_bilingual.html")
IMG_SRC = os.path.join(WORKDIR, "temp", "mineru_out", "images")
IMG_DST = os.path.join(OUTDIR, "images")
# ============================================================

blocks = json.load(open(BLOCKS, encoding="utf-8"))
trans = json.load(open(TRANS, encoding="utf-8"))

# ---- Re-assemble fenced code blocks (Listings) that the block parser split apart ----
# ⚠️ PAPER-SPECIFIC: 以下 _merge_listings 内的段落 id、代码正文、caption 均为示例论文
# （AI Agents That Matter）的特例。换论文时必须按实际 full.md 重写这一段：
#   1. 找到所有 ```lang ... ``` 围栏，记录被拆成的 para id 列表；
#   2. l1_text/l1_caption 等从 full.md 原文提取（不是从被压扁的段落恢复）；
#   3. JSON 类代码用 json.loads/dumps(indent=2) beautify；
#   4. caption_zh 必须翻译成中文（见 pitfalls D1）。
# 若论文没有代码块，直接返回 blocks。
def _merge_listings(blocks):
    by_id = {b["id"]: b for b in blocks}
    # Listing 1: para-112..para-117 (txt prompt + trailing caption)
    l1_ids = ["para-112", "para-113", "para-114", "para-115", "para-116", "para-117"]
    l1_text = [
        "You are a literature professor. I will provide you with snippets from a novel along with a question and corresponding choices pertaining to it. Please thoroughly analyze the content to accurately respond to the question.",
        "",
        "Relevant snippets from the novel:",
        "<context>",
        "",
        "Question:",
        "<question>",
        "",
        "Only respond with the index of the correct answer (e.g., choose between A, B, C, and D). Your output should not contain anything else.",
    ]
    l1_caption = ("Listing 1: Prompt used for RAG implementation on NovelQA. This is the prompt "
                  "from the original NovelQA paper. We only make the slight modification of adding "
                  "in the retrieved context.")
    # Build Chinese translation of the prompt from the (split) translated paragraphs
    fence = chr(96) * 3
    zh112 = trans.get("para-112", "").replace(fence + "txt", "").strip()
    zh117 = trans.get("para-117", "")
    zh_caption1 = ""
    if fence in zh117:
        zh_code_tail, zh_caption1 = zh117.split(fence, 1)
        zh_caption1 = zh_caption1.strip()
    else:
        zh_code_tail = zh117
    l1_text_zh = "\n\n".join([
        zh112, trans.get("para-113", ""), trans.get("para-114", ""),
        trans.get("para-115", ""), trans.get("para-116", ""), zh_code_tail.strip(),
    ])
    # Listing 2: para-128 (json snippet) + caption embedded in it
    l2_raw = by_id.get("para-128", {}).get("text", "")
    l2_caption = ("Listing 2: Example snippet from the original log files provided by the authors "
                  "of the STeP agent. The snippet shows how the rate limit on the Reddit site "
                  "affects evaluation. Given the observation from the web environment, the agent "
                  "correctly concludes that it's currently not possible to make a posting given "
                  "the rate limit imposed on the user. Despite the environment imposing this "
                  "limit, the task is still evaluated as successfully solved. This is an example "
                  "of incorrectly evaluated agents leading to inflated results.")
    # Read the ORIGINAL multi-line JSON from full.md (the block parser flattened it).
    # Then pretty-print with json.loads/dumps so every field is cleanly indented.
    md_path = os.path.join(WORKDIR, "temp", "mineru_out", "full.md")
    md_lines = open(md_path, encoding="utf-8").read().split("\n")
    json_lines, capturing = [], False
    for ln in md_lines:
        if ln.strip() == "```json":
            capturing = True
            continue
        if capturing and ln.strip().startswith("```"):
            break
        if capturing:
            json_lines.append(ln)
    l2_code = "\n".join(json_lines).strip()
    try:
        parsed = json.loads(l2_code)
        l2_code = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        pass  # keep original if parse fails
    l2_caption_zh = ("清单 2：STeP 智能体作者提供的原始日志片段示例。该片段展示了 Reddit 网站的风控限流"
                     "如何影响评估。给定来自网页环境的观察，智能体正确地推断出：由于该用户受到网站施加的"
                     "限流限制，当前无法发帖。尽管环境施加了这一限制，该任务仍被判定为成功完成。"
                     "这是一个因智能体被错误评估而导致结果虚高的例子。")

    new_blocks = []
    for b in blocks:
        if b["id"] == l1_ids[0]:
            new_blocks.append({"id": "code-listing-1", "type": "code", "language": "txt",
                               "text": "\n".join(l1_text), "text_zh": l1_text_zh,
                               "caption": l1_caption, "caption_zh": zh_caption1})
            continue
        if b["id"] in l1_ids[1:]:
            continue  # merged, skip
        if b["id"] == "para-128":
            new_blocks.append({"id": "code-listing-2", "type": "code", "language": "json",
                               "text": l2_code, "caption": l2_caption,
                               "caption_zh": l2_caption_zh})
            continue
        new_blocks.append(b)
    return new_blocks

blocks = _merge_listings(blocks)

def _merge_split_numbered_lists(blocks):
    """Merge numbered lists that the parser split on blank lines / continuation paragraphs.

    Paper pattern: '1. ... \\n\\n 2. ...' and sometimes an explanatory para between
    items ('2. ... \\n\\n For example, ... \\n\\n 3. ...'). parse_blocks emits each
    numbered item as its own list block and the explanation as a para, so each <ol>
    restarts at 1. Merge them into ONE list block; continuation paras become extra
    lines inside the preceding <li> (render_list treats non-numbered lines as
    continuations). Translations are concatenated to keep ids aligned.
    """
    num = re.compile(r"^\d+\.\s")
    out, i = [], 0
    while i < len(blocks):
        b = blocks[i]
        if b["type"] == "list" and num.match(b["text"].strip()):
            group = [(b, "item")]
            j = i + 1
            while j < len(blocks):
                nxt = blocks[j]
                if nxt["type"] == "list" and num.match(nxt["text"].strip()):
                    group.append((nxt, "item"))
                    j += 1
                elif (nxt["type"] == "para" and group and
                      j + 1 < len(blocks) and
                      blocks[j + 1]["type"] == "list" and
                      num.match(blocks[j + 1]["text"].strip())):
                    # continuation para sandwiched between numbered items
                    group.append((nxt, "cont"))
                    j += 1
                else:
                    break
            if len(group) > 1:
                def join_text(key):
                    parts = []
                    for blk, kind in group:
                        txt = (trans.get(blk["id"], "") if key == "zh" else blk["text"]).strip()
                        if not txt:
                            continue
                        if kind == "cont":
                            # append to the previous item as a continuation line
                            if parts:
                                parts[-1] += "\n" + txt
                        else:
                            parts.append(txt)
                    return "\n".join(parts)
                new_id = b["id"] + "-merged"
                trans[new_id] = join_text("zh")
                out.append({"id": new_id, "type": "list", "text": join_text("en")})
                i = j
                continue
        out.append(b)
        i += 1
    return out

blocks = _merge_split_numbered_lists(blocks)

# ---- Hand-reconstructed tables where MinerU flattened multi-row cells ----
# ⚠️ PAPER-SPECIFIC: TABLE_A1_ROWS / build_table_a1 是示例论文被压扁的表格重建案例。
# 换论文时：用 scripts/inspect_pdf.py 渲染原 PDF 页图并提取 cells/rowspan，
# 找出被压扁的表手工重建，逐值比对原文（见 pitfalls B1）。
# 没有压扁表格就删除本段并清空 TABLE_OVERRIDES。
TABLE_A1_ROWS = [
    # (paper, rowspan, agent, accuracy, cost)
    ("Zhou et al. [65]", 2, "LATS (GPT-4)", "88.0 (82.3-91.5)", "134.50 (123.98-147.13)"),
    (None, 0, "LATS (GPT-3.5)", "80.4 (78.7-83.5)", "9.49 (8.94-9.89)"),
    ("Zhong et al. [64]", 7, "LDB (GPT-4, GPT-3.5)", "91.0 (89.0-92.1)", "2.19 (2.14-2.25)"),
    (None, 0, "LDB (Reflexion, GPT-4)*", "92.9 (91.5-95.1)", "7.26 (6.19-9.63)"),
    (None, 0, "LDB (Reflexion, GPT-3.5)", "88.9 (86.6-0.91.5)", "4.19 (3.98-4.37)"),
    (None, 0, "LDB (GPT-4)*", "93.3 (92.1-94.5)", "6.36 (5.11-7.08)"),
    (None, 0, "LDB (GPT-3.5)", "80.2 (78.7-82.9)", "0.63 (0.56-0.77)"),
    (None, 0, "GPT-4 (baseline)", "89.6 (87.8-90.9)", "1.93 (1.91-1.95)"),
    (None, 0, "GPT-3.5 (baseline)", "73.9 (72.0-76.2)", "0.05 (0.05-0.05)"),
    ("Shinn et al. [44]", 1, "Reflexion (GPT-4)", "87.8 (86.0-90.9)", "3.90 (3.76-4.13)"),
    ("Our baselines", 3, "Warming (GPT-4)", "93.2 (92.1-93.9)", "2.45 (2.36-2.54)"),
    (None, 0, "Retry (GPT-4)", "92.0 (91.4-92.7)", "2.51 (2.46-2.56)"),
    (None, 0, "Escalation", "85.0 (84.1-85.4)", "0.27 (0.25-0.28)"),
]


def highlight_json(raw):
    """Token-wise JSON syntax highlighting (safe: escapes text first)."""
    s = html.escape(raw, quote=False)
    token = re.compile(
        r'("(?:[^"\\]|\\.)*")(\s*:)?'          # string, maybe a key
        r'|(-?\d+\.?\d*)'                       # number
        r'|\b(true|false|null)\b'               # literal
    )
    out, last = [], 0
    for m in token.finditer(s):
        out.append(s[last:m.start()])
        if m.group(1) is not None:
            if m.group(2):
                out.append('<span class="j-key">%s</span>%s' % (m.group(1), m.group(2)))
            else:
                out.append('<span class="j-str">%s</span>' % m.group(1))
        elif m.group(3) is not None:
            out.append('<span class="j-num">%s</span>' % m.group(3))
        else:
            out.append('<span class="j-bool">%s</span>' % m.group(4))
        last = m.end()
    out.append(s[last:])
    return "".join(out)


def build_table_a1():
    out = ['<table class="reconstructed" id="table-A1"><thead><tr>',
           '<th>Paper</th><th>Agent</th><th>Accuracy</th><th>Total Cost (USD)</th>',
           '</tr></thead><tbody>']
    for paper, span, agent, acc, cost in TABLE_A1_ROWS:
        out.append('<tr>')
        if paper:
            rs = ' rowspan="%d"' % span if span > 1 else ''
            out.append('<td class="paper"%s>%s</td>' % (rs, html.escape(paper)))
        out.append('<td>%s</td><td class="num">%s</td><td class="num">%s</td>' %
                   (html.escape(agent), html.escape(acc), html.escape(cost)))
        out.append('</tr>')
    out.append('</tbody></table>')
    return "".join(out)

TABLE_OVERRIDES = {
    "table-002": build_table_a1(),  # Table A1
}

os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(IMG_DST, exist_ok=True)

# copy images; rotate the one figure that is stored sideways in the PDF
import shutil
from PIL import Image
# ⚠️ PAPER-SPECIFIC: 需要顺时针转 90° 的图片文件名（见 pitfalls B5）。没有就留空集合。
# 判定方法：h > w×1.3 的图 → 肉眼确认文字是否竖排 → 是则加入。
ROTATE_CW_90 = set()
copied = 0
for f in os.listdir(IMG_SRC):
    src = os.path.join(IMG_SRC, f)
    dst = os.path.join(IMG_DST, f)
    if f in ROTATE_CW_90:
        Image.open(src).transpose(Image.Transpose.ROTATE_270).save(dst, quality=92)
    else:
        shutil.copy2(src, dst)
    copied += 1


def normalize_escapes(text):
    """Normalize MinerU LaTeX-style escapes (call on ANY raw text before display)."""
    math_glyphs = {r"\tau": "τ", r"\alpha": "α", r"\beta": "β",
                   r"\gamma": "γ", r"\approx": "≈", r"\times": "×"}
    for cmd, glyph in math_glyphs.items():
        text = text.replace(r"\$" + cmd + r"\$", glyph)
    latex_map = {
        r"\$": "$", r"\tau": "τ", r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
        r"\approx": "≈", r"\times": "×", r"\pm": "±", r"\to": "→",
        r"\%": "%", r"\&": "&", r"\_": "_",
    }
    for k, v in latex_map.items():
        text = text.replace(k, v)
    return text


def inline_md(text):
    """Convert inline markdown (bold/italic/code/links/sup/sub) to HTML, keep safe."""
    text = normalize_escapes(text)
    t = html.escape(text, quote=False)
    # restore safe inline tags that MinerU emits (escaped by html.escape above)
    for tag in ("sup", "sub"):
        t = t.replace("&lt;%s&gt;" % tag, "<%s>" % tag).replace("&lt;/%s&gt;" % tag, "</%s>" % tag)
    # links [label](url)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    # bold **x**
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    # italic *x*
    t = re.sub(r"(?<!\*)\*([^\*]+?)\*(?!\*)", r"<em>\1</em>", t)
    # citation markers [1] / [44, 65, 64] -> clickable anchor with hover preview
    # NOTE: do NOT sort the numbers — source citation order carries author intent.
    def cite_repl(m):
        nums = [x.strip() for x in m.group(1).split(",") if x.strip().isdigit()]
        if not nums:
            return m.group(0)
        links = "".join('<a class="cite" href="#ref-%s" data-ref="ref-%s">[%s]</a>' %
                        (n, n, n) for n in nums)
        return links
    # avoid matching markdown links already converted: only bare [digits]
    t = re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", cite_repl, t)
    return t


def render_list(text):
    """text lines are list items; non-numbered lines continue the previous item."""
    lines = [l for l in text.split("\n") if l.strip()]
    ordered = bool(re.match(r"^\d+\.", lines[0].strip())) if lines else False
    items, current = [], None
    for l in lines:
        st = l.strip()
        is_new = bool(re.match(r"^(?:\d+\.|•|\*|-)\s+", st))
        if is_new:
            if current is not None:
                items.append(current)
            current = re.sub(r"^(?:\d+\.|•|\*|-)\s*", "", st)
        else:
            # continuation of the previous item
            if current is not None:
                current += " " + st
            else:
                current = st
    if current is not None:
        items.append(current)
    tag = "ol" if ordered else "ul"
    return "<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline_md(x) for x in items), tag)
def block_pair(b):
    """Return (en_html, zh_html, kind) for a block."""
    typ = b["type"]
    if typ == "heading":
        lvl = b["level"]
        en = inline_md(b["text"])
        zh = inline_md(trans.get(b["id"], ""))
        anchor = "sec-" + b["id"]
        toc_items.append({"id": b["id"], "anchor": anchor, "level": lvl,
                          "title": b["text"], "title_zh": trans.get(b["id"], "")})
        return ('<h{l} id="{a}">{x}</h{l}>'.format(l=lvl, a=anchor, x=en),
                '<h{l}>{x}</h{l}>'.format(l=lvl, x=zh), "heading")

    if typ == "code":
        code_en = html.escape(b["text"])
        code_zh = html.escape(b.get("text_zh", b["text"]))
        if b.get("language") == "json":
            code_en = highlight_json(b["text"])
        cap_en = b.get("caption", "")
        cap_zh = b.get("caption_zh", "")
        en = ('<div class="listing"><pre><code>%s</code></pre>'
              '<div class="listing-cap">%s</div></div>' % (code_en, inline_md(cap_en)))
        zh = ('<div class="listing"><pre><code>%s</code></pre>'
              '<div class="listing-cap">%s</div></div>' % (code_zh, inline_md(cap_zh)))
        return en, zh, "code-full"

    if typ == "meta":
        return ("<p class='meta'>%s</p>" % inline_md(b["text"]),
                "<p class='meta'>%s</p>" % inline_md(b["text"]), "meta")

    if typ == "para":
        en = inline_md(b["text"])
        zh = inline_md(trans.get(b["id"], ""))
        # caption-like paragraph -> styled as figure caption
        cls = "caption" if re.match(r"^(Figure|Table|图|表)\s*[A-Z]?\d*\s*[:：]", b["text"]) else ""
        return ("<p class='%s'>%s</p>" % (cls, en),
                "<p class='%s'>%s</p>" % (cls, zh), "para")

    if typ == "list":
        return (render_list(b["text"]),
                render_list(trans.get(b["id"], "")), "list")

    if typ == "figure":
        img = "images/" + b["image"]
        cap_en = b.get("caption", "")
        cap_zh = trans.get(b["id"], "")
        en = '<figure><img src="%s" loading="lazy"><figcaption>%s</figcaption></figure>' % (
            img, inline_md(cap_en))
        zh = '<figure><img src="%s" loading="lazy"><figcaption>%s</figcaption></figure>' % (
            img, inline_md(cap_zh))
        return en, zh, "figure-full"

    if typ == "table":
        raw = TABLE_OVERRIDES.get(b["id"], b["html"])
        return ('<div class="table-wrap">%s</div>' % raw,
                '<div class="table-wrap table-zh-note">（表格内容保留英文原文，见左栏）</div>',
                "table-full")

    if typ == "ref":
        # references: show once in both columns (not translated); add anchor for citation links
        m = re.match(r"^\[(\d+)\]", b["text"])
        rid = ("ref-" + m.group(1)) if m else b["id"]
        return ("<p class='ref' id='%s'>%s</p>" % (rid, inline_md(b["text"])),
                "<p class='ref'>%s</p>" % inline_md(b["text"]), "ref")

    if typ == "checklist":
        txt = "<br>".join(inline_md(x) for x in b["text"].split("\n"))
        return ("<div class='checklist'>%s</div>" % txt,
                "<div class='checklist'>%s</div>" % txt, "checklist-full")

    return ("", "", "para")


# build rows
toc_items = []
rows = []
for b in blocks:
    en, zh, kind = block_pair(b)
    cls = "row kind-%s" % kind
    rows.append(
        '<div class="%s" data-kind="%s">'
        '<div class="cell en"><span class="tag">EN</span><div class="body">%s</div></div>'
        '<div class="cell zh"><span class="tag">中</span><div class="body">%s</div></div>'
        '</div>' % (cls, kind, en, zh)
    )

rows_html = "\n".join(rows)

# ---- build citation lookup (id -> reference text) for hover preview ----
ref_lookup = {}
for b in blocks:
    if b["type"] == "ref":
        m = re.match(r"^\[(\d+)\]", b["text"])
        if m:
            ref_lookup["ref-" + m.group(1)] = normalize_escapes(b["text"])
ref_json = json.dumps(ref_lookup, ensure_ascii=False)

# ---- build TOC (two levels, inferred from heading numbering) ----
def infer_toc_level(title):
    """1 for top-level sections, 2 for subsections like '1.1' / 'A.1'."""
    t = title.strip()
    if re.match(r"^\d+\.\d+\s", t):
        return 2
    if re.match(r"^[A-Z]\.\d+\s", t):
        return 2
    if re.match(r"^\d+\s", t):
        return 1
    if re.match(r"^[A-Z]\s", t):
        return 1
    return 1  # unnumbered sections (Abstract, References, Appendix, ...)

toc_links = []          # flat list for scroll-spy
toc_groups = []         # nested HTML: top-level with expandable children
current_group = None
for it in toc_items:
    lvl = infer_toc_level(it["title"])
    zh = it["title_zh"] or it["title"]
    title = it["title"]
    link = ('<a class="toc-l%d" href="#%s" data-anchor="%s" title="%s">'
            '<span class="toc-zh">%s</span>'
            '<span class="toc-en">%s</span></a>' % (
                lvl, it["anchor"], it["anchor"],
                html.escape(title, quote=True),
                html.escape(zh), html.escape(title)))
    toc_links.append({"html": link, "lvl": lvl, "anchor": it["anchor"], "title": title})

    if lvl == 1:
        gid = "tocgrp-" + it["id"]
        current_group = {"id": gid, "head": link, "children": []}
        toc_groups.append(current_group)
    else:
        if current_group is None:
            # a subsection before any section: treat as top-level
            current_group = {"id": "tocgrp-" + it["id"], "head": link, "children": []}
            toc_groups.append(current_group)
        else:
            current_group["children"].append(link)

# Build nested HTML with expand/collapse buttons on groups that have children
toc_parts = []
for g in toc_groups:
    if g["children"]:
        toc_parts.append(
            '<div class="toc-group" data-group="%s">'
            '<div class="toc-group-head">'
            '<button class="toc-expander" type="button" aria-label="展开/收起">▾</button>'
            '%s</div>'
            '<div class="toc-children">%s</div>'
            '</div>' % (g["id"], g["head"], "\n".join(g["children"]))
        )
    else:
        toc_parts.append(
            '<div class="toc-group no-children">'
            '<div class="toc-group-head"><span class="toc-expander-spacer"></span>%s</div>'
            '</div>' % g["head"]
        )
toc_html = "\n".join(toc_parts)
toc_count = sum(1 for it in toc_items if infer_toc_level(it["title"]) <= 2)

HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Agents That Matter — 双语对照</title>
<style>
  :root{
    --bg:#f7f8fa; --panel:#ffffff; --ink:#1a1d21; --muted:#6b7280;
    --line:#e5e7eb; --accent:#2563eb; --en-bg:#fbfcfe; --zh-bg:#f8fbf7;
    --shadow:0 1px 3px rgba(0,0,0,.06),0 8px 24px rgba(0,0,0,.04);
  }
  *{box-sizing:border-box}
  /* Anchor jumps must clear the sticky top bar (offset set by JS from real header height) */
  html{scroll-padding-top:var(--anchor-offset,120px)}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:var(--font-stack,-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",Roboto,Helvetica,Arial,sans-serif);
    line-height:1.75;font-size:15px}
  header{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);
    backdrop-filter:saturate(180%) blur(10px);border-bottom:1px solid var(--line);
    padding:14px 22px;display:flex;flex-wrap:wrap;align-items:center;gap:16px}
  header h1{font-size:16px;margin:0;font-weight:650;letter-spacing:.2px}
  header .sub{color:var(--muted);font-size:12.5px}
  .spacer{flex:1}
  .toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .seg{display:inline-flex;background:#eef0f4;border-radius:10px;padding:3px;gap:2px}
  .seg button{border:0;background:transparent;color:#4b5563;padding:6px 13px;border-radius:8px;
    cursor:pointer;font-size:13px;font-weight:550;transition:.15s}
  .seg button.active{background:#fff;color:var(--accent);box-shadow:var(--shadow)}
  .btn{border:1px solid var(--line);background:#fff;border-radius:9px;padding:6px 12px;
    cursor:pointer;font-size:13px;color:#374151}
  .btn:hover{border-color:var(--accent);color:var(--accent)}
  /* ---- font settings popover ---- */
  #fontPanel{position:fixed;top:60px;right:22px;z-index:120;width:250px;
    background:#fff;border:1px solid var(--line);border-radius:12px;
    box-shadow:0 10px 34px rgba(0,0,0,.14);padding:14px 16px;display:none}
  #fontPanel.show{display:block}
  #fontPanel h3{margin:0 0 12px;font-size:12.5px;color:#6b7280;font-weight:600;letter-spacing:.3px}
  .fp-row{display:flex;align-items:center;gap:10px;margin-bottom:13px}
  .fp-row label{font-size:12px;color:#374151;flex:0 0 34px}
  .fp-row input[type=range]{flex:1;accent-color:var(--accent)}
  .fp-val{font-size:12px;color:var(--accent);font-weight:600;flex:0 0 38px;text-align:right}
  .fp-presets{display:flex;gap:6px;margin-bottom:14px}
  .fp-presets button{flex:1;border:1px solid var(--line);background:#fff;border-radius:7px;
    padding:5px 0;font-size:11.5px;color:#374151;cursor:pointer}
  .fp-presets button:hover{border-color:var(--accent);color:var(--accent)}
  .fp-fonts{display:flex;flex-direction:column;gap:5px}
  .fp-fonts button{text-align:left;border:1px solid var(--line);background:#fff;border-radius:8px;
    padding:7px 10px;cursor:pointer;font-size:12.5px;color:#374151}
  .fp-fonts button:hover{border-color:var(--accent)}
  .fp-fonts button.active{background:#eef3ff;border-color:var(--accent);color:var(--accent)}
  .fp-fonts button .ff-sub{display:block;font-size:10.5px;color:#9aa1ac;margin-top:1px}
  .fp-close{position:absolute;top:8px;right:10px;border:0;background:transparent;
    font-size:16px;color:#9aa1ac;cursor:pointer}
  .fp-close:hover{color:#374151}
  /* ---- Sidebar TOC ---- */
  #sidebar{position:fixed;top:0;left:0;bottom:0;width:300px;z-index:60;
    background:#fff;border-right:1px solid var(--line);box-shadow:2px 0 12px rgba(0,0,0,.05);
    display:flex;flex-direction:column;transition:transform .25s ease}
  body.toc-collapsed #sidebar{transform:translateX(-100%)}
  .sb-head{padding:16px 18px 12px;border-bottom:1px solid var(--line);
    display:flex;align-items:center;gap:10px}
  .sb-head h2{font-size:13px;margin:0;font-weight:650;color:#374151;letter-spacing:.3px}
  .sb-head .count{font-size:11px;color:var(--muted);font-weight:400}
  .sb-collapse{margin-left:auto;border:1px solid var(--line);background:#fff;border-radius:7px;
    width:28px;height:28px;cursor:pointer;color:#6b7280;font-size:14px;line-height:1}
  .sb-collapse:hover{color:var(--accent);border-color:var(--accent)}
  .sb-filter{padding:10px 14px;border-bottom:1px solid var(--line)}
  .sb-filter input{width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:8px;
    font-size:12.5px;outline:none;box-sizing:border-box}
  .sb-filter input:focus{border-color:var(--accent)}
  .sb-list{flex:1;overflow-y:auto;padding:8px 0 40px}
  .sb-list a{display:block;text-decoration:none;transition:background .12s;line-height:1.35}
  .sb-list a:hover{background:#f3f6ff}
  .sb-list .toc-zh{display:block;font-size:12.5px;color:#1f2937}
  .sb-list .toc-en{display:block;font-size:10.5px;color:#9aa1ac;margin-top:1px}
  /* top-level group */
  .toc-group{margin:2px 0}
  .toc-group-head{display:flex;align-items:flex-start;padding-right:12px;
    border-left:3px solid transparent}
  .toc-group-head:hover{background:#f7f9ff}
  .toc-group-head .toc-l1{flex:1;padding:6px 0 6px 2px}
  .sb-list .toc-l1 .toc-zh{color:#111827;font-weight:700;font-size:13px}
  .sb-list .toc-l1 .toc-en{color:#6b7280}
  /* expander */
  .toc-expander{flex:0 0 20px;width:20px;height:20px;margin:5px 2px 0 8px;
    border:0;background:transparent;color:#6b7280;cursor:pointer;font-size:11px;
    border-radius:5px;transition:transform .15s}
  .toc-expander:hover{background:#e8edf7;color:var(--accent)}
  .toc-group.collapsed .toc-expander{transform:rotate(-90deg)}
  .toc-expander-spacer{flex:0 0 30px}
  /* children */
  .toc-children{overflow:hidden;transition:max-height .2s ease}
  .toc-group.collapsed .toc-children{max-height:0 !important}
  .toc-group-head .toc-l1.active{background:transparent}
  .toc-group-head:has(a.active){background:#eef3ff;border-left-color:var(--accent)}
  .sb-list .toc-l2{padding:4px 8px 4px 40px;font-size:11.5px}
  .sb-list .toc-l2 .toc-zh{font-size:11.5px;color:#4b5563;font-weight:400}
  .sb-list .toc-l2 .toc-en{font-size:10px;color:#aab2bf}
  .sb-list .toc-l2:before{content:"› ";color:#b6bfcc}
  .sb-list .toc-l2.active{background:#eef3ff}
  .sb-list .toc-l2.active .toc-zh{color:var(--accent)}
  .sb-list a[hidden]{display:none}
  /* tab to reopen when collapsed */
  #tocTab{position:fixed;top:70px;left:0;z-index:59;background:#fff;border:1px solid var(--line);
    border-left:0;border-radius:0 9px 9px 0;padding:8px 10px;cursor:pointer;font-size:12px;
    color:#374151;box-shadow:2px 2px 8px rgba(0,0,0,.06);display:none;writing-mode:vertical-rl}
  body.toc-collapsed #tocTab{display:block}
  /* content shifts right when sidebar open */
  body:not(.toc-collapsed) main,
  body:not(.toc-collapsed) header{margin-left:300px}
  main{max-width:1500px;margin:0 auto;padding:26px 22px 80px;transition:margin-left .25s ease}
  header{transition:margin-left .25s ease}
  .doc{background:var(--panel);border:1px solid var(--line);border-radius:14px;
    box-shadow:var(--shadow);overflow:hidden}
  .row{display:grid;border-bottom:1px solid var(--line)}
  .row:last-child{border-bottom:0}
  .cell{padding:14px 20px;min-width:0}
  .cell.en{background:var(--en-bg)}
  .cell.zh{background:var(--zh-bg)}
  .tag{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.6px;
    color:#9aa1ac;border:1px solid var(--line);border-radius:5px;padding:0 5px;
    line-height:16px;margin-bottom:8px;user-select:none}
  .zh .tag{color:#8a9a86}
  .body>*:first-child{margin-top:0}
  .body>*:last-child{margin-bottom:0}
  .body p{margin:0 0 .7em}
  h1,h2,h3,h4{line-height:1.35;margin:6px 0}
  .kind-heading .cell{padding-top:20px;padding-bottom:12px}
  .kind-heading h1{font-size:23px}
  .kind-heading h2{font-size:19px;color:#111827;border-left:3px solid var(--accent);padding-left:10px}
  .kind-heading h3{font-size:16px;color:#374151}
  .meta{color:var(--muted);font-size:13.5px;text-align:center}
  .caption{font-size:12.5px;color:var(--muted);line-height:1.6}
  .ref{font-size:12px;color:#4b5563;margin:0 0 6px}
  .checklist{font-size:12.5px;color:#4b5563}
  figure{margin:6px 0 10px;text-align:center}
  figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px}
  figcaption{font-size:12.5px;color:var(--muted);margin-top:8px;text-align:left;line-height:1.6}
  .table-wrap{overflow:auto}
  .table-wrap table{border-collapse:collapse;width:100%;font-size:12.5px;margin:6px 0}
  .table-wrap td,.table-wrap th{border:1px solid var(--line);padding:6px 9px;vertical-align:top;text-align:left}
  .table-wrap tr:nth-child(even){background:#fafbfc}
  .table-zh-note{color:var(--muted);font-size:12.5px;padding:10px 20px}
  ol,ul{margin:0;padding-left:22px}
  li{margin:0 0 .45em}
  a{color:var(--accent);text-decoration:none}
  a:hover{text-decoration:underline}
  sup{font-size:.72em;color:var(--accent)}
  /* ---- citations ---- */
  a.cite{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--accent);
    padding:0 1px;font-size:.9em;cursor:pointer}
  a.cite:hover{background:#e8f0fe;border-bottom-style:solid}
  #citePopup{position:fixed;z-index:200;max-width:420px;background:#fff;
    border:1px solid var(--line);border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.14);
    padding:11px 14px;font-size:12px;line-height:1.55;color:#374151;
    display:none;pointer-events:auto}
  #citePopup .cp-num{display:inline-block;background:var(--accent);color:#fff;
    border-radius:5px;padding:0 6px;font-size:11px;font-weight:700;margin-right:6px}
  #citePopup .cp-jump{display:block;margin-top:7px;color:var(--accent);
    font-size:11.5px;text-decoration:underline;cursor:pointer}
  /* ---- listing / code block ---- */
  .kind-code-full .cell{grid-column:1/-1}
  body.mode-side .kind-code-full .cell.zh{display:none}
  .listing{margin:4px 0}
  .listing pre{margin:0;background:#f6f8fa;border:1px solid #c9d1d9;border-radius:4px;
    padding:14px 16px;overflow:auto;font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;
    font-size:12px;line-height:1.5;color:#24292f;white-space:pre-wrap;word-break:break-word}
  .listing-cap{font-size:12px;color:var(--muted);margin-top:7px;line-height:1.55}
  .j-key{color:#0550ae}
  .j-str{color:#0a7d34}
  .j-num{color:#b35900}
  .j-bool{color:#8250df}
  /* ---- zoomable images ---- */
  figure img{cursor:zoom-in;transition:opacity .15s}
  figure img:hover{opacity:.92}
  #imgLightbox{position:fixed;inset:0;z-index:300;background:rgba(15,18,24,.9);
    display:none;align-items:center;justify-content:center;overflow:hidden;cursor:zoom-out}
  #imgLightbox.show{display:flex}
  #imgLightbox img{max-width:none;position:absolute;transform-origin:center center;
    box-shadow:0 10px 60px rgba(0,0,0,.5);border-radius:4px}
  #imgLightbox .lb-hint{position:absolute;top:18px;left:0;right:0;text-align:center;
    color:#d1d5db;font-size:12.5px;pointer-events:none}
  #imgLightbox .lb-ctrl{position:absolute;bottom:20px;left:0;right:0;
    display:flex;justify-content:center;gap:10px}
  #imgLightbox .lb-ctrl button{background:rgba(255,255,255,.12);color:#fff;
    border:1px solid rgba(255,255,255,.3);border-radius:8px;padding:7px 14px;
    cursor:pointer;font-size:13px}
  #imgLightbox .lb-ctrl button:hover{background:rgba(255,255,255,.22)}

  /* ---- MODE: side by side (default) ---- */
  body.mode-side .row{grid-template-columns:1fr 1fr}
  body.mode-side .cell.en{border-right:1px solid var(--line)}
  /* full-width blocks span both columns */
  body.mode-side .row.kind-figure-full,
  body.mode-side .row.kind-table-full,
  body.mode-side .row.kind-checklist-full{grid-template-columns:1fr 1fr}
  body.mode-side .kind-figure-full .cell.en,
  body.mode-side .kind-table-full .cell.en,
  body.mode-side .kind-checklist-full .cell.en{grid-column:1/-1;border-right:0}
  body.mode-side .kind-figure-full .cell.zh,
  body.mode-side .kind-table-full .cell.zh,
  body.mode-side .kind-checklist-full .cell.zh{grid-column:1/-1}
  body.mode-side .kind-figure-full .zh figure img,
  body.mode-side .kind-table-full .zh .table-wrap{display:none}
  body.mode-side .kind-figure-full .zh .tag,
  body.mode-side .kind-table-full .zh .tag{display:none}
  body.mode-side .kind-figure-full .zh,
  body.mode-side .kind-table-full .zh,
  body.mode-side .kind-checklist-full .zh{padding-top:2px}

  /* ---- MODE: stacked (EN above, ZH below) ---- */
  body.mode-stack .row{grid-template-columns:1fr}
  body.mode-stack .cell.en{border-bottom:1px dashed var(--line)}
  body.mode-stack .kind-figure-full .cell.zh .tag{display:inline-block}
  body.mode-stack .kind-figure-full .cell.zh figure img{display:none}
  body.mode-stack .kind-figure-full .cell.zh figcaption{display:block}
  body.mode-stack .kind-table-full .cell.zh{display:none}

  /* ---- MODE: English only / Chinese only ---- */
  body.mode-en .cell.zh{display:none}
  body.mode-en .row{grid-template-columns:1fr}
  body.mode-zh .cell.en{display:none}
  body.mode-zh .row{grid-template-columns:1fr}
  body.mode-zh .kind-figure-full .cell.zh figure img,
  body.mode-zh .kind-table-full .cell.zh .table-wrap{display:block}
  body.mode-zh .kind-figure-full .cell.zh figcaption{display:block}

  @media(max-width:1000px){
    body:not(.toc-collapsed) main,body:not(.toc-collapsed) header{margin-left:0}
    #sidebar{transform:translateX(-100%)}
    body:not(.toc-collapsed) #sidebar{transform:translateX(0)}
    #tocTab{display:block}
  }
  @media(max-width:820px){
    body.mode-side .row{grid-template-columns:1fr}
    body.mode-side .cell.en{border-right:0;border-bottom:1px dashed var(--line)}
  }
  .legend{font-size:12px;color:var(--muted);margin-left:4px}
</style>
</head>
<body class="mode-side">
<aside id="sidebar">
  <div class="sb-head">
    <h2>章节目录 <span class="count">__TOC_COUNT__ 节</span></h2>
    <button class="sb-collapse" id="sbCollapse" title="收起目录">«</button>
  </div>
  <div class="sb-filter"><input id="sbFilter" type="text" placeholder="筛选章节 / filter..."></div>
  <nav class="sb-list" id="sbList">
__TOC_HTML__
  </nav>
</aside>
<button id="tocTab" title="展开目录">» 目录</button>
<div id="citePopup"></div>
<div id="fontPanel">
  <button class="fp-close" id="fpClose" title="关闭">×</button>
  <h3>阅读设置</h3>
  <div class="fp-row">
    <label>字号</label>
    <input type="range" id="fpSize" min="12" max="24" step="1" value="15">
    <span class="fp-val" id="fpSizeVal">15px</span>
  </div>
  <div class="fp-presets">
    <button data-size="13">小</button>
    <button data-size="15">标准</button>
    <button data-size="18">大</button>
    <button data-size="21">特大</button>
  </div>
  <h3 style="margin-top:4px">中文字体</h3>
  <div class="fp-fonts" id="fpFonts">
    <button data-font="serif" class="active">思源宋体（推荐）<span class="ff-sub">Noto Serif SC · 长文阅读护眼</span></button>
    <button data-font="sans">思源黑体<span class="ff-sub">Noto Sans SC · 清晰现代</span></button>
    <button data-font="deng">等线<span class="ff-sub">Deng · 系统自带</span></button>
    <button data-font="yahei">微软雅黑<span class="ff-sub">Microsoft YaHei · 系统默认</span></button>
  </div>
</div>
<div id="imgLightbox">
  <div class="lb-hint">单击任意处关闭 · 滚轮缩放 · 拖动移动</div>
  <img id="lbImg" alt="">
  <div class="lb-ctrl">
    <button id="lbZoomOut">− 缩小</button>
    <button id="lbReset">重置</button>
    <button id="lbZoomIn">+ 放大</button>
  </div>
</div>
<header>
  <h1>AI Agents That Matter</h1>
  <span class="sub">Kapoor, Stroebl, Siegel, Nadgir &amp; Narayanan · Princeton · 2024 · CS329Z Week 1 Course Material</span>
  <span class="spacer"></span>
  <div class="toolbar">
    <div class="seg" id="modeSeg">
      <button data-mode="side" class="active">左右分栏</button>
      <button data-mode="stack">上下对照</button>
      <button data-mode="en">仅英文</button>
      <button data-mode="zh">仅中文</button>
    </div>
    <button class="btn" id="tocToggle">☰ 目录</button>
    <button class="btn" id="fontBtn">字 号</button>
    <button class="btn" id="topBtn">回到顶部</button>
  </div>
</header>
<main>
  <div class="doc">
__ROWS__
  </div>
</main>
<script>
var REF_DATA = __REF_JSON__;
(function(){
  var body=document.body, seg=document.getElementById('modeSeg');

  // Anchor offset: keep jumped-to headings below the sticky header.
  // Header height varies with wrapping (toolbar buttons), so measure it, don't hardcode.
  function syncAnchorOffset(){
    var h=document.querySelector('header');
    if(h){
      var gap=16; // breathing room above the heading
      document.documentElement.style.setProperty('--anchor-offset',
        Math.round(h.getBoundingClientRect().height+gap)+'px');
    }
  }
  syncAnchorOffset();
  window.addEventListener('resize',syncAnchorOffset);

  // Only swap mode-* classes; NEVER clobber className (would wipe toc-collapsed).
  var MODES=['side','stack','en','zh'];
  function setMode(m){
    MODES.forEach(function(x){body.classList.remove('mode-'+x)});
    body.classList.add('mode-'+m);
    [].forEach.call(seg.querySelectorAll('button'),function(x){
      x.classList.toggle('active',x.getAttribute('data-mode')===m)});
  }
  seg.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b) return;
    var m=b.getAttribute('data-mode');
    setMode(m);
    try{localStorage.setItem('bilingualMode',m)}catch(err){}
  });
  var saved=null; try{saved=localStorage.getItem('bilingualMode')}catch(err){}
  var qm=new URLSearchParams(location.search).get('mode');
  var m=qm||saved;
  if(m && MODES.indexOf(m)>=0){ setMode(m); }
  // ---- font settings: size slider (12-24) + font family switch ----
  var fp=document.getElementById('fontPanel'),
      fpSize=document.getElementById('fpSize'),
      fpSizeVal=document.getElementById('fpSizeVal');
  var WEST='-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif';
  var FONTS={
    serif:'"Noto Serif SC","Source Han Serif SC","Songti SC",STSong,'+WEST,
    sans :'"Noto Sans SC","Source Han Sans SC","PingFang SC",'+WEST,
    deng :'"DengXian","等线",'+WEST,
    yahei:'"Microsoft YaHei","微软雅黑",'+WEST
  };
  function applySize(px){
    document.body.style.fontSize=px+'px';
    fpSize.value=px; fpSizeVal.textContent=px+'px';
    try{localStorage.setItem('readerFontSize',px)}catch(e){}
  }
  function applyFont(key){
    document.documentElement.style.setProperty('--font-stack',FONTS[key]||FONTS.serif);
    [].forEach.call(document.querySelectorAll('#fpFonts button'),function(b){
      b.classList.toggle('active',b.getAttribute('data-font')===key)});
    try{localStorage.setItem('readerFont',key)}catch(e){}
  }
  // restore saved preferences (default: serif font, 15px)
  var savedSize=15, savedFont='serif';
  try{ savedSize=parseInt(localStorage.getItem('readerFontSize'))||15;
       savedFont=localStorage.getItem('readerFont')||'serif'; }catch(e){}
  applySize(savedSize); applyFont(savedFont);
  // open/close panel
  document.getElementById('fontBtn').addEventListener('click',function(){fp.classList.toggle('show')});
  document.getElementById('fpClose').addEventListener('click',function(){fp.classList.remove('show')});
  document.addEventListener('click',function(e){
    if(fp.classList.contains('show') && !fp.contains(e.target) &&
       e.target.id!=='fontBtn') fp.classList.remove('show');
  });
  // slider
  fpSize.addEventListener('input',function(){applySize(parseInt(fpSize.value))});
  // presets
  [].forEach.call(document.querySelectorAll('.fp-presets button'),function(b){
    b.addEventListener('click',function(){applySize(parseInt(b.getAttribute('data-size')))});
  });
  // font buttons
  [].forEach.call(document.querySelectorAll('#fpFonts button'),function(b){
    b.addEventListener('click',function(){applyFont(b.getAttribute('data-font'))});
  });
  document.getElementById('topBtn').addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'})});

  // ---- sidebar TOC ----
  var tocToggle=document.getElementById('tocToggle'),
      sbCollapse=document.getElementById('sbCollapse'),
      tocTab=document.getElementById('tocTab');
  function setToc(collapsed){
    body.classList.toggle('toc-collapsed',collapsed);
    try{localStorage.setItem('tocCollapsed',collapsed?'1':'0')}catch(e){}
  }
  tocToggle.addEventListener('click',function(){setToc(!body.classList.contains('toc-collapsed'))});
  sbCollapse.addEventListener('click',function(){setToc(true)});
  tocTab.addEventListener('click',function(){setToc(false)});
  try{if(localStorage.getItem('tocCollapsed')==='1')setToc(true)}catch(e){}

  // expand / collapse top-level groups
  var groups=[].slice.call(document.querySelectorAll('.toc-group'));
  function setGroup(g,collapsed){
    g.classList.toggle('collapsed',collapsed);
    var ch=g.querySelector('.toc-children');
    if(ch) ch.style.maxHeight = collapsed?'0':(ch.scrollHeight+'px');
  }
  // init: all expanded; set max-height for animation
  groups.forEach(function(g){
    var ch=g.querySelector('.toc-children');
    if(ch) ch.style.maxHeight=ch.scrollHeight+'px';
  });
  document.getElementById('sbList').addEventListener('click',function(e){
    var btn=e.target.closest('.toc-expander');
    if(btn){
      var g=btn.closest('.toc-group');
      setGroup(g,!g.classList.contains('collapsed'));
      e.preventDefault();
    }
  });

  // filter
  var filter=document.getElementById('sbFilter');
  filter.addEventListener('input',function(){
    var q=filter.value.trim().toLowerCase();
    [].forEach.call(document.querySelectorAll('#sbList a'),function(a){
      a.hidden = q ? (a.textContent.toLowerCase().indexOf(q)<0) : false;
    });
    // auto-expand groups that have matching children while filtering
    if(q){
      groups.forEach(function(g){
        var vis=[].some.call(g.querySelectorAll('a'),function(a){return !a.hidden});
        setGroup(g,!vis);
      });
    } else {
      groups.forEach(function(g){setGroup(g,false)});
    }
  });

  // scroll spy: highlight current section
  var links=[].slice.call(document.querySelectorAll('#sbList a'));
  var anchors=links.map(function(a){return document.getElementById(a.getAttribute('data-anchor'))});
  function onScroll(){
    var best=-1, pos=window.scrollY+140;
    for(var i=0;i<anchors.length;i++){
      if(anchors[i] && anchors[i].offsetTop<=pos) best=i; else break;
    }
    links.forEach(function(a,i){a.classList.toggle('active',i===best)});
    // auto-expand the parent group when a subsection is highlighted
    if(best>=0){
      var act=links[best], grp=act.closest('.toc-group');
      if(grp && act.classList.contains('toc-l2') && grp.classList.contains('collapsed')){
        setGroup(grp,false);
      }
    }
    if(best>=0 && links[best] && !links[best].hidden){
      var el=links[best], box=document.getElementById('sbList');
      var top=el.offsetTop-box.offsetTop, bot=top+el.offsetHeight;
      if(top<box.scrollTop||bot>box.scrollTop+box.clientHeight){
        box.scrollTop=top-box.clientHeight/2;
      }
    }
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  links.forEach(function(a){a.addEventListener('click',function(){
    if(window.innerWidth<821) setToc(true);
  })});
  onScroll();

  // ---- citation hover popup ----
  var popup=document.getElementById('citePopup'), hideTimer=null;
  function showCite(a){
    var id=a.getAttribute('data-ref'), text=REF_DATA[id]||'(reference not found)';
    var num=id.replace('ref-','');
    var clean=text.replace(/^\[\d+\]\s*/,'');
    popup.innerHTML='<span class="cp-num">'+num+'</span>'+clean+
      '<a class="cp-jump" href="#'+id+'">跳转到参考文献 →</a>';
    popup.style.display='block';
    var r=a.getBoundingClientRect();
    var x=Math.min(r.left, window.innerWidth-440), y=r.bottom+8;
    if(y+popup.offsetHeight>window.innerHeight-10) y=r.top-popup.offsetHeight-8;
    popup.style.left=Math.max(8,x)+'px';
    popup.style.top=Math.max(8,y)+'px';
  }
  function hideCite(){popup.style.display='none'}
  document.addEventListener('mouseover',function(e){
    var a=e.target.closest('a.cite'); if(!a)return;
    clearTimeout(hideTimer); showCite(a);
  });
  document.addEventListener('mouseout',function(e){
    var a=e.target.closest('a.cite'); if(!a)return;
    hideTimer=setTimeout(function(){
      if(!popup.matches(':hover')) hideCite();
    },160);
  });
  popup.addEventListener('mouseenter',function(){clearTimeout(hideTimer)});
  popup.addEventListener('mouseleave',hideCite);
  popup.addEventListener('click',function(e){
    if(e.target.closest('.cp-jump')){ hideCite(); }
  });

  // ---- image lightbox: click to fullscreen, wheel zoom, drag, click to close ----
  var lb=document.getElementById('imgLightbox'), lbImg=document.getElementById('lbImg');
  var scale=1, tx=0, ty=0, dragging=false, sx=0, sy=0;
  function applyTransform(){lbImg.style.transform='translate('+tx+'px,'+ty+'px) scale('+scale+')'}
  function openLightbox(src){
    lbImg.src=src; scale=1; tx=0; ty=0; applyTransform();
    lb.classList.add('show');
  }
  function closeLightbox(){lb.classList.remove('show');lbImg.src=''}
  document.addEventListener('click',function(e){
    var img=e.target.closest('figure img');
    if(img){ openLightbox(img.src); return; }
    if(e.target===lb || e.target.closest('.lb-hint')){ closeLightbox(); }
  });
  lb.addEventListener('wheel',function(e){
    e.preventDefault();
    var old=scale;
    scale=Math.min(6,Math.max(0.25,scale*(e.deltaY<0?1.12:0.89)));
    // zoom toward cursor
    tx=e.clientX-(e.clientX-tx)*(scale/old);
    ty=e.clientY-(e.clientY-ty)*(scale/old);
    applyTransform();
  },{passive:false});
  lb.addEventListener('mousedown',function(e){
    if(e.target.closest('.lb-ctrl'))return;
    dragging=true; sx=e.clientX-tx; sy=e.clientY-ty; lb.style.cursor='grabbing';
  });
  window.addEventListener('mousemove',function(e){
    if(!dragging)return;
    tx=e.clientX-sx; ty=e.clientY-sy; applyTransform();
  });
  window.addEventListener('mouseup',function(){dragging=false;lb.style.cursor='zoom-out'});
  document.getElementById('lbZoomIn').addEventListener('click',function(e){e.stopPropagation();scale=Math.min(6,scale*1.25);applyTransform()});
  document.getElementById('lbZoomOut').addEventListener('click',function(e){e.stopPropagation();scale=Math.max(0.25,scale*0.8);applyTransform()});
  document.getElementById('lbReset').addEventListener('click',function(e){e.stopPropagation();scale=1;tx=0;ty=0;applyTransform()});
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&lb.classList.contains('show'))closeLightbox()});
})();
</script>
</body>
</html>
'''

rows_html = HTML.replace("__ROWS__", rows_html)
rows_html = rows_html.replace("__TOC_HTML__", toc_html)
rows_html = rows_html.replace("__TOC_COUNT__", str(toc_count))
rows_html = rows_html.replace("__REF_JSON__", ref_json)
with open(OUTHTML, "w", encoding="utf-8") as f:
    f.write(rows_html)

print("HTML:", OUTHTML)
print("size:", os.path.getsize(OUTHTML), "bytes")
print("rows:", len(rows))
print("images copied:", copied)

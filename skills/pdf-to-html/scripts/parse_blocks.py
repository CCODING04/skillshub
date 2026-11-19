# -*- coding: utf-8 -*-
"""Parse MinerU full.md into structured blocks with stable IDs.
Output: blocks.json  -> list of {id, type, text, ...}
Block types:
  heading | para | list | figure | table | ref | meta | checklist
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "temp", "mineru_out", "full.md")
OUT = os.path.join(ROOT, "temp", "blocks.json")

lines = open(SRC, "r", encoding="utf-8").read().split("\n")

blocks = []
in_refs = False
in_checklist = False
counter = {"heading": 0, "para": 0, "list": 0, "figure": 0,
           "table": 0, "ref": 0, "meta": 0, "checklist": 0}


def new_id(t):
    counter[t] += 1
    return "%s-%03d" % (t, counter[t])


def is_figure_line(s):
    return bool(re.match(r"^!\[.*?\]\(images/.+?\)", s.strip()))


def is_table_line(s):
    return s.strip().startswith("<table")


def is_list_line(s):
    st = s.strip()
    return bool(re.match(r"^(\d+\.|•|\*|-)\s+", st))


def is_ref_line(s):
    return bool(re.match(r"^\[\d+\]\s+", s.strip()))


i = 0
n = len(lines)
while i < n:
    raw = lines[i]
    s = raw.strip()

    if not s:
        i += 1
        continue

    # section flags
    if s == "## References":
        in_refs = True
    if s == "## Checklist":
        in_checklist = True

    # headings
    if re.match(r"^#{1,6}\s+", s):
        lvl = len(s) - len(s.lstrip("#"))
        text = s.lstrip("# ").strip()
        blocks.append({"id": new_id("heading"), "type": "heading",
                       "level": lvl, "text": text})
        i += 1
        continue

    # image figure: gather ![]() line + following caption lines (Figure N: ...)
    if is_figure_line(s):
        m = re.search(r"\(images/(.+?)\)", s)
        img = m.group(1) if m else ""
        caption_lines = []
        j = i + 1
        while j < n:
            t = lines[j].strip()
            if not t:
                # allow one blank then check caption
                if j + 1 < n and re.match(r"^(Figure|Table)\s*\d+\s*:", lines[j+1].strip()):
                    j += 1
                    continue
                break
            if re.match(r"^(Figure|Table)\s*\d+\s*:", t):
                caption_lines.append(t)
                j += 1
                continue
            break
        blocks.append({"id": new_id("figure"), "type": "figure",
                       "image": img, "caption": " ".join(caption_lines)})
        i = j
        continue

    # HTML table (single line)
    if is_table_line(s):
        blocks.append({"id": new_id("table"), "type": "table", "html": s})
        i += 1
        continue

    # references
    if in_refs and not in_checklist and is_ref_line(s):
        blocks.append({"id": new_id("ref"), "type": "ref", "text": s})
        i += 1
        continue

    # checklist region: keep as meta (not translated)
    if in_checklist:
        # accumulate until end of file
        chunks = [s]
        i += 1
        while i < n:
            t = lines[i].strip()
            if t:
                chunks.append(t)
            i += 1
        blocks.append({"id": new_id("checklist"), "type": "checklist",
                       "text": "\n".join(chunks)})
        continue

    # list: consecutive list lines (allow wrapped continuation lines)
    if is_list_line(s):
        items = [s]
        i += 1
        while i < n:
            t = lines[i].strip()
            if not t:
                break
            if is_list_line(t) or (not re.match(r"^#{1,6}\s+", t)
                                   and not is_figure_line(t)
                                   and not is_table_line(t)
                                   and not is_ref_line(t)):
                items.append(t)
                i += 1
            else:
                break
        blocks.append({"id": new_id("list"), "type": "list", "text": "\n".join(items)})
        continue

    # meta lines: author / affiliation / date near top
    if counter["heading"] == 1 and counter["para"] == 0 and i < 10:
        blocks.append({"id": new_id("meta"), "type": "meta", "text": s})
        i += 1
        continue

    # paragraph: accumulate until blank or structural boundary
    para = [s]
    i += 1
    while i < n:
        t = lines[i].strip()
        if not t:
            break
        if (re.match(r"^#{1,6}\s+", t) or is_figure_line(t) or is_table_line(t)
                or is_ref_line(t) or is_list_line(t)):
            break
        para.append(t)
        i += 1
    blocks.append({"id": new_id("para"), "type": "para", "text": " ".join(para)})

json.dump(blocks, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# stats
from collections import Counter
c = Counter(b["type"] for b in blocks)
print("total blocks:", len(blocks))
for k, v in c.most_common():
    print("  %-10s %d" % (k, v))
print("translatable (heading/para/list/figure-caption):",
      sum(1 for b in blocks if b["type"] in ("heading", "para", "list") or
          (b["type"] == "figure" and b.get("caption"))))
print("images referenced:", sum(1 for b in blocks if b["type"] == "figure"))
print("\noutput:", OUT)

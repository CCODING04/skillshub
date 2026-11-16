#!/usr/bin/env python3
"""Lint a WeChat article: layout hard constraints (error) + content rules (warning).

Backwards compatible with the original 13 `checks`. New rules live in `rules[]`.
Use --strict (or ci_check.py) to make warnings blocking, like a CI gate.

Exit code 0 = gate passed, 1 = gate failed, 2 = input error.
"""
import argparse
import difflib
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import viewer_util  # noqa: E402  校验前剥离审核用查看器外壳

FORBIDDEN_TAGS = ["section", "figure", "figcaption", "script", "iframe", "link"]
ALLOWED_TAGS = {"html", "head", "meta", "title", "body", "div", "p", "img", "strong",
                "h1", "h2", "h3", "br", "blockquote", "span", "table", "tr", "td", "hr"}
STYLE_COMPONENTS = {"p", "div", "blockquote", "h1", "h2", "h3", "span", "strong", "img",
                    "table", "tr", "td"}
INTERNAL_JARGON = ["S0-A", "S0-B", "feasibility.json", "reader_notes", "process_appendix",
                   "validate_article", "build_article", "content.json", "base64", "IR 中间层",
                   "拍板", "draft-not-executed"]
META_INTERNAL = ["口径", "拍板", "S0-", "feasibility", "reader_notes", "process_appendix", "IR "]
CAVEAT_WORDS = ["非逐字", "书面化", "自拟", "整理者", "未经", "编译者", "整理"]
CAREER_HINTS = ["曾在", "此前", "加入", "任职", "毕业于", "工程经理", "核心开发", "负责人",
                "参与交付", "供职", "做过", "转行", "履历", "作者是", "创立", "带领"]
SOURCE_MARKERS = ["http", "X ", "X@" , "@", "《", "公众号", "原文", "来源"]

SHORT_PROFILE = {
    "min_zh_chars": 400,
    "min_glossary_notes": 3,
    "min_paragraphs": 8,
    "min_inline_styles": 10,
    "min_component_inline_rate": 0.90,
}

DEFAULT_CONFIG = {
    "min_inline_styles": 20,
    "min_paragraphs": 20,
    "min_component_inline_rate": 0.95,
    "min_glossary_notes": 8,
    "min_caveat_words": 2,
    "foot_bullets_min": 2,
    "foot_bullets_max": 6,
    "min_png_width": 2000,
    "min_zh_chars": 1500,
    "profile_threshold_zh": 1500,
    "min_images": 1,
    "min_blockquotes": 1,
    "min_bridge_zh": 40,
    "max_caption_h3_ratio": 0.55,
    "max_asides": 2,
    "internal_jargon": INTERNAL_JARGON,
}


def visible_text(h):
    t = re.sub(r"<script[\s\S]*?</script>", "", h, flags=re.I)
    t = re.sub(r"<style[\s\S]*?</style>", "", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"&[a-zA-Z]+;", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def png_dimensions(h):
    dims = []
    for m in re.finditer(r"data:image/(?:png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)", h):
        try:
            raw = base64.b64decode(m.group(1)[:64])
            if raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) >= 24:
                dims.append((int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")))
            else:
                dims.append(None)
        except Exception:
            dims.append(None)
    return dims


def component_inline_stats(h):
    total = styled = 0
    for name, attrs in re.findall(r"<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>", h):
        if name.lower() in STYLE_COMPONENTS:
            total += 1
            if re.search(r"\bstyle\s*=", attrs, re.I):
                styled += 1
    return styled, total


ASIDE_SPAN = re.compile(r"<!--\s*aside:start\s*-->[\s\S]*?<!--\s*aside:end\s*-->", re.I)


def caption_stats(h):
    # theme-driven renderer wraps images in <div>, older renderer in <p>: accept both.
    # 区块里的图，图注在框外（S26），所以中间允许跨过一层 </div>。
    flat = re.sub(r"<!--\s*aside:(?:start|end)\s*-->", "", h, flags=re.I)
    pairs = re.findall(
        r"<(?:p|div)[^>]*>\s*<img[^>]*>\s*</(?:p|div)>(?:\s*</div>)?\s*<p[^>]*>([\s\S]*?)</p>",
        flat, re.I)
    good = [p for p in pairs if re.search(r"图|封面|示意|图注", re.sub(r"<[^>]+>", "", p))]
    return len(good), len(pairs)


def captions_inside_asides(h):
    """区块（带边框的容器）里不该出现图注。

    图注是给读者读图的辅助，和正文同属一层；落进异色框里既比正文对比度低，
    也和全篇其它图注不是一种东西。框里只放图本身，图注紧贴在框外。
    """
    out = []
    for span in ASIDE_SPAN.findall(h):
        for p in re.findall(r"<p\b[^>]*>([\s\S]*?)</p>", span, re.I):
            text = re.sub(r"<[^>]+>", "", p).strip()
            if re.match(r"^(图|封面)\s*\d*\s*｜", text):
                out.append(text[:40])
    return out


CAPTION_P = re.compile(r"<p\b[^>]*text-align\s*:\s*center[^>]*>[\s\S]*?</p>", re.I)


def figure_gap_stats(h):
    """Chinese chars of real prose sitting between each pair of adjacent images.

    Captions are centre-aligned <p> and carry no prose, so they are stripped before
    counting: two figures separated only by their captions score ~0 and fail S22.
    """
    marks = [m.start() for m in re.finditer(r"<img\b", h, re.I)]
    if len(marks) < 2:
        return []
    tags = [m.end() for m in re.finditer(r"<img\b[^>]*>", h, re.I)]
    gaps = []
    for i in range(len(marks) - 1):
        start = tags[i] if i < len(tags) else marks[i]
        seg = h[start:marks[i + 1]]
        seg = CAPTION_P.sub(" ", seg)
        plain = re.sub(r"<[^>]+>", " ", seg)
        gaps.append(len(re.findall(r"[\u4e00-\u9fa5]", plain)))
    return gaps


def run_validation(html_path, *, expect_figures=0, strict=False, md_path=None,
                   ir_path=None, config=None, rules_out=None,
                   style_id=None, style_overrides=None):
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    applied_overrides = {}
    if style_overrides:
        for k, v in style_overrides.items():
            if k in cfg:
                applied_overrides[k] = {"default": cfg[k], "applied": v}
                cfg[k] = v
    path = Path(html_path)
    if not path.exists():
        return {"error": "file not found", "path": str(path), "valid": False}
    h = path.read_text(encoding="utf-8")

    # 校验前剥离「审核用图片查看器」外壳：那是工具层，不是排版内容，
    # 微信编辑器粘贴时会剥掉 script，所以门禁校验的是剥离后剩下的东西
    # ——也就是微信真正收到的排版。用户手写的 script 不在标记内，照样被 S03 拦。
    viewer_info = {"stripped": False, "bytes": 0, "note": "no viewer block"}
    try:
        h_before = len(h.encode("utf-8"))
        h, vbytes = viewer_util.strip(h)
        if vbytes:
            viewer_info = {
                "stripped": True,
                "bytes": vbytes,
                "note": "审核用图片查看器已剥离后校验；上传微信前用 strip_viewer.py 产出纯净版",
                "html_bytes_before": h_before,
                "html_bytes_after": len(h.encode("utf-8")),
            }
    except viewer_util.ViewerError as exc:
        viewer_info = {"stripped": False, "bytes": 0,
                       "error": str(exc),
                       "note": "查看器标记不完整，按含外壳校验（S03 会拦下）"}
    count = lambda pat: len(re.findall(pat, h, re.I | re.S))

    tags = [t.lower() for t in re.findall(r"<\s*([a-zA-Z][a-zA-Z0-9]*)", h)]
    used = sorted(set(tags))
    unexpected = [t for t in used if t not in ALLOWED_TAGS]
    forbidden_hits = {t: count(r"<\s*" + t + r"\b") for t in FORBIDDEN_TAGS}
    img_tags = re.findall(r"<img[^>]*>", h, re.I)
    img_count, b64_count = len(img_tags), count(r"data:image/[^;]+;base64,")
    bad_img = [t for t in img_tags if "width:100%" not in t.replace(" ", "")]
    no_alt = [t for t in img_tags if not re.search(r"\balt\s*=", t, re.I)]
    external = count(r"(?:src|href)\s*=\s*[\"']https?://")
    inline_styles = count(r"\bstyle\s*=")
    paragraphs = count(r"<p\b")
    blockquotes = count(r"<blockquote\b")
    styled, components = component_inline_stats(h)
    inline_rate = round(styled / components, 4) if components else 0.0
    dims = png_dimensions(h)
    dims_ok = bool(dims) and all(d and d[0] >= cfg["min_png_width"] for d in dims)
    captions, caption_pairs = caption_stats(h)
    figure_gaps = figure_gap_stats(h)
    asides = count(r"<!--\s*aside:start\s*-->")
    nested_asides = count(r"<!--\s*aside:start\s*-->[\s\S]*?<!--\s*aside:start\s*-->")
    buried_captions = captions_inside_asides(h)
    consecutive_br = count(r"<br\s*/?>\s*<br\s*/?>")

    text = visible_text(h)
    zh_chars = len(re.findall(r"[\u4e00-\u9fa5]", text))
    # Length-aware lint profile (S14 and content thresholds). Explicit in the report.
    profile = "long" if zh_chars >= cfg["profile_threshold_zh"] else "short"
    profile_overrides = {}
    if profile == "short":
        for k, val in SHORT_PROFILE.items():
            profile_overrides[k] = {"long": cfg[k], "short": val}
            cfg[k] = val
    jargon = [w for w in cfg.get("internal_jargon", []) if w in text]
    glossary = re.findall(r"[A-Za-z][A-Za-z0-9.+#_-]{2,}（[^）]*[\u4e00-\u9fa5][^）]*）", text)
    latin_tokens = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9.+#_-]{2,}", text)))

    head = text[:800]
    career = [w for w in CAREER_HINTS if w in head]
    has_person = bool(re.search(r"[A-Z][a-z]+ [A-Z][a-z]+|@[A-Za-z0-9_]+", head))
    speaker_intro = has_person and len(career) > 0

    meta_head = text[:1200]
    meta_internal = [w for w in META_INTERNAL if w in meta_head]
    foot = h[max(0, h.rfind("资料来源")):]
    foot_bullets = len(re.findall(r"· ", foot))
    caveat_hits = [w for w in CAVEAT_WORDS if w in foot] or [w for w in CAVEAT_WORDS if w in text]
    source_marker = any(m in foot for m in SOURCE_MARKERS)

    md_has_appendix = None
    md = ""
    if md_path and Path(md_path).exists():
        md = Path(md_path).read_text(encoding="utf-8")
        md_has_appendix = bool(re.search(r"整理过程与回溯|整理过程|回溯", md))

    is_talk = False
    ir = {}
    caption_h3 = None          # (相似度, 图注, 小标题)
    if ir_path and Path(ir_path).exists():
        ir = json.loads(Path(ir_path).read_text(encoding="utf-8"))
        kind = str(ir.get("source", {}).get("kind", "")).lower()
        is_talk = any(k in kind for k in ["video", "talk", "interview", "speech"]) or \
            any("讲者" in m.get("label", "") for m in ir.get("meta", []))
        caps = {f.get("id"): f.get("caption", "") for f in ir.get("figures", [])}

        def walk(blocks, last_h3):
            """按顺序走一遍，图注只和它前面最近的小标题比——这才是同屏竞争关系。"""
            nonlocal caption_h3
            for b in blocks:
                if b.get("type") == "h3":
                    last_h3 = b.get("text", "")
                elif b.get("type") == "figure":
                    cap, h3 = caps.get(b.get("id"), ""), last_h3
                    if cap and h3 and len(h3) >= 4:
                        r = difflib.SequenceMatcher(None, cap, h3).ratio()
                        if not caption_h3 or r > caption_h3[0]:
                            caption_h3 = (round(r, 3), cap, h3)
                elif b.get("type") == "aside":
                    walk(b.get("blocks", []), last_h3)
            return last_h3

        for sec in ir.get("sections", []):
            walk(sec.get("blocks", []), "")

    rules = []

    def add(rid, level, passed, message, actual=None):
        rules.append({"id": rid, "level": level, "passed": bool(passed),
                      "message": message, "actual": actual})

    # ---- layout: error ----
    add("S01", "error", count(r"<style\b") == 0, "禁止 <style> 标签（微信会过滤）")
    add("S02", "error", count(r"\bclass\s*=") == 0, "禁止 class 属性")
    add("S03", "error", sum(forbidden_hits.values()) == 0, "禁止 section/figure/figcaption/script 等标签",
        {k: v for k, v in forbidden_hits.items() if v})
    add("S04", "error", not unexpected, "标签必须在白名单内", unexpected)
    add("S05", "error", external == 0, "不得引用外部资源", external)
    add("S06", "error", inline_styles >= cfg["min_inline_styles"],
        f"内联样式数 >= {cfg['min_inline_styles']}（防止一个容器撑全篇）", inline_styles)
    add("S07", "error", img_count >= cfg.get("min_images", 1),
        "配图数 >= %d" % cfg.get("min_images", 1), img_count)
    add("S08", "error", img_count == b64_count, "图片数与内嵌 base64 数一致", [img_count, b64_count])
    add("S09", "error", (img_count == expect_figures) if expect_figures else True,
        "图片数符合预期", img_count)
    add("S10", "error", not bad_img, "每张图片 width:100%", len(bad_img))
    add("S11", "error", blockquotes >= cfg.get("min_blockquotes", 1),
        "引用块数 >= %d" % cfg.get("min_blockquotes", 1), blockquotes)
    add("S12", "error", "{{" not in h, "无未替换占位符")
    add("S13", "error", "资料来源" in text or "整理说明" in text, "必须有资料来源与整理说明")
    add("S14", "error", inline_rate >= cfg["min_component_inline_rate"],
        f"组件级内联覆盖率 >= {cfg['min_component_inline_rate']:.0%}", inline_rate)
    add("S15", "error", paragraphs >= cfg["min_paragraphs"],
        f"段落数 >= {cfg['min_paragraphs']}（禁止用 <br> 堆排版）", paragraphs)
    add("S16", "error", not no_alt, "每张图片必须有 alt", len(no_alt))
    add("S17", "error", dims_ok, "配图为 >=2x 高清 PNG（宽 >= %d）" % cfg["min_png_width"], dims)
    add("S18", "error", caption_pairs == img_count and captions == img_count,
        "每张图后必须有图注段落", {"captioned": captions, "pairs": caption_pairs, "images": img_count})
    add("S19", "error", consecutive_br == 0, "禁止连续 <br> 排版", consecutive_br)
    add("S20", "error", not jargon, "正文不得出现内部流程术语", jargon)
    add("S21", "error", zh_chars >= cfg["min_zh_chars"],
        f"正文中文字符 >= {cfg['min_zh_chars']}", zh_chars)
    add("S22", "error", all(g >= cfg["min_bridge_zh"] for g in figure_gaps),
        f"相邻两图之间必须有正文过渡（>= {cfg['min_bridge_zh']} 中文字，图注不算）",
        {"gaps": figure_gaps, "min": min(figure_gaps) if figure_gaps else None})
    ratio = caption_h3[0] if caption_h3 else 0.0
    add("S23", "error", ratio < cfg["max_caption_h3_ratio"],
        f"图注不复述它前面的小标题（相似度 < {cfg['max_caption_h3_ratio']}）；图注回答图在说什么，命名交给标题",
        {"ratio": ratio, "caption": caption_h3[1] if caption_h3 else None,
         "h3": caption_h3[2] if caption_h3 else None})
    add("S24", "error", asides <= cfg["max_asides"] and not nested_asides,
        f"区块（aside）全篇 ≤ {cfg['max_asides']} 处且不嵌套：区块用来分开一组内容，不能变成整节的外框",
        {"count": asides, "nested": nested_asides})
    add("S26", "error", not buried_captions,
        "图注留在图片下方、区块之外：框里只放图本身，图注与全篇其它图注同一层",
        {"captions_in_aside": buried_captions})

    # S25: Markdown 归档必须带上每张图。aside 当初就被导出器整块跳过，图与图注
    # 都消失，而 HTML 侧一切正常——只看成稿看不出来，必须比对两条出口。
    md_missing = []
    if md and ir:
        for f in ir.get("figures", []):
            cap = (f.get("caption") or "").strip()
            if cap and cap not in md:
                md_missing.append(f.get("id"))
        add("S25", "error", not md_missing,
            "每张图的图注都要出现在 Markdown 归档里：图不能只存在于 HTML 一侧",
            {"missing": md_missing, "figures": len(ir.get("figures", []))})

    # ---- content: warning (blocking under --strict) ----
    add("C01", "error" if is_talk else "warning", speaker_intro,
        "有明确作者/讲者的来源，开头须有履历或高光经历引子",
        {"person": has_person, "career_hints": career[:6], "is_talk": is_talk})
    add("C02", "warning", len(glossary) >= cfg["min_glossary_notes"],
        f"外文术语首次出现须带中文简注（>= {cfg['min_glossary_notes']} 处）",
        {"notes": len(glossary), "samples": glossary[:6], "latin_tokens": len(latin_tokens)})
    add("C03", "warning", cfg["foot_bullets_min"] <= foot_bullets <= cfg["foot_bullets_max"]
        and source_marker and len(caveat_hits) >= cfg["min_caveat_words"],
        "文末来源说明：2–6 条、含来源标识、含书面化/非逐字等声明",
        {"bullets": foot_bullets, "source_marker": source_marker, "caveats": caveat_hits})
    if md_path:
        add("C04", "warning", bool(md_has_appendix),
            "Markdown 存档须含「整理过程与回溯」附录", {"md": md_path, "found": bool(md_has_appendix)})
    add("C05", "warning", not meta_internal,
        "读者可见信息卡不得出现内部口径/流程词", meta_internal)

    errors = [r for r in rules if r["level"] == "error" and not r["passed"]]
    warnings = [r for r in rules if r["level"] == "warning" and not r["passed"]]
    gate_ok = not errors and (not strict or not warnings)
    checks = {
        "no_style_tag": rules[0]["passed"], "no_class_attr": rules[1]["passed"],
        "no_forbidden_tags": rules[2]["passed"], "no_unexpected_tags": rules[3]["passed"],
        "no_external_resources": rules[4]["passed"], "has_inline_styles": rules[5]["passed"],
        "has_images": rules[6]["passed"], "all_images_embedded": rules[7]["passed"],
        "figure_count_matches": rules[8]["passed"], "every_image_fluid": rules[9]["passed"],
        "has_blockquote": rules[10]["passed"], "no_placeholders": rules[11]["passed"],
        "has_sources_note": rules[12]["passed"],
    }
    report = {
        "valid": gate_ok, "strict": strict, "path": str(path.resolve()),
        "bytes": len(h.encode("utf-8")),
        "viewer": viewer_info,
        "summary": {
            "error_failures": [r["id"] for r in errors],
            "warning_failures": [r["id"] for r in warnings],
            "rules_total": len(rules), "rules_passed": sum(1 for r in rules if r["passed"]),
            "gate": "PASS" if gate_ok else "FAIL",
        },
        "stats": {
            "inline_styles": inline_styles, "component_inline_rate": inline_rate,
            "paragraphs": paragraphs, "blockquotes": blockquotes, "images": img_count,
            "base64_images": b64_count, "png_dimensions": dims, "zh_chars": zh_chars,
            "glossary_notes": len(glossary), "latin_tokens": len(latin_tokens),
            "foot_bullets": foot_bullets, "used_tags": used,
            "unexpected_tags": unexpected, "external_resources": external,
            "figure_captions": captions, "figure_gaps_zh": figure_gaps,
            "asides": asides,
            "speaker_intro": speaker_intro,
        },
        "profile": {"id": profile, "zh_chars": zh_chars,
                    "threshold": cfg["profile_threshold_zh"],
                    "applied_overrides": profile_overrides,
                    "note": "短稿独立阈值，全部写进报告，不静默放宽"},
        "checks": checks,
        "theme": {
            "id": style_id or "ink-tangerine",
            "applied_overrides": applied_overrides,
            "scoped_rules": sorted(applied_overrides.keys()),
            "note": "按风格调整的数值已显式记录，不是静默跳过；L0/L1 不变量不随风格变化。",
        },
        "rules": rules,
    }
    if rules_out:
        Path(rules_out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", help="article HTML to validate")
    ap.add_argument("--expect-figures", type=int, default=0)
    ap.add_argument("--out", default="", help="write full JSON report")
    ap.add_argument("--strict", action="store_true", help="warnings become blocking")
    ap.add_argument("--md", default="", help="Markdown archive to check for the process appendix")
    ap.add_argument("--ir", default="", help="content.json used to detect talk/interview sources")
    ap.add_argument("--config", default="", help="JSON file overriding rule thresholds")
    ap.add_argument("--rules-out", default="", help="write the rules report (for CI)")
    args = ap.parse_args()
    cfg = None
    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    report = run_validation(args.html, expect_figures=args.expect_figures, strict=args.strict,
                            md_path=args.md or None, ir_path=args.ir or None, config=cfg,
                            rules_out=args.rules_out or None)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    if not report.get("valid", False):
        s = report.get("summary", {})
        print("GATE FAIL | errors:", s.get("error_failures"),
              "| warnings:", s.get("warning_failures"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

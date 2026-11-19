#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF→双语HTML 交付门禁。把 pitfalls.md 中可机器判定的约束做成检查。

用法:
  python validate.py <workdir> [--strict]

<workdir> 是含 temp/ 与 courses/ 的项目根目录。
--strict 时任一 FAIL 返回退出码 1。
"""
import os, sys, re, json, glob

WORKDIR = None
RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": str(detail)})


def load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def find_html(wd):
    hits = glob.glob(os.path.join(wd, "courses", "**", "*_bilingual.html"), recursive=True)
    return hits[0] if hits else None


# ---------- A. 环境层 ----------
def check_env_contract():
    """A1/A2/A3: 通用 token 来源、JSON 容错、不打印 key（不绑定私有配置）。"""
    # 环境文件是可选来源之一，不存在时允许（可用 MINERU_API_TOKEN）
    env = os.path.join(WORKDIR, ".env.json")
    if os.path.exists(env):
        raw = open(env, encoding="utf-8").read()
        try:
            json.loads(raw)
            record("A-env JSON 可解析", True, "严格解析")
        except Exception:
            try:
                json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
                record("A-env JSON 可解析", True, "容错解析(尾随逗号)")
            except Exception as e:
                record("A-env JSON 可解析", False, str(e)[:80])
    else:
        record("A-env JSON 可解析", True, "无 .env.json（可用环境变量）")
    # A3: 扫描是否有打印 token 的代码（保守检测，排除注释里的说明文字）
    leaks = []
    for f in glob.glob(os.path.join(WORKDIR, "**", "*.py"), recursive=True):
        try:
            src = "\n".join(l for l in open(f, encoding="utf-8").read().splitlines()
                            if not l.strip().startswith("#"))
        except Exception:
            continue
        for pat in [r"print\s*\([^)]*token", r"print\s*\([^)]*\['mineru'\]",
                    r"print\s*\([^)]*\[\"mineru\"\]"]:
            if re.search(pat, src):
                leaks.append(os.path.basename(f))
    record("A-env 无 token 打印", not leaks, leaks)


# ---------- B. 转换/解析层 ----------
def check_fullmd():
    md = os.path.join(WORKDIR, "temp", "mineru_out", "full.md")
    ok = os.path.exists(md)
    record("B-full.md 存在", ok, md)
    if not ok:
        return None
    text = open(md, encoding="utf-8").read()
    # B1: 表格覆盖度由 HTML 侧检查；这里记录被压扁表（单元格内连续大写词粘连）
    flat = re.findall(r"<td[^>]*>([^<]{40,})</td>", text)
    suspect = [x[:40] for x in flat if re.search(r"\)[A-Z][a-z]", x)]
    record("B1-发现疑似压扁表格(需人工核对)", True,
           "%d 处；已发现即提示核对，非失败项" % len(suspect))
    # B2: LaTeX 转义
    esc = len(re.findall(r"\\\$", text))
    record("B2-full.md 含 LaTeX 转义(需渲染层归一化)", True, "%d 处" % esc)
    # B3: 围栏代码块
    fences = len(re.findall(r"^```", text, re.M))
    record("B3-围栏代码块数(需作为单一 code 块)", True, "%d 个围栏行" % fences)
    return text


def check_html_structure(html):
    # B2: 成品中不应有字面 \$ 或 \tau
    bad_esc = html.count(chr(92) + "$") + html.count("\\tau")
    record("B2-成品无字面 LaTeX 转义", bad_esc == 0, "%d 处" % bad_esc)
    # B3: 无字面围栏
    fence = chr(96) * 3
    record("B3-成品无字面代码块围栏", fence not in html, "")
    # B4: TOC 层级最多二级
    l3 = len(re.findall(r'class="toc-l3"', html))
    record("B4-TOC 无三级目录", l3 == 0, "%d 个 toc-l3" % l3)
    l1 = len(re.findall(r'class="toc-l1"', html))
    l2 = len(re.findall(r'class="toc-l2"', html))
    record("B4-TOC 有一级和二级", l1 > 0 and l2 > 0, "l1=%d l2=%d" % (l1, l2))
    # B5: 旋转图（检测异常高宽比的原图是否仍被直接引用——通过尺寸表判断）
    # 由 check_images 的 rotate-manifest 检查代替。


# ---------- B6. 编号列表连续性 ----------
def check_numbered_lists(md_text, html):
    """Catch numbered lists split into separate <ol> (each restarting at 1.)."""
    if not md_text:
        return
    # Source: groups of consecutive numbered lines 1. 2. 3. ... -> group sizes
    src_groups = []
    nums = [int(m.group(1)) for m in
            (re.match(r"^(\d+)\.\s", l.strip()) for l in md_text.split("\n")) if m]
    # split the flat number stream into ascending runs that start at 1
    cur = []
    for n in nums:
        if n == 1:
            if len(cur) >= 2:
                src_groups.append(len(cur))
            cur = [1]
        elif cur and n == cur[-1] + 1:
            cur.append(n)
        else:
            if len(cur) >= 2:
                src_groups.append(len(cur))
            cur = [n] if n == 1 else []
    if len(cur) >= 2:
        src_groups.append(len(cur))
    # Rendered: each <ol> li count (both EN and ZH columns present)
    ol_sizes = [len(re.findall(r"<li>", o)) for o in
                re.findall(r"<ol>(.*?)</ol>", html, re.S)]
    # Every source group size must appear among rendered ol sizes
    missing = [g for g in src_groups if g not in ol_sizes]
    record("B7-编号列表完整合并", not missing,
           "原文组%s 渲染ol%s 缺失%s" % (src_groups, sorted(set(ol_sizes)), missing))
    # No orphan single-item <ol> (the classic split symptom)
    singles = sum(1 for s in ol_sizes if s == 1)
    record("B7-无孤立单条编号列表", singles == 0, "%d 个" % singles)


# ---------- C. 渲染/交互层 ----------
def check_interaction(html):
    # C1/D4: 禁止 className 整体赋值（最重要，用户明确要求的规则）
    bad = re.findall(r"body\.className\s*=", html)
    record("C1-无 body.className 整体赋值", not bad, "%d 处" % len(bad))
    # 任何元素的 className 整体赋值都要警惕（D4：状态正交）
    bad_any = re.findall(r"\.className\s*=\s*['\"]", html)
    record("D4-无元素 className 整体赋值", not bad_any, "%d 处" % len(bad_any))
    # 应存在 setMode 用 classList
    record("C1-setMode 用 classList", "classList.remove('mode-" in html, "")
    # setToc 用 classList.toggle 而非赋值
    record("D4-setToc 用 classList.toggle",
           "classList.toggle('toc-collapsed'" in html, "")
    # C2: 字号控件
    has_slider = 'type="range"' in html and 'id="fpSize"' in html
    has_preset = html.count('data-size=') >= 3
    record("C2-字号滑块+预设", has_slider and has_preset,
           "slider=%s presets=%s" % (has_slider, has_preset))
    # C2: 可调小（min <= 13）
    m = re.search(r'id="fpSize"[^>]*min="(\d+)"', html)
    record("C2-字号可调小(min<=13)", bool(m) and int(m.group(1)) <= 13,
           m.group(1) if m else "no min")
    # C3: 字体切换 + 回退链
    fonts = len(re.findall(r'data-font="', html))
    record("C3-中文字体可切换(>=3)", fonts >= 3, "%d 种" % fonts)
    record("C3-含思源宋体", "Noto Serif SC" in html, "")
    # C4: sticky header anchor offset
    record("C4-html 有 scroll-padding-top", "scroll-padding-top" in html, "")
    record("C4-JS 实测 header 高度设 offset",
           "syncAnchorOffset" in html
           and "getBoundingClientRect().height" in html
           and "setProperty('--anchor-offset'" in html, "")


# ---------- D. 质量层 ----------
def check_quality(html, outdir):
    # D1: caption 翻译 —— figure figcaption 中应含中文
    caps = re.findall(r"<figcaption>(.*?)</figcaption>", html, re.S)
    zh_caps = sum(1 for c in caps if re.search(r"[\u4e00-\u9fff]", c))
    record("D1-图内caption有中文", len(caps) > 0 and zh_caps > 0,
           "%d/%d 含中文" % (zh_caps, len(caps)))
    # 独立 caption 段落：Figure/Table 开头的中英对照（至少存在中文"图/表"字样）
    record("D1-中文图表caption存在",
           bool(re.search(r"(图|表)\s*[A-Z]?\d+\s*[:：]", html)), "")
    # D2: 引用零死链
    cited = set(re.findall(r'data-ref="ref-(\d+)"', html))
    anchors = set(re.findall(r"id='ref-(\d+)'", html)) | set(re.findall(r'id="ref-(\d+)"', html))
    dead = cited - anchors
    record("D2-引用零死链", bool(cited) and not dead,
           "引用%d 锚点%d 死链%s" % (len(cited), len(anchors), sorted(dead)[:10]))
    # D3: 图片引用完整
    refs = set(re.findall(r'src="(images/[^"]+)"', html))
    missing = [r for r in refs if not os.path.exists(os.path.join(outdir, r))]
    record("D3-图片引用全部存在", bool(refs) and not missing,
           "引用%d 缺失%s" % (len(refs), missing[:3]))
    # 表格与 rowspan
    tables = html.count("<table")
    record("B1-成品含表格", tables > 0, "%d 个" % tables)
    if "LATS (GPT-4)" in html:  # 示例论文的已知重建表
        record("B1-TableA1重建含rowspan", "rowspan=" in html, "")


def main():
    global WORKDIR
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    WORKDIR = os.path.abspath(sys.argv[1])
    strict = "--strict" in sys.argv
    print("=== PDF→Bilingual HTML 门禁 ===\nworkdir:", WORKDIR)
    check_env_contract()
    md_text = check_fullmd()
    html_path = find_html(WORKDIR)
    record("D-找到双语HTML", bool(html_path), html_path or "未找到")
    if html_path:
        html = open(html_path, encoding="utf-8").read()
        outdir = os.path.dirname(html_path)
        check_html_structure(html)
        check_numbered_lists(md_text, html)
        check_interaction(html)
        check_quality(html, outdir)
    print()
    failed = 0
    for r in RESULTS:
        mark = "PASS" if r["ok"] else "FAIL"
        if not r["ok"]:
            failed += 1
        print("%-4s | %-40s | %s" % (mark, r["name"], r["detail"]))
    print("\nTOTAL: %d/%d PASS" % (len(RESULTS) - failed, len(RESULTS)))
    if strict and failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

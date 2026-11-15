#!/usr/bin/env python3
"""Render references/rules.md from the rule registry.

The registry is the single source of truth for which rules exist; the code is the
single source of truth for whether they pass. This script merges the two so the
markdown can never drift from either. CI re-renders and compares.
"""
import argparse
import json
import sys
from pathlib import Path

from ci_check import FIX

LEVEL_DOC = {
    "L0": "平台事实（微信编辑器行为，永不豁免）",
    "L1": "结构契约（成稿形态，可豁免但须人签字）",
    "L2": "可计量启发式（阈值，来自实测或反馈，定期复审）",
    "L3": "口径意图（由人在 S0-B 决定，不入自动判定）",
    "L4": "元规则（关于规则本身的规则）",
}

ENFORCED_BY = {
    "S": "`validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞）",
    "C": "`validate_article.py`（CI 门禁内容级，`--strict` 下阻塞）",
    "F": "`render_figures.py`（渲染前拦截，不通过不出图）",
}


def enforced(rule):
    if rule.get("enforced_by"):
        return rule["enforced_by"]
    return ENFORCED_BY.get(rule["id"][:1], "见脚本提示")


def render(registry):
    rules = sorted(registry["rules"], key=lambda r: (r["id"][0], r["id"]))
    out = [
        "# 规则清单",
        "",
        "> 本文件由 `scripts/render_rules_doc.py` 从 `assets/rule-registry.json` 生成，",
        "> 不要手改。改规则请改注册表或代码，然后重跑生成脚本；`ci_check.py` 会比对两者是否一致。",
        "",
        f"共 {len(rules)} 条。规则分五层，层级决定它能不能被豁免：",
        "",
    ]
    for lv, desc in LEVEL_DOC.items():
        out.append(f"- **{lv}** {desc}")
    out += ["", "| ID | 层级 | 要求 | 不满足时怎么改 | 执行位置 |", "|---|---|---|---|---|"]
    for r in rules:
        fix = r.get("fix") or FIX.get(r["id"], "见脚本输出的定位信息")
        title = r["title"].replace("|", "\\|")
        out.append(f"| {r['id']} | {r['level']} | {title} | {fix} | {enforced(r)} |")
    out += ["", "## 待复审", ""]
    prov = [r for r in rules if r.get("provisional")]
    if prov:
        out.append("以下规则来自单次反馈，尚未第二次验证；复审前不作为永久依据：")
        out.append("")
        for r in prov:
            out.append(f"- **{r['id']}** {r['title']}（{r.get('derived_from_feedback', '待补来源')}）")
    else:
        out.append("无。")
    out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="", help="rule-registry.json")
    ap.add_argument("--out", default="", help="rules.md path")
    ap.add_argument("--check", action="store_true", help="compare only, do not write")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    reg_path = Path(args.registry) if args.registry else root / "assets" / "rule-registry.json"
    out_path = Path(args.out) if args.out else root / "references" / "rules.md"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    text = render(reg)

    if args.check:
        current = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if current.strip() != text.strip():
            print(f"DRIFT: {out_path} 与注册表不一致，重跑 render_rules_doc.py", file=sys.stderr)
            return 1
        print(f"rules.md 与注册表一致（{len(reg['rules'])} 条）")
        return 0

    out_path.write_text(text, encoding="utf-8")
    print(f"wrote {out_path} ({len(reg['rules'])} rules)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

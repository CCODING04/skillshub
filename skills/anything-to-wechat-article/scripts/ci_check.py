#!/usr/bin/env python3
"""CI gate: strict lint + rule governance, emits ci-report.json.

Exit 0 = PASS, 1 = FAIL, 2 = NEEDS_DECISION (rule conflict, human must arbitrate),
3 = input/registry error. A failing or undecided gate means: DO NOT DELIVER.
"""
import argparse
import json
import sys
from pathlib import Path

from validate_article import run_validation
from check_rules import run_governance

FIX = {
    "S01": "移除 <style> 标签，全部样式写成内联 style",
    "S02": "移除 class，改用内联 style",
    "S03": "替换 section/figure/figcaption/script 等微信不保留的标签",
    "S04": "只使用白名单标签（div/p/img/strong/h1/br/blockquote/span 等）",
    "S05": "去掉外链 CSS/字体/JS，图片改 base64 内嵌",
    "S06": "用组件级内联样式，不要只给最外层容器一个 style",
    "S07": "至少生成一张自制信息图",
    "S08": "图片数必须与 base64 内嵌数一致",
    "S09": "检查 figures 清单与实际图片数",
    "S10": "给每个 img 的 style 补 width:100%",
    "S11": "至少保留一处金句引用块",
    "S12": "替换所有 {{...}} 占位符",
    "S13": "补「资料来源与整理说明」",
    "S14": "给每个 p/div/blockquote/h1/span/strong 补内联 style",
    "S15": "用 <p> 分段，不要用连续 <br> 堆排版",
    "S16": "给每张图补 alt 文本",
    "S17": "用 render_figures.py 以 --scale 2 重新渲染配图",
    "S18": "每张图后紧跟一个图注 <p>（含「图 N ｜…」或「封面…」）",
    "S19": "去掉连续 <br>",
    "S20": "删掉正文里的内部流程词（S0-A / feasibility / base64 / content.json 等）",
    "S21": "正文过短，检查 IR 是否漏了 sections",
    "C01": "开头补作者/讲者的公开履历引子，并明确标注与正文来源分开",
    "C02": "外文术语首次出现补中文简注，如 PR（代码合并请求）、lint（静态检查规则）",
    "C03": "文末来源说明保持 2–6 条，含来源标识与书面化/非逐字声明",
    "C04": "在 content.json 写 process_appendix，让 article.md 带上「整理过程与回溯」",
    "C05": "把内部口径移到 Markdown 附录，不要放读者可见的信息卡",
}


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="dist/wechat-article.html")
    ap.add_argument("--md", default="", help="Markdown archive (auto-detected next to HTML if omitted)")
    ap.add_argument("--ir", default="", help="content.json (talk detection + auto task-meta)")
    ap.add_argument("--out", default="", help="report directory (defaults to HTML directory)")
    ap.add_argument("--expect-figures", type=int, default=0)
    ap.add_argument("--config", default="", help="JSON thresholds override")
    ap.add_argument("--no-strict", action="store_true", help="warnings do not block (not recommended)")
    ap.add_argument("--registry", default="", help="rule registry (defaults to skill assets)")
    ap.add_argument("--theme", default="ink-tangerine", help="theme id chosen in S0-B")
    ap.add_argument("--theme-confirmed-by", default="", help="human who approved the theme (Step 0)")
    ap.add_argument("--task-meta", default="", help="JSON describing this task (source_kind, explicit_instructions)")
    ap.add_argument("--waivers", default="", help="human-signed waivers.json")
    ap.add_argument("--golden", default="", help="JSON with passed_rules of the accepted paradigm article")
    ap.add_argument("--ack-conflicts", default="", help="HUMAN-WRITTEN decision file; the model must not create it")
    ap.add_argument("--no-governance", action="store_true", help="skip rule governance (not recommended)")
    args = ap.parse_args()

    html = Path(args.html)
    if not html.exists():
        print(json.dumps({"error": "html not found", "path": str(html)}, ensure_ascii=False))
        return 3
    md = Path(args.md) if args.md else html.parent / "article.md"
    out_dir = Path(args.out) if args.out else html.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else None
    registry = Path(args.registry) if args.registry else \
        Path(__file__).resolve().parent.parent / "assets" / "rule-registry.json"

    theme_id = args.theme or "ink-tangerine"
    report = run_validation(
        str(html), expect_figures=args.expect_figures, strict=not args.no_strict,
        md_path=str(md) if md.exists() else None, ir_path=args.ir or None,
        config=cfg, rules_out=str(out_dir / "lint-report.json"),
        style_id=theme_id,
    )

    # --- N6: theme schema / placeholders / contrast gate ---
    import subprocess as _sp
    theme_check = {"valid": True, "note": "skipped"}
    checker = Path(__file__).with_name("check_themes.py")
    if checker.exists():
        _r = _sp.run([sys.executable, str(checker), "--skill-root", str(Path(__file__).resolve().parent.parent),
                      "--out", str(out_dir / "theme-report.json")], capture_output=True, text=True)
        theme_check = {"valid": _r.returncode == 0, "report": str(out_dir / "theme-report.json")}
        if _r.returncode != 0:
            print("THEME CHECK FAILED (see theme-report.json)", file=sys.stderr)

    # --- rule governance: detect conflicts BEFORE deciding pass/fail ---
    task_meta_path = args.task_meta
    if not task_meta_path and args.ir and Path(args.ir).exists():
        ir = json.loads(Path(args.ir).read_text(encoding="utf-8"))
        auto = {"source_kind": ir.get("source", {}).get("kind", "unknown"),
                "target": "wechat-html", "explicit_instructions": [],
                "theme": theme_id, "theme_confirmed_by": args.theme_confirmed_by or None}
        task_meta_path = str(out_dir / "task-meta.json")
        write_json(task_meta_path, auto)

    gov, review, gov_code = (None, None, 0)
    if not args.no_governance and registry.exists():
        gov, review, gov_code = run_governance(
            registry_path=str(registry), task_meta=task_meta_path or None,
            lint_report=report, waivers=args.waivers or None,
            golden=args.golden or None, out_dir=str(out_dir))
    if gov_code == 1:
        print("REGISTRY ERROR:", (gov or {}).get("details") or (gov or {}).get("error"), file=sys.stderr)
        return 3

    ack = None
    if args.ack_conflicts:
        p = Path(args.ack_conflicts)
        if not p.exists():
            print("ack file not found:", p, file=sys.stderr)
            return 3
        ack = json.loads(p.read_text(encoding="utf-8"))
        if not ack.get("approved_by") or not ack.get("decision"):
            print("确认文件必须由人填写 approved_by 与 decision；模型不得代填", file=sys.stderr)
            return 3

    needs = bool(gov and gov.get("needs_decision"))
    conflicts = (gov or {}).get("conflicts", [])
    governance = {
        "registry": str(registry.resolve()),
        "needs_decision": needs,
        "conflicts": [c["type"] + ":" + c["rule_id"] for c in conflicts],
        "provisional_rules": (gov or {}).get("provisional_rules", []),
        "acknowledged_by_human": bool(ack),
        "decision_owner": "human",
        "theme": {"id": theme_id, "confirmed_by": args.theme_confirmed_by or None},
    }

    if needs and not ack:
        ci = {
            "gate": "NEEDS_DECISION", "strict": not args.no_strict,
            "theme_check": theme_check,
            "article": str(html.resolve()), "governance": governance,
            "conflict_report": str(out_dir / "conflict-report.json"),
            "lint_gate": report["summary"]["gate"],
            "note": "规则与本次任务存在冲突，先由人裁决，再判断 PASS/FAIL；模型不裁决。",
        }
        write_json(out_dir / "ci-report.json", ci)
        print("CI GATE: NEEDS_DECISION | conflicts:", governance["conflicts"])
        for c in conflicts:
            print(f"  {c['type']} {c['rule_id']}: {c['evidence']}")
            for o in c["options"]:
                print(f"     {o['id']}. {o['action']} — {o['pros']}")
        print("decision_owner: human | report:", out_dir / "conflict-report.json")
        return 2

    failed = [r for r in report.get("rules", []) if not r["passed"]]
    ci = {
        "gate": ("FAIL" if not theme_check["valid"] else report["summary"]["gate"]),
        "theme_check": theme_check,
        "strict": not args.no_strict,
        "article": str(html.resolve()),
        "markdown": str(md.resolve()) if md.exists() else None,
        "rules_total": report["summary"]["rules_total"],
        "rules_passed": report["summary"]["rules_passed"],
        "error_failures": report["summary"]["error_failures"],
        "warning_failures": report["summary"]["warning_failures"],
        "failed_rules": [{"id": r["id"], "level": r["level"], "message": r["message"],
                          "actual": r["actual"], "how_to_fix": FIX.get(r["id"], "见 references/lint-rules.md")}
                         for r in failed],
        "governance": governance,
        "stats": report["stats"],
    }
    if ack:
        ci["human_decision"] = {"approved_by": ack.get("approved_by"),
                                "decision": ack.get("decision"), "note": ack.get("note", "")}
    write_json(out_dir / "ci-report.json", ci)
    print("CI GATE:", ci["gate"], "| rules passed:", ci["rules_passed"], "/", ci["rules_total"])
    print("errors:", ci["error_failures"] or "none", "| warnings:", ci["warning_failures"] or "none")
    print("governance:", governance["conflicts"] or "no conflict",
          "| provisional:", ",".join(governance["provisional_rules"]))
    for r in ci["failed_rules"]:
        print(f"  [{r['level']:7}] {r['id']}  {r['message']}")
        print(f"            -> {r['how_to_fix']}")
    print("report:", out_dir / "ci-report.json")
    return 0 if ci["gate"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

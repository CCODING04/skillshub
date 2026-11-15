#!/usr/bin/env python3
"""Rule governance: validate the registry and detect rule/task conflicts.

It NEVER decides. It emits conflict-report.json for a human to arbitrate.
Exit 0 = no conflict, 2 = needs human decision, 1 = registry error.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

LEVELS = {"L0", "L1", "L2"}
REQUIRED = ["id", "level", "title", "source", "scope", "review_after_days",
            "waiver_allowed", "provisional"]

OPTIONS = {
    "scope_mismatch": [
        {"id": "A", "action": "本次豁免该规则", "pros": "不把别类来源的约定硬套到本次", "cons": "本次可能缺少该规则保障的内容"},
        {"id": "B", "action": "把规则 scope 扩到本次来源类型", "pros": "规则更通用", "cons": "等于把单次偏好推广，需人确认是长期约定"},
        {"id": "C", "action": "维持规则，按规则补内容", "pros": "符合当前门禁", "cons": "可能不是本次想要的成稿形态"},
    ],
    "explicit_override": [
        {"id": "A", "action": "按用户本次指令豁免规则", "pros": "人的最新指令优先", "cons": "本次不受该规则约束"},
        {"id": "B", "action": "修订规则以容纳该指令", "pros": "规则与口径对齐", "cons": "需人确认长期生效"},
        {"id": "C", "action": "请用户澄清指令与规则的优先级", "pros": "避免误判", "cons": "需要多一轮交互"},
    ],
    "stale_fact": [
        {"id": "A", "action": "重新实测平台事实并更新 verified_at", "pros": "恢复规则可信度", "cons": "需一次实测"},
        {"id": "B", "action": "临时降级为 warning", "pros": "不阻塞交付", "cons": "规则暂时失去强制力"},
    ],
    "rule_id_drift": [
        {"id": "A", "action": "同步注册表与代码规则 id", "pros": "恢复一致性", "cons": "需确认哪边是准"},
    ],
    "repeated_waiver": [
        {"id": "A", "action": "把该规则降级或废止", "pros": "不再反复制造噪音", "cons": "失去该检查"},
        {"id": "B", "action": "保留但重写 scope/阈值", "pros": "保留意图、修正适用性", "cons": "需重新验证"},
    ],
    "paradigm_regression": [
        {"id": "A", "action": "修正新规则，重跑范式基线", "pros": "防止规则漂移", "cons": "需改代码"},
        {"id": "B", "action": "由人确认范式稿已过时并更新 golden", "pros": "承认范式演进", "cons": "旧基线失效"},
    ],
    "theme_preset_mismatch": [
        {"id": "A", "action": "以人选择的风格重建文章", "pros": "成稿与口径一致", "cons": "需重新生成"},
        {"id": "B", "action": "由人确认改用生成时的风格", "pros": "少一次重建", "cons": "需人改口"},
    ],
}


def days_since(value):
    try:
        return (date.today() - date.fromisoformat(value)).days
    except Exception:
        return 0


def load(path, default):
    if not path:
        return default
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def validate_registry(reg):
    errors = []
    rules = reg.get("rules", [])
    ids = [r.get("id", "?") for r in rules]
    if len(ids) != len(set(ids)):
        errors.append("duplicate rule ids")
    for r in rules:
        rid = r.get("id", "?")
        for k in REQUIRED:
            if k not in r:
                errors.append(f"{rid}: missing {k}")
        if r.get("level") not in LEVELS:
            errors.append(f"{rid}: invalid level {r.get('level')}")
        if r.get("level") == "L0" and r.get("waiver_allowed"):
            errors.append(f"{rid}: L0 rules must not allow waiver")
        if r.get("provisional") and not r.get("derived_from_feedback"):
            errors.append(f"{rid}: provisional rules require derived_from_feedback")
        src = r.get("source", {})
        if src.get("type") == "platform_fact" and not src.get("verified_at"):
            errors.append(f"{rid}: platform_fact requires verified_at")
    return errors, set(ids)


def conflict(kind, rule_id, level, evidence, impact, recommendation=None):
    return {
        "type": kind, "rule_id": rule_id, "level": level,
        "evidence": evidence, "impact": impact,
        "options": OPTIONS.get(kind, []),
        "recommendation": recommendation,
        "decision_owner": "human",
    }


def run_governance(*, registry_path, task_meta=None, lint_report=None,
                   waivers=None, golden=None, out_dir=None):
    reg = load(registry_path, None)
    if not reg:
        return {"error": "registry not found", "path": str(registry_path)}, None, 1
    errors, reg_ids = validate_registry(reg)
    if errors:
        return {"error": "invalid registry", "details": errors}, None, 1

    rules = reg["rules"]
    by_id = {r["id"]: r for r in rules}
    task = load(task_meta, {}) if isinstance(task_meta, str) else (task_meta or {})
    lint = load(lint_report, None) if isinstance(lint_report, str) else lint_report
    waiver_list = load(waivers, []) if isinstance(waivers, str) else (waivers or [])
    gold = load(golden, None) if isinstance(golden, str) else golden

    kind = task.get("source_kind")
    instructions = task.get("explicit_instructions", []) or []
    conflicts = []

    if kind:
        for r in rules:
            scope = r.get("scope", {}).get("source_kinds", ["*"])
            if "*" not in scope and kind not in scope:
                conflicts.append(conflict(
                    "scope_mismatch", r["id"], r["level"],
                    f"规则 {r['id']} scope={scope}，本次 source_kind={kind}",
                    f"「{r['title']}」源自别的来源类型，本次是否适用需人确认",
                    "A（依据：本次来源类型不在规则适用范围）"))

    for r in rules:
        for kw in r.get("conflict_keywords", []):
            if any(kw in str(ins) for ins in instructions):
                conflicts.append(conflict(
                    "explicit_override", r["id"], r["level"],
                    f"用户本次指令命中冲突关键词「{kw}」",
                    f"最新人的指令与规则「{r['title']}」相悖，须以人为准或请人澄清",
                    "A（依据：人的最新指令优先于既有规则）"))
                break

    for r in rules:
        src = r.get("source", {})
        if src.get("type") == "platform_fact":
            age = days_since(src.get("verified_at", ""))
            if age > r.get("review_after_days", 180):
                conflicts.append(conflict(
                    "stale_fact", r["id"], r["level"],
                    f"平台事实距上次核验 {age} 天，超过 {r.get('review_after_days')} 天",
                    "平台可能已改版，规则依据需要重新实测",
                    "A（依据：事实类规则必须重新核验）"))

    waiver_counts = Counter(w.get("rule_id") for w in waiver_list)
    for rid, n in waiver_counts.items():
        if n >= 3:
            conflicts.append(conflict(
                "repeated_waiver", rid, by_id.get(rid, {}).get("level", "L2"),
                f"该规则已被豁免 {n} 次",
                "反复豁免通常说明这条其实是偏好，而非普适规则",
                "A（依据：降低噪音，交人决定是否废止）"))

    if lint:
        code_ids = {r["id"] for r in lint.get("rules", [])}
        # 图内文字类规则（F*）在渲染前执行，不在文章 HTML 的 lint 报告里，
        # 但它们同样是可判定规则，必须计入一致性比对，否则每次都被误判成漂移。
        try:
            from render_figures import RULE_IDS as FIGURE_RULE_IDS
            code_ids |= set(FIGURE_RULE_IDS)
        except Exception:
            pass
        missing, extra = sorted(reg_ids - code_ids), sorted(code_ids - reg_ids)
        if missing or extra:
            conflicts.append(conflict(
                "rule_id_drift", "-", "L4",
                f"注册表独有={missing}；代码独有={extra}",
                "代码与治理注册表漂移，规则无法被审查",
                "A（依据：两者必须一致）"))

    lint_theme = (lint or {}).get("theme", {}).get("id") if lint else None
    task_theme = task.get("theme")
    if task_theme and lint_theme and task_theme != lint_theme:
        conflicts.append(conflict(
            "theme_preset_mismatch", "-", "L4",
            f"人选择的风格={task_theme}，但生成/校验用的风格={lint_theme}",
            "成稿风格与人的决定不一致，校验结果不可信",
            "A（依据：以人拍板的风格为准）"))

    review = {
        "registry_updated_at": reg.get("updated_at"),
        "registry_rules": len(rules),
        "theme_used": lint_theme or task_theme,
        "theme_pending_confirmation": bool(task_theme and not task.get("theme_confirmed_by")),
        "theme_scoped_rules": (lint or {}).get("theme", {}).get("scoped_rules", []),
        "provisional_rules": [r["id"] for r in rules if r.get("provisional")],
        "provisional_note": "源自单次用户反馈，需第二次验证；每次 CI 列出，不自动升级为永久规则",
        "waiver_counts": dict(waiver_counts),
        "stale_platform_facts": [c["rule_id"] for c in conflicts if c["type"] == "stale_fact"],
        "triggered_rules": [r["id"] for r in (lint or {}).get("rules", []) if not r.get("passed")],
        "paradigm_regression": [],
    }

    if gold and lint:
        was = set(gold.get("passed_rules", []))
        now_failed = {r["id"] for r in lint.get("rules", []) if not r.get("passed")}
        regressed = sorted(was & now_failed)
        review["paradigm_regression"] = regressed
        if regressed:
            conflicts.append(conflict(
                "paradigm_regression", ",".join(regressed), "L4",
                f"已验收范式稿在新规则下不再通过：{regressed}",
                "规则变更可能破坏了既有合格范式",
                "A（依据：先修规则再交付）"))

    report = {
        "needs_decision": bool(conflicts),
        "generated_at": date.today().isoformat(),
        "task": task,
        "conflicts": conflicts,
        "provisional_rules": review["provisional_rules"],
        "rule_review": "rule-review.json",
        "note": "模型不裁决。请人选择 A/B/C 或给出其它决定；确认后由人写 waivers.json / ack 文件。",
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "conflict-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / "rule-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report, review, 2 if conflicts else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--task-meta", default="")
    ap.add_argument("--lint-report", default="")
    ap.add_argument("--waivers", default="")
    ap.add_argument("--golden", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    report, review, code = run_governance(
        registry_path=args.registry, task_meta=args.task_meta or None,
        lint_report=args.lint_report or None, waivers=args.waivers or None,
        golden=args.golden or None, out_dir=args.out or None)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if code == 2:
        print("NEEDS HUMAN DECISION:", [c["type"] + ":" + c["rule_id"] for c in report["conflicts"]], file=sys.stderr)
    elif code == 1:
        print("REGISTRY ERROR:", report.get("details") or report.get("error"), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())

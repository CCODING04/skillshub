# 规则治理：什么能固化，什么不能

## 问题的形状

规则不能因为来自一次判断就变成永久真理。需要审查机制判断当前任务与既有规则是否冲突，冲突时及时汇报交人处理；但「要有思考过程」太模糊，需要尽量把能固化的固化下来。

关键判断：**「思考过程」的聪明程度不可固化，但「什么信号出现时必须停下」「汇报长什么样」「谁有权裁决」可以。**

把模糊的"审查机制"拆成三件可判定的事：

1. **信号**：列出可计算的触发条件（scope 不匹配、用户明确指令相悖、事实过期、规则漂移、反复豁免、范式回归）。
2. **汇报**：固定 `conflict-report.json` 结构，含证据、影响、候选动作与依据。
3. **裁决归属**：`decision_owner: human`。模型不自动豁免、不自动改规则、不静默跳过。

于是 L3（口径/意图）**不能固化成答案，但能固化成「必须停下来问」这个动作**——这是把模糊变清晰的钥匙。

## 五层模型

| 层 | 内容 | 能否固化 | 变更条件 | 可豁免 | 例子 |
|---|---|---|---|---|---|
| **L0 平台事实** | 目标平台的物理限制 | **完全固化，永不可豁免** | 平台改版，需重新实测 | 否 | 微信过滤 `<style>` / class；SVG 不可粘贴 |
| **L1 结构契约** | 输出格式、流程顺序、校验项 | **固化，变更需版本化 + 回归测试** | 范式升级并经人确认 | 否（可修订） | 全内联样式、图片双轨、S5 门禁 |
| **L2 可计量启发式** | 阈值与下限 | **数值可固化，适用性须人确认** | 复审 / 用户新口径 | 是，需签字 | 术语简注 ≥8、讲者引子、正文 ≥1500 |
| **L3 口径意图** | 主题、什么算对、偏好 | **不可固化成答案**；只能固化「必须询问」 | 每次任务由人定 | 不适用 | 是否发布、是否精简、采用哪个口径 |
| **L4 元规则** | 规则如何演进、冲突如何处理 | **可固化**：信号、汇报格式、裁决归属、复审触发 | 人确认 | 不适用 | 本文 + `rule-registry.json` + `check_rules.py` |

## 可固化边界（具体清单）

**能固化**

- 平台物理约束与输出结构契约（L0/L1）。
- 流程顺序：S0-A 调研 → S0-B 决策 → S1–S5 → CI 门禁。
- 可计量下限**及其检测方式**（不是"8 这个数天然正确"，而是"当前约定 8，并定期复审"）。
- 冲突信号清单（下表 7 条）。
- 汇报结构、豁免记录结构、复审触发条件。
- 规则注册表 schema 与「代码规则 id 必须和注册表对齐」这条校验。

**不能固化**

- 什么算好、主题、立场、口径、是否发布、是否精简。
- 冲突发生时选 A/B/C 的裁决。
- 某条规则是否该废止、是否该永久豁免。
- 启发式阈值的"正确性"——只能固化数值 + 复审周期 + 来源标记。

**半固化（最易出错的一层）**

来自**单次用户反馈**的规则（本 skill 的 C01 讲者引子、C02 术语简注正是这类）必须：

- 标 `provisional: true` 与 `derived_from_feedback`（哪一次反馈、原话）；
- 设较短 `review_after_days`（默认 30）；
- 每次 CI 在 `rule-review.json` 里显式提示「源自单次反馈，需第二次验证」；
- 换一类源（如 X 长文 vs 演讲视频）时由 `scope_mismatch` 信号提示人确认是否适用。

这样规则仍在，但**不再假装自己是永恒真理**。

## 冲突信号（可判定）

| 信号 | 判定条件 | 默认动作 |
|---|---|---|
| `scope_mismatch` | 规则 `scope.source_kinds` 不含本次 `task_meta.source_kind` | 汇报；不自动套用 |
| `explicit_override` | 用户本次明确指令命中规则 `conflict_keywords` | 汇报，最高优先；不自动覆盖 |
| `stale_fact` | `source.type = platform_fact` 且 `verified_at` 超过 `review_after_days` | 汇报，建议重新实测 |
| `rule_id_drift` | 代码里的规则 id 集合 ≠ 注册表 id 集合 | 阻塞；注册表与代码必须一致 |
| `repeated_waiver` | 同一规则被豁免 ≥3 次 | 汇报：该规则可能其实是偏好，应降级/废止 |
| `paradigm_regression` | 本次主题有 golden 范式稿，且其中通过的规则在新一轮失败 | 阻塞；先修规则再交付 |
| `style_preset_mismatch` | 人选择的风格 ≠ 生成/校验时用的风格 | 置 `NEEDS_DECISION`，成稿与口径不一致 |
| `style_pending_confirmation` | 用了非默认风格但无 `style_confirmed_by` | 写进 `rule-review.json` 提示（不阻塞）；风格属意图层，须由人确认 |

检测不到「规则在语义上不合适」这种模糊情况；只能靠上述信号去逼近，误报由人裁定。

**两个提示型机制（不阻塞，不进 `conflicts`）**：

- `provisional` 复审：所有 `provisional: true` 的规则 id 每次 CI 写进 `rule-review.json` 的 `provisional_rules`，附一句"源自单次反馈，需第二次验证"。它由人读、由人决定是否升级；**不触发 `NEEDS_DECISION`，不阻塞交付**。代码里没有 `provisional_review` 这个冲突信号，不要按阻塞信号理解。
- golden 范式回归：按主题选择 `assets/goldens/<theme>.json`（`--golden` 显式指定时优先）。只有存在对应 golden 时才比对 `paradigm_regression`；**某主题尚无 golden 时跳过该比对，并在 `rule-review.json` / `ci-report.json` 里写明"skipped (not a failure)"**，绝不伪造一个基线。新增主题不必补齐 golden 才能交付。

## 冲突处理流程

```
check_rules.py → conflict-report.json → 停下来 → 人选择 A/B/C
  → 写 waivers.json（本次/永久，含 approved_by）或由人确认修订注册表
  → 重跑 ci_check.py → 仍不过则继续交人
```

`ci_check.py` 在有冲突时把门禁置为 **`NEEDS_DECISION`**（既不是 PASS 也不是 FAIL），退出码 2；只有读到人写的确认文件 `--ack-conflicts` 才继续执行。**模型不得自己生成这个确认文件**。

## 汇报结构

```json
{
  "needs_decision": true,
  "task": {"source_kind": "x-article", "target": "wechat-html"},
  "conflicts": [{
    "type": "scope_mismatch", "rule_id": "C01", "level": "L2",
    "evidence": "C01 scope = talk/interview；本次 source_kind = x-article",
    "impact": "按规则会要求补作者履历引子，但该规则源自演讲类反馈",
    "options": [
      {"id": "A", "action": "本次豁免 C01", "pros": "不硬套演讲类约定", "cons": "本次缺作者背景"},
      {"id": "B", "action": "把 scope 扩到 x-article", "pros": "规则更通用", "cons": "需人确认这是长期约定"},
      {"id": "C", "action": "按规则补作者履历引子", "pros": "符合当前门禁", "cons": "可能不是本次想要的开篇"}
    ],
    "recommendation": "A（依据：本次为 X 长文，非演讲）",
    "decision_owner": "human"
  }],
  "provisional_rules": ["C01", "C02"],
  "rule_review": "rule-review.json"
}
```

推荐可以给，但 `decision_owner` 永远是人。

## 豁免机制

`waivers.json` 每条必须含：`rule_id`、`reason`、`scope`（`once` / `permanent`）、`approved_by`、`approved_at`、`expires`（永久豁免也要设复审日）。CI 在报告里显式列出 `waived_rules`，**不允许静默跳过**。`L0` 规则 `waiver_allowed: false`，注册表校验会拒绝。

## 复审机制

每次 CI 生成 `rule-review.json`：本次触发的规则、从未触发的规则、被豁免次数、stale 事实、provisional 清单、范式回归结果。触发人工复审的条件：时间到期 / 同规则豁免 ≥3 次 / 出现 `paradigm_regression` / 用户提出新口径。

## 规则变更流程

提议（含依据）→ **人确认** → 改 `rule-registry.json` → 跑基线回归→ 记录版本 → 更新 SKILL.md。不允许因为"这次跑不过"就直接调低阈值或删规则。

## 边界

这套机制能固化"何时停下、如何汇报、谁裁决"，不能固化"判断得对不对"。它把「上一回的偏好」从隐含的硬编码，变成**带来源、带范围、带有效期、可被质疑、由人裁决**的显式对象——这才是"不固化成永远正确"的工程含义。

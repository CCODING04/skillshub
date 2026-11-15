# S0-A 可行性调研规范（未知源先查再问）

## 为什么是「调研」，不是「猜」

| 行为 | 依据 | 结果 | 允许 |
|---|---|---|---|
| 猜测 | 模型先验 | 一个看起来合理的方案 | ❌ 不可靠，还会锚定用户判断 |
| 空手问 | 无 | 把负担丢给用户 | ❌ 用户没有足够信息做选择 |
| **调研** | 只读探测 + 当前网络检索 + 已有知识（标注过时风险） | **≥2 条候选路径 + 代价 + 回退** | ✅ 模型负责 |
| 决定 | 用户意图 | 选哪条、什么算对 | ✅ 只有人负责 |

原则：模型把事做到「有依据的方案」为止，**不越界到拍板**。调研做得越扎实，用户那一次选择越轻松、越准。

## 触发条件

- `source-adapters.md` 未列出的源；
- 已知渠道但环境可能变化（接口改版、域名被拦、许可调整）；
- 已有知识涉及时效性事实（平台规则、模型版本、API 形态）；
- 用户描述的源含糊（「这个网站上的东西」「那段语音」）。

## 调研五步

1. **只读探测**：`python scripts/probe_source.py --target <URL或路径> --out probe.json`。只做 HEAD / 类型识别 / 本地文件检查；不下载正文、不登录、不消耗积分。
2. **识别源类型**：URL 域名与路径特征、扩展名、content-type、本地文件魔数 → 归入已知适配器或标记 `unknown`。
3. **核实当下知识**：用 WebSearch / domain_search 查公开接口、镜像 API、格式与许可限制、已知故障、社区近期做法。**已有知识只当假设**，检索结果要带来源与日期；查不到就写「未找到可靠依据」。
4. **形成方案**：写 `feasibility.json`，至少 2 条候选路径，每条给工具、凭据、成本、风险、失败回退、置信度。
5. **带方案提问**：S0-B 把方案与决定项一起交给人，不先执行。

## probe.json（脚本产出，客观事实）

```json
{
  "target": "https://example.com/item/123",
  "kind": "url",
  "host": "example.com",
  "suffix": "",
  "http_status": 200,
  "content_type": "text/html; charset=utf-8",
  "content_length": null,
  "reachable_default": true,
  "reachable_custom_proxy": null,
  "local_file": null,
  "suggested_tools": ["WebFetch", "curl"],
  "notes": ["只读探测，未下载正文"]
}
```

## feasibility.json（模型产出，方案与判断）

```json
{
  "source": "https://example.com/item/123",
  "probed_at": "2026-11-12",
  "known_adapter": false,
  "confidence": "medium",
  "evidence": [
    {"claim": "该站有公开 JSON 接口", "source": "检索结果 URL", "date": "2026-11-12", "verified": false},
    {"claim": "默认代理对该域 502", "source": "probe.json", "date": "2026-11-12", "verified": true}
  ],
  "candidates": [
    {
      "id": "A",
      "path": "公开接口取正文 → 规范化为 IR",
      "tools": ["curl", "JSON 解析"],
      "credentials": "无",
      "cost": "低，约几十 KB",
      "risks": ["接口可能改版", "字段可能缺作者"],
      "fallback": "退回网页正文提取",
      "confidence": "medium"
    },
    {
      "id": "B",
      "path": "网页正文提取 → 去导航与广告 → 规范化为 IR",
      "tools": ["WebFetch"],
      "credentials": "无",
      "cost": "低",
      "risks": ["动态渲染可能取不到正文", "需人工核对作者与日期"],
      "fallback": "请用户提供原文粘贴或截图 OCR",
      "confidence": "high"
    }
  ],
  "adapter_draft": {
    "kind": "example-web",
    "extract": ["..."],
    "normalize_to": "content.json",
    "compliance_checks": ["核对作者与日期", "注明来源链接"],
    "status": "draft-not-executed"
  },
  "open_questions_for_user": [
    "走 A 还是 B？",
    "若正文取不全，是否允许改用你提供的原文？",
    "口径与篇幅按哪种？"
  ]
}
```

## 置信度与措辞

| 等级 | 含义 | 允许的说法 |
|---|---|---|
| `high` | 本机只读探测通过 + 有当前公开依据 | 「已探测可达；按公开文档路径 A 可行（尚未实跑全文）」 |
| `medium` | 有依据但未验证 | 「据检索到的做法，路径 A 可能可行，需要试跑确认」 |
| `low` | 只有推断 | 「未找到可靠依据，以下是待验证假设」 |

**禁止**把 `draft-not-executed` 说成「已支持该渠道」；禁止把检索摘要当成亲自验证；禁止省略 `evidence` 的日期与来源。

## 调研边界（红线）

- 只读：不下载 GB 级内容、不登录、不提交表单、不消耗积分、不写入除 `probe.json` / `feasibility.json` / 适配器草稿文本以外的文件。
- 已有知识可能过时，涉及当下事实必须检索；检索结果也可能错，标注 `verified: false`。
- 合规与事实是硬规范，不因方案而改变：不编造来源身份、地域表述合规、缺失片段标注。
- 调研结束即停，等待 S0-B 拍板。**不得因为「方案看起来很明显」就直接执行。**

## 带方案提问模板

```
这个源我没做过，先查了一轮（只读探测 + 检索，未动正文）：
· 探测：example.com 返回 200，text/html，默认代理可达
· 依据：检索到该站有公开 JSON 接口（来源、日期）；接口是否仍有效未验证
· 方案 A：接口取正文，成本低，风险是接口改版 → 回退网页提取
· 方案 B：网页正文提取，稳但可能漏作者日期 → 回退请你贴原文
· 我的推荐：B（依据：无需依赖未验证接口），置信度 high
请你定：走哪条？口径/篇幅/交付按哪套？确认后我才开始采集。
```

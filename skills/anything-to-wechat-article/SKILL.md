---
name: anything-to-wechat-article
description: 把任意来源（X 推文与 X 长文、视频、网页、PDF、Word、Markdown、音频、播客、会议记录、截图或粘贴文本）整理成微信公众号排版文章，输出全内联 HTML、自制中文信息图、六套主题与自定义配色。用户说转成公众号文章、做一篇公众号、X 视频转文章、把材料写成公众号、anything to wechat，或只做排版、只做配图时使用。不用于其他平台；AI 插画需先说明积分并取得同意。
---

# Anything to WeChat Article

任意来源 → 可直接粘进公众号编辑器的成稿：全内联 HTML、自制中文信息图、独立 PNG、Markdown、来源说明。

## 三层结构

本 skill 的约束分三层承载，越靠下越硬。**改行为时先找最硬的能承载它的层**，不要退到描述层去讲。

| 层 | 位置 | 承载什么 | 谁判定 |
|---|---|---|---|
| **规则层** | `scripts/` | 可机器判定的约束：结构、标签、对比度、密度、图内文本、跨越门禁 | 脚本，CI 退出码 |
| **模板层** | `assets/themes/*/theme.json`、`assets/figure_types/` | 可结构化的约束：所有字号、间距、颜色、组件槽位、画布尺寸 | 主题即规格，改模板就是改版式 |
| **描述层** | 本文件、`references/` | 不可判定的部分：流程顺序、卡点、口径归属、渠道适配 | 人 |

规则层与模板层的清单见 [`references/rules.md`](./references/rules.md)（由注册表生成，勿手改）与 `assets/themes/`（槽位即规格）。

## 执行什么

| 阶段 | 动作 | 产物 |
|---|---|---|
| S0-A 调研 | 只读探测 + 检索当下做法 + 算各路径代价 | `probe.json`、`feasibility.json` |
| S0-B 决策 | 带方案提问，人拍板 | `content.json.decisions` |
| S0-C 规则治理 | 检测规则与本次任务的冲突 | `conflict-report.json`、`rule-review.json` |
| S1 采集 | 按适配器取文本 + 元数据 | 正文/转写 + 来源信息 |
| S2 规范化 | 写成 IR | `content.json` |
| S3 配图 | HTML/CSS 版式 → 2x PNG | `figures/*.png` |
| S4 排版 | 选定主题渲染 | `wechat-article.html` + `article.md` |
| S5 校验 | CI 门禁 + 首屏截图 | `valid=true` 的交付包 |

主链严格串行，上一步是下一步的输入。**S5 门禁不过、或出现 `NEEDS_DECISION`，不交付。**

## 谁决定什么

归属很硬：**「什么算对」永远由人定，模型只负责把已定的事做清楚。**

| # | 决定项 | 归属 |
|---|---|---|
| 1 | 主题／标题方向／立场口径；什么算「对」；谁验收 | **人，最高优先** |
| 2 | 忠实逐字稿 vs 结构重整；引语是否书面化；争议段落去留 | **人** |
| 3 | 来源范围：转哪部分、缺失片段怎么处理、是否多信源校对 | **人** |
| 4 | 提取路径、清晰度、代理、STT 后端、是否允许额外积分 | 人；模型给检测数据 |
| 5 | 篇幅、配图数量与图型、逐字稿／Markdown、是否发布 | **人** |
| 6 | 排版主题：六套内置任选，或给主色派生一套 | **人**；模型给清单与映射 |

**必须停下来问的五个硬条件**：源未收录或描述含糊；可行路径 ≥2 需要取舍；涉及成本（积分／付费 API／GB 级下载）；目标、口径、验收标准不明；风格偏好没有依据（主题、配色、篇幅、图型、是否发布）。

**问之前要做完**：只读探测、`detect_options.py` 环境检测、必要检索、各路径代价估算，并给出选项 + 依据 + 推荐。空手提问和信息不足时的猜测都不算调研。

有客观依据的技术项（如 ffmpeg 重采样 16 kHz 单声道）在人知情后直接执行，依据写进 `decisions`。

判断法：某个选择错了会让用户说「我不是这个意思」，它是意图，交人；错了只会让脚本报错或变慢，它是技术参数，可自动。

## S0 调研、决策与治理

### S0-A 调研（只读）

1. 识别源类型：已知渠道查 [`source-adapters.md`](./references/source-adapters.md)；未知渠道走下面的分支。
2. `scripts/probe_source.py --target <URL 或本地路径> --out probe.json`：可达性、内容类型、扩展名、可能工具。不下载正文、不登录、不消耗积分。
3. 用 WebSearch / domain_search 核实当下做法。已有知识只当假设，标注可能过时。
4. 写 `feasibility.json`：≥2 条候选路径、工具与凭据、成本、风险与回退、置信度、待确认项。格式见 [`feasibility.md`](./references/feasibility.md)。
5. 调研结论标「≠ 已验证可行」；查不到就写「未找到可靠依据」。

**未知源**：只读探测 → 检索核实 → 适配器草稿 → 连同 ≥2 条候选交人选择 → 人选后写入 `adapters/` 再进 S1。草稿必须标注未验证步骤；调研阶段唯一允许的写操作是 `probe.json`、`feasibility.json` 与适配器草稿文本。

### S0-B 决策（人拍板）

把决定项与可行性方案一起摆出来。没有依据的偏好一律不默认；有客观依据的技术项可推荐，仍由人选。完整清单与提问模板见 [`decisions.md`](./references/decisions.md)。

运行 `detect_options.py` 拿环境数据，与 `probe.json`、`feasibility.json` 一起作为提问依据。

**主题（必问）**：**墨蓝橘笺**（默认，`ink-tangerine`）、摸鱼绿、摸鱼票据风、橄榄手记、留白禅意风、石墨极简风。用户给主色 HEX、色系名或氛围词时，用「风格骨架 → 换色相」派生：`scripts/derive_palette.py` 打印 palette、代码框六槽位与逐项对比度，**先给人确认再落稿**。清单与配方见 [`themes.md`](./references/themes.md)；结果写 `content.json.decisions.theme`。

**原作者**：不设独立署名组件，把原作者写进 `source.author`，随文末来源说明呈现。来源里能找到就不再问；找不到时 S0-B 才问是否需要补 `author`。

### S0-C 规则治理（每次任务都跑）

规则不是永恒真理。`assets/rule-registry.json` 给每条规则标注层级（L0 平台事实 / L1 结构契约 / L2 可计量启发式 / L3 口径意图 / L4 元规则）、来源、适用范围、核验日期与复审周期；来自单次反馈的规则标 `provisional`，每次 CI 提示复审，不自动升级为永久规则。

`scripts/check_rules.py` 在门禁前检测冲突：scope 与本次来源不匹配、人的明确指令与规则相悖、平台事实过期、代码与注册表 id 漂移、同规则反复豁免、已验收范式回归、provisional 待复审。命中即把门禁置为 **`NEEDS_DECISION`**（既非 PASS 也非 FAIL），产出 `conflict-report.json`（证据／影响／A·B·C 候选动作／依据／推荐），**停下来交人裁决**。

豁免须写 `waivers.json` 且含 `approved_by`（人）与复审日；**L0 不可豁免**；`--ack-conflicts` 只能由人写。完整机制见 [`rule-governance.md`](./references/rule-governance.md)。

## S1 采集

按 [`source-adapters.md`](./references/source-adapters.md) 选适配器。X 视频是内置适配器：`api.fxtwitter.com/<user>/status/<id>` 取媒体直链 → 按选定清晰度下载 → ffmpeg 提取 16 kHz 单声道 → 选定 STT 后端转写。任何渠道只要产出**文本 + 元数据 + 来源说明**即可继续。

三条采集纪律：

1. **先探测后下载**：先取 HEAD、媒体清单、HLS 主列表，确认时长、码率、音轨、字幕，再按 S0 选定清晰度下载。只做转写时优先音轨。
2. **失败分域定位**：直连、同域子域、协议、域名变体、备用 API 分别测一次，把「网络问题」缩到具体域名或通道。不对同一路径反复重试。
3. **同源不互称信源**：平台字幕、转写、官方页面先做两两归一化 CER；一致度高时合并为同一来源的不同版本，`caveats` 里写明校对材料与同源判断。同源一致度不是准确率。

## S2 规范化

写成 `assets/content_ir.example.json` 结构的 `content.json`：`source / title / subtitle / meta / lead / sections[] / figures[] / takeaways / closing_quote / sources / caveats / decisions`。

- `reader_notes` 只进 HTML 文末，面向外部读者；`process_appendix` 只进 Markdown，供内部回溯。
- 校对付在本层完成：多信源比对、专名、章节编号、缺失片段。
- **IR 是唯一边界**：换渠道只改适配器，渲染层不动；排版阶段不改口径。

## S3 配图

先定每张图唯一要回答的问题，再选图型（封面／对比／流程／清单／路线图），用 `assets/figure_types/` 的 HTML/CSS 版式，经 `scripts/render_figures.py` 用无头浏览器 2 倍渲染。图型选择与画布规格见 [`figure-workflow.md`](./references/figure-workflow.md)。

**默认用 HTML/CSS 画图，不调用生图工具**：中文标注交给 DOM，既不乱码也不花积分。只有人明确指定 AI 插画才改变，且先说明积分消耗并取得同意；任何情况下都不用生图模型渲染中文标注。

图内文字写具体主体（人名、团队名、产品名），图会被单独转发，脱离正文就没有指代对象。这条由 `render_figures.py` 在渲染前拦截（F01），不通过不出图。

渲染后**逐张复看**：文字完整、无截断乱码、卡片不溢出、副标题不被压、底部结论可见；改完重渲染再看。

## S4 排版

`scripts/build_article.py` 读 `content.json` + 选定主题，生成全内联 HTML（图片 base64）与 Markdown。主题来自 `assets/themes/<id>/theme.json`（`--theme`），或用 `--theme-path` 指向派生主题。同一份 IR 可换主题重复出稿。

微信编辑器的平台事实（不可豁免，S01–S05 与此对应）：会过滤 `<style>` 与 class，所以样式只能内联；只保留白名单标签；外链资源会失效，图片要 base64 内嵌。细则见 [`layout-spec.md`](./references/layout-spec.md)。

组件的可用槽位以主题为准：`paragraph / quote / card / aside / tip / list_item / h3 / caption / code / table / head`。新增组件先加槽位再写模板，避免出现只有某一篇才有的样式。

**区块（aside）**：把一组内容（通常是一张图加一句说明）收进带边框的容器，和上下文分开；全篇最多两处、不嵌套（S24）。它承担「分组」这一件事，不承担强调。

## S5 校验交付

```bash
python scripts/ci_check.py --html dist/wechat-article.html --md dist/article.md \
  --ir content.json --theme <S0-B 选定的主题> --out dist
```

门禁内含三项判定，任一项不过即 `FAIL`：

| 判定 | 内容 | 退出码 |
|---|---|---|
| 结构 + 内容规则 | S 级（结构，error）与 C 级（内容，`--strict` 下也阻塞） | 1 |
| 主题 | schema、槽位齐全、正文与代码框对比度 | 1 |
| 规则清单 | `references/rules.md` 与注册表、与代码里的规则 id 三方一致 | 1 |

`NEEDS_DECISION`（退出码 2）表示规则与本次任务冲突，**这不是失败，是交人裁决**。单独排查时可用 `check_themes.py --out …`、`render_rules_doc.py --check` 看详情。`ci-report.json` / `lint-report.json` / `rule-review.json` 随交付落盘，里面有逐条修复建议。

交付前再截一次首屏，确认图片不是破图、首屏没有被重复信息占满。交付包：HTML 主稿、独立 PNG、Markdown、逐字稿（如有）、来源与整理说明。

## 自适应边界

- **结构层可自适应**：节数、图数、图型、是否有元数据／金句／行动清单、是否需要音频与转写。IR 可选字段缺省即不渲染。
- **渠道层可自适应**：未列出的源按「只读探测 → 检索核实 → 适配器草稿 → 人确认」收敛；新增渠道只写适配器，不改 S3–S5。
- **意图层永不自适应**：主题、立场、口径、什么算对、是否发布，永远在 S0-B 由人定。

## Resources

| 文件 | 用途 |
|---|---|
| `references/rules.md` | 规则清单（由注册表生成，含层级、要求、修复、执行位置） |
| `assets/rule-registry.json` | 规则注册表，规则层的单一来源 |
| `references/rule-governance.md` | 规则分层、可固化边界、冲突信号、汇报与豁免机制 |
| `references/layout-spec.md` | 微信编辑器的平台事实、标签白名单、组件槽位 |
| `references/themes.md` | 六套主题、风格配方、色系映射、派生算法 |
| `references/figure-workflow.md` | 图型选择、画布规格、渲染与复看 |
| `references/source-adapters.md` | 源适配器契约、IR 字段、内置渠道与新增步骤 |
| `references/decisions.md` | S0-B 决定项与提问模板 |
| `references/feasibility.md` | S0-A 调研规范、`feasibility.json` 结构 |
| `scripts/probe_source.py` | 只读源探测，输出 `probe.json` |
| `scripts/detect_options.py` | 检测环境／代理／模型／清晰度／后端 |
| `scripts/render_figures.py` | HTML/CSS → 2x PNG；渲染前跑 F01，浏览器失败自动回退 |
| `scripts/build_article.py` | IR → 全内联 HTML + Markdown |
| `scripts/derive_palette.py` | 主色 + 骨架 → palette、代码框六槽位、对比度 |
| `scripts/validate_article.py` | S／C 级规则（结构 + 内容），支持 `--strict` / `--md` / `--ir` |
| `scripts/check_themes.py` | 主题 schema、槽位、代码框六槽位、对比度校验 |
| `scripts/ci_check.py` | CI 门禁入口，输出 `ci-report.json` 与逐条修复建议 |
| `scripts/check_rules.py` | 注册表校验 + 冲突检测 |
| `scripts/render_rules_doc.py` | 从注册表生成 `references/rules.md` |
| `assets/themes/` | 六套主题：语义 token + 页面参数 + 组件槽位 + 骨架模板 |
| `assets/figure_types/` | 四种图型骨架 + `manifest.example.json` |
| `assets/content_ir.example.json` | IR 示例（含 `cover_carries_title`、`aside`） |
| `assets/waivers.example.json` | 由人签字的豁免记录格式 |

## 首次使用：Python 解释器

先运行 `scripts/resolve_python.py --json`，按结果决定是否询问：

| 判定 | 动作 |
|---|---|
| 已有记住的路径（`~/.skillshub/python.json`） | 直接用，不询问 |
| 系统有可用的默认 `python` / `python3`（非商店存根） | 直接用，不询问 |
| 检测到 `uv` 或 `conda` / `poetry` / `pipenv` / `hatch` / `pdm` / `pyenv` / `mamba` / `rye` | 用其默认解释器，不询问 |
| 以上都没有 | **在 S0 主动询问路径**，得到后 `resolve_python.py --set "<路径>"` 记住，之后不再问 |

配置只留本机，不写进仓库、不随 skill 打包；可用 `--clear` 清除重问。判定结果在 `process_appendix` 留一行便于回溯。

## Quick start

```bash
PY="<按上一节判定出的解释器路径>"
$PY scripts/detect_options.py                                        # 环境数据
$PY scripts/probe_source.py --target <URL或路径> --out probe.json    # 只读探测
# 检索核实 → 写 feasibility.json → 带方案问 S0-B
$PY scripts/build_article.py --list-themes                           # 六套主题
$PY scripts/derive_palette.py --primary "#A8551F" --skeleton olive --name "赭石手记"
# 人拍板后：采集 → 写 content.json → 画 figures/*.html
$PY scripts/render_figures.py --manifest figures/manifest.json
$PY scripts/build_article.py --content content.json --figures-dir figures --theme ink-tangerine --out dist
$PY scripts/ci_check.py --html dist/wechat-article.html --md dist/article.md \
  --ir content.json --theme ink-tangerine --out dist               # 门禁：不过不交付（内含主题与规则清单检查）
```

---
name: anything-to-wechat-article
description: 把任意来源（X 推文与 X 长文、视频、网页、PDF、Word、Markdown、音频、播客、会议记录、截图或粘贴文本）整理成微信公众号排版文章，输出全内联 HTML、自制中文信息图、六套主题与自定义配色。用户说转成公众号文章、做一篇公众号、X 视频转文章、把材料写成公众号、anything to wechat，或只做排版、只做配图时使用。不用于其他平台；AI 插画需先说明积分并取得同意。
---

# Anything to WeChat Article

把任意来源转成可直接粘贴进微信公众号编辑器的成稿：全内联样式 HTML、自制中文信息图、独立 PNG、Markdown 与来源说明。

## 执行什么

| 阶段 | 动作 | 产物 |
|---|---|---|
| S0-A 调研 | 只读探测 + 检索当下做法 + 算各路径代价 | `probe.json`、`feasibility.json`（≥2 方案） |
| S0-B 决策 | 带方案提问，用户拍板 | `content.json.decisions` |
| S0-C 规则治理 | 检测规则/任务冲突，交人裁决 | `conflict-report.json`、`rule-review.json` |
| S1 采集 | 按适配器取文本 + 元数据 | 转写/正文 + 来源信息 |
| S2 规范化 | 写成 IR | `content.json` |
| S3 配图 | HTML/CSS 版式 → 2x PNG，逐张检查 | `figures/*.png` |
| S4 排版 | 选定主题渲染 | `wechat-article.html` + `article.md` |
| S5 校验 | 硬约束校验 + 首屏截图 | `valid=true` 的交付包 |

主链严格串行，上一步是下一步的输入；探测、检索、渲染可在阶段内并行。调研只读，不越界到执行。**S5 的 CI 门禁不过不许交付。**

## 判断线（可检验）

- **对比度**：以六套内置主题实际取值为准——正文/墨色对纸底 ≥ 7:1（WCAG AAA），代码 text 对代码底 ≥ 12:1，关键字/注释/语言标签 ≥ 4.5:1。`check_themes.py` 与 `--audit-themes` 用同一套门槛。不够就调明度，不靠加粗放大。
- **主题一致**：一篇只用一套主题；章节头骨架全篇统一，不混用两种编号样式。
- **代码框**：六槽位（底 / 字 / 关键字 / 注释 / 边框 / 左条）按主题取值，六套互不共用近似灰；`keyword` 与 `label` 分开。
- **配图**：每张图先有一个「唯一要回答的问题」；图注回答该问题，不复述标题；图内事实可在原文找到。**两张图不挨着排**——中间要有正文段落（≥40 中文字）承接，图注不算过渡（S22）。
- **排版**：`<style` = 0、`class=` = 0、外链资源 = 0；标签限于 `div/p/img/strong/h1/h2/br/blockquote/span/table/tr/td`。
- **交付**：`validate_article.py --expect-figures N` 返回 `valid=true`，未替换占位符 = 0，`<img` 数 = base64 图数 = 独立 PNG 数。
- **抓眼**：一屏只留一个命名者（一个主导标题层级、一个视觉焦点），导语与卡片标题不重复标题主张。**封面已用视觉承担的主标题/栏目/副标题，正文用 `cover_carries_title: true` 省去**，不重复一遍。

## 明确拒绝

- 用「先做出来再说」代替调研；空手提问；替用户拍板。
- 给六套主题套同一套近似灰的代码框；用深色头的浅橙画行内关键字。
- 对比度不足时靠加粗、放大字号、描边或浅色硬凑。
- 插图复述标题；把讲者个人选择画成标准答案；默认流程里调用生图工具；用生图模型渲染中文标注；未说明积分并取得同意就改变默认画图方式。
- 生成 `{{作者名}}` / `{{一句话简介}}` 之类占位符，或编造作者身份。
- 让某个章节被巨型外框或异色背景单独包住，破坏全篇统一。
- 不跑校验就交付；把破图、空白页或未替换字段当成品。

## 何时必须停下来问

**硬条件（满足任一条就必须问）**：

1. 源未收录，或源描述含糊。
2. 可行路径 ≥2，需要取舍。
3. 涉及成本：积分、付费 API、GB 级模型/权重下载。
4. 目标、口径、验收标准不明。
5. 风格偏好没有依据（主题、配色、篇幅、图型、是否发布）。

**问之前必须做完**：只读探测、环境检测（`detect_options.py`）、必要检索、各路径代价估算，并给出选项 + 依据 + 推荐。信息不足时不许空手提问，也不许替用户拍板。

**有客观依据的技术项**（如 ffmpeg 重采样 16 kHz 单声道）可以在用户知情后直接执行，并在 `decisions` 里写明依据。

## Step 0 — 调研与决策（不可跳过）

### S0-A 调研（只读）

1. 识别源类型：已知渠道查 `references/source-adapters.md`；未知渠道走「未知源分支」。
2. `scripts/probe_source.py --target <URL 或本地路径> --out probe.json` 只读探测：可达性、内容类型、扩展名、可能工具。不下载正文、不登录、不消耗积分。
3. 用 WebSearch / domain_search 核实当下做法：公开接口、镜像 API、格式与许可限制、已知故障。已有知识只当假设，标注可能过时。
4. 写 `feasibility.json`：≥2 条候选路径、工具与凭据、成本、风险与回退、置信度、待确认项。格式见 `references/feasibility.md`。
5. 标注「调研结论 ≠ 已验证可行」；查不到就写「未找到可靠依据」。

### S0-B 决策（人拍板）

把决定项与可行性方案一起摆给用户。没有依据的偏好一律不默认；有客观依据的技术项可推荐，仍由用户选。完整清单见 `references/decisions.md`。

| # | 决定项 | 归属 |
|---|---|---|
| 1 | 主题／标题方向／立场口径；什么算「对」；谁验收 | **人，最高优先** |
| 2 | 忠实逐字稿 vs 结构重整；引语是否书面化；争议段落保留与否 | **人** |
| 3 | 来源范围：转哪部分、缺失片段怎么处理、是否多信源校对 | **人** |
| 4 | 提取路径、清晰度、代理、STT 后端、是否允许额外积分 | 人；模型给检测数据 |
| 5 | 篇幅、配图数量与图型、逐字稿／Markdown、是否发布 | **人** |
| 6 | 排版主题：六套内置任选，或给主色／色系／氛围派生一套 | **人**；模型给清单与映射 |

运行 `scripts/detect_options.py` 拿环境数据，与 `probe.json`、`feasibility.json` 一起作为提问依据。

**主题（必问）**：六套内置 —— **墨蓝橘笺**（默认，`ink-tangerine`）、摸鱼绿（`moyu-green`）、摸鱼票据风（`moyu-ticket`）、橄榄手记（`olive-journal`）、留白禅意风（`zen-whitespace`）、石墨极简风（`graphite-minimal`），各配一句风格描述。

用户给主色 HEX、色系名（绿／蓝／赭／灰…）或氛围词（沉稳／清爽／暖调／学术／杂志感）时，用「风格骨架 → 换色相」派生，不把现有主题换个色相：`scripts/derive_palette.py` 打印完整 palette、代码框六槽位与逐项对比度，**先给用户确认再落稿**。清单、配方与规则见 `references/themes.md`；结果写入 `content.json.decisions.theme`。

**原作者（N8）**：不设独立署名组件，直接把原作者名称写进 `source.author`，随文末来源说明呈现。来源里找到就不再问；找不到时，S0-B 才询问是否需要补 `author` 字段。禁止编造作者/身份/简介，禁止 `{{作者名}}` 占位符。

### 未知源分支

未列出的源：不猜、不直接动手、也不空手问。

只读探测 → 检索核实 → 生成适配器草稿（提取路径、工具、回退、合规检查）→ 连同 ≥2 条候选方案交人选择 → 人选后写入 `adapters/` 再进入 S1。

草稿不是已实现：未验证步骤必须标注，禁止把可行性方案说成「跑通过」。调研阶段唯一允许的写操作是 `probe.json` / `feasibility.json` 与适配器草稿文本。


### S0-C 规则治理与冲突卡点（每次任务都跑）

规则不是永恒真理。`assets/rule-registry.json` 给每条规则标注层级（**L0 平台事实 / L1 结构契约 / L2 可计量启发式**）、来源、适用范围、核验日期与复审周期；来自**单次反馈**的规则标 `provisional: true`，每次 CI 都提示「需第二次验证」，不自动升级为永久规则。

`scripts/check_rules.py` 在门禁前检测冲突：规则 scope 与本次来源不匹配、用户明确指令与规则相悖、平台事实过期、代码与注册表 id 漂移、同规则反复豁免、已验收范式回归、provisional 待复审。命中即把门禁置为 **`NEEDS_DECISION`**（既不是 PASS 也不是 FAIL），产出 `conflict-report.json`（证据 / 影响 / A·B·C 候选动作 / 依据 / 推荐），**停下来交人裁决**。

模型不得：自动豁免、自动改规则、静默跳过、自己生成 `--ack-conflicts` 确认文件。豁免须写 `waivers.json` 且含 `approved_by`（人）与复审日；**L0 规则不可豁免**。完整机制见 `references/rule-governance.md`。

## Workflow

**S0-A** → **S0-B** → **S1** → **S2** → **S3** → **S4** → **S5**。

### S1 采集（渠道无关）
按 `references/source-adapters.md` 选适配器。X 视频是内置适配器：`api.fxtwitter.com/<user>/status/<id>` 取媒体直链 → 按选定清晰度下载 → ffmpeg 提取 16 kHz 单声道 → 选定 STT 后端转写。任何渠道只要产出**文本 + 元数据 + 来源说明**即可继续。

### S2 规范化（IR 是边界）
写成 `assets/content_ir.example.json` 结构的 `content.json`：`source / title / subtitle / meta / lead / sections[] / figures[] / takeaways / closing_quote / sources / caveats / decisions`。
`reader_notes` 只进 HTML 文末，面向外部读者；`process_appendix` 只进 Markdown，供内部回溯。校对付在此层完成（多信源比对、专名、章节编号、缺失片段）。换渠道只改适配器，渲染层不动。

### S3 配图（默认代码画图）
按 `references/figure-workflow.md`：先定每张图唯一要回答的问题，再选图型（封面／对比／流程／清单／路线图），用 `assets/figure_types/` 的四种 HTML/CSS 版式，经 `scripts/render_figures.py` 用无头浏览器 2 倍渲染，**逐张检查溢出与压字后复看**。图注写清图在回答什么；只画原文确有的事实与关系。**默认不调用生图工具，一律用 HTML/CSS 版式经无头浏览器 2× 渲染 PNG**（中文标注交给 DOM，既不乱码也不花积分）。只有用户明确指定 AI 插画时才改变，且须先说明积分消耗并取得同意；任何情况下都不用生图模型渲染中文标注。

### S4 排版
`scripts/build_article.py` 读 `content.json` + 选定主题，生成全内联 HTML（图片 base64）与 Markdown。主题来自 `assets/themes/<id>/theme.json`（`--theme`，默认 `ink-tangerine`），或用 `--theme-path` 指向派生主题。同一份 IR 可换主题重复出稿。规范见 `references/layout-spec.md`，主题与派生见 `references/themes.md`。

### S5 校验交付（CI 门禁，不可跳过）

```bash
python scripts/check_themes.py --out dist/theme-report.json      # 主题 schema / 占位符 / 对比度
python scripts/derive_palette.py --audit-themes                  # 六套主题对比度审计
python scripts/ci_check.py --html dist/wechat-article.html --md dist/article.md \
  --ir content.json --theme <S0-B 选定的主题> --out dist
```

`validate_article.py` 跑 error 级 `S01–S22` 与 warning 级 `C01–C05`；CI 默认 `--strict`，warning 也阻塞。`check_themes.py` 与 `--audit-themes` 的结果一并纳入门禁，`ci-report.json` / `lint-report.json` / `rule-review.json` 随交付落盘。**门禁不过、或出现 `NEEDS_DECISION`，都不许交付。**

再截一次首屏确认图片不是破图。交付：HTML 主稿、独立 PNG、Markdown、逐字稿（如有）、来源与整理说明。

## 自适应边界

- **结构层可自适应**：节数、图数、图型、是否有元数据／金句／行动清单、是否需要音频与转写。IR 可选字段缺省即不渲染。
- **渠道层可自适应**：未列出的源按「只读探测 → 检索核实 → 适配器草稿 → 人确认」收敛；新增渠道只写适配器，不改 S3–S5。
- **意图层永不自适应**：主题、立场、口径、什么算对、是否发布，永远在 S0-B 由人定。

判断法：如果某个选择错了会让用户说「我不是这个意思」，它是意图，交给用户；如果错了只会让脚本报错或变慢，它是技术参数，可自动。

## Resources

| 文件 | 用途 |
|---|---|
| `references/decisions.md` | S0-B 决定项、提问模板、必须问的硬条件 |
| `references/feasibility.md` | S0-A 调研规范、feasibility.json 结构、置信度标注 |
| `references/source-adapters.md` | 源适配器契约、IR 规范、内置渠道与新增步骤 |
| `references/guardrails.md` | 规则与反例：触发条件、执行动作、判断线、明确禁止 |
| `references/layout-spec.md` | 排版硬规范：标签白名单、六主题体系、代码框六槽位 |
| `references/themes.md` | 六套主题、五套风格配方、色系映射、派生算法与示例 |
| `references/figure-workflow.md` | 插图五层工作流、问题→图型、渲染与校验闭环 |
| `scripts/probe_source.py` | 只读源探测，输出 `probe.json` |
| `scripts/detect_options.py` | 检测环境／代理／模型／清晰度／后端 |
| `scripts/render_figures.py` | 矢量式 HTML → 2x PNG 批量渲染 |
| `scripts/build_article.py` | IR → 全内联 HTML + Markdown；`--theme` / `--theme-path` / `--list-themes` |
| `scripts/derive_palette.py` | 主色 + 骨架 → palette、代码框六槽位、对比度；`--write-theme` / `--audit-themes` |
| `scripts/validate_article.py` | 27 条 lint（S01–S22 / C01–C05），支持 `--strict` / `--md` / `--ir` |
| `scripts/ci_check.py` | CI 门禁入口；输出 `ci-report.json` 与逐条修复建议 |
| `scripts/check_themes.py` | 主题 schema、模板占位符、代码六槽位、对比度校验 |
| `scripts/check_rules.py` | 规则注册表校验 + 冲突检测，产出 `conflict-report.json` / `rule-review.json` |
| `references/guardrails.md` | 规则与反例：触发条件、执行动作、判断线、明确禁止 |
| `references/rule-governance.md` | 规则分层、可固化边界、冲突信号、汇报与豁免机制 |
| `references/lint-rules.md` | 硬约束规则表（ID、级别、判定、修复） |
| `assets/rule-registry.json` | 规则注册表（层级／来源／scope／有效期／provisional） |
| `assets/waivers.example.json` | 由人签字的豁免记录格式 |
| `assets/themes/` | 六套内置主题（语义 token + 页面参数 + 组件样式 + HTML 骨架） |
| `assets/figure_types/` | 四种图型骨架 + `manifest.example.json` |
| `assets/content_ir.example.json` | IR 示例与字段说明（含 `cover_carries_title`） |

## 首次使用：Python 解释器

先运行 `scripts/resolve_python.py --json`，按结果决定是否询问：

| 判定 | 动作 |
|---|---|
| 已有记住的路径（`~/.skillshub/python.json`） | 直接用，**不询问** |
| 系统存在可用的默认 `python` / `python3`（非 Microsoft Store 存根） | 直接用，**不询问** |
| 检测到 `uv` 或 `conda` / `poetry` / `pipenv` / `hatch` / `pdm` / `pyenv` / `mamba` / `rye` 等环境管理器 | 用其默认解释器，**不询问** |
| 以上都没有 | **在 S0 主动询问用户 Python 运行地址**，得到后执行 `resolve_python.py --set "<路径>"` 记住，之后不再问 |

- 这是技术参数的自动判定，不进 S0-B 决策表；但「询问并记住」这一步不可跳过，也不能凭猜测填一个路径。
- 配置只留在本机用户目录，**不写进仓库、不随 skill 打包**；用户可用 `--clear` 清除后重新询问。
- 判定结果要在 `probe.json` / `process_appendix` 里留一行，便于回溯。

## Quick start

```bash
# 先按「首次使用：Python 解释器」一节判定：有可用默认 python 或 uv 等环境管理器则不询问；
# 否则在 S0 询问用户路径并用 resolve_python.py --set 记住。PY 取判定结果。
PY="<判定出的解释器路径>"
$PY scripts/detect_options.py                     # 环境数据
$PY scripts/probe_source.py --target <URL或路径> --out probe.json    # 只读探测（未知源必做）
# 检索核实 → 写 feasibility.json → 带方案问 S0-B
$PY scripts/build_article.py --list-themes                        # 六套主题清单
$PY scripts/derive_palette.py --list-skeletons                    # 六种风格骨架
$PY scripts/derive_palette.py --primary "#A8551F" --skeleton olive --name "赭石手记"
# 用户拍板后：采集 → 写 content.json → 画 figures/*.html
$PY scripts/render_figures.py --manifest figures/manifest.json
$PY scripts/build_article.py --content content.json --figures-dir figures --theme moyu-green --out dist
# 派生主题：--theme-path themes/zheshi-journal/theme.json
$PY scripts/check_themes.py --out dist/theme-report.json
$PY scripts/derive_palette.py --audit-themes
$PY scripts/ci_check.py --html dist/wechat-article.html --md dist/article.md \
  --ir content.json --theme ink-tangerine --out dist     # 门禁：不过不许交付
```

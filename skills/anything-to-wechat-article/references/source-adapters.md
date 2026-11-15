# 源适配器与 IR：anything 的边界

## 契约

**任何来源只要能产出 `content.json`（IR），就能进入同一套排版与配图管线。** 渠道差异全部收敛在适配器里，S3–S5 不改一行。

```
[任意源] --adapter--> [content.json IR] --build_article.py--> [公众号 HTML + PNG + MD]
                          ^
                    人在这层确认口径
```

## IR 字段（`assets/content_ir.example.json`）

| 字段 | 必填 | 说明 |
|---|---|---|
| `schema_version` | 是 | 目前 `1.0` |
| `source` | 是 | `kind`、`url`、`author`、`captured_at`、`completeness_note` |
| `title` / `subtitle` | 是 | 主标题、副标题 |
| `meta` | 否 | `[{label, value}]`，信息卡；没有就不渲染 |
| `lead` | 是 | 导语段落数组 |
| `sections` | 是 | `[{no, heading, paragraphs[], quote?, cards[]?}]`，节数自适应 |
| `figures` | 否 | `[{id, type, question, file, caption}]`，图数自适应 |
| `takeaways` | 否 | 行动清单字符串数组 |
| `closing_quote` | 否 | 结尾深底引用 |
| `sources` | 是 | 资料来源数组 |
| `caveats` | 是 | 书面化、自拟小标题、缺失片段、非逐字逐句等声明 |
| `reader_notes` | 否 | 面向外部读者的精简来源说明，只渲染进 HTML 文末；缺省时回退 `sources` + `caveats` |
| `process_appendix` | 否 | 面向内部的详细整理过程，只追加到 Markdown，供回溯 |
| `decisions` | 是 | Step 0 用户拍板的口径与参数，后续阶段不得擅改 |

可选字段缺省即不渲染对应组件，这就是「结构自适应」的实现方式。

## 内置适配器

| 源 | 提取路径 | 产物 | 注意 |
|---|---|---|---|
| **X 视频／推文** | `api.fxtwitter.com/<user>/status/<id>` 取 `media.videos[].formats`；按选定清晰度下载；ffmpeg 提取 16 kHz 单声道；选定 STT 后端转写 | 转写文本 + 元数据 | 默认代理可能拦 `*.twimg.com`；HLS 主列表常含独立音轨与自动字幕，可作校对材料；片头缺失要标注 |
| 一般网页 / 文章 URL | WebFetch 或 curl 取正文；去导航与广告 | 正文 + 标题 + 发布时间 | 需核对作者与日期，注意反爬 |
| 本地音视频 | ffmpeg 提取音频 → STT | 转写文本 | 长音频切片，按静音或字幕间隙对齐 |
| PDF | PDF 提取工具读文字与表格 | 正文 | 扫描件需 OCR，图表要单独说明 |
| Word / Markdown / TXT | 直接读取 | 正文 | 保留标题层级映射到 `sections` |
| 图片 / 截图 | OCR 或图像理解 | 文字 + 图中关系 | 需人工核对 OCR 错字 |
| 播客 / RSS | 取音频 → STT | 转写文本 | 注意片头广告与多说话人 |
| 会议录音 / 纪要 | STT + 说话人分离 | 带角色文本 | 「谁说的」需核对，不要臆测 |
| 用户粘贴的纯文本 | 直接规范化 | 正文 | 最可靠的源，仍需确认口径 |

## X 适配器详细步骤

1. `https://api.fxtwitter.com/<user>/status/<id>` → `media.videos[].formats` 得到各清晰度直链与码率。
2. 拿 HLS 主列表（`pl/...m3u8`）看独立音轨与自动字幕；字幕可作校对参考。
3. **按 Step 0 选定的清晰度**下载。同一视频各清晰度音轨码率可能相同（例如都是 AAC 128 kbps）；只做转写时先测音轨，高画质可能无增益。
4. ffmpeg：`-vn -ac 1 -ar 16000` 输出 wav 与 mp3，送转写用 mp3。
5. STT 后端按 Step 0：平台托管（零部署）或本地 Qwen3-ASR / FunASR / faster-whisper（离线可控）。
6. 校对：转写 + 平台字幕 + 官方页面／原始讲稿三方比对；专名、章节编号、数字写法逐个核；**先做同源检测**（两两归一化 CER），同一来源的两个结果不能互称独立信源。
7. 写 `caveats`：片头缺失、口语书面化、小标题自拟、非逐字逐句。

## 未知源：先调研，再写适配器

`source-adapters.md` 未列出的源，走 `SKILL.md` 的 S0-A：只读探测（`scripts/probe_source.py`）→ 用检索核实当下做法（不靠记忆拍脑袋）→ 产出 `feasibility.json`（≥2 条候选路径、代价、风险、失败回退、置信度）→ 生成适配器草稿 → **S0-B 由人选一条** → 人选后才把草稿落成 `adapters/` 下的实现。

完整规范见 `references/feasibility.md`。草稿状态必须标 `draft-not-executed`，禁止把「查到可行路径」说成「已支持该渠道」。这让渠道层也能自适应，而不必预先写死所有来源。

## 新增一个适配器（4 步）

1. 定义 `source.kind` 与必需元数据。
2. 写「源 → 文本 + 元数据」的提取步骤（工具、失败回退、合规检查）。
3. 把文本规范化为 IR，填 `sources` 与 `caveats`。
4. 在 `detect_options.py` 里补该源需要的环境检测；不动 `build_article.py` / `render_figures.py`。

## 自适应的边界

**能自适应**：节数、图数、图型、是否有元数据／金句／清单、是否需要音频与转写、是否附逐字稿、语言（IR 只承载文本）。
**不能自适应**：主题、立场、口径、什么算对、是否发布、成本与画质取舍。这些永远在 Step 0 由人定；检测只负责把客观数据摆上桌。

一个判断法：如果某个选择**错了会让用户说「我不是这个意思」**，它就是意图，交给用户；如果错了只会让脚本报错或跑得慢，它才是技术参数，可以自动。

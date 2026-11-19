---
name: pdf-to-html
description: 把学术论文 PDF 转成"英中双语对照、保留图片表格、可全文阅读"的自包含 HTML：用 MinerU 转 Markdown、按领域翻译、生成左右分栏/上下对照/仅英/仅中四种模式，带可折叠目录、引用悬浮预览、图片全屏缩放、字号滑块与中文字体切换。用户提供论文 PDF 或 arXiv 链接并要求"翻译成双语对照网页/保留图片/对照 PDF 排版"时使用。也适用于课程 Course Material 整理归档。
---

# PDF → 双语对照 HTML

把一篇论文 PDF 变成可直接阅读的双语 HTML 成品，并**对照原 PDF 校验**内容对齐。核心不是"转换"，而是"转换 + 校验"——MinerU 的输出有多处已知陷阱，不校验就会静默出错。

## 三层结构（越靠下越硬）

| 层 | 位置 | 承载 | 谁判定 |
|---|---|---|---|
| **规则层** | `scripts/validate.py` | 可机器判定的约束：无字面转义/围栏、TOC 层级、引用零死链、图片完整、无 className 整体赋值、字号/字体控件 | 脚本退出码 |
| **模板层** | `assets/build_html_template.py` | HTML 结构与全部交互逻辑（四种模式、目录、引用、lightbox、字号面板） | 模板即规格 |
| **描述层** | 本文件、`references/pitfalls.md` | 流程顺序、人工判定点、论文特例处理 | 人 |

**改行为先找最硬能承载它的层**：能脚本判定的写进 validate.py，不要只在文档里描述。

## 执行流程（严格串行）

1. **S0 环境预检（先于一切）**：运行 `python scripts/setup_env.py --workdir <项目根> --init`。它会检查**项目默认 Python**（`.env.json['python']`，无效则自动探测并写回）和 **MinerU API key**（环境变量 / `.env.json['mineru']` / `~/.mineru/token`）。**若缺 key，脚本退出码 2 并给出获取引导——key 无法自动生成，必须先让用户提供**（`--set-key` 或 `export MINERU_API_TOKEN`），此时停止后续步骤。脚本只报告 key 来源与长度，绝不打印值。见 pitfalls A1-A3。
2. **S1 获取 PDF**：下载到工作目录；用 `scripts/inspect_pdf.py` 渲染页图 + 提取表格 cells/rowspan（需 PyMuPDF，缺失时自动降级 poppler），**以原 PDF 为校验基准**。
3. **S2 MinerU 转换**：`scripts/mineru_convert.py --url <PDF_URL> --out temp/mineru_out` —— URL 提交 v4 API → 轮询 → 下载 zip（`full.md` + `images/`）；URL 不通时自动 `--pdf` 本地上传兜底。
4. **S3 分块**：`scripts/parse_blocks.py` 把 `full.md` 切成带 id 的结构化块（heading/para/list/figure/table/ref）。
5. **S4 翻译**：`scripts/make_translate_tasks.py` 切 N 份 + 注入统一术语表 → 并行翻译 → 合并为 `translations_merged.json` → 质检（零遗漏、无异常截断）。术语表见脚本内 GLOSSARY，领域词（token/embedding 等）保留英文。
6. **S5 构建 HTML**：复制 `assets/build_html_template.py` 到工作区，**按当前论文改写 PAPER_CONFIG 与所有标注 `PAPER-SPECIFIC` 的段**（Listing、重建表格、旋转图）→ 运行生成 HTML。
7. **S6 门禁**：`python scripts/validate.py <workdir> --strict`，FAIL 必须修到 PASS。
8. **S7 浏览器实测**：`python scripts/browser_test.py <产物HTML>` —— 用系统 Chrome/Edge headless 跑交互断言（模式切换保持目录状态、目录折叠、引用浮窗+锚点、lightbox、字号、锚点偏移、零死链）。零生态依赖，找不到浏览器用 `--chrome` 指定。

## 关键约束（必读）

- **对照原 PDF 校验**：MinerU 会把合并单元格表格压扁、产生 LaTeX 转义、拆散代码块——每一条都必须按 `references/pitfalls.md` 处理。表格数量对不上时先看原页图，别急着判定缺失。
- **禁止 `element.className = ...` 整体赋值**：多个独立 UI 状态（mode / toc-collapsed）共存时必须用 `classList` 精确增删。这是用户明确要求长期记住的规则。
- **所有 caption 都要有中文翻译**：包括 figure 块内嵌 caption 和独立的 Figure/Table caption 段落。
- **引用零死链**：文中 `[n]` 与 `id="ref-n"` 一一对应。
- **锚点跳转要避开 sticky 顶栏**：`scroll-padding-top` 由 JS 实测 header 高度动态设置，不要写死；改动后必须跑 browser_test.py 验证。
- **进度/归档**：按项目 README 的目录规则归档；进度是否更新必须用户确认，不擅自改。

## 论文特例清单（每次必须重新判定）

这些是**论文相关**而非通用逻辑，模板里标了 `PAPER-SPECIFIC`：
- 被压扁需手工重建的表格（如示例的 Table A1）
- 围栏代码块（Listing）中被拆散的段落 id 与中英 caption
- 需要旋转 90° 的图片（异常高宽比 h>w×1.3 且文字竖排）
- 输出路径（章节名、资料名）

没有的项目就删掉对应配置，不要留示例论文的值。

## 门禁边界

`validate.py` 覆盖 20 条坑中的 17 条（环境契约、转义/围栏、TOC 层级、表格 rowspan、引用、编号列表、图片、caption、状态类、锚点偏移）；`browser_test.py` 另覆盖交互类（目录/引用/lightbox/字号/锚点偏移实测）。剩 2 条本质需人工判断：B5（旋转图肉眼确认方向）、B6（表格数量对不上时先看原页）——脚本会提示，但结论由人下。**不要因为门禁全绿就跳过这两条。**

自检基线：示例论文产物 `validate.py` 应 29/29 PASS，`browser_test.py` 应 9/9 PASS；模板 `assets/build_html_template.py` 的 HTML/CSS/JS 段与成品逐行一致。

## 参考

- `references/pitfalls.md` — 全部 20 条真实踩坑记录（症状/根因/约束/检测），**本 skill 的知识核心**
- `scripts/validate.py` — 交付门禁（静态检查，29 项）
- `scripts/browser_test.py` — 浏览器交互门禁（Chrome/Edge headless，零生态依赖，9 项）
- `scripts/inspect_pdf.py` — 通用 PDF 检查（页图 PNG + 表格 cells，PyMuPDF/poppler 自动降级）
- `assets/build_html_template.py` — HTML 模板（含全部交互逻辑）
- `scripts/setup_env.py` — 环境预检与初始化（项目 Python + MinerU key，缺则创建/引导）
- `scripts/mineru_convert.py` / `parse_blocks.py` / `make_translate_tasks.py` — 流程脚本

## 环境要求（通用）

- Python 3 + `requests`（仅 MinerU 转换需要）；`pip install requests`
- PDF 检查：建议 `pip install pymupdf`；无则用 poppler 命令行（仅页图，无表格 cells）
- 浏览器测试：任意 Chrome/Chromium/Edge，无需 Playwright/Puppeteer/ego
- 依赖解析顺序、参数均通过 CLI 或环境变量提供，**不绑定任何厂商目录或项目私有配置**

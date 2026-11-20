# skillshub

可复用的 Agent Skill 集合。当前收录 **4 个 skill** · **v1**（其中 2 个为 README 外部引用）。

## 目录

- [收录](#收录)
- [Skill 介绍](#skill-介绍)
  - [anything-to-wechat-article](#anything-to-wechat-article)
  - [pdf-to-html](#pdf-to-html)
  - [lieflat-less-ai-tone](#lieflat-less-ai-tone)
  - [diagram-design](#diagram-design)
- [安装](#安装)
- [快速开始](#快速开始)
  - [公众号排版](#公众号排版)
  - [PDF 转双语网页](#pdf-转双语网页)

## 收录

| Skill | 用途 | 位置 / 来源 |
|---|---|---|
| `anything-to-wechat-article` | 把任意来源整理成微信公众号排版文章 | [`skills/anything-to-wechat-article/`](skills/anything-to-wechat-article/) |
| `pdf-to-html` | 把论文 PDF 转成可全文阅读的英中双语对照网页 | [`skills/pdf-to-html/`](skills/pdf-to-html/) |
| `lieflat-less-ai-tone` | 基于语料研究的去 AI 味检测与最小改写（外部引用） | [GitHub 仓库](https://github.com/larashero3-dotcom/lieflat-less-ai-tone) |
| `diagram-design` | 生成单文件 HTML + SVG 的编辑式图表（外部引用） | [GitHub 仓库](https://github.com/cathrynlavery/diagram-design) |

## Skill 介绍

### anything-to-wechat-article

- **输入**：X 推文／长文／视频、网页、PDF、Word、Markdown、音频、播客、会议记录、截图或粘贴文本。
- **输出**：全内联样式 HTML、独立 PNG、Markdown 存档、逐字稿（如有）、来源与整理说明。
- **流程**：只读调研 → 由人拍板口径与主题 → 采集 → 写成 IR → 代码画图 → 主题排版 → CI 门禁。
- **特点**：六套内置主题（可按主色派生）、配图一律 HTML/CSS 渲染成 2× PNG、32 条可机器判定的规则（结构 / 内容 / 图内文本）、规则与本次任务冲突时交人裁决。

![公众号排版示例首屏](assets/screenshots/example.png)

> 用仓库内的示例 IR 渲染，内容均为虚构演示数据；全内联样式 HTML + 自制中文信息图，无生图工具。

### pdf-to-html

- **输入**：论文 PDF 或 arXiv 链接。
- **输出**：自包含双语 HTML——左右分栏／上下对照／仅英／仅中四种模式，保留图片表格，带可折叠目录、引用悬浮预览、图片全屏缩放、字号滑块与中文字体切换。
- **流程**：环境预检（自动检查项目 Python 与 MinerU key，缺失则创建/引导）→ MinerU 转换 → 分块翻译 → 对照原 PDF 校验并构建 HTML → 静态门禁 + 浏览器门禁。
- **特点**：把 20 条真实踩坑固化为机器约束（29 项静态检查 + 9 项 Chrome headless 交互测试）；零厂商生态依赖，Python 3 + 任意浏览器即可运行。详见 [`SKILL.md`](skills/pdf-to-html/SKILL.md) 与 [`踩坑清单`](skills/pdf-to-html/references/pitfalls.md)。

![双语对照网页示例首屏](assets/screenshots/pdf-to-html.png)

### lieflat-less-ai-tone

> 外部引用：本仓库不收录源文件，仅链接到 [larashero3-dotcom/lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone)。

- **输入**：一篇中文成稿。
- **输出**：先给出检测报告（指标、研究参照、原文例句、具体改法）；用户确认后再改写、复测并生成前后对比。
- **流程**：脚本检测 + 语义候选判读 → 分层报告等待用户回复 → 最小改动改写 → 复测对比。
- **特点**：基于两轮实测语料（1,169 篇、约 520 万汉字、100+ 指标、约 50 万次模型语义判断）；A/B/C/H/X/F 分级，C/H/X 级默认不改；“最小改动、信息守恒、不制造参差”防止过度改写。许可 CC BY-NC 4.0，商用需上游授权。

![去 AI 味 Skill 研究概览](https://raw.githubusercontent.com/larashero3-dotcom/lieflat-less-ai-tone/main/assets/less-ai-tone-hero-zh.png)

> 图片来自上游仓库 README。

### diagram-design

> 外部引用：本仓库不收录源文件，仅链接到 [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design)。

- **输入**：自然语言描述的图表需求，或 draw.io / Mermaid / Excalidraw / PlantUML 源文件。
- **输出**：单个自包含 `.html`（内联 SVG），双击即可打开，也可导出 SVG / PNG。
- **流程**：选图表类型 → 规划布局 → 生成编辑式 SVG 图表；可从网站 onboard 品牌色与字体。
- **特点**：51 种图表类型；1px 细线、无阴影、4px 网格的编辑式设计系统；单文件、无构建、无 JS、无外链图片；支持导入重绘与品牌 onboarding。许可 MIT。

![Diagram Design 演示：从提示到成图](https://raw.githubusercontent.com/cathrynlavery/diagram-design/main/docs/hero/demo.gif)

> 图片来自上游仓库 README。

## 安装

把所需 skill 的整个目录交给 Agent，让它自己读取 `SKILL.md` 完成安装与配置即可。

外部引用的两个 skill 不在本仓库内，可用 Agent Skills 包管理器直接安装：

```bash
npx skills add larashero3-dotcom/lieflat-less-ai-tone
npx skills add cathrynlavery/diagram-design
```

## 快速开始

### 公众号排版

```bash
python scripts/build_article.py --list-themes
python scripts/check_themes.py
python scripts/ci_check.py --html dist/wechat-article.html --md dist/article.md \
  --ir content.json --theme ink-tangerine --out dist
```

### PDF 转双语网页

```bash
# 0) 环境预检（缺 Python 配置/MinerU key 时按提示创建，key 需自行提供）
python skills/pdf-to-html/scripts/setup_env.py --workdir . --init

# 1) MinerU 转换（token 也可放环境变量 MINERU_API_TOKEN）
python skills/pdf-to-html/scripts/mineru_convert.py --url https://arxiv.org/pdf/XXXX.XXXXX --out temp/mineru_out

# 2) 分块 / 翻译 / 构建：见 SKILL.md 的 S3-S5

# 3) 双门禁
python skills/pdf-to-html/scripts/validate.py . --strict
python skills/pdf-to-html/scripts/browser_test.py courses/<章节>/CourseMaterial/<论文>/<论文>_bilingual.html
```

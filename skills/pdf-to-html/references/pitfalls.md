# 踩坑清单：PDF → 双语 HTML 全流程

本文件是本 skill 的知识核心。每一条来自真实事故，按 **症状 / 根因 / 约束 / 检测** 记录。
约束的机器判定版本在 `scripts/validate.py`；改行为时优先改脚本门禁，不要只改这里的描述。

---

## A. 环境层

### A1. Python 解释器不可用 / 不唯一
- **症状**：`python --version` 报商店占位符错误，或系统有多个 Python 版本。
- **根因**：Windows App execution aliases；或多版本并存。
- **约束**：**S0 先跑 `scripts/setup_env.py --init`**——检查项目默认 Python（`.env.json['python']`），无效则自动探测真解释器并写回；不盲目信 PATH 别名（`looks_like_real_python` 真正执行 `-c` 验证）。允许环境变量 `PYTHON` 或 `--set-python` 指定。
- **检测**：`setup_env.py` 报告项目 Python 的 READY/MISSING 与来源（不打印值）。

### A2. JSON 配置含尾随逗号
- **症状**：严格 `json.loads` 解析失败。
- **根因**：人工维护的 JSON 常有尾随逗号。
- **约束**：解析配置时先容错 `re.sub(r",\s*([}\]])", r"\1", raw)` 再 json.loads（脚本已内置）。
- **检测**：脚本内置。

### A3. API key 泄露
- **症状**（风险）：把 token 打印到日志/对话。
- **约束**：token 按优先级从 ① 环境变量 `MINERU_API_TOKEN` ② `--token-file` ③ `./.env.json` ④ `~/.mineru/token` 读取；**任何脚本不得打印 key 值或其片段**，日志只打印来源/长度/HTTP 状态码。若 S0 预检发现缺失，`setup_env.py` 退出码 2 并引导用户创建（`--set-key` / `export`）——**key 不能由模型编造**。
- **检测**：`setup_env.py` 报告来源与长度；`validate.py` 扫描是否有 `print(token)` 类语句。

### A4. MinerU v4 只接受 URL
- **症状**：本地文件路径提交被拒。
- **约束**：提交用 `POST /api/v4/extract/task` + `{"url": ...}`，`model_version="vlm"`；轮询 `GET /api/v4/extract/task/{id}`；取 `data.full_zip_url` 下载。境外 URL 可能超时，需准备本地上传后手（`POST /api/v4/file-urls/batch` → PUT → 轮询 batch）。

### A5. 浏览器测试要零生态依赖
- **症状**：专用浏览器 CLI（如 ego lite 的 `ego-browser`）报 `browser runtime is not available`——CLI 与 App 版本不匹配，或其 runtime 不在 PATH。
- **根因**：依赖某个厂商的私有 CLI + 运行中的 App + 版本配套，环境一换就断。
- **约束**：**默认用 `scripts/browser_test.py`**——注入自测 JS 到 HTML 副本，用系统 Chrome/Edge 的 `--headless --dump-dom` 取结果，只需一个浏览器、零 Python 三方库。找不到浏览器时用 `--chrome` 显式指定。ego lite 等专用 CLI 仅在用户明确要求时作为可选补充。
- **注意**：测试标记要在 JS 里拼接生成（` '__BEGIN'+'__' `），否则 `--dump-dom` 会匹配到 `<script>` 源码里的字面量。锚点偏移用实测断言，不同窗口宽度下 header 高度不同（headless 窄窗可达 141px vs 常规 104px），正好验证动态测量的必要性。

---

## B. 转换 / 解析层

### B1. MinerU 压扁复杂表格（最严重）
- **症状**：Table A1 的合并单元格 + 多行 agent 连成一坨：`LATS (GPT-4)LATS (GPT-3.5)`、`88.0 (82.3-91.5)80.4 (78.7-83.5)`。
- **根因**：MinerU 的 `full.md` 把 rowspan 表格拍平成单行。
- **约束**：**必须对照原 PDF 逐表核验**。用 `scripts/inspect_pdf.py` 渲染页图 + 提取 cells/rowspan（PyMuPDF 后端）；合并单元格表格手工重建后逐值比对原文，不许手抄不校验。
- **注意**：论文原文的明显笔误（如 `88.9 (86.6-0.91.5)`）忠实保留，不擅自"改正"。
- **检测**：validate.py `check_tables()`（表格数、rowspan 存在性）。

### B2. LaTeX 转义污染
- **症状**：HTML 显示字面 `\$4`、`\$\tau\$-bench`。
- **根因**：MinerU 为防 LaTeX 解析输出 `\$`，`\$\tau\$` 里的 `$` 其实是数学定界符。
- **约束**：渲染前归一化：`\$\<cmd>\$` → 对应 Unicode（τ/α/…），剩余 `\$` → `$`。**任何原始文本显示前都要归一化**——不止正文，还包括注入 JS 的 REF_DATA（悬浮预览数据）等非 inline_md 路径。抽成 `normalize_escapes()` 统一调用。
- **事故**：REF_DATA 直接用 `json.dumps(ref_lookup)` 注入，没走 inline_md，导致 [62] 浮窗显示 `\$\tau\$-bench`。由 validate.py 门禁发现。
- **检测**：validate.py `check_html_structure()`（成品中字面 `\$` 与 `\tau` 必须为 0，含 script 区）。

### B3. 围栏代码块被拆散
- **症状**：Listing 1 的 ```` ```txt ```` 变成可见文本，prompt 被拆成 6 段；Listing 2 的 JSON 被压成一段。
- **根因**：块解析器不认识围栏代码块。
- **约束**：解析器必须识别 ```` ```lang ... ``` ```` 作为单一 code 块；从 `full.md` 原文提取代码内容（不是从被压扁的段落恢复）；JSON 用 `json.loads/dumps(indent=2)` beautify；加语法高亮。
- **检测**：validate.py `check_code_blocks()`（无字面围栏、JSON 多行）。

### B4. 标题层级藏在编号里
- **症状**：目录里 `1 Introduction` 和 `1.1 What is...` 同级——因为论文除标题外全是 `##`。
- **根因**：Markdown 的 `#` 数量无法区分这种论文结构。
- **约束**：TOC 层级**从标题文本编号推断**：`^\d+\.\d+`/`^[A-Z]\.\d+` → 二级，其余 → 一级。最多两级。
- **检测**：validate.py `check_toc_levels()`。

### B5. 旋转图片
- **症状**：一张图 526×1809，文字竖排，无法阅读。
- **约束**：检测异常高宽比（h > w×1.3）→ 肉眼确认是否旋转 → 顺时针/逆时针 90° 转正。转换脚本复制图片时处理，重跑不覆盖。**注意区分**：正常竖版表格图（如 1098×1434）不要误转。
- **检测**：validate.py `check_images()`（记录旋转过的图）。

### B6. PDF 工具误报表格数量
- **症状**：PDF 表格提取工具报 9 个表，实际 8 个（工具把一张大表拆成两文件、把图注误判成表）。
- **根因**：一张大表被拆成两文件、图注被误判成表。
- **约束**：表格数量差异**不能直接判定缺失**，必须看原页图确认。

---

## C. 渲染 / 交互层

### C1. 多个独立状态禁止整体赋值（★ 用户明确要求长期记住）
- **症状**：点击"上下对照/左右分栏"导致已收起的目录意外展开。
- **根因**：`body.className = 'mode-' + m` 整体覆盖，抹掉了并列的 `toc-collapsed` 类。
- **约束**：**绝不用 `element.className = ...` 整体赋值**；必须用 `classList.add/remove/toggle` 精确增删。模式切换写 `setMode()`：先 remove 所有 `mode-*`，再 add 目标。
- **检测**：validate.py `check_no_class_clobber()`（扫描模板 JS 中 `body.className=` 赋值）。

### C2. 字号只能循环不能调小
- **症状**：只有 "A+字号"，无法减小。
- **约束**：字号用滑块（12–24px）+ 预设挡位，存 localStorage；面板点击外部关闭。
- **检测**：validate.py `check_font_controls()`（slider + presets + 字体切换存在）。

### C3. 中文字体不适读
- **症状**：默认微软雅黑长文阅读吃力。
- **约束**：默认思源宋体 Noto Serif SC（衬线，长文护眼，与英文衬线统一）；提供思源黑体/等线/雅黑切换；CSS 变量 `--font-stack` 带完整回退链。
- **检测**：validate.py `check_font_controls()`。

### C4. Sticky top bar 遮挡锚点跳转（★ 实测 header 104px）
- **症状**：点击目录/引用跳转后，目标标题不见——被 sticky header 完全盖住。
- **根因**：浏览器把锚点滚到视口顶部 (y=0)，而 header `position:sticky;top:0` 浮在其上。实测 `headingTop=0`、`headerBottom=104`、`obscured=true`。
- **约束**：`html{scroll-padding-top:var(--anchor-offset,120px)}`，并用 JS 在初始化与 resize 时**实测 header 高度 +16px 呼吸空间**写入 `--anchor-offset`，不写死（header 因工具按钮 flex-wrap 会变高）。
- **不要**用 JS 拦截点击手动 scrollTo——原生 scroll-padding-top 对目录、引用、所有 `#anchor` 一视同仁，更简单可靠。
- **检测**：validate.py `check_anchor_offset()`；browser_test.py 断言 `offset >= header 高度 + 10`（不同窗口宽度下 header 高度会变，动态测量是关键）。

---

## D. 质量 / 对齐层

### D1. caption 翻译完整性
- **约束**：所有 Figure/Table/Listing caption（含 figure 块内嵌 caption）都必须有中文翻译。
- **检测**：validate.py `check_captions()`。

### D2. 引用死链
- **约束**：文中每个 `[n]` 都有对应 `id="ref-n"` 锚点，一一对应。
- **检测**：validate.py `check_citations()`。

### D3. 图片引用完整性
- **约束**：HTML 中每个 `images/xxx` 引用都指向存在的文件。
- **检测**：validate.py `check_images()`。

### D4. 状态类与模式类正交
- **约束**：任何 UI 操作（字号/目录/引用/图片）都不得改变无关的 `mode-*` / `toc-collapsed` 状态。
- **检测**：`scripts/browser_test.py`（Chrome headless，零生态依赖）。

### D5. 编号列表被拆散，每项都从 1. 开始（★ 用户实测反馈）
- **症状**：论文正文的编号结论列表（1. 2. 3. 4. 5.），渲染后每一段都显示 "1."，没有递增。
- **根因**：parse_blocks 遇到列表项之间的空行就断开，把 5 条切成 5 个独立 list 块；每段各自渲染成 `<ol><li>`，浏览器自然都从 1 开始。项间若有说明段落（如 "For example, ..."）插在中间，还会把一个列表拆成两段 `<ol>`。
- **约束**：渲染前把被拆散的编号列表**合并回单一 list 块**——收集连续编号项，并把夹在中间的 para 作为上一项的续行并入（render_list 把非编号行视为续行而非新 li）。译文按 id 顺序拼接，保持中英对齐。
- **检测**：validate.py `B7-编号列表完整合并`（原文编号组长度必须出现在渲染的 ol li 数中）+ `B7-无孤立单条编号列表`。
- **注意**：区分"引用编号 `[27][6][26]`"（原文如此，忠实保留，不要排序）与"列表项编号 1. 2. 3."（被拆散，必须合并）——两者都是"序号"但问题完全不同。

# 公众号排版硬规范

微信编辑器会过滤样式表与 class；一份合格成稿的内联样式实测统计如下（不是凭印象）：

```
925,222 bytes | <style> 标签 0 | class 属性 0 | 内联 style 111 处
标签：html head meta title body div(6) p(53) img(4) strong(30) h1(1) br(12) blockquote(10) span(7)
无 section / figure / figcaption / script
base64 图片 4 张；配色 9 个色值
```

## 硬规范

1. **只用内联样式**：微信编辑器会过滤 `<style>` 与 class，任何依赖样式表或类名的排版粘贴后都会塌。
2. **标签白名单**：`div / p / img / strong / h1 / h2 / br / blockquote / span / table / tr / td`。禁用 `section / figure / figcaption / script / iframe`。多列布局优先 `table`，少用 flex。
3. **图片双轨**：HTML 内嵌 `data:image/png;base64,…` 保证本地预览自包含；同时输出独立 PNG 供公众号后台手动上传（粘贴时 base64 不一定被编辑器接管）。
4. **图注与图片分离**：用 `<p><img …></p>` + 一个居中的小字 `<p>` 作图注，不用 `figure/figcaption`。
5. **外层容器**：由主题 `page` 决定 —— 默认 `max-width:677px;margin:0 auto;padding:24px 20px 56px;font-size:16px;line-height:1.85;letter-spacing:.3px`，背景用主题 `page_bg`（不写死 `#FFFFFF`，橄榄手记是 `#FDFDF8`）。字体栈 `-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif`；禅意风标题可换衬线。
6. **不使用外链**：字体、CSS、JS 一律不引；无 `position:fixed`。
7. **文末必须写**：资料来源、整理流程、引语是否书面化、小标题是否自拟、缺失片段说明。
8. **一屏一个命名者**：每屏只保留一个主导标题层级与一个视觉焦点；导语不重复标题主张，卡片标题不重复章节名。缩略图状态下仍能读出唯一主张才算过关。

## 主题体系

每套主题是 `assets/themes/<id>/theme.json`，含五块：

- `tokens`：paper / surface / border / ink / body / muted / primary / accent / radius
- `page`：`max_width / padding / font_size / line_height / letter_spacing`
- `styles`：标题、导语、正文、引用、卡片、提示卡、表格、图注等组件样式串
- `html`：章节头、代码框、表格、插图、文末 CTA 等骨架模板
- `code`：代码框六槽位（`bg / text / keyword / comment / border / accent`）+ `label / header_bg / dots` 与各段样式

六套内置主题、五套风格配方、色系映射与派生算法见 [`themes.md`](./themes.md)。**只改配色不改骨架**会得到「同一张脸换口红」；要换风格请换主题或按骨架派生。

**全篇统一**：一篇只引用一个 `theme.json`，章节头骨架全篇一致，不混用两种编号样式。禁止给单个章节套巨型外框、异色背景或独立主题，破坏整体节奏。

## 代码框六槽位（所有主题共用结构）

| 槽位 | 用途 | 约束 |
|---|---|---|
| `bg` | 代码底 | 主题 token，模板写 `{code_bg}` |
| `text` | 代码字 | 对 `bg` ≥ 12:1 |
| `keyword` | 行内关键字 | 画在 `bg` 上，对 `bg` ≥ 4.5:1 |
| `comment` | 注释 | 以 `#` 或 `//` 开头的行整体降级，对 `bg` ≥ 4.5:1 |
| `border` | 外框 | 部分主题同时做虚线分隔 |
| `accent` | 左侧强调条 | 主色派生，通常 2–4px |

附加：`label`（语言标签，画在代码头上，对 `header_bg` ≥ 4.5:1）、`header_bg`（橄榄手记是 `#1E1F23` 深墨窄条）、`dots`（mac 三色圆点开关）、`radius`（绿/票据/手账不同）。

**`keyword` 与 `label` 必须分开取值**：前者在浅底，后者在代码头，深色头主题不能共用一个浅橙。**六槽位必须按主题取值，禁止把六套统一成同一套近似灰**；新增主题用 `derive_palette.py` 派生，并跑 `--audit-themes` 检查对比度。

## 设计令牌（默认主题「墨蓝橘笺」`ink-tangerine`）

| 用途 | 值 |
|---|---|
| 正文 | `#3F3F3F`，16px，行高 1.85 |
| 主色（标题／深底引用） | `#20344F` |
| 强调色（编号、竖线、关键词） | `#E27145` |
| 浅底（引用块、信息卡） | `#FAF8F4` |
| 次级灰 | `#8A94A0` / `#5A6675` / `#C9CDD3` |
| 代码底 / 代码字 | `#F4F2ED` / `#1F2933` |
| 页面底 / 卡片底 | `#FFFFFF` / `#FAF8F4` |

两色以内为主，灰阶不算主色；全篇色值控制在 10 个内（代码框六槽位另计）。其他主题的取值见 [`themes.md`](./themes.md)。

## 组件片段（墨蓝橘笺参考款，可直接复制，全部内联）

其余五套的章节头、引用卡、提示卡、CTA 结构各自不同，以 `assets/themes/<id>/theme.json` 的 `html` 与 `styles` 为准，不要用下面的片段硬套到别的主题上。

```html
<!-- 章节标题 -->
<p style="margin:38px 0 16px;"><span style="display:inline-block;padding:3px 10px;background:#20344F;color:#FFFFFF;font-size:13px;border-radius:3px;letter-spacing:1px;">01</span>　<strong style="font-size:20px;color:#20344F;">小标题</strong></p>

<!-- 正文 -->
<p style="margin:0 0 18px;text-align:justify;">段落，关键句用 <strong style="color:#20344F;">加粗主色</strong>。</p>

<!-- 金句引用 -->
<blockquote style="margin:24px 0 28px;padding:16px 18px;background:#FAF8F4;border-left:4px solid #E27145;color:#20344F;font-size:17px;line-height:1.85;">金句</blockquote>

<!-- 图片 + 图注 -->
<p style="margin:26px 0 8px;text-align:center;"><img src="data:image/png;base64,…" alt="图 1" style="width:100%;height:auto;display:block;border-radius:6px;"></p>
<p style="margin:0 0 26px;text-align:center;font-size:13px;color:#8A94A0;">图 1 ｜ 这张图在回答什么</p>

<!-- 信息卡 / 清单项 -->
<div style="margin:0 0 16px;padding:14px 18px;background:#FAF8F4;border-radius:6px;">①　条目</div>

<!-- 分割线 -->
<p style="margin:0 0 34px;text-align:center;color:#C9CDD3;font-size:14px;letter-spacing:6px;">● ● ●</p>

<!-- 结尾深底引用 -->
<blockquote style="margin:24px 0 30px;padding:18px;background:#20344F;color:#FFFFFF;font-size:17px;line-height:1.9;border-radius:6px;">收束语</blockquote>
```

## 图片尺寸

| 类型 | 画布 | 2x 输出 |
|---|---|---|
| 头图 | 1080×460 | 2160×920 |
| 正文对比／清单图 | 1080×600 ~ 1080×660 | 2160×1200 ~ 2160×1320 |

宽度固定 1080，高度按内容定；`html,body` 固定宽高、`overflow:hidden`，避免截图留白。

## 校验规则（`scripts/validate_article.py`）

- `<style` 出现次数 = 0；`class=` = 0；外链 `http(s)://` 资源 = 0
- 禁用标签 `section / figure / figcaption / script / iframe` 出现次数 = 0
- `<img` 数 = base64 图片数，且 > 0；未替换占位符 `{{` = 0
- `blockquote` ≥ 1；每个 `<img` 的 `style` 含 `width:100%`
- 输出 JSON 报告，不通过时退出码非 0

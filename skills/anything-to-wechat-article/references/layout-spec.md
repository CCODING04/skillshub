# 版式规范

本文件只写三样东西：微信编辑器的平台事实、标签与槽位边界、主题文件的位置。
**具体数值（字号、间距、颜色、圆角）不在文档里，以 `assets/themes/<id>/theme.json` 为准**——
文档抄一遍数值就会和主题漂移，而主题是能被渲染验证的那一层。

## 平台事实（L0，不可豁免）

1. 编辑器过滤 `<style>` 与 class：**样式只能内联在每个元素上**，依赖样式表或类名的排版粘贴后会塌。
2. 只保留白名单标签：`div / p / img / strong / h1 / h2 / br / blockquote / span / table / tr / td`。多列布局用 `table`。
3. 外链资源会失效：字体、CSS、JS 一律不引；图片走 `data:image/png;base64,…`。
4. 图片双轨：HTML 内嵌 base64 保证本地预览自包含，同时输出独立 PNG 供后台手动上传（粘贴时编辑器不一定接管 base64）。
5. 图注与图片分离：`<p><img …></p>` + 一个居中小字 `<p>` 作图注；`figure/figcaption` 不被保留。
6. 页面容器由主题 `page` 决定（`max_width / padding / font_size / line_height / letter_spacing`），背景取 `page_bg`。

这些事实对应 S01–S05，由 `validate_article.py` 判定，不靠人记。

## 槽位边界

组件样式的名字是固定的一组，渲染器只认这些键。新增组件＝先加槽位、再写模板，不允许某一篇独有样式。

| 类别 | 槽位 |
|---|---|
| 页面 | `page.max_width / padding / font_size / line_height / letter_spacing` |
| 文本 | `paragraph`、`lead`、`h3`、`caption`、`highlight` |
| 块 | `quote`、`card`、`aside`、`aside_title`、`tip`、`list_item` |
| 头部 | `kicker`、`title`、`subtitle`、`meta`、`meta_label`、`divider` |
| 表格 | `th`、`td`、`td_alt` |
| 文末 | `source`、`source_heading`、`source_item` |
| 代码 | `code`（六槽位 + label / header_bg / dots / radius） |
| 骨架 | `html.head / takeaways_head / takeaway_item / closing / source / figure / figure_caption / table / code` |

`aside` 是「区块」：把一组内容（通常一张图加一句说明）收进带边框的容器，用来和上下文分开。它承担分组，不承担强调；全篇最多两处、不嵌套（S24）。图与图注是两个槽位（ / ），因为图注要留在框外（S26）。

## 主题文件

```
assets/themes/<id>/theme.json
  tokens   语义色板（primary / accent / ink / body / muted / muted_dark / surface / border / page_bg / radius / font_stack …）
  page     页面参数
  styles   上面那张槽位表的样式串，{token} 占位符在渲染时求值
  html     骨架模板，{{field}} 占位符由渲染器填
  code     代码框六槽位与各段样式
```

同一份 IR 换主题就能重出稿，说明版式确实在主题里而不在文档里。

**一篇只引用一个 `theme.json`**；章节头骨架全篇一致；单节不套独立主题或异色背景（区块除外，且受 S24 约束）。

六套主题的清单、风格配方、色系映射与派生算法见 [`themes.md`](./themes.md)；对比度与六槽位由 `check_themes.py`、`derive_palette.py --audit-themes` 判定。

## 画布

| 类型 | 画布 | 2× 输出 |
|---|---|---|
| 头图 | 1080×460 | 2160×920 |
| 正文对比／清单图 | 1080×600 ~ 1080×660 | 2160×1200 ~ 2160×1320 |

宽度固定 1080，高度按内容定；`html, body` 固定宽高并 `overflow:hidden`，避免截图留白。配图规则见 [`rules.md`](./rules.md)。

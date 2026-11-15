# 主题与配色

公众号排版不是「换一套颜色」，而是一套**设计语言**：字阶与行高、章节头骨架、卡片形状、代码框结构、装饰元素共同决定读感。本 skill 把每套设计语言拆成两半：

- **骨架（skeleton）**：几何与节奏 —— 圆角/直角、章节头结构、代码框头部、虚线/实线、序号大小、留白尺度。
- **语义 token（tokens）**：颜色 —— 纸底、面、边框、墨色、正文、muted、主色、强调色，以及代码框六槽位。

换色相只改 token；换风格只换骨架。两件事不混在一起，用户给一个主色时才不会得到「同一张脸换了口红」。

## 一、六套内置主题

全部在 `assets/themes/<id>/theme.json`，`build_article.py --list-themes` 可打印。

| id | 中文名 | 一句话风格 |
|---|---|---|
| `ink-tangerine` | **墨蓝橘笺**（默认） | 深藏蓝压阵、橘色点睛的经典杂志笺：留白克制，信息卡与引用块用暖白纸面。 |
| `moyu-green` | 摸鱼绿 | 轻盈通透的薄荷纸：薄荷浅底、圆角卡片、荧光笔式强调，像一份清爽的团队手册。 |
| `moyu-ticket` | 摸鱼票据风 | 黑框纸票据：直角黑边、撕边虚线、错位硬阴影，像一张能撕下来贴工位的操作票。 |
| `olive-journal` | 橄榄手记 | 米白纸面手账：橄榄灰纸色、墨色标题条、橙色圆点与细线，像一页认真标注的笔记。 |
| `zen-whitespace` | 留白禅意风 | 大留白灰绿：细发丝线、衬线标题、几乎不用色块，靠字距与留白建立节奏。 |
| `graphite-minimal` | 石墨极简风 | 无彩灰阶层级：黑白灰三档、超大幽灵序号、左侧细线，只用极少量橙色做锚点。 |

### 关键 token

| 主题 | primary | accent | ink | body | surface | border | page_bg | radius |
|---|---|---|---|---|---|---|---|---|
| ink-tangerine | `#20344F` | `#E27145` | `#20344F` | `#3F3F3F` | `#FAF8F4` | `#C9CDD3` | `#FFFFFF` | 6px |
| moyu-green | `#059669` | `#FDE68A` | `#111827` | `#374151` | `#F0FDF4` | `#E5E7EB` | `#FFFFFF` | 8px |
| moyu-ticket | `#059669` | `#A7F3D0` | `#1A1A1A` | `#555555` | `#FFFEF8` | `#1A1A1A` | `#FFFFFF` | 0 |
| olive-journal | `#1E1F23` | `#ED7B2F` | `#23251D` | `#4D4F46` | `#EEEFE9` | `#BFC1B7` | `#FDFDF8` | 6px |
| zen-whitespace | `#4A5D52` | `#B5C8BC` | `#2B2B2B` | `#525252` | `#F7F9F8` | `#E8E8E8` | `#FFFFFF` | 0 |
| graphite-minimal | `#52525B` | `#F97316` | `#27272A` | `#52525B` | `#F4F4F5` | `#E4E4E7` | `#FFFFFF` | 0 |

### 代码框六槽位（按各成品实测取值，不统一成一套灰）

| 主题 | 底 bg | 代码字 text | 关键字 keyword | 注释 comment | 边框 border | 左强调 accent | 语言标签 label | 代码头 |
|---|---|---|---|---|---|---|---|---|
| ink-tangerine | `#F4F2ED` | `#1F2933` | `#A85632` | `#5F6B78` | `#D6D0C5` | `#20344F` | `#A85632` | 同底 |
| moyu-green | `#D1FAE5` | `#04110C` | `#047857` | `#4F6B60` | `#6EE7B7` | `#059669` | `#047857` | 同底 + mac dots |
| moyu-ticket | `#F0FDF4` | `#1A1A1A` | `#047857` | `#666666` | `#1A1A1A` | `#059669` | `#047857` | 虚线分隔 + mac dots |
| olive-journal | `#FDFDF8` | `#23251D` | `#B05A16` | `#65675E` | `#BFC1B7` | `#ED7B2F` | `#ED7B2F` | `#1E1F23` 深墨窄条 |
| zen-whitespace | `#EEF3F0` | `#2B2B2B` | `#3D5046` | `#62665E` | `#E8E8E8` | `#4A5D52` | `#3D5046` | 同底，无圆角 |
| graphite-minimal | `#F4F4F5` | `#27272A` | `#3F3F46` | `#6B6B75` | `#E4E4E7` | `#3F3F46` | `#3F3F46` | 同底，大写 lang |

> `keyword` 画在浅色代码底上（行内 `**关键字**`），`label` 画在代码头上。两者分开取值：橄榄手记的 `keyword` 必须压深到 `#B05A16`（对 `#FDFDF8` 4.76:1），`label` 保持 `#ED7B2F` 配深墨头（对 `#1E1F23` 5.86:1）。其余五套代码头同底，`label` 与 `keyword` 同值。
>
> 六槽位之外还有 `header_bg`、`dots`（mac 三色圆点）与各自 `frame/header/label/body/line/comment/keyword` 样式串。样式串里的颜色全部写成 `{code_*}` 占位符，由 `Theme` 在构建时解析，所以改一处颜色就能整套联动。

## 二、六套风格配方（设计语言）

这些配方用于**选骨架**，不是配色表。用户提到对应关键词时优先套用。

### 墨蓝橘笺 · ink（默认）

- 骨架：6px 圆角、暖白纸面；页面 677px 宽、`24px 20px 56px` 内边距、正文 16px / 行高 1.85 / 字距 0.3px；章节头是「深蓝方块编号（padding 3px 10px、13px、3px 圆角、字距 1px）+ 全角空格 + 20px 深蓝粗体标题」，段距上 38px / 下 16px；金句引用是 4px 橘色左线 + `#FAF8F4` 暖白底 + 17px / 1.85；提示卡是 4px 深蓝左线 + 6px 圆角；分割线 `● ● ●`（14px、字距 6px、`#C9CDD3`）；文末 CTA 是深蓝底、17px / 1.9、6px 圆角；表格表头深蓝底白字，偶数行铺暖白。
- 配色关系：`#20344F` 深藏蓝压阵（标题、表头、代码左条、文末 CTA），`#E27145` 橘只做点睛（kicker、引用左线、带走编号、强调小字），暖白 `#FAF8F4` 铺引用、卡片、资料与偶数行，正文 `#3F3F3F`，灰阶 `#8A94A0 / #5A6675 / #C9CDD3`；全篇双色以内。代码框是米底 `#F4F2ED` + 深字 `#1F2933` + 4px 深蓝左条，语言标签 `#A85632`。
- 适合：工作汇报、行业与竞品分析、方法论长文、正式访谈与案例拆解、品牌与产品发布稿——需要「稳、可信、能转发给同事」的场合。
- 不要用错：深蓝方块编号 + 暖白卡片密度偏高，章节多时重复感强，少于 4 节的短图文会显得板正；橘色只能点睛，拿它铺大面积会立刻失掉克制；不适合轻松娱乐、年轻化种草、强视觉冲击的选题。与橄榄手记只共享 6px 圆角与暖白面块：橄榄纸底本身是米白 `#FDFDF8`，本套纸底纯白 `#FFFFFF`、暖白只在面块里；章节头橄榄用「24px 数字 + PART + 竖线」和墨色标题条，本套用深蓝方块 + 深蓝粗体标题，两套骨架不能混用。

### 摸鱼绿 · green

- 骨架：8px 圆角、浅绿面、卡片底色 `#F0FDF4`；章节头是「28px 大号数字 + PART 小标 + 竖线 + 标题」；转折处用 `///`。
- 配色关系：paper 白 → surface 极浅绿；accent 用高明度暖黄（荧光笔），不压深；代码底是中等饱和薄荷，关键字压深到可读深绿。
- 适合：团队手册、效率工具、运营 SOP、轻量教程。
- 不要用错：正文行高 1.75 偏紧，长论述段落多时要慎用。

### 摸鱼票据风 · ticket

- 骨架：全直角（radius 0）、`#1A1A1A` 黑边、5px 错位硬阴影、虚线撕边；章节头是黑边底 + 绿方块编号 + 粗体标题；代码头用虚线分隔。
- 配色关系：纸面 `#FFFEF8` 微暖白；黑白为主，绿只做编号与强调；代码底浅绿，边框回到纯黑让票据感成立。
- 适合：清单、检查表、操作票、活动规则、复古印刷感选题。
- 不要用错：黑边密度高，图多或表多时容易糊；适合结构简单的内容。

### 橄榄手记 · olive

- 骨架：6px 圆角、米白纸面 `#FDFDF8`、橄榄灰面 `#EEEFE9`；章节头 24px 数字 + PART + 竖线 + 20px 标题；文末 CTA 用深墨双框；资料来源是墨色标题条。
- 配色关系：primary 是墨色（不是彩色），橙色 `#ED7B2F` 只做圆点、细线与强调；代码框是米白底 + 深墨窄头 + 橙关键字。
- 适合：读书笔记、方法论拆解、编辑感强的长文、访谈整理。
- 不要用错：整篇偏暖偏灰，写技术参数时对比度要盯紧。

### 留白禅意风 · zen

- 骨架：全直角、32px 上下留白、1.9 行高；章节头是 `01 · SETUP` kicker + 22px 衬线标题 + 40px 短线；文末收束用 blockquote。
- 配色关系：灰绿 `#4A5D52` 做主色，accent 是低饱和的 `#B5C8BC`，几乎不用色块；代码框无圆角、左侧 2px 细线。
- 适合：观点长文、哲学/设计/学术向、极简产品介绍。
- 不要用错：信息密度必须低；表格和代码多时会破坏留白节奏。

### 石墨极简风 · graphite

- 骨架：全直角、34px 上下留白；章节头是 48px 幽灵数字 + 10px 大写 kicker + 20px 标题 + 底边线；代码框左侧 3px 深灰线。
- 配色关系：无彩灰阶（`#27272A` / `#52525B` / `#F4F4F5` / `#E4E4E7`），橙色 `#F97316` 只做极小锚点；代码关键字也是灰阶，不抢色。
- 适合：技术文档、架构说明、代码教程、冷峻品牌稿。
- 不要用错：无彩色容易显得没有情绪，观点型长文需要靠标题与图来提气。

## 三、用户给色系／氛围时怎么选骨架

**原则：色系名只决定色相，骨架决定设计语言。** 不要拿「绿色」就只换 hue 而留原骨架，也不要拿「沉稳」就一律用墨蓝橘笺。

### 色系词 → 推荐骨架

| 用户说 | 推荐骨架 | 理由 |
|---|---|---|
| 绿、薄荷、清爽、自然 | `green` | 薄荷浅面 + 荧光强调本来就是绿系语言 |
| 墨绿、灰绿、竹、禅 | `zen` | 低饱和灰绿 + 大留白 |
| 橄榄、卡其、米色、手账 | `olive` | 米白纸面 + 墨色标题条 |
| 蓝、藏蓝、沉稳、正式 | `ink` | 深蓝压阵 + 暖白纸面 |
| 黑、灰、银、极简、技术 | `graphite` | 无彩灰阶 + 幽灵序号 |
| 赭、棕、牛皮纸、复古、票据 | `ticket` | 暖白纸 + 黑边票据 |
| 橙、暖调、编辑感 | `olive` 或 `ink` | 橙在橄榄是圆点，在墨蓝是点睛 |

### 氛围词 → 骨架

| 氛围 | 骨架 |
|---|---|
| 沉稳、正式、汇报、杂志感 | `ink` |
| 清爽、活力、轻快、团队 | `green` |
| 纸感、复古、票据、规则 | `ticket` |
| 手账、暖调、笔记、编辑 | `olive` |
| 克制、学术、留白、安静 | `zen` |
| 冷峻、极简、工程、文档 | `graphite` |

### 只给一个主色 HEX

按 HLS 判断，再让用户确认骨架：

- 饱和度 < 5% → 无彩色，骨架默认 `graphite`（石墨）或 `zen`（偏亮灰）。
- 色相 90°–165°（绿/青）→ `green` 或 `zen`。
- 色相 20°–45°（橙/赭/棕）→ `olive` 或 `ticket`。
- 色相 200°–250°（蓝）→ `ink`。
- 其他（红/紫/黄）→ 先问用途，再按氛围选；不要默认塞进 `ink`。

## 四、派生算法（`scripts/derive_palette.py`）

输入：一个主色 HEX + 一个骨架名。输出：完整语义 token、代码框六槽位（含 header）与逐项对比度报告。

### Step 1 归一化输入

- HEX 接受 `#RGB` / `#RRGGBB`，非法值直接报错退出。
- 色系词/氛围词先按第三节映射到骨架，再取一个代表色 HEX（或让用户给 HEX）。

### Step 2 保留骨架，只换色相

骨架参数写在 `SKELETONS` 里：`surface_l / surface_s`（面亮度与饱和）、`paper`（白纸或染色纸）、`code_bg_l / code_bg_s`（代码底）、`accent` 类型（`fixed` / `warm_tint` / `tint` / `complement`）、`code_border_l`。派生时这些**结构参数不变**，只把主色的色相 `h` 代进去。

### Step 3 派生语义 token（同族关系）

| token | 关系 |
|---|---|
| `page_bg` | 白纸骨架取 `#FFFFFF`；`tinted` 骨架取主色色相、极低饱和（约 1–3%）、明度 0.987 |
| `surface` | 主色色相，饱和 `surface_s × (0.35 + 0.65 × tint)`，明度 `surface_l`（0.94–0.98） |
| `surface_alt` | 同上但更浅（`surface_l + 0.022`） |
| `border` | 主色降饱和到 10–30%，明度 0.82 |
| `border_accent` | 主色再降饱和，明度 0.76，用于强调边框 |
| `ink` | 主色色相，饱和 16%，明度 0.13（近墨） |
| `body` | 主色色相，饱和 8%，明度 0.16 |
| `muted` | 主色色相，饱和 6%，明度 0.62（装饰用） |
| `muted_dark` | 主色色相，饱和 7%，明度 0.44（可读弱化字） |
| `primary` | 用户主色保留色相，饱和不低于 45%，再按对比度压深 |
| `accent` | 按骨架：`graphite` 固定暖橙、`green` 固定高亮黄、`ink`/`olive` 暖橙、`ticket`/`zen` 主色浅色调 |

其中 `tint = min(1, s × 2.2)` 让高饱和主色得到更明显的染色，低饱和主色不至于把纸面染脏。

### Step 4 代码框六槽位

| 槽位 | 关系 |
|---|---|
| `bg` | 主色色相，饱和 `code_bg_s × (0.5 + 0.5 × tint)`，明度 `code_bg_l`（0.90–0.99） |
| `text` | 主色色相，饱和 10%，明度 0.12，再压到对 `bg` ≥ 12:1 |
| `keyword` | `olive`/`ink` 固定暖橙（0.075 色相，80% 饱和）；其余用主色色相、饱和 ≥ 55%；明度 0.42 起，压到 ≥ 4.5:1 |
| `comment` | 主色色相，饱和 8%，明度 0.40 起，压到 ≥ 4.5:1 |
| `border` | 主色色相降饱和，明度按骨架 `code_border_l`（0.76–0.91） |
| `accent`（左条） | 取 `primary`，对代码底 ≥ 3:1 |
| `label`（语言标签） | 默认同 `keyword`；深色代码头骨架用暖橙（0.075 色相、80% 饱和）提亮到对 `header_bg` ≥ 4.5:1 |
| `header_bg` | 默认同 `bg`；`olive` 骨架用 `#1E1F23` 深墨窄条 |

**关键字与标签分开派生**：`keyword` 画在浅色代码底上（行内 `**关键字**`），`label` 画在代码头上，两者不能共用一个颜色。深色头骨架若提亮后的 `label` 仍达不到 4.5:1，才把 `header_bg` 改回 `code_bg` 并补一条底边线；**不得为了保住深色头而让标签或关键字低于门槛**。

### Step 5 对比度门槛

按 WCAG 相对亮度（sRGB 线性化后加权 0.2126 / 0.7152 / 0.0722）计算：

| 检查项 | 门槛 |
|---|---|
| `body` / `page_bg` | ≥ 12:1 |
| `ink` / `page_bg` | ≥ 12:1 |
| `primary` / `page_bg` | ≥ 4.5:1 |
| `accent` / `page_bg` | ≥ 3:1（仅 `green`，荧光笔不高亮就不像荧光笔）；其余 ≥ 4.5:1 |
| `code_text` / `code_bg` | ≥ 12:1 |
| `keyword` / `code_bg` | ≥ 4.5:1 |
| `comment` / `code_bg` | ≥ 4.5:1 |
| `label` / `header_bg` | ≥ 4.5:1 |
| `muted_dark` / `page_bg` | ≥ 4.5:1 |

不达标时用 `darken_to()` 沿 HLS 的 L 轴每步 −0.005 压深，直到达标或 L ≤ 0.04；深色头上的 `label` 用 `lighten_to()` 提亮。**只调明度，不用加粗、放大字号或浅色硬凑**。

### Step 6 输出

- 终端：骨架、主色映射、palette、代码六槽位、逐项对比度与 `ALL PASS` / `FAILED`。
- `--json`：同一份数据的 JSON，便于脚本消费。
- `--write-theme <path>`：克隆骨架 `theme.json`，替换 token 与代码槽位、改写代码头背景，产出可直接 `--theme-path` 使用的主题文件（带 `derived_from` 与 `recipe`）。

## 五、用法与示例

```bash
python scripts/derive_palette.py --list-skeletons
python scripts/derive_palette.py --primary "#A8551F" --skeleton olive --name "赭石手记"
python scripts/derive_palette.py --primary "#2F6B5F" --skeleton zen --name "松烟青" --json
python scripts/derive_palette.py --primary "#A8551F" --skeleton olive \
    --name "赭石手记" --id zheshi-journal --write-theme themes/zheshi-journal/theme.json
```

### 示例：非内置主题的赭石手记（主色 `#A8551F` + olive 骨架）

```
SKELETON  olive  (橄榄手记 · 手账 / 暖调 / 编辑感)
PRIMARY   #A8551F → #A8551F

PALETTE
  primary        #A8551F
  accent         #C0550F
  ink            #26201C
  body           #2C2826
  muted          #A49D98
  muted_dark     #786F68
  surface        #F2F1F0
  surface_alt    #F7F6F6
  border         #DCCFC6
  border_accent  #E3BBA0
  page_bg        #FCFCFC

CODE BOX · 六槽位（底 / 字 / 关键字 / 注释 / 边框 / 左条）
  底 bg                 #FCFCFC
  代码字 text           #221E1C
  关键字 keyword        #B35C13
  注释 comment          #6E645E
  边框 border           #D2C5BC
  左侧强调 accent       #A8551F
  语言标签 label        #E88330
  代码头 header         #1E1F23

CONTRAST
  正文 body / 纸底 page_bg          14.23:1  ≥12.0 PASS
  墨色 ink / 纸底 page_bg           15.68:1  ≥12.0 PASS
  主色 primary / 纸底 page_bg        5.14:1  ≥4.5  PASS
  辅助色 accent / 纸底 page_bg        4.50:1  ≥4.5  PASS
  代码字 text / 代码底 bg            16.11:1  ≥12.0 PASS
  关键字 keyword / 代码底 bg          4.59:1  ≥4.5  PASS
  注释 comment / 代码底 bg            5.61:1  ≥4.5  PASS
  语言标签 label / 代码头 header       6.05:1  ≥4.5  PASS
  弱化字 muted_dark / 纸底            4.79:1  ≥4.5  PASS

RESULT   ALL PASS
```

关键字压到 `#B35C13`（浅底 4.59:1），语言标签单独提亮到 `#E88330`（深墨头 6.05:1），深色头因此保留。对照内置橄榄手记：`keyword #B05A16`（4.76:1）、`label #ED7B2F`（5.86:1）。**结构和颜色可以按骨架变，读不清不行。**

## 六、出稿与验收

```bash
# 内置主题
python scripts/build_article.py --content content.json --figures-dir figures \
    --theme moyu-green --out dist

# 派生主题
python scripts/build_article.py --content content.json --figures-dir figures \
    --theme-path themes/zheshi-journal/theme.json --out dist

python scripts/validate_article.py dist/wechat-article.html --expect-figures 4
```

换主题只改渲染层，不动 IR；同一份 `content.json` 可以并行出多套稿。验收必须回到 `validate_article.py` 的 0 ERROR，再截图看首屏与文末（表格、代码框、图注三处最容易露馅）。

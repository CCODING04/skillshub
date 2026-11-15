# 硬约束规则表（lint / CI）

## 为什么需要两套规则

2026-11-13 实测了两份由其他 agent 用本 skill 生成的公众号 HTML。两者的**排版结构全部合规**（0 个 `<style>`、0 个 class、187／190 处内联样式、4 张 2× base64 图全带 alt），旧版 13 项校验全部通过；但仍缺了人一眼能看出的内容要求：作者履历引子、外文术语简注、Markdown 过程附录。

结论：**结构合法 ≠ 内容达标**。只查标签的 lint 会给出虚假的安全感，所以规则分成两级：

- `error`：机器可判定、错了就一定不该交付 → 永远阻塞。
- `warning`：内容质量启发式 → 普通模式只提示，`--strict`（CI 默认）下阻塞。

## 运行

```bash
# 门禁（CI 用，warning 也阻塞）
python scripts/ci_check.py --html dist/wechat-article.html --md dist/article.md \
  --ir content.json --out dist
# 单跑 lint（旧 13 项仍兼容）
python scripts/validate_article.py dist/wechat-article.html --expect-figures 4
# 完整严格模式
python scripts/validate_article.py dist/wechat-article.html --strict --md dist/article.md \
  --ir content.json --rules-out dist/lint-report.json
# 调阈值（只能放宽数值，不能关闭 error 级规则）
python scripts/ci_check.py --html ... --config lint-config.json
```

产物：`ci-report.json`（门禁结论 + 每条失败规则的修复建议）、`lint-report.json`（全部规则与统计）。退出码 0 通过 / 1 失败，可直接接 CI。

## error 级：结构硬约束

| ID | 规则 | 判定 | 拦住什么 |
|---|---|---|---|
| S01 | 无 `<style>` | 出现数 = 0 | 微信过滤样式表 |
| S02 | 无 class | 出现数 = 0 | 微信过滤 class |
| S03 | 无禁用标签 | section/figure/figcaption/script/iframe/link = 0 | 粘贴后塌陷 |
| S04 | 标签白名单 | 无白名单外标签 | 编辑器兼容 |
| S05 | 无外链资源 | src/href 不含 http(s) | 图片与字体失效 |
| S06 | 内联样式密度 | `style=` ≥ 20 | 「一个容器撑全篇」的退化版式 |
| S07 | 至少一张图 | img ≥ 1 | 漏配图 |
| S08 | 图片全部内嵌 | img 数 = base64 数 | 破图 |
| S09 | 图片数符合预期 | 与 `--expect-figures` 一致 | 漏图／多图 |
| S10 | 图片自适应 | 每个 img 含 `width:100%` | 移动端溢出 |
| S11 | 有引用块 | blockquote ≥ 1 | 版式层级缺失 |
| S12 | 无占位符 | 不含 `{{` | 模板没填完 |
| S13 | 有来源说明 | 含「资料来源／整理说明」 | 读者无从溯源 |
| S14 | 组件级内联覆盖率 | 长文 ≥ 95%、短稿 ≥ 90%（按正文中文字数 1500 分档） | 部分元素粘贴后丢样式 |
| S15 | 段落密度 | `<p>` ≥ 20 | 用 `<br>` 堆排版 |
| S16 | 图片 alt | 每个 img 有 alt | 无障碍与图注缺失 |
| S17 | 配图为高清 | base64 PNG 宽 ≥ 2000（2× 1080） | 低清／未走渲染脚本 |
| S18 | 每图有图注 | 每个 `<p><img></p>` 后紧跟含「图/封面/示意」的 `<p>` | 图不知在回答什么 |
| S19 | 无连续 `<br>` | 连续 br = 0 | 伪段落 |
| S20 | 无内部流程词 | 正文不含 S0-A / feasibility / base64 / content.json / 拍板 等 | 把流程黑话写给读者 |
| S21 | 正文长度 | 中文字符 ≥ 1500 | IR 漏 sections／空稿 |
| S22 | 相邻图之间要有文字 | 任意两张紧邻的图之间，非图注的中文字符 ≥ 40 | 两图连排＝信息密集区没有过渡，读者在手机上会直接滑过去 |

## warning 级：内容质量（`--strict` 下阻塞）

| ID | 规则 | 判定 | 依据 |
|---|---|---|---|
| C01 | 作者／讲者引子 | 正文前 800 字含人名 + 履历线索（曾在／加入／工程经理／核心开发…）；提供 `--ir` 且为演讲/访谈类时升级为 error | 演讲类文章需以讲者公开履历或高光经历起笔 |
| C02 | 外文术语简注 | 形如 `英文（含中文）` 的简注 ≥ 8 处（出处型括号不计入目标） | 外部读者不应被假设看过原始材料；下限由项目约定，复审见规则注册表 |
| C03 | 文末来源说明形态 | 2–6 条 + 含来源标识 + 含 ≥2 个「非逐字／书面化／自拟／整理者」 | 面向外部读者要简洁，细节留给 Markdown |
| C04 | Markdown 过程附录 | `--md` 文件含「整理过程与回溯」 | 便于落盘回溯（IR 的 `process_appendix`） |
| C05 | 信息卡不泄露内部口径 | 前 1200 字不含「口径／拍板／S0-／reader_notes」等 | 口径属内部信息，应放存档版 |

## 调整阈值

`lint-config.json` 可覆盖：`min_inline_styles`、`min_paragraphs`、`min_component_inline_rate`、`min_glossary_notes`、`min_caveat_words`、`foot_bullets_min/max`、`min_png_width`、`min_zh_chars`、`internal_jargon`。

**不允许**通过配置把某条 error 规则整体关闭——这会让门禁失去意义。若某规则确实不适用，应在 `ci-report.json` 里记录豁免理由，由人确认，而不是静默跳过。

## 主题与阈值（N1）

风格/配色统一由 `assets/themes/` 六套主题管理（`--theme`），`style-presets` 体系已删除。lint 阈值**不随主题变化**：`check_themes.py` 校验主题 schema、模板占位符、代码六槽位与对比度，`derive_palette.py --audit-themes` 审计配色，两者结果都进 `ci_check.py` 门禁。任何按主题调整阈值的做法都必须写进 `lint-report.json`，不静默跳过。

## 长短稿 profile

`validate_article.py` 按正文中文字数自动分档（阈值 1500 字），并在 `lint-report.json` 的 `profile` 里显式写出档位与每一项放宽值：

| 项 | 长文（默认） | 短稿 |
|---|---|---|
| `min_zh_chars` | 1500 | 400 |
| `min_glossary_notes` | 8 | 3 |
| `min_paragraphs` | 20 | 8 |
| `min_inline_styles` | 20 | 10 |
| `min_component_inline_rate` | 0.95 | 0.90 |

组件演示用的示例 IR 会被判为 short；**真实任务按长文处理**，不要拿示例稿的字数判断任务篇幅。

## 长短稿 profile

`validate_article.py` 按正文中文字数自动分档（阈值 1500 字），并在 `lint-report.json` 的 `profile` 里显式写出档位与每一项放宽值：

| 项 | 长文（默认） | 短稿 |
|---|---|---|
| `min_zh_chars` | 1500 | 400 |
| `min_glossary_notes` | 8 | 3 |
| `min_paragraphs` | 20 | 8 |
| `min_inline_styles` | 20 | 10 |
| `min_component_inline_rate` | 0.95 | 0.90 |

组件演示用的示例 IR 会被判为 short；**真实任务按长文处理**，不要拿示例稿的字数判断任务篇幅。

## 规则的边界

lint 能查「有没有」「数量够不够」，查不了「写得对不对」。讲者履历是否属实、术语解释是否准确、引语是否忠实原意，仍需要人看。把 lint 当门禁，别当审稿人。

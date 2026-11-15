# 规则清单

> 本文件由 `scripts/render_rules_doc.py` 从 `assets/rule-registry.json` 生成，
> 不要手改。改规则请改注册表或代码，然后重跑生成脚本；`ci_check.py` 会比对两者是否一致。

共 32 条。规则分五层，层级决定它能不能被豁免：

- **L0** 平台事实（微信编辑器行为，永不豁免）
- **L1** 结构契约（成稿形态，可豁免但须人签字）
- **L2** 可计量启发式（阈值，来自实测或反馈，定期复审）
- **L3** 口径意图（由人在 S0-B 决定，不入自动判定）
- **L4** 元规则（关于规则本身的规则）

| ID | 层级 | 要求 | 不满足时怎么改 | 执行位置 |
|---|---|---|---|---|
| C01 | L2 | 开头有作者或讲者的履历 | 开头补作者/讲者的公开履历引子，并明确标注与正文来源分开 | `validate_article.py`（CI 门禁内容级，`--strict` 下阻塞） |
| C02 | L2 | 外文术语带中文简注 | 外文术语首次出现补中文简注，如 PR（代码合并请求）、lint（静态检查规则） | `validate_article.py`（CI 门禁内容级，`--strict` 下阻塞） |
| C03 | L2 | 文末来源说明简洁可溯源 | 文末来源说明保持 2–6 条，含来源标识与书面化/非逐字声明 | `validate_article.py`（CI 门禁内容级，`--strict` 下阻塞） |
| C04 | L2 | Markdown 带整理过程附录 | 在 content.json 写 process_appendix，让 article.md 带上「整理过程与回溯」 | `validate_article.py`（CI 门禁内容级，`--strict` 下阻塞） |
| C05 | L2 | 信息卡只放读者需要的信息 | 把内部口径移到 Markdown 附录，不要放读者可见的信息卡 | `validate_article.py`（CI 门禁内容级，`--strict` 下阻塞） |
| F01 | L1 | 图里写清主体，不用代词 | 把「她/他」换成具体人名、团队名或产品名；引语确需保留原话时，在图表 HTML 里写 <!-- allow-pronoun: 理由 --> | `render_figures.py`（渲染前拦截，不通过不出图） |
| S01 | L0 | 样式全部内联在元素上 | 移除 <style> 标签，全部样式写成内联 style | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S02 | L0 | 样式只走 style 属性 | 移除 class，改用内联 style | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S03 | L0 | 只使用微信编辑器保留的标签 | 替换 section/figure/figcaption/script 等微信不保留的标签 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S04 | L1 | 标签限于白名单 | 只使用白名单标签（div/p/img/strong/h1/br/blockquote/span 等） | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S05 | L0 | 资源全部内嵌 | 去掉外链 CSS/字体/JS，图片改 base64 内嵌 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S06 | L1 | 组件级内联样式达到下限 | 用组件级内联样式，不要只给最外层容器一个 style | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S07 | L1 | 至少一张自制信息图 | 至少生成一张自制信息图 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S08 | L1 | 图片数与内嵌数一致 | 图片数必须与 base64 内嵌数一致 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S09 | L1 | 图片数与 figures 清单一致 | 检查 figures 清单与实际图片数 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S10 | L1 | 每张图宽度自适应 | 给每个 img 的 style 补 width:100% | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S11 | L1 | 至少一处引用块 | 至少保留一处金句引用块 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S12 | L1 | 占位符全部替换 | 替换所有 {{...}} 占位符 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S13 | L1 | 文末有来源说明 | 补「资料来源与整理说明」 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S14 | L1 | 组件内联覆盖率达到下限 | 给每个 p/div/blockquote/h1/span/strong 补内联 style | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S15 | L1 | 段落密度达标 | 用 <p> 分段，不要用连续 <br> 堆排版 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S16 | L1 | 每张图带 alt 文本 | 给每张图补 alt 文本 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S17 | L1 | 配图按 2 倍输出 | 用 render_figures.py 以 --scale 2 重新渲染配图 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S18 | L1 | 每张图后有图注 | 每张图后紧跟一个图注 <p>（含「图 N ｜…」或「封面…」） | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S19 | L1 | 段落用 p 分隔 | 去掉连续 <br> | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S20 | L1 | 正文用读者语言，不出现内部流程词 | 删掉正文里的内部流程词（S0-A / feasibility / base64 / content.json 等） | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S21 | L1 | 正文长度达标 | 正文过短，检查 IR 是否漏了 sections | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S22 | L1 | 相邻两图之间有一段正文 | 两张图挨在一起了：在它们之间补一段正文（图注不算过渡），或删掉信息重复的那张 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S23 | L1 | 图注不复述它前面的小标题 | 图注换个说法：写出这张图在说什么，命名交给它上面的小标题 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S24 | L1 | 区块不超过两处且不嵌套 | 区块最多两处且不能套叠：只把确实需要分开的一组内容收进框 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S25 | L1 | Markdown 归档包含全部图注 | 检查 build_article.py 的 Markdown 分支是否处理了这个块类型（aside 必须递归） | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |
| S26 | L1 | 图注在图片下方、区块之外 | 把图注移出区块容器，紧跟图片之后；框里只放图本身 | `validate_article.py`（CI 门禁 error 级，`--strict` 下 warning 也阻塞） |

## 待复审

以下规则来自单次反馈，尚未第二次验证；复审前不作为永久依据：

- **C01** 开头有作者或讲者的履历（单次反馈，未经第二类来源验证；适用范围待确认）
- **C02** 外文术语带中文简注（单次反馈；阈值需定期复审）
- **C03** 文末来源说明简洁可溯源（单次反馈；条数为约定值）
- **C04** Markdown 带整理过程附录（单次反馈；存档版为可选能力）
- **C05** 信息卡只放读者需要的信息（单次审核发现；适用范围待确认）

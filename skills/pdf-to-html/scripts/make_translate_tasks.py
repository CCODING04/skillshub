# -*- coding: utf-8 -*-
"""Split translatable blocks into N task files with a shared glossary."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
blocks = json.load(open(os.path.join(ROOT, "temp", "blocks.json"), encoding="utf-8"))

GLOSSARY = """统一术语表（翻译时必须遵守，保证全文一致）：
- AI agent(s) → AI 智能体（首次可写“AI 智能体（AI agent）”）；agent → 智能体
- agentic → 智能体性/具备智能体特征（agentic 保留可附注）
- benchmark → 基准测试（或“基准”）；leaderboard → 排行榜
- accuracy → 准确率；cost → 成本；inference cost → 推理成本
- Pareto curve / Pareto frontier → 帕累托曲线 / 帕累托前沿
- SOTA (state-of-the-art) → 当前最优（SOTA）；保留 SOTA 缩写
- baseline → 基线；joint optimization → 联合优化
- holdout / hold-out set → 留出集（可首次附 holdout）；overfitting → 过拟合
- few-shot → 少样本（few-shot）；zero-shot → 零样本（zero-shot）
- prompt → 提示词；temperature → 温度（temperature）
- token → token（不翻译，保留英文）
- embedding → embedding（不翻译，保留英文）
- retrieval / RAG → 检索 / RAG（检索增强生成）
- LLM → 大语言模型（LLM）
- GPT-3.5 / GPT-4 / Llama-3 等模型名 → 保留英文
- 论文名、框架名（DSPy、ColBERTv2、WebArena、HumanEval、HotPotQA、NovelQA 等）→ 保留英文
- reproducibility → 可复现性；standardization → 标准化
- System 2 → 系统 2（System 2）
- case study → 案例研究；distribution → 分布；in/out-of-distribution → 分布内/分布外
- 度量单位 USD、美元符号、数值、置信区间、引用编号 [n] → 原样保留

翻译风格要求：
1. 忠实原意，学术书面语，通顺中文。不要遗漏任何句子。
2. 不确定的专业词可不翻译，保留英文；或在中文后加括号标注英文原词。
3. 列表项保持逐条对应；标题简洁准确。
4. 只输出 JSON，不要输出任何解释文字。"""

# translatable: heading/para/list, plus figure blocks (caption may be empty)
trans = [b for b in blocks if b["type"] in ("heading", "para", "list", "figure")]

N = 5
chunks = [trans[i::N] for i in range(N)]
# Note: strided split breaks contiguity; use contiguous split instead
size = (len(trans) + N - 1) // N
chunks = [trans[i:i+size] for i in range(0, len(trans), size)]

taskdir = os.path.join(ROOT, "temp", "translate_tasks")
os.makedirs(taskdir, exist_ok=True)

for idx, chunk in enumerate(chunks, 1):
    task = {
        "glossary": GLOSSARY,
        "instruction": "请将 input 中每个块的 text（或 caption 字段）翻译成中文，"
                       "按 id 输出 {\"id\": \"中文翻译\"}。figure 块只翻译 caption 字段（若为空则跳过，不输出该 id）。"
                       "heading 翻译标题；list 的每条列表项都要翻译并保持换行；para 整段翻译。",
        "input": [
            {"id": b["id"], "type": b["type"],
             "text": b.get("text", ""),
             "caption": b.get("caption", "")}
            for b in chunk
        ],
    }
    p = os.path.join(taskdir, "task_%d.json" % idx)
    json.dump(task, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("task_%d.json: %d blocks (%s -> %s)" % (idx, len(chunk), chunk[0]["id"], chunk[-1]["id"]))

print("total translatable:", len(trans))

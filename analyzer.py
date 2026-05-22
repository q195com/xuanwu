# -*- coding: utf-8 -*-
"""
Anti-Zhuque 文本特征分析器

纯 Python 实现，不依赖外部 AI API。
分析文本的 AI 特征指标，输出朱雀检测风险诊断报告。
"""

import re
import math
from collections import Counter
from dataclasses import dataclass, field


# ============================================================
#  AI 特征词库
# ============================================================

# 高频 AI 过渡词/连接词
TRANSITION_WORDS = [
    "此外", "另外", "而且", "同时", "与此同时",
    "然而", "不过", "尽管如此", "但是", "虽然",
    "首先", "其次", "再次", "最后", "最终",
    "总之", "综上所述", "总而言之", "概括来说",
    "值得注意的是", "需要指出的是", "不可否认",
    "事实上", "实际上", "毫无疑问",
    "一方面", "另一方面",
]

# AI 高频词汇（来自 humanizer-zh 词库 + 中文补充）
AI_BUZZWORDS = [
    "至关重要", "深入探讨", "不断演变", "格局", "关键性",
    "充满活力", "宝贵的", "持久的", "展示", "彰显",
    "培养", "增强", "突出", "相互作用", "奠定基础",
    "关键角色", "核心地位", "重要意义", "深远影响",
    "不可磨灭", "深深植根于", "独特魅力", "丰富内涵",
    "蓬勃发展", "日益增长", "广泛关注", "积极推动",
    "有效促进", "显著提升", "全面推进", "深度融合",
    "赋能", "助力", "引领", "驱动", "构建",
    "生态", "闭环", "矩阵", "抓手", "底层逻辑",
    "令人叹为观止", "坐落于", "开创性", "里程碑",
]

# 公众号文章特有的 AI 味词汇
WECHAT_AI_WORDS = [
    "干货", "硬核", "建议收藏", "强烈推荐",
    "不得不说", "说实话", "毋庸置疑",
    "一文读懂", "深度解析", "全面盘点",
    "划重点", "敲黑板",
]

# 小说写作的 AI 味词汇
NOVEL_AI_WORDS = [
    "瞳孔骤缩", "倒吸一口凉气", "冷笑一声", "嘴角上扬",
    "满场死寂", "全场震惊", "空气仿佛凝固",
    "心中暗道", "不由得", "忍不住",
    "咬了摇牙", "攥紧了拳头", "眼中闪过一丝",
]

# 否定式排比模板
NEGATION_PATTERNS = [
    r"不仅仅是.*?而是",
    r"不只是.*?更是",
    r"不仅.*?而且.*?还",
    r"这不是.*?而是",
]

# 三段式模板
TRIPLE_PATTERNS = [
    r"([\u4e00-\u9fa5]+)、([\u4e00-\u9fa5]+)和([\u4e00-\u9fa5]+)",
    r"([\u4e00-\u9fa5]+)、([\u4e00-\u9fa5]+)、([\u4e00-\u9fa5]+)",
]


# ============================================================
#  数据结构
# ============================================================

@dataclass
class RiskItem:
    """单个风险项"""
    name: str
    value: float
    threshold: float
    risk_level: str  # "高", "中", "低"
    detail: str = ""


@dataclass
class DiagnosisReport:
    """诊断报告"""
    total_chars: int = 0
    total_sentences: int = 0
    total_paragraphs: int = 0
    risks: list = field(default_factory=list)
    overall_risk: str = "低"
    score: int = 100  # 满分100, 越高越"像人写的"

    # 原始数据
    sentence_lengths: list = field(default_factory=list)
    paragraph_lengths: list = field(default_factory=list)
    hit_transition_words: list = field(default_factory=list)
    hit_ai_buzzwords: list = field(default_factory=list)
    hit_patterns: list = field(default_factory=list)


# ============================================================
#  分句/分段
# ============================================================

def split_sentences(text: str) -> list[str]:
    """中文分句：按句号、问号、感叹号、省略号分割"""
    text = text.strip()
    parts = re.split(r'([。！？…\!\?]+)', text)
    sentences = []
    i = 0
    while i < len(parts):
        s = parts[i].strip()
        if i + 1 < len(parts) and re.match(r'^[。！？…\!\?]+$', parts[i + 1]):
            s += parts[i + 1]
            i += 2
        else:
            i += 1
        cleaned = re.sub(r'[。！？…\!\?\s]', '', s)
        if len(cleaned) >= 2:
            sentences.append(s)
    return sentences


def split_paragraphs(text: str) -> list[str]:
    """分段：按空行分割（两个及以上换行符），保留多行段落"""
    paras = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paras if p.strip()]


# ============================================================
#  指标计算函数
# ============================================================

def calc_burstiness(sentence_lengths: list[int]) -> dict:
    """
    计算突发性(Burstiness)指标
    """
    if len(sentence_lengths) < 3:
        return {"std_dev": 0, "mean": 0, "cv": 0, "uniform_triplets": 0, "total_triplets": 0}

    mean = sum(sentence_lengths) / len(sentence_lengths)
    variance = sum((x - mean) ** 2 for x in sentence_lengths) / len(sentence_lengths)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean if mean > 0 else 0

    uniform_triplets = 0
    total_triplets = len(sentence_lengths) - 2
    for i in range(total_triplets):
        trio = sentence_lengths[i:i + 3]
        trio_mean = sum(trio) / 3
        if trio_mean == 0:
            continue
        max_diff = max(abs(x - trio_mean) / trio_mean for x in trio)
        if max_diff < 0.20:
            uniform_triplets += 1

    return {
        "std_dev": round(std_dev, 2),
        "mean": round(mean, 2),
        "cv": round(cv, 3),
        "uniform_triplets": uniform_triplets,
        "total_triplets": total_triplets,
    }


def calc_transition_density(text: str, word_list: list[str]) -> dict:
    """计算过渡词/AI词汇密度"""
    hits = []
    for word in word_list:
        count = text.count(word)
        if count > 0:
            hits.extend([word] * count)
    total_chars = len(text)
    density = len(hits) / (total_chars / 1000) if total_chars > 0 else 0
    return {
        "hits": hits,
        "count": len(hits),
        "density_per_1k": round(density, 2),
        "unique_hits": list(set(hits)),
    }


def calc_pattern_hits(text: str) -> dict:
    """检测否定式排比、三段式等 AI 模式"""
    hits = []
    for pattern in NEGATION_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            hits.append({"type": "否定式排比", "pattern": pattern, "count": len(matches)})

    for pattern in TRIPLE_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            for m in matches:
                items = m if isinstance(m, tuple) else (m,)
                if all(len(item) <= 4 for item in items):
                    hits.append({"type": "三段式排列", "content": "、".join(items), "count": 1})

    return {"hits": hits, "total": sum(h["count"] for h in hits)}


def calc_sentence_structure_repetition(sentences: list[str]) -> dict:
    """分析句式重复率"""
    if len(sentences) < 3:
        return {"repetition_rate": 0, "repeated_groups": 0, "same_start_groups": 0, "same_pattern_groups": 0, "total_groups": 0}

    def get_sentence_start(s):
        cleaned = re.sub(r'^[\"\"「『【\s]+', '', s)
        return cleaned[:3] if len(cleaned) >= 3 else cleaned

    def get_sentence_pattern(s):
        length = len(s)
        if length < 10:
            length_cat = "短"
        elif length < 25:
            length_cat = "中"
        else:
            length_cat = "长"
        ending = s[-1] if s else ""
        return f"{length_cat}_{ending}"

    same_start_groups = 0
    for i in range(len(sentences) - 2):
        starts = [get_sentence_start(sentences[j]) for j in range(i, i + 3)]
        if len(set(s[:2] for s in starts)) == 1:
            same_start_groups += 1

    same_pattern_groups = 0
    for i in range(len(sentences) - 2):
        patterns = [get_sentence_pattern(sentences[j]) for j in range(i, i + 3)]
        if len(set(patterns)) == 1:
            same_pattern_groups += 1

    total_groups = len(sentences) - 2
    repetition_rate = (same_start_groups + same_pattern_groups) / (total_groups * 2) if total_groups > 0 else 0

    return {
        "repetition_rate": round(repetition_rate, 3),
        "same_start_groups": same_start_groups,
        "same_pattern_groups": same_pattern_groups,
        "total_groups": total_groups,
    }


def calc_cross_paragraph_consistency(paragraphs: list[str]) -> dict:
    """
    分析跨段一致性（已集成防崩溃边界处理）
    """
    para_stats = []
    for p in paragraphs:
        sents = split_sentences(p)
        if not sents:  # 过滤掉只有空行或纯标点的无效段落
            continue
        lengths = [len(re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', s)) for s in sents]
        avg_len = sum(lengths) / len(lengths) if lengths else 0
        chars = re.sub(r'[^\u4e00-\u9fa5]', '', p)
        vocab_richness = len(set(chars)) / len(chars) if chars else 0
        para_stats.append({
            "avg_sentence_len": avg_len,
            "vocab_richness": vocab_richness,
            "num_sentences": len(sents),
        })

    if len(para_stats) < 2:
        return {"consistency_score": 0, "sentence_len_cv": 0, "vocab_richness_cv": 0, "para_count": len(para_stats)}

    avg_lens = [s["avg_sentence_len"] for s in para_stats]
    vocab_riches = [s["vocab_richness"] for s in para_stats]

    mean_len = sum(avg_lens) / len(avg_lens)
    len_cv = (math.sqrt(sum((x - mean_len)**2 for x in avg_lens) / len(avg_lens)) / mean_len) if mean_len > 0 else 0

    mean_vocab = sum(vocab_riches) / len(vocab_riches)
    vocab_cv = (math.sqrt(sum((x - mean_vocab)**2 for x in vocab_riches) / len(vocab_riches)) / mean_vocab) if mean_vocab > 0 else 0

    consistency_score = max(0, min(1, 1 - (len_cv + vocab_cv) / 2))

    return {
        "consistency_score": round(consistency_score, 3),
        "sentence_len_cv": round(len_cv, 3),
        "vocab_richness_cv": round(vocab_cv, 3),
        "para_count": len(para_stats),
    }


# ============================================================
#  主分析函数
# ============================================================

def analyze(text: str, mode: str = "article") -> DiagnosisReport:
    """对文本进行全面 AI 特征分析"""
    report = DiagnosisReport()

    paragraphs = split_paragraphs(text)
    sentences = split_sentences(text)
    sentence_lengths = [len(re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', s)) for s in sentences]

    report.total_chars = len(text)
    report.total_sentences = len(sentences)
    report.total_paragraphs = len(paragraphs)
    report.sentence_lengths = sentence_lengths
    report.paragraph_lengths = [len(p) for p in paragraphs]

    # 短文本降级标记处理逻辑
    is_short_text = len(sentences) < 5

    # ---- 1. 突发性分析 ----
    burst = calc_burstiness(sentence_lengths)
    risk_level = "低"
    if not is_short_text:
        if burst["cv"] < 0.2:
            risk_level = "高"
        elif burst["cv"] < 0.35:
            risk_level = "中"

    report.risks.append(RiskItem(
        name="突发性 (Burstiness)",
        value=burst["cv"],
        threshold=0.35,
        risk_level=risk_level,
        detail=f"句长标准差={burst['std_dev']}，变异系数={burst['cv']}，"
               f"均匀三连句={burst['uniform_triplets']}/{burst['total_triplets']}"
    ))

    # ---- 2. 过渡词密度 ----
    trans = calc_transition_density(text, TRANSITION_WORDS)
    report.hit_transition_words = trans["unique_hits"]
    risk_level = "低"
    if trans["density_per_1k"] > 5:
        risk_level = "高"
    elif trans["density_per_1k"] > 3:
        risk_level = "中"

    report.risks.append(RiskItem(
        name="过渡词密度",
        value=trans["density_per_1k"],
        threshold=3.0,
        risk_level=risk_level,
        detail=f"命中 {trans['count']} 个过渡词：{', '.join(trans['unique_hits'][:10])}"
    ))

    # ---- 3. AI 高频词 ----
    extra_words = []
    if mode == "article":
        extra_words = WECHAT_AI_WORDS
    elif mode == "novel":
        extra_words = NOVEL_AI_WORDS

    ai_words = calc_transition_density(text, AI_BUZZWORDS + extra_words)
    report.hit_ai_buzzwords = ai_words["unique_hits"]
    risk_level = "低"
    if ai_words["density_per_1k"] > 4:
        risk_level = "高"
    elif ai_words["density_per_1k"] > 2:
        risk_level = "中"

    report.risks.append(RiskItem(
        name="AI 高频词密度",
        value=ai_words["density_per_1k"],
        threshold=2.0,
        risk_level=risk_level,
        detail=f"命中 {ai_words['count']} 个 AI 词：{', '.join(ai_words['unique_hits'][:10])}"
    ))

    # ---- 4. AI 模式 ----
    patterns = calc_pattern_hits(text)
    report.hit_patterns = patterns["hits"]
    risk_level = "低"
    if patterns["total"] > 3:
        risk_level = "高"
    elif patterns["total"] > 1:
        risk_level = "中"

    report.risks.append(RiskItem(
        name="AI 结构模式",
        value=patterns["total"],
        threshold=1,
        risk_level=risk_level,
        detail=f"命中 {patterns['total']} 处模式"
               + (f"：{'、'.join(h['type'] for h in patterns['hits'][:5])}" if patterns["hits"] else "")
    ))

    # ---- 5. 句式重复率 ----
    struct = calc_sentence_structure_repetition(sentences)
    risk_level = "低"
    if not is_short_text:
        if struct["repetition_rate"] > 0.3:
            risk_level = "高"
        elif struct["repetition_rate"] > 0.15:
            risk_level = "中"

    report.risks.append(RiskItem(
        name="句式重复率",
        value=struct["repetition_rate"],
        threshold=0.15,
        risk_level=risk_level,
        detail=f"相同开头={struct['same_start_groups']}，相同句式={struct['same_pattern_groups']}" + (" (样本过少已忽略)" if is_short_text else "")
    ))

    # ---- 6. 跨段一致性 ----
    cross = calc_cross_paragraph_consistency(paragraphs)
    risk_level = "低"
    if len(paragraphs) >= 3:
        if cross["consistency_score"] > 0.85:
            risk_level = "高"
        elif cross["consistency_score"] > 0.7:
            risk_level = "中"

    report.risks.append(RiskItem(
        name="跨段一致性",
        value=cross["consistency_score"],
        threshold=0.7,
        risk_level=risk_level,
        detail=f"句长段间CV={cross['sentence_len_cv']}，词汇丰富度段间CV={cross['vocab_richness_cv']}"
    ))

    # ---- 综合评分 ----
    high_count = sum(1 for r in report.risks if r.risk_level == "高")
    mid_count = sum(1 for r in report.risks if r.risk_level == "中")

    report.score = max(0, 100 - high_count * 20 - mid_count * 10)

    if high_count >= 3:
        report.overall_risk = "高（极可能被标记为 AI）"
    elif high_count >= 1:
        report.overall_risk = "中（存在被标记风险）"
    else:
        report.overall_risk = "低（较难被检测）"

    return report


def format_report(report: DiagnosisReport) -> str:
    """格式化输出诊断报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("  🔍 Anti-Zhuque 朱雀检测风险诊断报告")
    lines.append("=" * 60)
    lines.append(f"  📝 文本统计：{report.total_chars} 字 | "
                 f"{report.total_sentences} 句 | {report.total_paragraphs} 段")
    lines.append(f"  ⚡ 综合评分：{report.score}/100")
    lines.append(f"  🎯 风险等级：{report.overall_risk}")
    lines.append("-" * 60)

    for risk in report.risks:
        emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}[risk.risk_level]
        lines.append(f"  {emoji} {risk.name}")
        lines.append(f"     当前值: {risk.value}  |  安全阈值: {risk.threshold}  |  风险: {risk.risk_level}")
        if risk.detail:
            lines.append(f"     详情: {risk.detail}")
        lines.append("")

    lines.append("=" * 60)

    if report.hit_ai_buzzwords:
        lines.append(f"  ⚠️  命中的 AI 高频词：")
        lines.append(f"     {', '.join(report.hit_ai_buzzwords[:20])}")
    if report.hit_transition_words:
        lines.append(f"  ⚠️  命中的过渡词：")
        lines.append(f"     {', '.join(report.hit_transition_words[:20])}")
    if report.hit_ai_buzzwords or report.hit_transition_words:
        lines.append("")

    return "\n".join(lines)
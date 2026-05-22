# -*- coding: utf-8 -*-
"""
Anti-Zhuque 主入口

使用方式：
  python main.py input.txt                    # 默认公众号文章模式
  python main.py input.txt --mode novel       # 小说模式
  python main.py input.txt --mode academic    # 学术论文模式
  python main.py input.txt --analyze-only     # 只分析不生成 prompt
  python main.py original.txt --compare rewritten.txt  # 对比改写前后
"""

import argparse
import os
import sys

from analyzer import analyze, format_report

# 映射本地文件路径
MODE_PROMPT_MAP = {
    "article": "article.md",
    "novel": "novel.md",
    "academic": "academic.md",
}

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def load_prompt_template(mode: str) -> str:
    """加载 prompt 模板 (带内存 Fallback 保护机制)"""
    filename = MODE_PROMPT_MAP.get(mode, "article.md")
    filepath = os.path.join(PROMPTS_DIR, filename)
    
    # 优先读取本地独立配置文件
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
            
    # 如果 prompts 文件夹及文件缺失，优雅降级为读取内存字典，防止 FileNotFoundError 崩溃
    try:
        from app import PROMPT_TEMPLATES
        return PROMPT_TEMPLATES.get(mode, PROMPT_TEMPLATES["article"])
    except ImportError:
        # 极端的兜底字符串
        return "请改写以下文本，消除AI感：\n{text}\n必须替换词汇：\n{ai_words_section}\n消除模式：\n{patterns_section}"


def build_prompt(text: str, report, mode: str) -> str:
    """根据分析结果构建针对性改写 prompt"""
    template = load_prompt_template(mode)

    # 构建 AI 词汇替换段落
    ai_words_lines = []
    if report.hit_ai_buzzwords:
        ai_words_lines.append("以下 AI 高频词在你的文本中被检测到，**必须逐一替换**：")
        for word in report.hit_ai_buzzwords[:20]:
            ai_words_lines.append(f"- 「{word}」")
    if report.hit_transition_words:
        ai_words_lines.append("\n以下过渡词被检测到，**必须删除或替换**：")
        for word in report.hit_transition_words[:15]:
            ai_words_lines.append(f"- 「{word}」")
    ai_words_section = "\n".join(ai_words_lines) if ai_words_lines else "（未检测到明显的 AI 高频词）"

    # 构建模式段落
    patterns_lines = []
    if report.hit_patterns:
        for p in report.hit_patterns:
            patterns_lines.append(f"- {p['type']}（出现 {p['count']} 次）")
    patterns_section = "\n".join(patterns_lines) if patterns_lines else "（未检测到明显的 AI 模式）"

    # 替换模板变量
    prompt = template.replace("{ai_words_section}", ai_words_section)
    prompt = prompt.replace("{patterns_section}", patterns_section)
    prompt = prompt.replace("{text}", text)

    return prompt


def run_analysis(text: str, mode: str, analyze_only: bool = False):
    """执行分析并输出结果"""
    print(f"\n  📋 模式: {mode}")
    print()

    # 分析
    report = analyze(text, mode)
    print(format_report(report))

    if analyze_only:
        return

    # 生成 prompt
    prompt = build_prompt(text, report, mode)

    # 保存 prompt
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_prompt.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"  ✅ 改写 Prompt 已保存到: {output_path}")
    print(f"  📌 请将该 Prompt 文件的内容发送给 AI 助手进行改写")
    print()

    if report.score < 40:
        print("  💡 建议：该文本 AI 特征非常明显，建议：")
        print("     1. 先用 AI 助手按 Prompt 改写一轮")
        print("     2. 自己手动修改一些句子，加入个人经历和口语化表达")
        print("     3. 再用本工具检测一次，确认指标改善")
        print()


def run_comparison(original_path: str, rewritten_path: str, mode: str):
    """对比改写前后的指标变化"""
    with open(original_path, "r", encoding="utf-8") as f:
        original_text = f.read()
    with open(rewritten_path, "r", encoding="utf-8") as f:
        rewritten_text = f.read()

    # 严格按照“原版、改写版”进行顺序计算
    report_orig = analyze(original_text, mode)
    report_new = analyze(rewritten_text, mode)

    print("\n" + "=" * 60)
    print("  📊 改写前后对比")
    print("=" * 60)
    print(f"  {'指标':<20} {'改写前':>10} {'改写后':>10} {'变化':>10}")
    print("-" * 60)

    for r_orig, r_new in zip(report_orig.risks, report_new.risks):
        change = r_new.value - r_orig.value
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        print(f"  {r_orig.name:<20} {r_orig.value:>10} {r_new.value:>10} {arrow}{abs(change):>8.2f}")

    print("-" * 60)
    score_change = report_new.score - report_orig.score
    arrow = "↑" if score_change > 0 else "↓" if score_change < 0 else "→"
    print(f"  {'综合评分':<20} {report_orig.score:>10} {report_new.score:>10} {arrow}{abs(score_change):>8}")
    print(f"  {'风险等级':<20} {report_orig.overall_risk}")
    print(f"  {'':<20} {report_new.overall_risk}")
    print("=" * 60)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Anti-Zhuque: 反朱雀 AI 检测文本分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py input.txt                     分析并生成改写 Prompt
  python main.py input.txt --mode novel        小说模式
  python main.py input.txt --analyze-only      只分析不生成 Prompt
  python main.py orig.txt --compare new.txt    对比改写前后
        """
    )
    parser.add_argument("input", help="输入文本文件路径")
    parser.add_argument("--mode", choices=["article", "novel", "academic"],
                        default="article", help="场景模式 (默认: article)")
    parser.add_argument("--analyze-only", action="store_true",
                        help="只分析不生成改写 Prompt")
    parser.add_argument("--compare", metavar="REWRITTEN_FILE",
                        help="与改写后的文件进行对比")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"  ❌ 文件不存在: {args.input}")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        print("  ❌ 输入文件为空")
        sys.exit(1)

    if args.compare:
        if not os.path.exists(args.compare):
            print(f"  ❌ 对比文件不存在: {args.compare}")
            sys.exit(1)
        run_comparison(args.input, args.compare, args.mode)
    else:
        run_analysis(text, args.mode, args.analyze_only)


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
import gradio as gr
import os
import sys
import json
import urllib.request
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyzer import analyze, format_report

API_URL = os.environ.get("API_URL", "")
API_KEY = os.environ.get("API_KEY", "")

# 🌟 玄武经典 AI 腔测试范文
DEFAULT_TEXT = """随着人工智能技术的飞速发展，在这个不断演变的格局中，深入探讨其核心机制显得至关重要。不可否认，新技术的出现不仅显著提升了生产效率，而且还在很大程度上重塑了我们的生活方式。综上所述，把握时代脉搏，积极推动技术创新，具有极其深远的重要意义。
人工智能作为新一轮科技革命与产业变革的核心驱动力，其迭代升级彻底打破了传统技术的边界桎梏，从底层算法迭代、大数据算力支撑到多场景落地应用，全方位渗透于社会生产、民生服务、科研探索、公共治理等各个领域，推动人类社会从信息化、数字化时代全面迈向智能化时代。不同于传统技术单一的工具属性，人工智能具备自主学习、动态适配、智能决策、自主迭代的核心特质，能够依托海量数据资源持续优化模型精度，突破人类体力与脑力的固有局限，解决诸多传统模式下难以攻克的复杂问题，为社会高质量发展注入源源不断的核心动能。
从产业发展层面来看，人工智能技术的深度落地，重构了全球产业结构与生产体系。在工业领域，智能生产线、工业机器人、数字孪生等智能技术的普及应用，实现了生产流程的自动化、精细化、智能化管控，彻底改变了传统工业粗放式、人力密集型的生产模式。产品研发、生产制造、质量检测、仓储物流等全链条效率大幅提升，生产误差率显著降低，有效降低了企业的人力成本与时间成本，推动传统制造业完成转型升级，助力高端制造、智能制造产业蓬勃发展。在农业领域，AI智能监测、无人机植保、智慧灌溉、农作物长势分析等技术的应用，打破了传统农业靠天吃饭的局限，实现农业生产的精准化、科学化管理，有效提升农作物产量与品质，推动现代农业体系的构建与完善。在服务业领域，智能客服、智慧物流、智能推荐、无人配送等新业态层出不穷，极大优化了服务流程，提升了服务效率与用户体验，催生了全新的经济增长点，推动数字经济与实体经济深度融合。"""


def load_prompt_template(mode):
    file_map = {
        "article": "article.md",
        "novel": "novel.md",
        "academic": "academic.md"
    }
    filename = file_map.get(mode, "article.md")
    
    possible_paths = [
        os.path.join(os.path.dirname(__file__), filename),
        os.path.join(os.path.dirname(__file__), "prompts", filename)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
                
    return "请改写以下文本以降低 AI 痕迹：\n\n{ai_words_section}\n\n{patterns_section}\n\n待改写文本：\n{text}"


def build_prompt(text, report, mode):
    template = load_prompt_template(mode)
    
    ai_words_lines = []
    if report.hit_ai_buzzwords:
        ai_words_lines.append("以下 AI 高频词必须逐一替换：")
        for w in report.hit_ai_buzzwords[:20]:
            ai_words_lines.append(f"- 「{w}」")
    if report.hit_transition_words:
        ai_words_lines.append("\n以下过渡词必须删除或替换：")
        for w in report.hit_transition_words[:15]:
            ai_words_lines.append(f"- 「{w}」")
    ai_words_section = "\n".join(ai_words_lines) if ai_words_lines else "（未检测到明显的 AI 高频词）"
    
    patterns_lines = []
    if report.hit_patterns:
        for p in report.hit_patterns:
            patterns_lines.append(f"- {p['type']} (出现 {p['count']} 次)")
    patterns_section = "\n".join(patterns_lines) if patterns_lines else "（未检测到明显的 AI 模式）"
    
    return template.replace("{ai_words_section}", ai_words_section).replace("{patterns_section}", patterns_section).replace("{text}", text)


def generate_xuanwu_highlighter(text):
    if not text.strip():
        return "<div style='color:#999;padding:20px;text-align:center'>暂无分析数据</div>"
        
    paragraphs = text.split('\n')
    html_out = "<div class='xuanwu-content-panel'>"
    
    for para in paragraphs:
        if not para.strip():
            html_out += "<br/>"
            continue
            
        sentences = re.split(r'(?<=[。！？；？\n])', para)
        para_html = "<p style='margin-bottom: 14px; line-height: 1.8; font-size: 15px; color: #333; text-align: justify;'>"
        
        for sent in sentences:
            if not sent.strip():
                continue
                
            sent_len = len(sent)
            has_buzzword = any(w in sent for w in ["随着", "深入探讨", "至关重要", "显著提升", "综上所述", "不可否认", "不仅如此", "格局", "总而言之", "值得注意的是", "重要意义", "深远影响"])
            
            if sent_len > 35 and has_buzzword:
                bg_color = "#ffeef0"
                border_style = "border-bottom: 2px dashed #ff4d4f;"
                tip_text = f"【🔴 高风险 (AI特征极浓)】\n句子较长({sent_len}字)且命中了AI核心高频套话，书面学生腔严重，建议彻底口语化打碎。"
            elif sent_len > 25 or has_buzzword:
                bg_color = "#fffbe6"
                border_style = "border-bottom: 2px dashed #ffc53d;"
                tip_text = f"【🟡 中风险 (疑似 AI 句式)】\n句式结构较为工整，过渡较为机械。建议更换句式语序或删减过渡词。"
            else:
                bg_color = "transparent"
                border_style = "none"
                tip_text = ""

            if bg_color != "transparent":
                para_html += f"""<span title="{tip_text}" style="background-color: {bg_color}; {border_style} padding: 2px 0; cursor: help; display: inline;">{sent}</span>"""
            else:
                para_html += f"<span>{sent}</span>"
                
        para_html += "</p>"
        html_out += para_html
        
    html_out += "</div>"
    return html_out


def analyze_text(text, mode, current_rewritten=""):
    if not text or not text.strip():
        return "<div style='color:#999;padding:20px;text-align:center'>请输入文本后点击分析</div>", "", gr.update(value="", visible=False), gr.update(visible=False), gr.update(visible=False)

    text_str = str(text)
    current_rewritten_str = str(current_rewritten) if current_rewritten else ""

    report = analyze(text_str, mode)
    xuanwu_highlight_html = generate_xuanwu_highlighter(text_str)
    prompt = build_prompt(text_str, report, mode)

    color = "#28a745" if report.score >= 70 else "#ffc107" if report.score >= 40 else "#dc3545"
    emoji = "🟢" if report.score >= 70 else "🟡" if report.score >= 40 else "🔴"
    
    score_html = f"""
    <div style="text-align:center;padding:16px;background:#f8f9fa;border-radius:12px;margin-bottom:16px;border:1px solid #eef0f2">
        <div style="font-size:46px;font-weight:bold;color:{color};line-height:1">{report.score}</div>
        <div style="font-size:13px;color:#666;margin-top:4px">综合原创度得分 / 100</div>
        <div style="font-size:16px;margin-top:8px;font-weight:bold;color:#333">{emoji} {report.overall_risk}</div>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:13px">"""
    for risk in report.risks:
        e = {"高": "🔴", "中": "🟡", "低": "🟢"}[risk.risk_level]
        score_html += f"""<tr style="border-bottom:1px solid #f1f1f1"><td style="padding:8px 4px;color:#333">{e} {risk.name}</td><td style="padding:8px 4px;text-align:center;font-weight:bold">{risk.value}</td><td style="padding:8px 4px;text-align:center"><span style="padding:2px 6px;border-radius:4px;font-size:11px;background:{'#ffeef0' if risk.risk_level=='高' else '#fffbe6' if risk.risk_level=='中' else '#f6ffed'};color:{'#ff4d4f' if risk.risk_level=='高' else '#d46b08' if risk.risk_level=='中' else '#52c41a'}">{risk.risk_level}</span></td></tr>"""
    score_html += "</table>"

    show_compare = gr.update(visible=True) if current_rewritten_str.strip() else gr.update(visible=False)

    return xuanwu_highlight_html, score_html, gr.update(value=prompt, visible=True), gr.update(visible=True), show_compare


def rewrite_via_api(text, mode):
    if not API_URL:
        return "请先在环境变量中配置有效的 Hugging Face API_URL 和 API_KEY"
    if not text or not text.strip():
        return "请输入文本"
        
    report = analyze(str(text), mode)
    prompt = build_prompt(str(text), report, mode)
    
    payload_data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 2048,
            "temperature": 0.8,
            "return_full_text": False
        },
        "options": { "wait_for_model": True }
    }
    payload = json.dumps(payload_data).encode("utf-8")
    clean_url = API_URL.strip()
    
    try:
        req = urllib.request.Request(clean_url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "Mozilla/5.0 AntiXuanwuClient")
        
        if API_KEY:
            token = API_KEY.strip()
            auth_value = token if token.startswith("Bearer ") else f"Bearer {token}"
            req.add_header("Authorization", auth_value)
            
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                return data[0]["generated_text"].strip()
            elif isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"].strip()
            else:
                return f"接口调用成功，但返回了未知的结构：{data}"
    except Exception as e:
        return f"改写失败：{e}"


def handle_rewrite_output(rewritten_text):
    if not rewritten_text or rewritten_text.startswith("请") or rewritten_text.startswith("改写失败"):
        return gr.update(value=rewritten_text, visible=True), gr.update(visible=False), gr.update(visible=False)
    return gr.update(value=rewritten_text, visible=True), gr.update(visible=True), gr.update(visible=True)


def compare_text(orig, rewritten, mode):
    if not orig or not rewritten or not orig.strip() or not rewritten.strip():
        return gr.update(value="请先输入改写前后的文本", visible=True)
    r1 = analyze(str(orig), mode)
    r2 = analyze(str(rewritten), mode)
    lines = ["=" * 60, f"  {'指标':<20} {'改写前':>10} {'改写后':>10} {'变化':>10}", "-" * 60]
    for a, b in zip(r1.risks, r2.risks):
        ch = b.value - a.value
        arr = "↑" if ch > 0 else "↓" if ch < 0 else "→"
        lines.append(f"  {a.name:<20} {a.value:>10} {b.value:>10} {arr}{abs(ch):>8.2f}")
    lines.append("-" * 60)
    sc = r2.score - r1.score
    arr = "↑" if sc > 0 else "↓" if sc < 0 else "→"
    lines.append(f"  {'综合评分':<20} {r1.score:>10} {r2.score:>10} {arr}{abs(sc):>8}")
    lines.append(f"  {'改写前风险':<20} {r1.overall_risk}")
    lines.append(f"  {'改写后风险':<20} {r2.overall_risk}")
    lines.append("=" * 60)
    return gr.update(value="\n".join(lines), visible=True)


CUSTOM_CSS = """
/* ── 全局重置 ── */
footer { display: none !important; }
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
    background: #f0f4ff !important;
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
}
.main { padding: 0 !important; }

/* ── 顶部导航 ── */
.xuanwu-navbar {
    background: #fff;
    border-bottom: 1px solid #e8ecf4;
    padding: 0 32px;
    height: 56px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.xuanwu-logo {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 17px;
    font-weight: 700;
    color: #1a1a2e;
    text-decoration: none;
}
.xuanwu-logo-icon {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #4f6ef7 0%, #2d44c8 100%);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 16px;
}
.xuanwu-nav-tag {
    font-size: 12px;
    color: #666;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 2px 8px;
    margin-left: 4px;
}

/* ── 副标题横幅 ── */
.xuanwu-hero {
    background: #fff;
    padding: 20px 32px 18px;
    border-bottom: 1px solid #e8ecf4;
    font-size: 14px;
    color: #444;
    line-height: 1.7;
}

/* ── 主体内容区 ── */
.xuanwu-main-wrap {
    display: flex;
    gap: 0;
    padding: 20px 24px;
    min-height: calc(100vh - 140px);
    align-items: flex-start;
}

/* ── 左侧编辑面板 ── */
.xuanwu-left-panel {
    flex: 1.4;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(79,110,247,0.07);
    overflow: hidden;
    margin-right: 16px;
}
.xuanwu-tabs {
    display: flex;
    border-bottom: 1px solid #eef0f8;
    padding: 0 16px;
    background: #fff;
    overflow-x: auto;
}
.xuanwu-tab {
    padding: 12px 16px;
    font-size: 13px;
    color: #666;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    transition: all 0.2s;
}
.xuanwu-tab.active {
    color: #fff;
    background: #4f6ef7;
    border-radius: 6px 6px 0 0;
    border-bottom: 2px solid #4f6ef7;
    font-weight: 600;
}
.xuanwu-editor-area {
    padding: 16px;
    min-height: 380px;
    max-height: 460px;
    overflow-y: auto;
    font-size: 14px;
    line-height: 1.8;
    color: #333;
}
.xuanwu-editor-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-top: 1px solid #eef0f8;
    background: #fafbff;
}
.xuanwu-char-count {
    font-size: 12px;
    color: #999;
}
.xuanwu-btn-group {
    display: flex;
    gap: 8px;
}
.xuanwu-btn-clear {
    background: none;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    color: #666;
    cursor: pointer;
    transition: all 0.2s;
}
.xuanwu-btn-clear:hover { border-color: #4f6ef7; color: #4f6ef7; }
.xuanwu-btn-detect {
    background: linear-gradient(135deg, #4f6ef7 0%, #2d44c8 100%);
    border: none;
    border-radius: 6px;
    padding: 7px 20px;
    font-size: 13px;
    color: #fff;
    cursor: pointer;
    font-weight: 600;
    transition: opacity 0.2s;
}
.xuanwu-btn-detect:hover { opacity: 0.88; }
.xuanwu-btn-rewrite {
    background: linear-gradient(135deg, #36b37e 0%, #00875a 100%);
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    color: #fff;
    cursor: pointer;
    font-weight: 600;
    transition: opacity 0.2s;
}
.xuanwu-btn-rewrite:hover { opacity: 0.88; }

/* ── 右侧结果面板 ── */
.xuanwu-right-panel {
    width: 320px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.xuanwu-result-card {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(79,110,247,0.07);
    padding: 20px;
}
.xuanwu-result-title {
    font-size: 13px;
    font-weight: 600;
    color: #e53e3e;
    background: #fff5f5;
    border: 1px solid #fed7d7;
    border-radius: 6px;
    padding: 6px 12px;
    margin-bottom: 12px;
    display: inline-block;
}
.xuanwu-result-title.safe {
    color: #276749;
    background: #f0fff4;
    border-color: #9ae6b4;
}
.xuanwu-result-title.warn {
    color: #744210;
    background: #fffff0;
    border-color: #f6e05e;
}
.xuanwu-hint {
    font-size: 12px;
    color: #999;
    line-height: 1.6;
    margin-bottom: 16px;
    padding: 8px;
    background: #fafbff;
    border-radius: 6px;
}

/* ── 饼图 ── */
.xuanwu-pie-wrap {
    display: flex;
    justify-content: center;
    margin: 8px 0 16px;
}
.xuanwu-pie-svg { filter: drop-shadow(0 2px 8px rgba(0,0,0,0.10)); }

/* ── 图例 ── */
.xuanwu-legend {
    display: flex;
    justify-content: center;
    gap: 16px;
    flex-wrap: wrap;
    margin-top: 8px;
}
.xuanwu-legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #555;
}
.xuanwu-legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

/* ── 风险明细 ── */
.xuanwu-risk-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px solid #f3f4f8;
    font-size: 13px;
}
.xuanwu-risk-row:last-child { border-bottom: none; }
.xuanwu-risk-name { color: #444; }
.xuanwu-risk-val { font-weight: 700; color: #1a1a2e; }
.xuanwu-risk-badge {
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 10px;
    font-weight: 600;
}
.badge-high { background: #ffeef0; color: #e53e3e; }
.badge-mid  { background: #fffbe6; color: #d69e2e; }
.badge-low  { background: #f0fff4; color: #276749; }

/* ── 亮点诊断下方 ── */
.xuanwu-highlight-card {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(79,110,247,0.07);
    padding: 16px 20px;
    margin-top: 12px;
}
.xuanwu-highlight-title {
    font-size: 13px;
    font-weight: 700;
    color: #4f6ef7;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* ── 场景模式选择 ── */
.xuanwu-mode-bar {
    display: flex;
    gap: 8px;
    padding: 12px 16px 0;
    background: #fff;
}
.xuanwu-mode-btn {
    padding: 5px 14px;
    border-radius: 20px;
    border: 1px solid #dde1f0;
    font-size: 12px;
    color: #666;
    cursor: pointer;
    background: #f7f8fc;
    transition: all 0.18s;
}
.xuanwu-mode-btn.active, .xuanwu-mode-btn:hover {
    background: #4f6ef7;
    color: #fff;
    border-color: #4f6ef7;
}

/* ── 改写结果区 ── */
.xuanwu-rewrite-card {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(79,110,247,0.07);
    padding: 16px 20px;
    margin-top: 12px;
}

/* ── Gradio 组件隐藏/覆盖 ── */
#input_text_wrap textarea,
#rewritten_text_wrap textarea {
    border: none !important;
    box-shadow: none !important;
    font-size: 14px !important;
    line-height: 1.8 !important;
    color: #333 !important;
    background: transparent !important;
    padding: 0 !important;
    resize: none !important;
}
#input_text_wrap label,
#rewritten_text_wrap label,
#score_panel_wrap label,
#highlight_panel_wrap label,
#prompt_box_wrap label,
#compare_result_wrap label { display: none !important; }

/* 隐藏 Gradio 默认按钮样式，改用自定义 */
#analyze_btn_wrap button,
#rewrite_btn_wrap button,
#clear_btn_wrap button,
#reanalyze_btn_wrap button,
#compare_btn_wrap button {
    border-radius: 6px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 8px 18px !important;
    transition: opacity 0.2s !important;
}

/* 隐藏多余的容器边框 */
.gr-box, .gr-form { box-shadow: none !important; border: none !important; }
"""


def build_score_html(report):
    """生成朱雀风格的右侧结果面板 HTML（含 SVG 饼图）"""
    # 风险等级 → 配色
    color_map = {"高": "#FC8181", "中": "#F6E05E", "低": "#68D391"}
    
    # 计算饼图数据（用 risks 的 value 归一化，或固定三段）
    # 简化：AI特征占比 = 100 - score，疑似AI = score的一部分，人工特征 = 剩余
    score = report.score
    ai_pct   = max(0, min(100, 100 - score)) * 0.6
    semi_pct = max(0, min(100, 100 - score)) * 0.4
    human_pct = 100 - ai_pct - semi_pct

    def pct_to_arc(pct, start_angle, r=70, cx=90, cy=90):
        """将百分比转为 SVG arc path"""
        import math
        angle = pct / 100 * 360
        end_angle = start_angle + angle
        large = 1 if angle > 180 else 0
        s_rad = math.radians(start_angle - 90)
        e_rad = math.radians(end_angle - 90)
        x1 = cx + r * math.cos(s_rad)
        y1 = cy + r * math.sin(s_rad)
        x2 = cx + r * math.cos(e_rad)
        y2 = cy + r * math.sin(e_rad)
        return f"M {cx} {cy} L {x1:.2f} {y1:.2f} A {r} {r} 0 {large} 1 {x2:.2f} {y2:.2f} Z", end_angle

    a1, end1 = pct_to_arc(human_pct, 0)
    a2, end2 = pct_to_arc(semi_pct, end1)
    a3, _    = pct_to_arc(ai_pct,   end2)

    # 整体风险标题
    if score >= 70:
        title_cls = "safe"
        title_txt = "未发现明显的人工创作特征" if score < 85 else "✅ 人工创作特征明显"
    elif score >= 40:
        title_cls = "warn"
        title_txt = "⚠️ 疑似含有 AI 创作特征"
    else:
        title_cls = ""
        title_txt = "🔴 检测到明显 AI 创作特征"

    # 风险明细行
    rows_html = ""
    for risk in report.risks:
        badge_cls = {"高": "badge-high", "中": "badge-mid", "低": "badge-low"}[risk.risk_level]
        badge_txt = {"高": "高风险", "中": "中风险", "低": "低风险"}[risk.risk_level]
        rows_html += f"""
        <div class="xuanwu-risk-row">
            <span class="xuanwu-risk-name">{risk.name}</span>
            <span class="xuanwu-risk-val">{risk.value:.2f}</span>
            <span class="xuanwu-risk-badge {badge_cls}">{badge_txt}</span>
        </div>"""

    html = f"""
    <div class="xuanwu-result-card">
        <div class="xuanwu-result-title {title_cls}">{title_txt}</div>
        <div class="xuanwu-hint">提示：本结果仅为辅助判断，不应作为任何审核或处罚的决定性依据。</div>

        <div class="xuanwu-pie-wrap">
            <svg class="xuanwu-pie-svg" width="180" height="180" viewBox="0 0 180 180">
                <path d="{a1}" fill="#68D391" opacity="0.9"/>
                <path d="{a2}" fill="#F6E05E" opacity="0.9"/>
                <path d="{a3}" fill="#FC8181" opacity="0.9"/>
                <circle cx="90" cy="90" r="38" fill="white"/>
                <text x="90" y="86" text-anchor="middle" font-size="20" font-weight="bold" fill="#1a1a2e">{score}</text>
                <text x="90" y="102" text-anchor="middle" font-size="9" fill="#999">原创度得分</text>
            </svg>
        </div>

        <div class="xuanwu-legend">
            <div class="xuanwu-legend-item">
                <div class="xuanwu-legend-dot" style="background:#68D391"></div>
                <span>人工特征 {human_pct:.1f}%</span>
            </div>
            <div class="xuanwu-legend-item">
                <div class="xuanwu-legend-dot" style="background:#F6E05E"></div>
                <span>疑似AI {semi_pct:.1f}%</span>
            </div>
            <div class="xuanwu-legend-item">
                <div class="xuanwu-legend-dot" style="background:#FC8181"></div>
                <span>AI特征 {ai_pct:.1f}%</span>
            </div>
        </div>

        <div style="margin-top:16px">{rows_html}</div>
    </div>
    """
    return html


init_report = analyze(DEFAULT_TEXT, "article")
init_html = generate_xuanwu_highlighter(DEFAULT_TEXT)
init_prompt_text = build_prompt(DEFAULT_TEXT, init_report, "article")
init_score_html = build_score_html(init_report)

_NAVBAR_HTML = """
<div class="xuanwu-navbar">
    <div class="xuanwu-logo">
        <div class="xuanwu-logo-icon">🛡</div>
        <span>玄武AI检测助手</span>
    </div>
    <span class="xuanwu-nav-tag">AI生成检测 ∨</span>
</div>
<div class="xuanwu-hero">
    玄武 AIGC 检测基于多种先进分析引擎，构造精细化规则模型进行训练，能够识别出人类和 AI 的书写模式。
    该系统在处理中文数据方面表现尤为出色，集成玄武高亮诊断与 Hugging Face 无服务器推理 API，助您的文章稳如玄武。
</div>
"""

_LEFT_PANEL_HTML = f"""
<div class="xw-card">
  <div class="xw-mode-bar">
    <button class="xw-mode active" data-mode="article" onclick="xwSetMode(this)">公众号文章</button>
    <button class="xw-mode" data-mode="novel"   onclick="xwSetMode(this)">小说</button>
    <button class="xw-mode" data-mode="academic" onclick="xwSetMode(this)">学术论文</button>
  </div>
  <textarea id="xw-editor"
    placeholder="请粘贴需要检测或改写的文本……"
    oninput="xwSync()"
  >{DEFAULT_TEXT}</textarea>
  <div class="xw-footer">
    <span class="xw-count" id="xw-count">{len(DEFAULT_TEXT)} 字</span>
    <div class="xw-btns">
      <button class="xw-btn-clear"   onclick="xwClear()">清空</button>
      <button class="xw-btn-rewrite" onclick="xwRewrite()">✍️ 一键改写</button>
      <button class="xw-btn-detect"  onclick="xwDetect()">🔍 立即检测</button>
    </div>
  </div>
</div>
<style>
.xw-card {{
  background:#fff;
  border-radius:12px;
  box-shadow:0 2px 12px rgba(79,110,247,.08);
  overflow:hidden;
  display:flex;
  flex-direction:column;
}}
.xw-mode-bar {{
  display:flex;
  gap:8px;
  padding:12px 16px 10px;
  border-bottom:1px solid #eef0f8;
  background:#fff;
}}
.xw-mode {{
  padding:5px 16px;
  border-radius:20px;
  border:1px solid #dde1f0;
  font-size:13px;
  color:#666;
  cursor:pointer;
  background:#f7f8fc;
  transition:all .18s;
}}
.xw-mode.active {{
  background:#4f6ef7;
  color:#fff;
  border-color:#4f6ef7;
  font-weight:600;
}}
#xw-editor {{
  width:100%;
  min-height:340px;
  max-height:440px;
  padding:16px;
  font-size:14px;
  line-height:1.85;
  color:#333;
  border:none;
  outline:none;
  resize:vertical;
  font-family:'PingFang SC','Microsoft YaHei',sans-serif;
  box-sizing:border-box;
  background:#fff;
}}
.xw-footer {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:10px 16px;
  border-top:1px solid #eef0f8;
  background:#fafbff;
}}
.xw-count {{font-size:12px;color:#aaa;}}
.xw-btns {{display:flex;gap:8px;}}
.xw-btn-clear {{
  background:none;border:1px solid #ddd;border-radius:6px;
  padding:7px 14px;font-size:13px;color:#666;cursor:pointer;transition:all .2s;
}}
.xw-btn-clear:hover{{border-color:#4f6ef7;color:#4f6ef7;}}
.xw-btn-rewrite {{
  background:linear-gradient(135deg,#36b37e,#00875a);border:none;border-radius:6px;
  padding:7px 14px;font-size:13px;color:#fff;cursor:pointer;font-weight:600;transition:opacity .2s;
}}
.xw-btn-rewrite:hover{{opacity:.85;}}
.xw-btn-detect {{
  background:linear-gradient(135deg,#4f6ef7,#2d44c8);border:none;border-radius:6px;
  padding:7px 20px;font-size:13px;color:#fff;cursor:pointer;font-weight:600;transition:opacity .2s;
}}
.xw-btn-detect:hover{{opacity:.85;}}
</style>
<script>
function xwSync() {{
  const txt = document.getElementById('xw-editor').value;
  document.getElementById('xw-count').textContent = txt.length + ' 字';
  // 同步到隐藏的 Gradio Textbox
  const hidden = document.querySelector('#xw-hidden-input textarea');
  if (hidden) {{
    hidden.value = txt;
    hidden.dispatchEvent(new Event('input', {{bubbles:true}}));
  }}
}}
function xwSetMode(btn) {{
  document.querySelectorAll('.xw-mode').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const radios = document.querySelectorAll('#xw-mode-radio input[type=radio]');
  radios.forEach(r => {{ if (r.value === btn.dataset.mode) r.click(); }});
}}
function xwClear() {{
  document.getElementById('xw-editor').value = '';
  xwSync();
  // 触发清空按钮
  const btn = document.querySelector('#xw-clear-btn button');
  if (btn) btn.click();
}}
function xwDetect() {{
  xwSync();
  setTimeout(() => {{
    const btn = document.querySelector('#xw-analyze-btn button');
    if (btn) btn.click();
  }}, 80);
}}
function xwRewrite() {{
  xwSync();
  setTimeout(() => {{
    const btn = document.querySelector('#xw-rewrite-btn button');
    if (btn) btn.click();
  }}, 80);
}}
// 当改写结果写回时同步显示到编辑器（可选）
window.xwSetEditor = function(txt) {{
  document.getElementById('xw-editor').value = txt;
  xwSync();
}};
</script>
"""

with gr.Blocks(title="玄武 AI 检测助手", css=CUSTOM_CSS) as demo:

    # ── 顶部导航 ──
    gr.HTML(_NAVBAR_HTML)

    # ── 隐藏的 Gradio 状态组件（不渲染，只传值） ──
    with gr.Row(visible=False):
        mode = gr.Radio(
            choices=[("公众号文章", "article"), ("小说", "novel"), ("学术论文", "academic")],
            value="article",
            elem_id="xw-mode-radio",
        )
    with gr.Row(visible=False):
        input_text = gr.Textbox(value=DEFAULT_TEXT, elem_id="xw-hidden-input")
        clear_btn   = gr.Button("清空",         elem_id="xw-clear-btn")
        analyze_btn = gr.Button("立即检测",      elem_id="xw-analyze-btn")
        rewrite_btn = gr.Button("一键改写",      elem_id="xw-rewrite-btn")

    # ── 主体两栏 ──
    with gr.Row():
        # 左侧：完全自定义 HTML 编辑区
        with gr.Column(scale=7):
            gr.HTML(_LEFT_PANEL_HTML)

        # 右侧：结果面板
        with gr.Column(scale=3):
            score_panel = gr.HTML(value=init_score_html, show_label=False)

    # ── 高亮诊断（宽行，在两栏下方） ──
    with gr.Row():
        with gr.Column():
            gr.HTML('<div class="xuanwu-highlight-title" style="margin-top:12px;font-size:14px;font-weight:700;color:#4f6ef7;padding:0 4px">🔦 玄武高亮诊断</div>')
            highlight_panel = gr.HTML(
                value=f'<div class="xuanwu-highlight-card">{init_html}</div>',
                elem_id="highlight_panel_wrap",
                show_label=False,
            )

    # ── 改写 Prompt ──
    with gr.Accordion("📋 改写 Prompt（可复制到其他 AI 使用）", open=False, visible=True) as prompt_accordion:
        prompt_box = gr.Textbox(
            value=init_prompt_text,
            lines=10,
            interactive=False,
            visible=True,
            show_label=False,
            elem_id="prompt_box_wrap",
        )

    # ── 改写结果 ──
    rewritten_text = gr.Textbox(
        placeholder="改写结果将显示在此处……",
        lines=10,
        visible=False,
        interactive=True,
        show_label=False,
        elem_id="rewritten_text_wrap",
    )

    with gr.Row(visible=False) as reanalyze_row:
        reanalyze_btn = gr.Button("🔁 对改写结果重新分析", variant="primary", elem_id="reanalyze_btn_wrap")

    with gr.Row(visible=False) as compare_row:
        compare_btn = gr.Button("📊 对比改写前后效果", variant="secondary", elem_id="compare_btn_wrap")

    compare_result = gr.Textbox(
        lines=12,
        visible=False,
        interactive=False,
        show_label=False,
        elem_id="compare_result_wrap",
    )

    # ── Event bindings ──────────────────────────────────────────

    def _analyze_wrap(text, mode, rewritten):
        highlight, score_html, prompt, prompt_vis, compare_vis = analyze_text(text, mode, rewritten)
        return highlight, build_score_html(analyze(str(text), mode)), prompt, prompt_vis, compare_vis

    clear_btn.click(
        fn=lambda: (
            "",
            "<div style='color:#999;padding:40px;text-align:center;font-size:14px'>请输入文本后点击立即检测</div>",
            "<div style='color:#999;padding:20px;text-align:center'>暂无分析数据</div>",
            gr.update(value="", visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        ),
        inputs=[],
        outputs=[input_text, score_panel, highlight_panel, rewritten_text, reanalyze_row, compare_row, compare_result],
    )

    analyze_btn.click(
        fn=_analyze_wrap,
        inputs=[input_text, mode, rewritten_text],
        outputs=[highlight_panel, score_panel, prompt_box, prompt_accordion, compare_row],
    )

    rewrite_btn.click(
        fn=rewrite_via_api,
        inputs=[input_text, mode],
        outputs=[rewritten_text],
    ).then(
        fn=handle_rewrite_output,
        inputs=[rewritten_text],
        outputs=[rewritten_text, reanalyze_row, compare_row],
    )

    reanalyze_btn.click(
        fn=_analyze_wrap,
        inputs=[rewritten_text, mode, rewritten_text],
        outputs=[highlight_panel, score_panel, prompt_box, prompt_accordion, compare_row],
    )

    compare_btn.click(
        fn=compare_text,
        inputs=[input_text, rewritten_text, mode],
        outputs=[compare_result],
    )


if __name__ == "__main__":
    demo.launch()

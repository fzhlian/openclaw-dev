from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from app.models import AILikelihoodResult, CredibilityResult, ExtractedArticle
from app.utils import domain_from_url, sentence_split, truncate


OFFICIAL_DOMAIN_SUFFIXES = (".gov", ".edu", ".org")
TRUSTED_MEDIA_HINTS = (
    "reuters",
    "apnews",
    "bbc",
    "nytimes",
    "wsj",
    "ft.com",
    "economist",
    "nature.com",
)
CLICKBAIT_TERMS = ("震惊", "必看", "疯传", "绝对", "终极", "内幕", "独家", "惊人", "彻底", "暴涨")
TEMPLATE_PHRASES = (
    "值得注意的是",
    "不难发现",
    "从某种意义上说",
    "总的来说",
    "可以看出",
    "综上所述",
    "毋庸置疑",
    "换句话说",
)


def _source_score(article: ExtractedArticle) -> tuple[int, list[str]]:
    domain = domain_from_url(article.url)
    reasons: list[str] = []
    if domain.endswith(OFFICIAL_DOMAIN_SUFFIXES) or domain.startswith("www.gov"):
        reasons.append("来源域名接近官方或公共机构站点")
        return 28, reasons
    if any(hint in domain for hint in TRUSTED_MEDIA_HINTS):
        reasons.append("来源属于较成熟的媒体或专业出版域")
        return 22, reasons
    if article.source and article.source != domain:
        reasons.append("文章来源明确，站点与标题元信息较完整")
        return 16, reasons
    reasons.append("来源信息有限，站点可靠性难以单独确认")
    return 8, reasons


def _evidence_score(text: str) -> tuple[int, list[str]]:
    reasons: list[str] = []
    number_hits = len(re.findall(r"\d", text))
    quote_hits = text.count("“") + text.count('"')
    link_hits = len(re.findall(r"https?://|www\.", text, flags=re.IGNORECASE))
    if number_hits >= 12:
        reasons.append("正文包含较多可核对的数字、时间或量化信息")
    if quote_hits >= 2:
        reasons.append("正文出现引述或原话片段")
    if link_hits >= 1:
        reasons.append("正文留下了外部链接或引用线索")
    score = min(25, 5 + min(number_hits, 12) + min(quote_hits * 2, 8) + min(link_hits * 4, 8))
    if score < 8:
        reasons.append("正文以概括性表述为主，一手证据较少")
    return score, reasons


def _cross_check_score(text: str) -> tuple[int, list[str]]:
    reasons: list[str] = []
    source_mentions = len(set(re.findall(r"(表示|称|according to|reported by)\s*([A-Za-z\u4e00-\u9fff]{2,20})", text, flags=re.IGNORECASE)))
    date_mentions = len(re.findall(r"\b20\d{2}\b|\d{4}[-/]\d{1,2}[-/]\d{1,2}", text))
    if source_mentions >= 2:
        reasons.append("文中存在多个来源指向，具备一定交叉印证空间")
    if date_mentions >= 2:
        reasons.append("文中给出了多个时间锚点，便于外部核对")
    score = min(25, 6 + min(source_mentions * 6, 12) + min(date_mentions * 2, 7))
    if score < 8:
        reasons.append("可交叉印证线索较少，外部核对成本偏高")
    return score, reasons


def _risk_penalty(article: ExtractedArticle) -> tuple[int, list[str]]:
    risks: list[str] = []
    penalty = 0
    title = article.title or ""
    text = article.text
    if any(term in title for term in CLICKBAIT_TERMS):
        penalty -= 8
        risks.append("标题存在明显情绪化或标题党措辞")
    if "!!!" in title or "？？？" in title or "???" in title:
        penalty -= 4
        risks.append("标题使用夸张标点，可能放大情绪导向")
    if len(re.findall(r"(永远|一定|毫无疑问|彻底证明|百分之百)", text)) >= 2:
        penalty -= 5
        risks.append("正文出现绝对化表述，削弱论证稳健性")
    if len(text) < 500:
        penalty -= 3
        risks.append("正文较短，支撑信息可能不够充分")
    return penalty, risks


def assess_credibility(article: ExtractedArticle | dict[str, Any]) -> CredibilityResult:
    data = article if isinstance(article, ExtractedArticle) else ExtractedArticle(**article)
    source_score, source_reasons = _source_score(data)
    evidence_score, evidence_reasons = _evidence_score(data.text)
    cross_score, cross_reasons = _cross_check_score(data.text)
    penalty, risks = _risk_penalty(data)
    score = max(0, min(100, source_score + evidence_score + cross_score + penalty))
    if score >= 80:
        level = "较高可信"
    elif score >= 60:
        level = "中等可信"
    elif score >= 40:
        level = "存疑"
    else:
        level = "高风险 / 低可信"
    reasons = []
    for item in source_reasons + evidence_reasons + cross_reasons:
        if item not in reasons:
            reasons.append(item)
    if not risks:
        risks.append("当前评分仍依赖文本层启发式，建议结合外部来源复核")
    return CredibilityResult(score=score, level=level, reasons=reasons[:4], risks=risks[:4])


def assess_ai_likelihood(article: ExtractedArticle | dict[str, Any]) -> AILikelihoodResult:
    data = article if isinstance(article, ExtractedArticle) else ExtractedArticle(**article)
    text = data.text
    if len(text) < 180:
        return AILikelihoodResult(
            score=0,
            level="无法判断",
            reasons=["正文过短，缺少稳定的文本风格特征"],
            limitations=["短文本很容易被人工编辑或标题格式干扰"],
        )
    sentences = sentence_split(text)
    template_hits = sum(text.count(phrase) for phrase in TEMPLATE_PHRASES)
    unique_sent_starts = len({sentence[:8] for sentence in sentences if sentence})
    repeated_ratio = 1.0 - (unique_sent_starts / max(len(sentences), 1))
    token_matches = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text.lower())
    lexical_diversity = len(set(token_matches)) / max(len(token_matches), 1)
    detail_hits = len(re.findall(r"\d|“|\"|%|@|#|现场|采访|照片|文件", text))
    paragraph_lengths = [len(part.strip()) for part in text.split("\n\n") if part.strip()]
    variance = 0.0
    if paragraph_lengths:
        mean = sum(paragraph_lengths) / len(paragraph_lengths)
        variance = sum((value - mean) ** 2 for value in paragraph_lengths) / len(paragraph_lengths)
    smoothness_penalty = 10 if variance and math.sqrt(variance) < 40 else 0
    score = min(
        100,
        max(
            0,
            template_hits * 8
            + int(repeated_ratio * 30)
            + (12 if lexical_diversity < 0.28 else 0)
            + smoothness_penalty
            - min(detail_hits, 18),
        ),
    )
    if score >= 75:
        level = "较高 AI 痕迹"
    elif score >= 50:
        level = "中度 AI 痕迹"
    elif score >= 25:
        level = "轻度 AI 痕迹"
    else:
        level = "低 AI 痕迹"
    reasons: list[str] = []
    if template_hits:
        reasons.append("多处段落出现模板化衔接语")
    if repeated_ratio > 0.45:
        reasons.append("句首结构重复度偏高，节奏较机械")
    if lexical_diversity < 0.28:
        reasons.append("词汇分布偏收敛，抽象概括多于细节展开")
    if smoothness_penalty:
        reasons.append("段落长度过于均匀，转承较平滑")
    if detail_hits >= 12:
        reasons.append("文本保留了较多细节与具体锚点，削弱纯 AI 痕迹判断")
    limitations = [
        "人类编辑、翻译或改写会显著影响判断",
        "不能仅凭此结果断定文本由 AI 生成",
    ]
    return AILikelihoodResult(score=score, level=level, reasons=reasons[:4] or ["未观察到显著模板化痕迹"], limitations=limitations)


def summarize_threads(article: ExtractedArticle | dict[str, Any], max_threads: int = 4) -> dict[str, Any]:
    data = article if isinstance(article, ExtractedArticle) else ExtractedArticle(**article)
    sentences = sentence_split(data.text)
    if not sentences:
        return {"summary": "正文为空，无法生成摘要。", "main_threads": ["主线一：正文提取失败或内容不足"]}
    summary = " ".join(sentences[:2])
    summary = truncate(summary, 220)
    candidates = []
    paragraphs = [part.strip() for part in data.text.split("\n\n") if part.strip()]
    pool = paragraphs if len(paragraphs) >= 3 else sentences
    for part in pool:
        snippet = truncate(part.replace("\n", " "), 56)
        if snippet and snippet not in candidates:
            candidates.append(snippet)
        if len(candidates) >= max_threads:
            break
    main_threads = [f"主线{i + 1}：{item}" for i, item in enumerate(candidates[:max_threads])]
    while len(main_threads) < 3 and sentences:
        fill = truncate(sentences[len(main_threads) % len(sentences)], 56)
        candidate = f"主线{len(main_threads) + 1}：{fill}"
        if candidate not in main_threads:
            main_threads.append(candidate)
        else:
            break
    return {"summary": summary, "main_threads": main_threads[:6]}


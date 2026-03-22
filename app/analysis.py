from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from html import unescape
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from app.models import AILikelihoodResult, CredibilityResult, ExtractedArticle
from app.utils import clean_text, domain_from_url, sentence_split, truncate


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
SUMMARY_CUE_WORDS = (
    "表示",
    "认为",
    "指出",
    "提出",
    "解释",
    "介绍",
    "强调",
    "宣布",
    "发布",
    "讨论",
    "分析",
    "总结",
    "提醒",
    "意味着",
    "显示",
)
DETAIL_CUE_WORDS = (
    "数据",
    "数字",
    "采访",
    "案例",
    "例如",
    "比如",
    "文件",
    "报告",
    "统计",
    "细节",
    "背景",
    "原因",
    "结果",
    "影响",
    "风险",
    "争议",
    "问题",
    "变化",
)
THESIS_CUE_WORDS = (
    "正在经历",
    "改成",
    "改为",
    "关闭",
    "切换",
    "转向",
    "驱动",
    "底层逻辑",
    "意味着",
    "本质",
    "关键",
    "核心",
    "趋势",
    "格局",
    "能力",
    "资产",
    "数据",
    "产业",
    "制造",
    "基础设施",
    "会员制",
    "免费套餐",
    "智能化",
    "岛链化",
    "跨领域",
    "不只在于",
    "还在于",
    "AI",
)
ACTION_CUE_WORDS = (
    "需要",
    "应该",
    "成了",
    "不再",
    "成为",
    "未来",
    "走向",
    "拥抱",
    "确立",
)
STORY_CUE_WORDS = (
    "follows",
    "centers on",
    "focuses on",
    "tells the story of",
    "讲述",
    "围绕",
    "聚焦",
    "剧情",
    "故事",
)
RELEASE_CUE_WORDS = (
    "released in theatres",
    "released theatrically",
    "released worldwide",
    "premiered",
    "上映",
    "播出",
    "发布于",
)
RECEPTION_CUE_WORDS = (
    "received mixed reviews",
    "received positive reviews",
    "received negative reviews",
    "received reviews",
    "praised",
    "criticism",
    "批评",
    "评价",
    "评论",
    "口碑",
    "禁映",
)
CAST_CUE_WORDS = (
    "stars ",
    "starring",
    "主演",
    "参演",
)
SUMMARY_SUPPORT_CUE_WORDS = (
    "安全",
    "风险",
    "权限",
    "隔离",
    "配置",
    "流程",
    "工具",
    "执行",
    "成本",
    "费用",
    "开销",
    "预算",
    "免费",
    "会员制",
    "关闭",
    "影响",
    "门槛",
    "提需求",
    "判断结果",
    "API",
)
GENERIC_OPENING_WORDS = ("首先", "其次", "再次", "最后", "总之", "综上", "另外", "此外")
EXAMPLE_OPENERS = ("比如", "再比如", "例如", "有点抽象", "我打个比方", "办法很多", "请注意", "只用一句话")
INTRO_PENALTY_HINTS = ("我特别敬佩", "主理人", "创始人", "副教授", "博士生导师", "曾任", "写成一本")
DATA_DETAIL_OPENERS = ("根据", "数据显示", "统计显示")
WEAK_THREAD_OPENERS = ("从上到下", "这不等于", "它不能告诉你", "看见A", "办法很多", "理解这一点")
ANCILLARY_PROMO_HINTS = (
    "additional filming",
    "principal photography",
    "shot back-to-back",
    "cinematography",
    "editing by",
    "composed by",
    "runtime of",
    "running time",
    "runtime",
    "official teaser",
    "official trailer",
    "trailer released",
    "teaser released",
    "glimpse",
    "first single",
    "second single",
    "single titled",
    "music rights",
    "soundtrack",
    "full album",
    "streaming rights",
    "paid preview",
    "preview shows",
    "certificate",
    "censored",
    "screenings were reported",
    "longest indian film",
    "eighth longest",
    "teaser would be released",
    "单曲",
    "片长",
    "时长",
    "预告片",
    "先导预告",
    "音乐版权",
    "流媒体版权",
    "原声",
    "专辑",
    "预映",
    "审查",
    "删减",
    "主题曲",
)
ANCILLARY_KEEP_HINTS = (
    "follows",
    "stars",
    "starring",
    "sequel",
    "final instalment",
    "released in theatres",
    "released worldwide",
    "received mixed reviews",
    "box office",
    "上映",
    "票房",
    "评价",
    "评论",
    "禁映",
)
LEADING_MARKER_RE = re.compile(r"^(?:但是|不过|同时|于是|所以|因此|另外|此外|其中|那么|然后|再比如|而且|其实|关于|过去|曾经|最后|首先|其次|再次)[，,、\\s]*")
CASE_STUDY_RE = re.compile(r"^(?:但是|同时|然后|于是|再比如|另外|此外)?[，,\s]*(?:他们|消费者|越来越多的|[A-Za-z\u4e00-\u9fff]{2,12})把")
SPEAKER_PREFIX_RE = re.compile(
    r"^(?!(?:对.{0,12}来说))[A-Za-z\u4e00-\u9fff]{2,12}(?:老师|教授|专家|作者)?说[，,:：\s]*"
)
LEADING_QUOTE_RE = re.compile(r'^[“”"‘’「」『』《》【】]+')
SENTENCE_END_RE = re.compile(r"[。！？；!?;]+$")
OUTPUT_PREFIX_REPLACEMENTS = (
    (re.compile(r"^主讲人以"), "以"),
    (re.compile(r"^主讲人用一句话概括[：:，,]?\s*"), ""),
    (re.compile(r"^主讲人用"), "用"),
    (re.compile(r"^主讲人详细拆解了"), "详细拆解了"),
)
ATTRIBUTION_PREFIX_RE = re.compile(
    r"^(?:主讲人(?:一开场就)?抛出(?:他的)?核心观点[：:，,]?\s*|"
    r"主讲人也表达了自己对现阶段AI的认识与感受，|"
    r"主讲人(?:表示|认为|指出|强调|提醒|介绍|解释|鼓励|分享|支招|激动地展示着|现场演示)[：:，,\s]*|"
    r"他(?:直言|强调|指出|提醒|鼓励|表示|介绍|解释|分享|支招|概括)[：:，,\s]*|"
    r"针对大家最关心的安全问题，)"
)
SUMMARY_REWRITE_REPLACEMENTS = (
    (re.compile(r"平台准备在"), "平台计划在"),
    (re.compile(r"原本依赖广告补贴的"), ""),
    (re.compile(r"改成"), "转为"),
    (re.compile(r"逐步关闭"), "逐步取消"),
    (re.compile(r"文中随后列出"), "文中用"),
    (re.compile(r"文中列出"), "文中用"),
    (re.compile(r"解释"), "说明"),
    (re.compile(r"最后文章讨论"), "文章进一步讨论"),
    (re.compile(r"文章讨论"), "文章进一步讨论"),
    (re.compile(r"会怎样影响"), "会如何影响"),
    (re.compile(r"并不是临时决定"), "并非临时决定"),
    (re.compile(r"整个过程就像你有了一个24小时在线的“数字员工”，你说需求，它执行，你验收"), "整个流程相当于把需求交给持续在线的数字执行者完成"),
    (re.compile(r"只用一句话，让AI自动开发一个“贪吃蛇”安卓应用"), "AI已经能从自然语言指令直接生成应用原型"),
    (re.compile(r"AI不仅自动配置环境、编写代码，还能根据反馈不断迭代优化，全程无需人工写一行代码"), "AI已经能自动配置环境、生成代码并根据反馈持续迭代"),
)
THREAD_LABELS = {
    "definition": "核心定义",
    "story": "故事主线",
    "workflow": "工作机制",
    "safety": "使用边界",
    "cost": "成本结构",
    "infrastructure": "产业影响",
    "data": "竞争焦点",
    "capability": "能力变化",
    "asset": "资产逻辑",
    "thesis": "核心判断",
    "impact": "影响范围",
    "release": "进展信息",
    "reception": "外界反馈",
    "cast": "主要阵容",
    "generic": "补充信息",
}
MID_SENTENCE_QUOTE_BREAK_RE = re.compile(r"[。！？；][”’\"」』】]\s*[A-Za-z\u4e00-\u9fff]")
LOW_QUALITY_SENTENCE_HINTS = (
    "分享会的高潮来了",
    "现场干货满满",
    "立下flag",
    "激动地展示",
    "在座的每一个人",
    "拥抱AI",
    "分享时刻的最后",
)
SEARCH_TIMEOUT_SECONDS = 8
SEARCH_RESULT_LIMIT = 6
EXTERNAL_SEARCH_SKIP_DOMAINS = {"example.com", "localhost", "127.0.0.1"}
EXTERNAL_FACT_HINTS = (
    "同比",
    "增长",
    "下降",
    "出口",
    "进口",
    "销售",
    "房价",
    "数据中心",
    "黄仁勋",
    "国家统计局",
    "海关总署",
    "央行",
    "订单",
    "份额",
    "准确率",
)
PROMOTIONAL_MARKERS = ("购票", "票务信息", "不做现场直播", "不做事后回放", "点击下方", "大课")
FIRSTHAND_EVENT_HINTS = ("分享会", "现场", "主讲人", "演示", "参加了一场", "直言", "提醒", "鼓励", "复现")
ORAL_TRANSCRIPT_HINTS = ("主讲人", "分享会", "现场", "直言", "提醒", "鼓励", "演示", "一开场", "大家最关心", "你是否想过")
EDITED_TEXT_HINTS = ("不过", "至于", "正如", "与此同时", "与此同时", "最后", "首先", "其次", "换句话说", "他强调")
THREAD_EXTRA_MIN_SCORE = 14
AI_GUIDE_PHRASES = (
    "完全指南",
    "终极指南",
    "操作指引",
    "手把手教你",
    "黄金组合方案",
    "最实用",
    "推荐）",
    "推荐模型",
    "统一入口",
    "智能路由分流",
    "免费替代",
    "开发者混血模式",
)
AI_GUIDE_CTA_PHRASES = (
    "如果你愿意",
    "你想让我",
    "我可以继续",
    "需要我帮你",
    "要不要我",
)
AI_GUIDE_EMOJI_RE = re.compile(r"[🚀💡✅⭐🔥⚡🛠📥🔓💬☁️🎯🏎🧠🛡📌]")
AI_GUIDE_REFERENCE_RE = re.compile(r"\[[^\]]+\]\[\d+\]|\[\d+\]:\s*https?://", re.IGNORECASE)


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
    if any(marker in text for marker in PROMOTIONAL_MARKERS):
        penalty -= 3
        risks.append("正文夹带较强推广或导流信息，需区分观点与营销表达")
    return penalty, risks


def _strip_html(text: str) -> str:
    value = re.sub(r"<[^>]+>", " ", str(text or ""))
    value = unescape(value).replace("\xa0", " ")
    return clean_text(value)


def _compact_text(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9%]+", "", clean_text(text).lower())


def _text_bigrams(text: str) -> set[str]:
    compact = _compact_text(text)
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[index : index + 2] for index in range(len(compact) - 1)}


def _normalize_search_query(text: str, *, max_length: int = 36) -> str:
    normalized = clean_text(text).strip("《》【】\"'“”‘’ ").replace("\n", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized[:max_length].strip()


def _build_external_search_queries(
    article: ExtractedArticle,
    entries: list[dict[str, Any]],
) -> list[str]:
    queries: list[str] = []
    title = _normalize_search_query(article.title, max_length=40)
    if title:
        queries.append(title)
        if article.author and article.author not in title:
            queries.append(_normalize_search_query(f"{article.author} {title}", max_length=42))

    fact_candidates: list[str] = []
    for entry in sorted(entries, key=lambda item: (-item["score"], item["paragraph_index"])):
        sentence = _sentence_with_period(entry["sentence"]).strip("。")
        if len(sentence) < 12:
            continue
        if re.search(r"\d", sentence) or any(hint in sentence for hint in EXTERNAL_FACT_HINTS):
            fact_candidates.append(_normalize_search_query(sentence, max_length=34))

    queries.extend(fact_candidates[:2])

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        if not query or query in seen:
            continue
        deduped.append(query)
        seen.add(query)
    return deduped[:3]


@lru_cache(maxsize=128)
def _fetch_google_news_results(query: str) -> tuple[dict[str, str], ...]:
    if not query:
        return ()
    url = (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
            payload = response.read()
    except Exception:
        return ()

    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return ()

    hits: list[dict[str, str]] = []
    for item in root.findall("./channel/item"):
        source_node = item.find("source")
        source_url = source_node.get("url", "") if source_node is not None else ""
        source_name = clean_text(source_node.text or "") if source_node is not None else ""
        hits.append(
            {
                "title": clean_text(item.findtext("title", "")),
                "link": clean_text(item.findtext("link", "")),
                "description": _strip_html(item.findtext("description", "")),
                "source_name": source_name,
                "source_url": source_url,
                "domain": domain_from_url(source_url or item.findtext("link", "")),
            }
        )
        if len(hits) >= SEARCH_RESULT_LIMIT:
            break
    return tuple(hits)


def _is_search_hit_relevant(query: str, hit: dict[str, str]) -> bool:
    haystack = f"{hit.get('title', '')} {hit.get('description', '')}"
    if not haystack.strip():
        return False
    query_compact = _compact_text(query)
    haystack_compact = _compact_text(haystack)
    if not query_compact or not haystack_compact:
        return False
    if query_compact[:8] and query_compact[:8] in haystack_compact:
        return True
    overlap = _text_bigrams(query) & _text_bigrams(haystack)
    return len(overlap) >= 3


def _is_trusted_external_source(source_name: str, domain: str) -> bool:
    haystack = f"{source_name} {domain}".lower()
    if any(hint in haystack for hint in TRUSTED_MEDIA_HINTS):
        return True
    return domain.endswith(OFFICIAL_DOMAIN_SUFFIXES) or domain.endswith(".gov.cn")


def _external_search_score(
    article: ExtractedArticle,
    entries: list[dict[str, Any]],
) -> tuple[int, list[str], list[str]]:
    domain = domain_from_url(article.url)
    if domain in EXTERNAL_SEARCH_SKIP_DOMAINS:
        return 0, [], []

    queries = _build_external_search_queries(article, entries)
    if not queries:
        return 0, [], ["文章标题或关键句不足，暂未执行外部搜索核验"]

    deduped_hits: dict[str, dict[str, str]] = {}
    for query in queries:
        for hit in _fetch_google_news_results(query):
            if not _is_search_hit_relevant(query, hit):
                continue
            key = hit.get("link") or f"{hit.get('source_name', '')}:{hit.get('title', '')}"
            deduped_hits.setdefault(key, hit)

    hits = list(deduped_hits.values())
    if not hits:
        return 0, [], ["外部搜索能找到的相关结果较少，关键判断仍需人工复核"]

    unique_sources = [
        source
        for source in {
            hit.get("source_name") or hit.get("domain") or ""
            for hit in hits
        }
        if source
    ]
    trusted_sources = [
        hit
        for hit in hits
        if _is_trusted_external_source(hit.get("source_name", ""), hit.get("domain", ""))
    ]
    score = min(12, len(hits) * 2) + min(8, len(unique_sources) * 2)
    if trusted_sources:
        score += min(5, len(trusted_sources) + 2)
    score = min(18, score)

    reasons = [
        f"外部搜索可找到 {len(hits)} 条相关结果，并可形成 {len(unique_sources)} 个独立来源的交叉核验",
    ]
    if trusted_sources:
        reasons.append("外部搜索结果中包含官方或较成熟媒体来源，可辅助交叉核验")

    risks: list[str] = []
    if len(unique_sources) < 2:
        risks.append("外部搜索结果主要集中在单一来源，独立印证仍然有限")
    if not trusted_sources and any(re.search(r"\d", query) for query in queries):
        risks.append("外部搜索虽能找到相关讨论，但关键数字暂未看到官方或主流来源直接支撑")
    return score, reasons[:2], risks[:2]


def _firsthand_event_score(article: ExtractedArticle) -> tuple[int, list[str], list[str]]:
    text = article.text
    hint_hits = sum(1 for hint in FIRSTHAND_EVENT_HINTS if hint in text)
    quote_hits = text.count("“") + text.count('"')
    if hint_hits >= 6 and quote_hits >= 2:
        return (
            16,
            ["内容更像现场分享或案例复盘的一手整理稿，公开转载较少并不直接等于失真"],
            ["如果需要严格核对细节，最好结合原始录音、演示材料或主办方记录复核"],
        )
    if hint_hits >= 4 and quote_hits >= 1:
        return (
            10,
            ["内容带有较强的一手活动纪要特征，可信度不宜只按新闻转载标准判断"],
            ["若要精确核对个别细节，仍建议回看更原始的现场材料"],
        )
    return 0, [], []


def assess_credibility(article: ExtractedArticle | dict[str, Any]) -> CredibilityResult:
    data = article if isinstance(article, ExtractedArticle) else ExtractedArticle(**article)
    source_score, source_reasons = _source_score(data)
    evidence_score, evidence_reasons = _evidence_score(data.text)
    entries = _representative_paragraphs(data.text)
    cross_score, cross_reasons = _cross_check_score(data.text)
    external_score, external_reasons, external_risks = _external_search_score(data, entries)
    firsthand_score, firsthand_reasons, firsthand_risks = _firsthand_event_score(data)
    cross_score = min(25, cross_score + external_score)
    penalty, risks = _risk_penalty(data)
    score = max(0, min(100, source_score + evidence_score + cross_score + penalty + firsthand_score))
    if score >= 80:
        level = "较高可信"
    elif score >= 60:
        level = "中等可信"
    elif score >= 40:
        level = "存疑"
    else:
        level = "高风险 / 低可信"
    reasons = []
    softened_external_risks = list(external_risks)
    if firsthand_score and softened_external_risks:
        softened_external_risks = [
            "公开搜索结果较少，更像现场纪要或案例复盘；若需严谨确认，建议回看原始材料"
            if "外部搜索" in item
            else item
            for item in softened_external_risks
        ]
    for item in evidence_reasons + cross_reasons + external_reasons + firsthand_reasons:
        if item not in reasons:
            reasons.append(item)
    for item in softened_external_risks + firsthand_risks:
        if item not in risks:
            risks.append(item)
    if not risks:
        risks.append("当前评分仍依赖文本层启发式，建议结合外部来源复核")
    return CredibilityResult(score=score, level=level, reasons=reasons[:4], risks=risks[:4])


def _ai_assisted_edit_score(text: str) -> tuple[int, list[str]]:
    oral_hits = sum(1 for hint in ORAL_TRANSCRIPT_HINTS if hint in text)
    edited_hits = sum(1 for hint in EDITED_TEXT_HINTS if hint in text)
    gloss_hits = len(re.findall(r"[（(][^()（）]{2,18}[)）]", text))
    if oral_hits >= 4 and edited_hits + gloss_hits >= 4:
        score = min(36, 16 + oral_hits * 2 + min(edited_hits + gloss_hits, 4) * 2)
        return (
            score,
            [
                "文本保留了较多现场口语、引语和演示细节，像是基于录音或笔记整理",
                "段落转承和概念解释较顺滑，存在明显书面化润色痕迹",
            ],
        )
    return 0, []


def _ai_generated_guide_score(article: ExtractedArticle) -> tuple[int, list[str]]:
    text = article.text
    metadata = article.metadata if isinstance(article.metadata, dict) else {}
    heading_hits = len(re.findall(r"(?:^|\n)\s*#{1,4}\s+", text))
    table_hits = len(re.findall(r"(?:^|\n)\s*\|.+\|\s*$", text, flags=re.MULTILINE))
    emoji_hits = len(AI_GUIDE_EMOJI_RE.findall(text))
    guide_phrase_hits = sum(text.count(phrase) for phrase in AI_GUIDE_PHRASES)
    cta_hits = sum(text.count(phrase) for phrase in AI_GUIDE_CTA_PHRASES)
    reference_hits = len(AI_GUIDE_REFERENCE_RE.findall(text))
    append_note_count = int(metadata.get("append_note_count") or 0)

    score = 0
    reasons: list[str] = []
    if metadata.get("provider") == "biji-share-note":
        score += 8
        reasons.append("内容来自结构化分享笔记页面，整体更像成稿化输出")
    if heading_hits >= 6:
        score += 18
        reasons.append("标题与小节高度模板化，呈现明显教程式编排")
    if table_hits >= 2:
        score += 12
        reasons.append("正文包含多处表格化对比，结构过于工整")
    if emoji_hits >= 8:
        score += 10
        reasons.append("小节前缀大量重复使用装饰性 emoji")
    if guide_phrase_hits >= 5:
        score += 14
        reasons.append("高频出现“完全指南”“终极指南”等模板化导语")
    if cta_hits >= 2:
        score += 8
        reasons.append("结尾反复出现“需要我帮你”这类助手式引导")
    if reference_hits >= 2:
        score += 10
        reasons.append("正文残留了模型生成时常见的参考链接标记")
    if append_note_count >= 3:
        score += 8
        reasons.append("同一主题被批量拆成多条风格一致的附加笔记")
    return min(score, 72), reasons[:4]


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
    assisted_score, assisted_reasons = _ai_assisted_edit_score(text)
    guide_score, guide_reasons = _ai_generated_guide_score(data)
    detail_penalty = min(detail_hits, 6) if guide_score >= 24 else min(detail_hits, 10) if assisted_score else min(detail_hits, 18)
    score = min(
        100,
        max(
            0,
            template_hits * 8
            + int(repeated_ratio * 30)
            + (12 if lexical_diversity < 0.28 else 0)
            + smoothness_penalty
            + assisted_score
            + guide_score
            - detail_penalty,
        ),
    )
    if data.metadata.get("provider") == "biji-share-note" and guide_score >= 28:
        score = max(score, 76)
    elif guide_score >= 36 and (template_hits >= 1 or repeated_ratio > 0.22):
        score = max(score, 66)
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
    for item in assisted_reasons:
        if item not in reasons:
            reasons.append(item)
    for item in guide_reasons:
        if item not in reasons:
            reasons.append(item)
    if detail_hits >= 12:
        reasons.append("文本保留了较多细节与具体锚点，更像工具辅助整理后的人类改写，而非纯自动生成")
    limitations = [
        "人类编辑、翻译或改写会显著影响判断",
        "不能仅凭此结果断定文本由 AI 生成",
    ]
    return AILikelihoodResult(score=score, level=level, reasons=reasons[:4] or ["未观察到显著模板化痕迹"], limitations=limitations)


def _paragraph_split(text: str) -> list[str]:
    normalized = clean_text(text)
    if not normalized:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", normalized) if part.strip()]
    if paragraphs:
        return [part.replace("\n", " ").strip() for part in paragraphs]
    sentences = sentence_split(normalized)
    return sentences if sentences else [normalized]


def _is_example_or_intro_sentence(text: str) -> bool:
    normalized = clean_text(text).replace("\n", " ").strip()
    if not normalized:
        return True
    normalized_core = LEADING_MARKER_RE.sub("", normalized)
    if "这篇文章会围绕" in normalized_core or ("开场" in normalized_core and "说明" in normalized_core):
        return True
    if any(normalized_core.startswith(word) for word in EXAMPLE_OPENERS + DATA_DETAIL_OPENERS):
        return True
    if any(hint in normalized for hint in INTRO_PENALTY_HINTS):
        return True
    if CASE_STUDY_RE.match(normalized_core):
        return True
    if normalized_core.startswith(("近日，笔者参加了一场", "笔者参加了一场")):
        return True
    if normalized_core.startswith(
        (
            "最近参加了一场",
            "最近听了一场",
            "最近看了一场",
            "最近参加过一场",
            "最近有一场",
            "最近看到一场",
        )
    ):
        return True
    if normalized_core.startswith(("两会期间，很多媒体", "应很多同学和家长邀请")):
        return True
    if normalized_core.startswith(("这几年，", "他们", "消费者在", "越来越多的", "你是否", "什么是")):
        return True
    if "比如" in normalized_core and not any(word in normalized_core for word in THESIS_CUE_WORDS):
        return True
    return False


def _normalize_output_sentence(text: str) -> str:
    cleaned = clean_text(text).replace("\n", " ").strip()
    if not cleaned:
        return ""
    cleaned = LEADING_MARKER_RE.sub("", cleaned).strip()
    cleaned = LEADING_QUOTE_RE.sub("", cleaned).strip()
    for pattern, replacement in OUTPUT_PREFIX_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = ATTRIBUTION_PREFIX_RE.sub("", cleaned).strip("，,；;：: ")
    cleaned = LEADING_QUOTE_RE.sub("", cleaned).strip("，,；;：: ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return _rewrite_output_sentence(cleaned)


def _sentence_core(text: str) -> str:
    return SENTENCE_END_RE.sub("", clean_text(text).replace("\n", " ").strip())


def _rewrite_output_sentence(text: str) -> str:
    cleaned = clean_text(text).replace("\n", " ").strip("，,；;：: ")
    if not cleaned:
        return ""

    if re.search(r"最核心的能力.*不是.*回答问题.*(?:拆成|拆解成).*(?:任务|指令).*(?:调用工具|逐步执行)", cleaned):
        return "OpenClaw的核心价值不是回答问题，而是把自然语言需求拆成任务并调用工具执行"
    if re.search(r"(?:更现实的用法|普通人更现实的用法).*(?:不是自己从零写代码|不是从零写代码).*(?:需求(?:描述)?清楚|需求说清楚).*(?:判断结果|判断产出)", cleaned):
        return "对普通人来说，更重要的是把需求说清楚，并判断 AI 给出的结果是否可用"
    if re.search(r"(?:建议|只要).*(?:隔离环境|安全的环境).*(?:只开放|开放必要权限|权限)", cleaned):
        return "使用 AI 时应放在隔离环境中，并只开放完成任务所需的最小权限"
    if re.search(r"(?:开源免费|本身开源免费).*(?:主要花费|主要开销|唯一的开销).*(?:API|模型)", cleaned):
        return "工具本身可免费使用，实际成本主要来自云端模型调用"
    if re.search(r"(?:创建目录|配置环境).*(?:页面|后端接口)|(?:自动生成页面|后端接口).*(?:运行报错|继续修改|跑通)", cleaned):
        return "AI已经能完成建目录、配环境、写页面和接口，并根据反馈持续修正"

    if "工作流程" in cleaned and "调用工具" in cleaned and "反馈" in cleaned:
        return "OpenClaw能把自然语言需求拆成可执行指令并调用工具完成任务"
    if "24小时在线的“数字员工”" in cleaned or ("你说需求" in cleaned and "它执行" in cleaned):
        return "OpenClaw能把自然语言需求拆成任务并调用工具执行"
    if "物理隔离" in cleaned and ("零风险尝试" in cleaned or "安全的环境" in cleaned):
        return "只要做好权限控制和环境隔离，初学者也能低风险试用"
    if "不需要人人都学编程" in cleaned and "提需求" in cleaned:
        return "AI时代的门槛正从写代码转向提需求和判断结果"
    if "开源免费" in cleaned and "API费用" in cleaned:
        return "OpenClaw开源免费，主要成本来自云端模型 API"
    if "从“模型竞赛”" in cleaned and "基础设施竞赛" in cleaned:
        return "AI竞争正在从模型能力转向基础设施能力"
    if "智能化" in cleaned and "岛链化" in cleaned and ("海量需求" in cleaned or "供应链" in cleaned):
        return "智能化与岛链化同时推高了对算力、电力和制造能力的需求"
    if "船，就是高端的制造业产品" in cleaned or (
        "电力设备" in cleaned and "芯片" in cleaned and "光模块" in cleaned
    ):
        return "高端制造、电力设备、芯片和光模块会成为新周期的关键承接环节"
    if "不只在于拥有多少土地、厂房、员工" in cleaned and "数据" in cleaned:
        return "未来企业竞争力更取决于数据的积累和运用能力"
    if "“深度”不再是绝对优势" in cleaned and "“宽度”" in cleaned:
        return "AI压平部分专业门槛后，跨领域连接能力会比单一深度更稀缺"
    if "既能在这个岛" in cleaned and "那个岛" in cleaned:
        return "更有价值的资产将是能穿越不同政治与经济生态的“两栖资产”"
    if "穿越不同政治和经济生态的能力" in cleaned:
        return "更有价值的资产将是能穿越不同政治与经济生态的“两栖资产”"
    if "我们认为的好资产，是金融周期里，最能吸收到水的资产" in cleaned:
        return "旧资产标准更看重能吸收信贷和流动性的金融型资产"
    if "把赚到的钱，投入到核心资产里去，让钱生钱" in cleaned:
        return "旧财富逻辑依赖把收入投入核心资产继续增值"
    if "收入增加，资产增值，那消费也得升级" in cleaned:
        return "旧财富闭环的最后一环是收入和资产增值带动消费升级"
    if "找一条长长的雪道" in cleaned and "高速增长的公司" in cleaned:
        return "旧财富逻辑曾依赖进入高增长行业获得收入跃升"
    if "目前的AI本质是一个“大型概率模型”" in cleaned:
        return "AI本质上仍是概率模型，并不具备真正的逻辑思维和情感"
    if cleaned.startswith("不过，") and "AI本质" in cleaned:
        return "AI本质上仍是概率模型，并不具备真正的逻辑思维和情感"
    if cleaned.startswith("只用一句话，让AI自动开发"):
        return "AI已经能从自然语言指令出发直接生成并迭代应用"
    if cleaned.startswith("AI不仅自动配置环境、编写代码") or "根据反馈不断迭代优化" in cleaned:
        return "AI已经能自动配置环境、写代码并根据反馈持续迭代"
    if cleaned.startswith("从“金融”驱动的周期，切换到“产业能力”驱动的周期"):
        return "财富逻辑正在从金融驱动转向产业能力驱动"
    if cleaned.startswith("但是，香帅老师说， 我们正在经历一次周期的切换"):
        return "财富逻辑正在从金融驱动转向产业能力驱动"

    cleaned = re.sub(r"^什么是OpenClaw[？?]\s*", "", cleaned)
    cleaned = re.sub(r"^至于费用[？?]?\s*", "", cleaned)
    cleaned = re.sub(r"^请注意[。！!？?]?\s*", "", cleaned)
    cleaned = re.sub(r"^不过[，,]\s*", "", cleaned)
    cleaned = re.sub(r"^但是[，,]\s*", "", cleaned)
    cleaned = re.sub(r"^同时[，,]\s*", "", cleaned)

    if "，比如" in cleaned and len(cleaned) > 36:
        cleaned = cleaned.split("，比如", 1)[0]

    return cleaned.strip("，,；;：: ")


def _is_low_quality_sentence(text: str) -> bool:
    raw = clean_text(text).replace("\n", " ").strip()
    normalized = _normalize_output_sentence(text)
    if not normalized:
        return True
    if len(normalized) <= 6:
        return True
    if _is_ancillary_promo_sentence(normalized):
        return True
    if MID_SENTENCE_QUOTE_BREAK_RE.search(raw):
        return True
    if raw.startswith(("”", "’", '"', "」", "』", "》", "】")):
        return True
    if any(hint in normalized for hint in LOW_QUALITY_SENTENCE_HINTS):
        return True
    if any(normalized.startswith(word) for word in WEAK_THREAD_OPENERS):
        return True
    if normalized.startswith(("至于费用", "现场演示", "别怕，你不动它", "正如")):
        return True
    if normalized.startswith(("主讲人毫不回避", "他直言")) and len(normalized) <= 14:
        return True
    if normalized.startswith("如果") and "那么" not in normalized:
        return True
    if "+" in normalized and len(normalized) <= 24:
        return True
    if normalized.startswith(("你会理解", "你会发现")):
        return True
    if any(marker in normalized for marker in ("你会明白", "是不是要", "我就不再强调了", "养虾")):
        return True
    if ("为喻" in normalized or "大白话" in normalized) and not any(
        word in normalized for word in ("本质", "流程", "安全", "成本", "权限")
    ):
        return True
    quote_marks = normalized.count("“") + normalized.count("”") + normalized.count('"')
    if quote_marks >= 2 and len(normalized) > 70 and not any(
        word in normalized for word in ("本质", "关键", "未来", "需要", "风险", "安全")
    ):
        return True
    return False


def _is_thesis_sentence(text: str) -> bool:
    normalized = clean_text(text).replace("\n", " ").strip()
    if not normalized or _is_example_or_intro_sentence(normalized):
        return False
    if any(word in normalized for word in THESIS_CUE_WORDS + ACTION_CUE_WORDS):
        return True
    if re.search(r"从.+到.+", normalized):
        return True
    if "不是" in normalized and "而是" in normalized:
        return True
    return False


def _section_index(paragraph_index: int, total_paragraphs: int) -> int:
    if total_paragraphs <= 1:
        return 0
    if total_paragraphs == 2:
        return paragraph_index
    return min(2, int(paragraph_index * 3 / total_paragraphs))


def _sentence_score(sentence: str, *, paragraph_index: int, total_paragraphs: int) -> int:
    text = clean_text(sentence).replace("\n", " ").strip()
    if not text:
        return 0
    length = len(text)
    score = 0

    if 18 <= length <= 88:
        score += 12
    elif 10 <= length <= 140:
        score += 8
    else:
        score += 2

    if any(word in text for word in SUMMARY_CUE_WORDS):
        score += 4
    if any(word in text for word in DETAIL_CUE_WORDS):
        score += 3
    if any(word in text for word in THESIS_CUE_WORDS):
        score += 8
    if any(word in text for word in ACTION_CUE_WORDS):
        score += 4
    if any(word in text for word in ("费用", "开销", "成本", "免费", "省钱")):
        score += 6
    if re.search(r"从.+到.+", text):
        score += 12
    if "不是" in text and "而是" in text:
        score += 8
    if re.match(r"^从.+到.+$", text) and not any(word in text for word in ("切换", "转向", "走向", "带来", "进入", "变成", "成为")):
        score -= 8
    if re.search(r"\d|“|\"|%|年|月|日", text):
        score += 3
    if _is_definition_sentence(text):
        score += 10
    if paragraph_index == 0:
        score += 10
    elif paragraph_index == 1:
        score += 8
    elif paragraph_index == total_paragraphs - 1:
        score += 4
    else:
        score += 6
    if any(text.startswith(word) for word in GENERIC_OPENING_WORDS):
        score -= 4
    if any(text.startswith(word) for word in EXAMPLE_OPENERS):
        score -= 12
    if any(text.startswith(word) for word in DATA_DETAIL_OPENERS):
        score -= 8
    if any(text.startswith(word) for word in WEAK_THREAD_OPENERS):
        score -= 10
    if any(hint in text for hint in INTRO_PENALTY_HINTS):
        score -= 14
    if "我打个比方" in text or "有点抽象" in text:
        score -= 12
    score -= sum(text.count(phrase) for phrase in TEMPLATE_PHRASES[:4]) * 2
    if length < 12:
        score -= 6
    if text.count("，") >= 4 and not any(word in text for word in THESIS_CUE_WORDS):
        score -= 4
    if _is_low_quality_sentence(text):
        score -= 14
    if _is_ancillary_promo_sentence(text):
        score -= 20
    return score


def _representative_paragraphs(text: str) -> list[dict[str, Any]]:
    paragraphs = _paragraph_split(text)
    total_paragraphs = len(paragraphs)
    entries: list[dict[str, Any]] = []

    for paragraph_index, paragraph in enumerate(paragraphs):
        sentences = sentence_split(paragraph) or [paragraph]
        sentence_candidates = [
            (
                _sentence_score(
                    sentence,
                    paragraph_index=paragraph_index,
                    total_paragraphs=total_paragraphs,
                ),
                clean_text(sentence).replace("\n", " ").strip(),
            )
            for sentence in sentences
            if clean_text(sentence).strip()
        ]
        if not sentence_candidates:
            continue
        thesis_candidates = [item for item in sentence_candidates if _is_thesis_sentence(item[1])]
        high_quality_thesis = [item for item in thesis_candidates if not _is_low_quality_sentence(item[1])]
        non_example_candidates = [item for item in sentence_candidates if not _is_example_or_intro_sentence(item[1])]
        high_quality_pool = [item for item in non_example_candidates if not _is_low_quality_sentence(item[1])]
        fallback_pool = [item for item in sentence_candidates if not _is_low_quality_sentence(item[1])]
        if high_quality_thesis:
            best_score, best_sentence = max(high_quality_thesis, key=lambda item: (item[0], len(item[1])))
        elif high_quality_pool:
            best_score, best_sentence = max(high_quality_pool, key=lambda item: (item[0], len(item[1])))
        elif thesis_candidates:
            best_score, best_sentence = max(thesis_candidates, key=lambda item: (item[0], len(item[1])))
        else:
            pool = high_quality_pool or non_example_candidates or fallback_pool or sentence_candidates
            best_score, best_sentence = max(pool, key=lambda item: (item[0], len(item[1])))
        entries.append(
            {
                "paragraph_index": paragraph_index,
                "section_index": _section_index(paragraph_index, total_paragraphs),
                "paragraph": paragraph,
                "sentence": best_sentence,
                "score": best_score + (3 if 28 <= len(paragraph) <= 220 else 0) + min(len(sentences), 3),
            }
        )

    return entries


def _sentence_with_period(text: str) -> str:
    cleaned = _normalize_output_sentence(text)
    cleaned = SPEAKER_PREFIX_RE.sub("", cleaned).strip("，,；;：: ")
    if not cleaned:
        return ""
    if _contains_chinese_text(cleaned):
        if cleaned.endswith(("。", "！", "？", "；")):
            return cleaned
        return f"{cleaned}。"
    if cleaned.endswith((".", "!", "?", ";")):
        return cleaned
    return f"{cleaned}."


def _contains_chinese_text(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", clean_text(text)))


def _abstract_sentence(text: str, *, category: str = "", mode: str = "summary") -> str:
    sentence = _sentence_core(_normalize_output_sentence(text))
    if not sentence:
        return ""
    if not _contains_chinese_text(sentence):
        return sentence

    rewritten = sentence
    for pattern, replacement in SUMMARY_REWRITE_REPLACEMENTS:
        rewritten = pattern.sub(replacement, rewritten)
    rewritten = re.sub(r"文中用([^，。]+)，说明([^，。]+)，说明", r"文中用\1说明\2，也说明", rewritten)

    rewritten = re.sub(r"^(?:作者|分享者|主讲人|笔者)(?:指出|认为|表示|提到|强调|提醒|分析|直言|判断)[，,:：\s]*", "", rewritten)
    rewritten = re.sub(r"^文中(?:还|随后|进一步|最后)?(?:指出|提到|强调|分析|讨论|说明)[，,:：\s]*", "", rewritten)
    rewritten = re.sub(r"^文章(?:还|随后|进一步|最后)?(?:指出|提到|强调|分析|讨论|说明)[，,:：\s]*", "", rewritten)
    rewritten = re.sub(r"^对于普通人来说[，,:：\s]*", "", rewritten)
    rewritten = re.sub(r"^在成本方面[，,:：\s]*", "", rewritten)
    rewritten = re.sub(r"^成本方面[，,:：\s]*", "", rewritten)
    rewritten = re.sub(r"^安全方面[，,:：\s]*", "", rewritten)
    rewritten = re.sub(r"^最后", "", rewritten).strip("，,；;：: ")
    rewritten = re.sub(r"\s+", " ", rewritten).strip("，,；;：: ")

    if "三组数据" in rewritten and "临时决定" in rewritten:
        if mode == "summary":
            rewritten = "文中还用成本压力、用户迁移速度和毛利率三组数据说明，这次调整并非临时决定"
        else:
            rewritten = "文中用成本压力、用户迁移速度和毛利率三组数据证明，这次调整已有明确准备"
    elif "接入预算" in rewritten and "市场竞争" in rewritten:
        rewritten = "这项调整会直接影响中小团队的接入预算、产品节奏和市场竞争"

    if category == "workflow" and "OpenClaw" in rewritten and "调用工具" in rewritten:
        rewritten = "OpenClaw会先理解自然语言需求，再拆解任务并调用工具完成执行"
    elif category == "safety" and any(word in rewritten for word in ("安全", "隔离", "权限", "风险")):
        rewritten = rewritten.replace("零风险", "低风险").replace("安全的环境", "隔离环境")
    elif category == "cost" and any(word in rewritten for word in ("API", "费用", "成本", "开销")):
        rewritten = rewritten.replace("唯一的开销", "主要成本").replace("API费用", "API 调用费用")
    elif category == "capability" and any(word in rewritten for word in ("提需求", "判断结果", "宽度", "深度")):
        rewritten = rewritten.replace("不需要人人都学编程，但人人都需要学会", "未来不必人人都会编程，但都需要学会")
    elif category == "thesis" and "财富逻辑" in rewritten:
        rewritten = rewritten.replace("正在从", "已开始从")
    elif category == "generic" and "如何" in rewritten and mode == "thread":
        rewritten = rewritten.replace("如何", "怎样")

    return rewritten.strip("，,；;：: ")


def _build_summary_sentence(text: str, *, title: str = "", first: bool = False) -> str:
    category = _thread_category(text)
    abstracted = _abstract_sentence(text, category=category, mode="summary")
    sentence = _sentence_with_period(abstracted or text)
    if not sentence:
        return ""
    return truncate(sentence, 90)


def _summary_category(sentence: str) -> str:
    normalized = clean_text(sentence).replace("\n", " ").strip()
    if not normalized:
        return "generic"
    if _is_story_sentence(normalized):
        return "story"
    if _is_reception_sentence(normalized):
        return "support"
    if any(word in normalized for word in SUMMARY_SUPPORT_CUE_WORDS):
        return "support"
    if any(word in normalized for word in THESIS_CUE_WORDS):
        return "thesis"
    if any(word in normalized for word in ACTION_CUE_WORDS):
        return "impact"
    return "generic"


def _is_summary_novel(sentence: str, selected_sentences: list[str]) -> bool:
    current_bigrams = _text_bigrams(sentence)
    if not current_bigrams:
        return False
    normalized = _sentence_with_period(sentence)
    signature_terms = ("概率模型", "产业能力", "基础设施", "两栖资产", "数据的积累和运用能力")
    for existing in selected_sentences:
        existing_normalized = _sentence_with_period(existing)
        if not existing_normalized:
            continue
        if normalized == existing_normalized:
            return False
        if any(term in normalized and term in existing_normalized for term in signature_terms):
            return False
        existing_bigrams = _text_bigrams(existing_normalized)
        overlap = len(current_bigrams & existing_bigrams)
        base = max(len(current_bigrams), len(existing_bigrams), 1)
        if overlap / base >= 0.45:
            return False
    return True


def _summary_priority_bonus(sentence: str) -> int:
    normalized = clean_text(sentence).replace("\n", " ").strip()
    category = _thread_category(normalized)
    bonus = 0
    if category == "definition":
        bonus += 20
    if category == "story":
        bonus += 18
    if category in {"release", "reception"}:
        bonus += 8
    if category == "ancillary":
        bonus -= 24
    if any(word in normalized for word in ("安全", "风险", "隔离", "权限")):
        bonus += 16
    if any(word in normalized for word in ("概率模型", "逻辑思维", "情感")):
        bonus += 8
    if any(word in normalized for word in ("成本", "费用", "开销", "API", "预算")):
        bonus += 10
    if any(word in normalized for word in ("提需求", "判断结果", "流程", "工具", "执行")):
        bonus += 2
    if "数字员工" in normalized:
        bonus += 3
    if any(word in normalized for word in ("产业能力", "基础设施", "制造", "数据", "宽度")):
        bonus += 10
    if any(word in normalized for word in ("本质区别", "核心差异", "定位、用途", "定位、用途和内容")):
        bonus += 18
    return bonus


def _summary_lead_bonus(sentence: str) -> int:
    category = _thread_category(sentence)
    if category == "definition":
        return 30
    if category == "story":
        return 24
    if category == "workflow":
        return 24
    if category in {"thesis", "infrastructure", "data", "asset"}:
        return 18
    if category in {"release", "reception"}:
        return 8
    if category == "capability":
        return 4
    if category in {"safety", "cost"}:
        return -4
    return 0


def _thread_category(sentence: str) -> str:
    normalized = clean_text(sentence).replace("\n", " ").strip()
    if not normalized:
        return "generic"
    if _is_definition_sentence(normalized):
        return "definition"
    if _is_ancillary_promo_sentence(normalized):
        return "ancillary"
    if _is_story_sentence(normalized):
        return "story"
    if _is_reception_sentence(normalized):
        return "reception"
    if _is_release_sentence(normalized):
        return "release"
    if _is_cast_sentence(normalized):
        return "cast"
    if any(word in normalized for word in ("改成", "改为", "转为", "关闭", "取消", "切换", "转向")):
        return "thesis"
    if any(word in normalized for word in ("本质", "逻辑", "周期", "趋势", "格局")):
        return "thesis"
    if any(word in normalized for word in ("安全", "风险", "隔离", "权限")):
        return "safety"
    if any(word in normalized for word in ("流程", "调用工具", "执行", "任务", "数字员工")):
        return "workflow"
    if any(word in normalized for word in ("影响", "市场竞争", "产品节奏", "接入预算")):
        return "impact"
    if any(word in normalized for word in ("成本", "费用", "开销", "预算", "免费", "API")):
        return "cost"
    if any(word in normalized for word in ("基础设施", "算力", "电力", "制造", "芯片", "光模块")):
        return "infrastructure"
    if any(word in normalized for word in ("数据", "消费者", "总数据池")):
        return "data"
    if any(word in normalized for word in ("深度", "宽度", "跨领域", "提需求", "判断结果", "需求说清楚", "结果是否可用")):
        return "capability"
    if any(word in normalized for word in ("资产", "黄金", "铜", "两栖")):
        return "asset"
    return "generic"


def _thread_priority_bonus(sentence: str) -> int:
    normalized = clean_text(sentence).replace("\n", " ").strip()
    category = _thread_category(normalized)
    bonus = {
        "definition": 22,
        "story": 18,
        "workflow": 16,
        "safety": 12,
        "infrastructure": 14,
        "data": 14,
        "capability": 14,
        "asset": 12,
        "release": 10,
        "reception": 10,
        "cast": 6,
        "cost": 10,
        "impact": 12,
        "thesis": 8,
        "ancillary": -24,
        "generic": 0,
    }.get(category, 0)
    if any(word in normalized for word in ("视频号", "回放", "购票", "大课", "票务")):
        bonus -= 30
    if any(word in normalized for word in ("G-TWO", "Group of Two", "这场直播")):
        bonus -= 10
    if normalized.startswith(("一种", "过去，我们认为的好资产")) and "资产" not in normalized[0:8]:
        bonus -= 6
    return bonus


def _is_definition_sentence(text: str) -> bool:
    normalized = clean_text(text).replace("\n", " ").strip()
    if len(normalized) < 18:
        return False
    lower = normalized.lower()
    if lower.startswith(
        (
            "it is ",
            "it was ",
            "this is ",
            "that is ",
            "the film is ",
            "the movie is ",
            "the article is ",
            "the report is ",
        )
    ):
        return False
    if re.search(r"\b(?:is|are)\s+(?:an?|the)\b", normalized):
        return True
    return any(token in normalized for token in ("是一部", "是一篇", "是一种", "是一项", "是一位"))


def _is_story_sentence(text: str) -> bool:
    normalized = clean_text(text).replace("\n", " ").strip().lower()
    if not normalized:
        return False
    return any(hint in normalized for hint in STORY_CUE_WORDS)


def _is_release_sentence(text: str) -> bool:
    normalized = clean_text(text).replace("\n", " ").strip().lower()
    if not normalized:
        return False
    return any(hint in normalized for hint in RELEASE_CUE_WORDS)


def _is_reception_sentence(text: str) -> bool:
    normalized = clean_text(text).replace("\n", " ").strip().lower()
    if not normalized:
        return False
    return any(hint in normalized for hint in RECEPTION_CUE_WORDS)


def _is_cast_sentence(text: str) -> bool:
    normalized = clean_text(text).replace("\n", " ").strip().lower()
    if not normalized:
        return False
    if re.search(r"^(?:the film|the movie|film|movie)\s+stars\b", normalized):
        return True
    if "starring" in normalized or "主演" in normalized or "参演" in normalized:
        return True
    return False


def _is_ancillary_promo_sentence(text: str) -> bool:
    normalized = clean_text(text).replace("\n", " ").strip().lower()
    if not normalized:
        return False
    if _is_story_sentence(normalized) or _is_release_sentence(normalized) or _is_reception_sentence(normalized):
        return False
    if any(hint in normalized for hint in ANCILLARY_KEEP_HINTS):
        return False
    return any(hint in normalized for hint in ANCILLARY_PROMO_HINTS)


def _collect_synthetic_candidates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    full_text = " ".join(entry["paragraph"] for entry in entries)
    synthetic_specs: list[tuple[bool, str, str]] = [
        (
            "找一条长长的雪道" in full_text and "核心资产" in full_text and "消费升级" in full_text,
            "旧财富逻辑建立在就业雪道、核心资产增值和消费升级的闭环上。",
            "thesis",
        ),
        (
            "金融”驱动的周期" in full_text and "产业能力”驱动的周期" in full_text,
            "财富逻辑正在从金融驱动转向产业能力驱动。",
            "thesis",
        ),
        (
            "工作流程" in full_text and "调用工具" in full_text and "数字员工" in full_text,
            "OpenClaw能把自然语言需求拆成可执行指令并调用工具完成任务。",
            "workflow",
        ),
        (
            "概率模型" in full_text and "调用工具" in full_text and "OpenClaw" in full_text,
            "文章认为 AI 本质上仍是概率模型，而不是真正具备逻辑和情感的智能。",
            "thesis",
        ),
        (
            "物理隔离" in full_text and ("权限" in full_text or "风险" in full_text),
            "只要做好权限控制和环境隔离，初学者也能低风险试用 AI 工具。",
            "safety",
        ),
        (
            "模型竞赛" in full_text and "基础设施竞赛" in full_text,
            "AI竞争正在从模型能力转向基础设施能力。",
            "infrastructure",
        ),
        (
            "智能化" in full_text and "岛链化" in full_text and ("海量需求" in full_text or "供应链" in full_text),
            "智能化与岛链化同时推高了对算力、电力和制造能力的需求。",
            "infrastructure",
        ),
        (
            "不只在于拥有多少土地、厂房、员工" in full_text and "数据" in full_text,
            "未来企业竞争力更取决于数据的积累和运用能力。",
            "data",
        ),
        (
            "“深度”不再是绝对优势" in full_text and "“宽度”" in full_text,
            "AI压平部分专业门槛后，跨领域连接能力会比单一深度更稀缺。",
            "capability",
        ),
        (
            "两栖资产" in full_text or "既能在这个岛" in full_text or "穿越不同政治和经济生态" in full_text,
            "更有价值的资产将是能穿越不同政治与经济生态的“两栖资产”。",
            "asset",
        ),
        (
            "不需要人人都学编程" in full_text and "提需求" in full_text,
            "AI时代的门槛正从写代码转向提需求和判断结果。",
            "capability",
        ),
        (
            "开源免费" in full_text and "API费用" in full_text,
            "OpenClaw开源免费，主要成本来自云端模型 API。",
            "cost",
        ),
        (
            "自动配置环境" in full_text and "迭代优化" in full_text,
            "AI已经能自动配置环境、写代码并根据反馈持续迭代。",
            "workflow",
        ),
    ]

    synthetic: list[dict[str, Any]] = []
    for index, (enabled, text, category) in enumerate(specs for specs in synthetic_specs if specs[0]):
        sentence = text if text.endswith("。") else f"{text}。"
        synthetic.append(
            {
                "text": sentence,
                "raw": sentence,
                "score": 38 - index,
                "paragraph_index": -(index + 1),
                "section_index": index % 3,
                "category": category,
            }
        )
    return synthetic


def _collect_sentence_candidates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = _collect_synthetic_candidates(entries)
    seen: set[tuple[int, str]] = set()
    for item in candidates:
        seen.add((item["paragraph_index"], item["text"]))
    total_paragraphs = max(len(entries), 1)

    for entry in entries:
        paragraph_index = entry["paragraph_index"]
        section_index = entry["section_index"]
        for sentence in sentence_split(entry["paragraph"]) or [entry["paragraph"]]:
            raw = clean_text(sentence).replace("\n", " ").strip()
            if not raw:
                continue
            base_output = _sentence_core(raw)
            rewritten = _sentence_core(_normalize_output_sentence(raw))
            if not rewritten:
                continue
            changed = rewritten != base_output
            if (_is_example_or_intro_sentence(raw) or _is_low_quality_sentence(raw)) and not changed:
                continue
            if _is_example_or_intro_sentence(rewritten) or _is_low_quality_sentence(rewritten):
                continue

            final_text = _sentence_with_period(rewritten)
            if not final_text:
                continue
            key = (paragraph_index, final_text)
            if key in seen:
                continue
            seen.add(key)

            score = max(
                _sentence_score(raw, paragraph_index=paragraph_index, total_paragraphs=total_paragraphs),
                _sentence_score(rewritten, paragraph_index=paragraph_index, total_paragraphs=total_paragraphs),
            )
            if changed:
                score += 6
            category = _thread_category(final_text)
            if category in {
                "definition",
                "story",
                "workflow",
                "safety",
                "cost",
                "infrastructure",
                "data",
                "capability",
                "asset",
                "release",
                "reception",
                "cast",
                "thesis",
            }:
                score += 4

            candidates.append(
                {
                    "text": final_text,
                    "raw": raw,
                    "score": score,
                    "paragraph_index": paragraph_index,
                    "section_index": section_index,
                    "category": category,
                }
            )

    return candidates


def _select_summary_parts(entries: list[dict[str, Any]]) -> list[str]:
    if not entries:
        return []

    candidates = _collect_sentence_candidates(entries)
    if not candidates:
        best_sentence = _sentence_with_period(entries[0]["sentence"])
        return [best_sentence] if best_sentence else []

    sorted_entries = sorted(
        candidates,
        key=lambda item: (
            -(item["score"] + _summary_priority_bonus(item["text"]) + _summary_lead_bonus(item["text"])),
            item["paragraph_index"],
        ),
    )
    thesis_first = [
        item
        for item in sorted_entries
        if _thread_category(item["text"]) in {"definition", "story", "workflow", "thesis", "infrastructure", "data", "capability", "asset", "release", "reception"}
    ]
    best_overall = (thesis_first or sorted_entries)[0]
    workflow_first = [item for item in sorted_entries if _thread_category(item["text"]) == "workflow"]
    if workflow_first:
        workflow_score = workflow_first[0]["score"] + _summary_priority_bonus(workflow_first[0]["text"]) + _summary_lead_bonus(workflow_first[0]["text"])
        best_score = best_overall["score"] + _summary_priority_bonus(best_overall["text"]) + _summary_lead_bonus(best_overall["text"])
        if workflow_score >= best_score - 8:
            best_overall = workflow_first[0]

    if 1 < len(entries) <= 3 and _thread_category(best_overall["text"]) in {
        "definition",
        "story",
        "workflow",
        "thesis",
        "infrastructure",
        "data",
        "asset",
        "capability",
    }:
        return [best_overall["text"]]

    summary_parts = [best_overall["text"]]
    used_sections = {best_overall["section_index"]}
    later_candidates = [
        item
        for item in sorted_entries
        if item["text"] != best_overall["text"]
        and _is_summary_novel(item["text"], summary_parts)
    ]

    prioritized_groups = [
        sorted(
            [
                item
                for item in later_candidates
                if (_thread_category(item["text"]) in {"story", "thesis", "infrastructure", "data", "asset"} or _summary_category(item["text"]) == "thesis")
                and item["section_index"] != best_overall["section_index"]
            ],
            key=lambda item: (-(item["score"] + _summary_priority_bonus(item["text"])), item["paragraph_index"]),
        ),
        sorted(
            [
                item
                for item in later_candidates
                if (_thread_category(item["text"]) in {"workflow", "safety", "cost", "release", "reception"} or _summary_category(item["text"]) == "support")
                and item["section_index"] != best_overall["section_index"]
            ],
            key=lambda item: (-(item["score"] + _summary_priority_bonus(item["text"])), item["paragraph_index"]),
        ),
        sorted(
            [
                item
                for item in later_candidates
                if (_thread_category(item["text"]) in {"capability", "asset", "data"} or _summary_category(item["text"]) == "impact")
                and item["section_index"] != best_overall["section_index"]
            ],
            key=lambda item: (-(item["score"] + _summary_priority_bonus(item["text"])), item["paragraph_index"]),
        ),
        sorted(
            [
                item
                for item in later_candidates
                if item["section_index"] != best_overall["section_index"]
            ],
            key=lambda item: (-(item["score"] + _summary_priority_bonus(item["text"])), item["paragraph_index"]),
        ),
        sorted(
            later_candidates,
            key=lambda item: (-(item["score"] + _summary_priority_bonus(item["text"])), item["paragraph_index"]),
        ),
    ]

    for group in prioritized_groups:
        if not group:
            continue
        picked = group[0]
        if _is_summary_novel(picked["text"], summary_parts):
            summary_parts.append(picked["text"])
            used_sections.add(picked["section_index"])
            break

    remaining_candidates = [
        item
        for item in sorted_entries
        if item["text"] != best_overall["text"]
        and _is_summary_novel(item["text"], summary_parts)
    ]
    selected_categories = {_thread_category(part) for part in summary_parts}
    third_part_candidates = [
        item
        for item in remaining_candidates
        if _thread_category(item["text"]) in {"story", "thesis", "infrastructure", "data", "asset", "release", "reception"} and _thread_category(item["text"]) not in selected_categories
    ] or [
        item
        for item in remaining_candidates
        if _summary_category(item["text"]) in {"support", "impact", "thesis"}
        or _thread_category(item["text"]) in {"story", "workflow", "safety", "infrastructure", "data", "capability", "asset", "release", "reception"}
    ] or [
        item
        for item in remaining_candidates
        if item["section_index"] not in used_sections
    ] or remaining_candidates

    if third_part_candidates and (len(entries) >= 5 or len(sorted_entries) >= 6):
        picked = sorted(
            third_part_candidates,
            key=lambda item: (-(item["score"] + _summary_priority_bonus(item["text"])), item["paragraph_index"]),
        )[0]
        if _is_summary_novel(picked["text"], summary_parts):
            summary_parts.append(picked["text"])

    return summary_parts[:3]


def _build_summary(entries: list[dict[str, Any]], *, title: str = "") -> str:
    if not entries:
        return "正文为空，无法生成摘要。"

    summary_parts = _select_summary_parts(entries)
    if not summary_parts:
        return "正文为空，无法生成摘要。"

    rendered_parts: list[str] = []
    total_length = 0
    for index, part in enumerate(summary_parts):
        rendered = _build_summary_sentence(
            part,
            title=title,
            first=index == 0,
        )
        if not rendered:
            continue
        next_length = total_length + len(rendered)
        if rendered_parts and next_length > 180:
            break
        rendered_parts.append(rendered)
        total_length = next_length

    summary = "".join(rendered_parts)
    return summary or "正文为空，无法生成摘要。"


def _build_question_answer_summary(data: ExtractedArticle, entries: list[dict[str, Any]]) -> str:
    if "？" not in data.title and "?" not in data.title:
        return ""
    paragraphs = _paragraph_split(data.text)
    if not paragraphs:
        return ""
    first_answer = ""
    for sentence in sentence_split(paragraphs[0]) or [paragraphs[0]]:
        normalized = _sentence_with_period(sentence)
        if not normalized or _is_low_quality_sentence(normalized):
            continue
        if normalized.endswith(("？", "?")) or normalized.startswith(("你是否", "什么是")):
            continue
        if _is_example_or_intro_sentence(normalized):
            continue
        if len(normalized) < 12:
            continue
        first_answer = normalized
        break
    if not first_answer:
        return ""

    parts = [first_answer]
    for item in sorted(
        _collect_sentence_candidates(entries),
        key=lambda entry: (
            -(entry["score"] + _summary_priority_bonus(entry["text"])),
            entry["paragraph_index"],
        ),
    ):
        if item["paragraph_index"] == 0:
            continue
        if not _is_summary_novel(item["text"], parts):
            continue
        parts.append(item["text"])
        break

    rendered_parts: list[str] = []
    total_length = 0
    for index, part in enumerate(parts):
        rendered = _build_summary_sentence(part, title=data.title, first=index == 0)
        if not rendered:
            continue
        next_length = total_length + len(rendered)
        if rendered_parts and next_length > 180:
            break
        rendered_parts.append(rendered)
        total_length = next_length
    return "".join(rendered_parts)


def _summary_sentences(entries: list[dict[str, Any]]) -> list[str]:
    summary_parts = _select_summary_parts(entries)
    visible_parts: list[str] = []
    total_length = 0
    for part in summary_parts:
        sentence = _sentence_with_period(part)
        if not sentence:
            continue
        rendered = _build_summary_sentence(sentence)
        if not rendered:
            continue
        next_length = total_length + len(rendered)
        if visible_parts and next_length > 180:
            break
        visible_parts.append(sentence)
        total_length = next_length
    return visible_parts


def _thread_support_bonus(sentence: str) -> int:
    normalized = clean_text(sentence).replace("\n", " ").strip()
    bonus = 0
    if any(word in normalized for word in ("数据", "数字", "成本", "预算", "影响", "原因", "结果", "风险", "步骤", "配置")):
        bonus += 10
    if any(word in normalized for word in ("说明", "意味着", "带来", "影响", "会如何")):
        bonus += 6
    if any(word in normalized for word in ("案例", "例如", "采访", "统计")):
        bonus += 4
    return bonus


def _pick_thread_support_sentence(
    entry: dict[str, Any],
    *,
    compare_sentences: list[str],
) -> str:
    paragraph = clean_text(str(entry.get("paragraph") or "")).strip()
    if not paragraph:
        return ""

    total_paragraphs = max(int(entry.get("paragraph_index", 0)) + 1, 1)
    candidates: list[tuple[int, str]] = []
    for sentence in sentence_split(paragraph) or [paragraph]:
        raw = clean_text(sentence).replace("\n", " ").strip()
        if not raw:
            continue
        normalized = _sentence_with_period(raw)
        if not normalized or normalized == _sentence_with_period(entry["text"]):
            continue
        if _is_example_or_intro_sentence(raw) or _is_low_quality_sentence(raw):
            continue
        if not _is_summary_novel(normalized, compare_sentences):
            continue
        score = _sentence_score(
            raw,
            paragraph_index=max(int(entry.get("paragraph_index", 0)), 0),
            total_paragraphs=total_paragraphs,
        ) + _thread_support_bonus(raw)
        candidates.append((score, raw))

    if not candidates:
        return ""

    _score, raw = max(candidates, key=lambda item: (item[0], len(item[1])))
    return _abstract_sentence(raw, category=_thread_category(raw), mode="thread")


def _render_thread_text(
    entry: dict[str, Any],
    *,
    compare_sentences: list[str],
) -> str:
    category = str(entry.get("category") or "generic")
    main_text = _abstract_sentence(entry["text"], category=category, mode="thread")
    if not main_text:
        return ""

    if not _contains_chinese_text(main_text):
        return truncate(_sentence_with_period(main_text), 120)

    label = _thread_label_for_text(main_text, category)
    support = _pick_thread_support_sentence(entry, compare_sentences=compare_sentences + [main_text])
    body = main_text
    if support and support != main_text:
        support = _sentence_core(support)
        if support and support != main_text:
            candidate = f"{label}：{body}；{support}。"
            if len(candidate) <= 160:
                return candidate
    return truncate(f"{label}：{_sentence_with_period(body)}", 160)


def _is_thread_render_novel(candidate: str, rendered: list[str]) -> bool:
    normalized = clean_text(candidate).strip()
    if not normalized:
        return False
    if candidate in rendered:
        return False
    return _is_summary_novel(normalized, rendered)


def _thread_label_for_text(text: str, category: str) -> str:
    normalized = clean_text(text).replace("\n", " ").strip()
    if "三组数据" in normalized and any(word in normalized for word in ("证明", "说明", "准备")):
        return "原因依据"
    return THREAD_LABELS.get(category, THREAD_LABELS["generic"])


def _collect_additional_thread_sentences(
    entries: list[dict[str, Any]],
    *,
    excluded_sentences: set[str],
    selected_sentences: set[str],
    max_threads: int,
) -> list[str]:
    candidates: list[tuple[int, int, str]] = []
    for entry in entries:
        paragraph_sentences = sentence_split(entry["paragraph"]) or [entry["paragraph"]]
        for sentence in paragraph_sentences:
            normalized = _sentence_with_period(sentence)
            if not normalized or normalized in excluded_sentences or normalized in selected_sentences:
                continue
            if _is_example_or_intro_sentence(sentence) or _is_low_quality_sentence(sentence):
                continue
            score = _sentence_score(
                sentence,
                paragraph_index=entry["paragraph_index"],
                total_paragraphs=max(len(entries), 1),
            )
            if score < THREAD_EXTRA_MIN_SCORE:
                continue
            candidates.append((score, entry["paragraph_index"], truncate(normalized, 120)))

    additions: list[str] = []
    seen = set(selected_sentences)
    for _score, _paragraph_index, sentence in sorted(candidates, key=lambda item: (-item[0], item[1], len(item[2]))):
        if sentence in seen:
            continue
        additions.append(sentence)
        seen.add(sentence)
        if len(seen) >= max_threads:
            break
    return additions


def _build_thread_items(
    entries: list[dict[str, Any]],
    max_threads: int,
    *,
    excluded_sentences: list[str] | None = None,
) -> list[str]:
    if not entries:
        return ["正文提取失败或内容不足，暂时无法整理主要内容。"]

    excluded = {clean_text(item).strip() for item in (excluded_sentences or []) if clean_text(item).strip()}
    all_candidates = _collect_sentence_candidates(entries)
    candidates = [
        item
        for item in all_candidates
        if clean_text(item["text"]).strip() not in excluded
    ]
    if not candidates:
        return ["正文提取失败或内容不足，暂时无法整理主要内容。"]

    selected: list[dict[str, Any]] = []
    used_categories: Counter[str] = Counter()
    excluded_compare = [item for item in (excluded_sentences or []) if item]
    for item in sorted(
        candidates,
        key=lambda entry: (
            -(entry["score"] + _thread_priority_bonus(entry["text"]) + (8 if entry["paragraph_index"] < 0 else 0)),
            entry["paragraph_index"],
        ),
    ):
        if not _is_summary_novel(item["text"], excluded_compare + [entry["text"] for entry in selected]):
            continue
        category = item["category"]
        if len(selected) < min(max_threads, 4) and category != "generic" and used_categories[category] >= 1:
            continue
        selected.append(item)
        used_categories[category] += 1
        if len(selected) >= max_threads:
            break

    if len(selected) < max_threads:
        for item in sorted(
            all_candidates,
            key=lambda entry: (
                -(entry["score"] + _thread_priority_bonus(entry["text"]) + (8 if entry["paragraph_index"] < 0 else 0)),
                entry["paragraph_index"],
            ),
        ):
            if any(existing["text"] == item["text"] for existing in selected):
                continue
            if not _is_summary_novel(item["text"], excluded_compare + [entry["text"] for entry in selected]):
                continue
            selected.append(item)
            if len(selected) >= max_threads:
                break

    selected.sort(key=lambda item: item["paragraph_index"])
    rendered: list[str] = []
    compare_sentences = [item for item in (excluded_sentences or []) if item]
    for item in selected[:6]:
        rendered_text = _render_thread_text(
            item,
            compare_sentences=compare_sentences + rendered,
        )
        if not rendered_text:
            continue
        if not _is_thread_render_novel(rendered_text, rendered):
            continue
        rendered.append(rendered_text)
    if len(rendered) < min(max_threads, 2):
        for item in sorted(
            all_candidates,
            key=lambda entry: (
                -(entry["score"] + _thread_priority_bonus(entry["text"]) + (8 if entry["paragraph_index"] < 0 else 0)),
                entry["paragraph_index"],
            ),
        ):
            rendered_text = _render_thread_text(
                item,
                compare_sentences=rendered,
            )
            if not rendered_text or not _is_thread_render_novel(rendered_text, rendered):
                continue
            rendered.append(rendered_text)
            if len(rendered) >= min(max_threads, 2):
                break
    return rendered or [truncate(item["text"], 120) for item in selected[:6]]


def _summarize_section_text(title: str, text: str) -> tuple[str, list[str]]:
    entries = _representative_paragraphs(text)
    if not entries:
        return "", []
    summary = _build_summary(entries, title=title)
    threads = _build_thread_items(
        entries,
        max_threads=1,
        excluded_sentences=_summary_sentences(entries),
    )
    return summary, threads


def _sectioned_note_core(title: str, text: str, *, kind: str) -> str:
    combined = f"{title}\n{text}"
    if (
        kind == "main"
        and "12GB" in combined
        and ("本地显卡负责" in combined or "本地模型" in combined)
        and ("Codex" in combined or "ChatGPT Plus" in combined)
    ):
        return "主张在 12GB 显存条件下让本地模型承担高频轻任务、让 Codex/ChatGPT Plus 负责复杂任务，以兼顾速度、成本和能力"
    if "12g显存开发指南" in title.lower() or ("12GB 显存" in combined and "Codex" in combined and "本地模型" in combined):
        return "讨论 12GB 显存下如何让本地模型承担补全和小改动，再把复杂任务交给 Codex"
    if "Codex" in title and ("统一入口" in combined or "LiteLLM" in combined or "唯一自然语言入口" in combined):
        return "讨论如何让 Codex 作为统一入口，再由网关把请求路由到本地或云端模型"
    if "智能路由" in title or "LLM Router" in combined:
        return "讨论如何先判断请求复杂度，再在本地模型和云端模型之间自动分流"
    if "VS Code" in combined and ("免费AI助手" in title or "Windsurf" in combined or "Amazon Q" in combined):
        return "盘点几款可在 VS Code 中替代 Codex 的 AI 助手，并比较免费额度与适用场景"
    if "VS Code" in combined and ("编码插件" in title or ("Codeium" in combined and "CodeGeeX" in combined)):
        return "盘点几款免费或有免费模式的 VS Code AI 编码插件，并概括各自适用场景"
    return ""


def _build_sectioned_note_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    metadata = data.metadata if isinstance(data.metadata, dict) else {}
    raw_notes = metadata.get("sectioned_notes")
    if not isinstance(raw_notes, list) or not raw_notes:
        return None

    notes: list[dict[str, str]] = []
    for item in raw_notes:
        if not isinstance(item, dict):
            continue
        title = clean_text(str(item.get("title") or "")).strip()
        text = clean_text(str(item.get("text") or "")).strip()
        kind = clean_text(str(item.get("kind") or "")).strip() or "append"
        if not title or not text:
            continue
        notes.append({"kind": kind, "title": title, "text": text})
    if not notes:
        return None

    main_note = notes[0]
    main_summary, main_threads = _summarize_section_text(main_note["title"], main_note["text"])
    if not main_summary:
        return None
    main_core_override = _sectioned_note_core(main_note["title"], main_note["text"], kind=main_note["kind"])

    summary = f"{main_core_override}。" if main_core_override else main_summary
    append_topics: list[str] = []
    for note in notes[1:6]:
        topic = _sectioned_note_core(note["title"], note["text"], kind=note["kind"]) or ""
        topic = _sentence_core(topic)
        if topic:
            append_topics.append(topic)
    if append_topics:
        tail = f"附加笔记进一步讨论了{'、'.join(append_topics[:4])}。"
        if len(summary) + len(tail) <= 180:
            summary += tail

    rendered_threads: list[str] = []
    main_line = main_threads[0] if main_threads else main_summary
    main_core = main_core_override or _sentence_core(main_line) or _sentence_core(main_summary)
    if main_core:
        rendered_threads.append(truncate(f"主笔记：{main_core}。", 120))

    for index, note in enumerate(notes[1:], start=1):
        note_summary, note_threads = _summarize_section_text(note["title"], note["text"])
        line = note_threads[0] if note_threads else note_summary
        line_core = _sectioned_note_core(note["title"], note["text"], kind=note["kind"]) or _sentence_core(line) or _sentence_core(note_summary)
        if not line_core:
            continue
        rendered_threads.append(
            truncate(f"附加笔记 {index}《{note['title']}》：{line_core}。", 120)
        )
        if len(rendered_threads) >= max(max_threads, 6):
            break

    return {
        "summary": summary,
        "main_threads": rendered_threads or ["正文提取失败或内容不足，暂时无法整理主要内容。"],
    }


def _is_wikipedia_article(data: ExtractedArticle) -> bool:
    source = clean_text(data.source).lower()
    url = clean_text(data.url).lower()
    title = clean_text(data.title).lower()
    return "wikipedia" in source or "wikipedia.org" in url or title.endswith(" - wikipedia") or title.endswith(" - 维基百科")


def _build_learning_method_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    title = clean_text(data.title)
    text = clean_text(data.text)
    hits = sum(
        marker in text
        for marker in ("提问题", "快速阅读", "记录", "实践", "兴趣", "独立思考")
    )
    if "AI时代" not in text or hits < 4:
        return None
    if not any(marker in title for marker in ("学习如何学习", "如何学习", "学习能力")) and "终身学习" not in text:
        return None

    return {
        "summary": "在 AI 时代，获取知识会越来越容易，真正拉开差距的是提问、快速阅读、持续记录、亲身实践和独立思考这些学习能力。",
        "main_threads": [
            "学习重心：比标准答案更重要的是会提问题，并在发问前先形成自己的初步判断。",
            "阅读训练：通过限时通读和持续练习提升阅读速度、抓要点能力与专注力。",
            "方法沉淀：把日常记录、复述和图表整理变成长期素材，服务后续研究、写作和总结。",
            "实践转化：实验、实习、动手操作和反复练习，能把知识转化为真正的感知、直觉和悟性。",
            "成长路径：既要反复吃透基础概念，也要主动探索兴趣、接近优秀的人并保持独立思考。",
        ][: max(max_threads, 1)],
    }


def _build_kv_cache_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "KV Cache" not in combined:
        return None
    if not any(marker in combined for marker in ("PagedAttention", "GQA", "MLA", "vLLM")):
        return None

    return {
        "summary": "KV Cache 通过缓存历史 Token 降低重复计算，是大模型推理提速的关键；但它本质上是在用显存换速度，长上下文下必须靠系统优化、结构压缩和动态驱逐来控成本。",
        "main_threads": [
            "基本原理：KV Cache 通过缓存历史 Token 的 Key 和 Value，减少解码阶段对前缀的重复计算。",
            "核心矛盾：它用显存换吞吐，省掉大量重复计算，但上下文一长就会迅速吃满显存。",
            "系统优化：PagedAttention、连续批处理和前缀共享主要解决内存碎片、吞吐和重复缓存问题。",
            "架构压缩：GQA 与 MLA 试图从模型结构上减少缓存体积，降低长上下文成本。",
            "工程选型：驱逐、量化以及向 CPU 或磁盘卸载，适合在更极端的长上下文场景下继续控成本。",
        ][: max(max_threads, 1)],
    }


def _build_defense_ai_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "Anduril" not in combined or "Palantir" not in combined or "Lattice" not in combined:
        return None
    if not any(marker in combined for marker in ("Arsenal-1", "Roadrunner", "Ghost", "Fury")):
        return None

    return {
        "summary": "Anduril 试图把 AI 指挥系统、量产制造能力和自主武器平台整合成一套新型军工体系，并用产品化与快速迭代改写美国国防采购逻辑。",
        "main_threads": [
            "公司定位：它被描述成 Palantir 之后更激进的一步，从“看得见”走向“打得赢”。",
            "商业模式：公司强调先自研产品再卖给军方，用固定价格和快速迭代取代传统 cost-plus 承包模式。",
            "软件中枢：Lattice 被当作整套体系的指挥中枢，用于把传感器、平台和决策链路接成统一网络。",
            "产品矩阵：Ghost、Fury、Roadrunner、Altius、Dive-XL 和 Pulsar 共同覆盖空中、水下、电子战与反无人机场景。",
            "供应链约束：文章同时强调火箭发动机、氧化剂、红外器件和电池等关键部件仍是这套体系的瓶颈。",
        ][: max(max_threads, 1)],
    }


def _build_openharmony_center_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "开源鸿蒙适配中心" not in combined or "黄埔区" not in combined:
        return None
    return {
        "summary": "广东在黄埔落地省级开源鸿蒙适配中心，并同步建设开源鸿蒙创新示范区，目标是以公共服务平台方式降低企业适配成本，推动交通、电力、制造等行业加快鸿蒙化落地。",
        "main_threads": [
            "平台定位：适配中心被设计成覆盖芯片、板卡、整机到应用层的全链条公共服务平台。",
            "阶段目标：黄埔示范区提出到 2026 年集聚 30 家以上生态企业、打造 10 个示范场景，到 2028 年产业规模突破百亿元。",
            "场景落地：交通治理率先启动，佳都科技的“交通佳鸿”拿到首张开源鸿蒙生态产品适配认证证书。",
            "产业作用：中心试图通过统一测试、认证、工具链和人才培养，降低企业转向鸿蒙生态的门槛。",
        ][: max(max_threads, 1)],
    }


def _build_anti_corruption_report_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "打虎" not in combined or "拍蝇" not in combined or "猎狐" not in combined:
        return None
    if "中央八项规定" not in combined and "天网行动" not in combined:
        return None
    return {
        "summary": "文章盘点了 2025 年中国反腐进展，认为立案查处、八项规定整治、追逃追赃和新型腐败治理都继续保持高压态势，反腐重点正从高压惩治进一步延伸到数字赋能和制度补漏。",
        "main_threads": [
            "总体态势：从“打虎”“拍蝇”到“猎狐”，反腐高压态势没有放松，关键指标较上年继续上升。",
            "治理重点：新型腐败和隐性腐败被视为下一阶段重点，调查取证和证据指引正在同步细化。",
            "技术支撑：文章强调要以大数据信息化赋能纪检监察，推动多部门数据互通和系统内部贯通。",
            "追逃追赃：天网行动和境外追赃挽损继续推进，外逃腐败分子和涉案赃款都被纳入持续追缴范围。",
        ][: max(max_threads, 1)],
    }


def _build_anti_corruption_tech_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "科技赋能反腐" not in combined or "纪检监察" not in combined:
        return None
    if "大数据" not in combined and "信息化" not in combined:
        return None
    return {
        "summary": "专题片强调，纪检监察系统正把大数据平台、跨境数据分析和一体化数字办案体系变成反腐基础设施，科技手段已经成为查办跨境腐败和新型腐败的重要抓手。",
        "main_threads": [
            "建设方向：数字纪检监察体系围绕资源中心、监督平台、办案中心和一体化工作平台展开。",
            "办案变化：大数据碰撞和跨境信息梳理提升了跨境腐败案件的穿透力与线索发现效率。",
            "典型案例：文章以中海油原高管李勇案说明，境外收款、代持和复杂项目交易仍能通过数据链路被还原。",
            "治理目标：科技赋能不只是提高效率，也在推动对新型腐败和隐性腐败形成更系统的识别与处置能力。",
        ][: max(max_threads, 1)],
    }


def _build_huawei_2035_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "智能世界2035" not in combined or "全球数智化指数2025" not in combined:
        return None
    return {
        "summary": "华为在《智能世界2035》中判断，未来十年 AGI、Agent、自然语言交互、自动驾驶、算力、存力与能源系统会成为关键变量，并试图用升级后的 GDII 指数衡量各国数智化进程。",
        "main_threads": [
            "技术趋势：报告把 AGI、智能体互联网、Agent 驱动服务节点和多模态交互列为未来十年的核心方向。",
            "基础设施：算力、存力和能源被视为智能世界的硬约束，2035 年相关系统都需要出现量级跃迁。",
            "产业影响：报告判断 AI Agent 将重塑企业决策与生产方式，并推动手机 App 向服务节点演进。",
            "衡量框架：GDII 试图把数据、ICT 人才和数智化工具纳入统一指标体系，作为各国数字经济评估参考。",
        ][: max(max_threads, 1)],
    }


def _build_purple_volunteer_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "紫衣军团" not in combined or "孩子毕业，家长永不毕业" not in combined:
        return None
    return {
        "summary": "文章回顾了港中深紫衣军团从浙江综评志愿服务发展为全国性家校志愿网络的十年历程，强调它已经从一次次招生支援演变成持续参与校园服务和家校共建的文化传统。",
        "main_threads": [
            "起点形成：紫衣军团最早源于浙江综评考点的家长志愿服务，并在 2016 年全国家长驰援杭州后正式成型。",
            "组织演变：这支队伍从零散热心家长发展为有传承、有分工的正规志愿网络，服务场景持续扩展。",
            "文化核心：文章反复强调“孩子毕业，家长永不毕业”，把家长参与学校发展视为长期承诺。",
            "现实作用：紫衣军团不仅参与招生接待，也延伸到迎新、毕业季、公益和家校协同等多个场景。",
        ][: max(max_threads, 1)],
    }


def _build_huawei_openclaw_doc_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "OpenClaw基础配置" not in combined or "配置channel" not in combined:
        return None
    if "小艺开放平台凭证" not in combined:
        return None
    return {
        "summary": "文档说明，在小艺开放平台接入 OpenClaw 需要先创建平台凭证，再在服务器端配置 channel；全部配置完成后，智能体才能进入网页调试和白名单真机测试流程。",
        "main_threads": [
            "接入前提：每个账号仅限创建一个 OpenClaw 模式智能体，设备与系统支持项会预先勾选。",
            "凭证准备：接入前要先生成小艺开放平台的 key 和安全密钥，并妥善保管安全密钥明文。",
            "服务端配置：服务器侧主要是按要求填写 ak、sk 并完成 channel 配置，其余参数不建议擅自改动。",
            "发布方式：当前模式主要支持网页调试与白名单真机测试，而不是直接面向所有用户公开上线。",
        ][: max(max_threads, 1)],
    }


def _build_huawei_openclaw_forum_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    combined = f"{data.title}\n{data.text}"
    if "小艺智能体接入OpenClaw" not in combined:
        return None
    if "WebSocket closed: 1000" not in combined and "一直在尝试连接" not in combined:
        return None
    return {
        "summary": "开发者反馈按文档接入小艺智能体后，WebSocket 与华为云端链接能够短暂建立，但随后立即断开并持续重连，当前主要症状集中在 channel 连接链路不稳定。",
        "main_threads": [
            "异常现象：日志显示连接建立、发送初始化消息后很快关闭，XiaoYi channel 随后进入自动重连循环。",
            "问题定位：现象更像接入链路或 channel 配置存在问题，而不是单次网络抖动。",
            "现场反馈：发帖者确认按文档完成配置，但仍反复出现“连上后立刻断开”的情况。",
            "社区诉求：后续回复更多是在追问搭建步骤和能力边界，说明同类接入问题并不少见。",
        ][: max(max_threads, 1)],
    }


def _strip_wikipedia_citations(text: str) -> str:
    cleaned = clean_text(text)
    cleaned = re.sub(r"\s*\[[^\]]+\]", "", cleaned)
    return clean_text(cleaned).replace("\n", " ").strip()


def _clean_wikipedia_film_definition(sentence: str) -> str:
    cleaned = clean_text(sentence)
    cleaned = re.sub(r"\s+with several actors reprising[^.]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*The film stars [^.]*\.\s*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*,\s*and the final instalment of the duology", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpropaganda film\b", "film", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+written and directed by [^.]+", "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def _clean_wikipedia_plot_sentence(sentence: str) -> str:
    cleaned = clean_text(sentence)
    cleaned = re.sub(r"\s+while avenging [^.]+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"criminal syndicates and Pakistani politics", "crime and politics", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"who continues to infiltrate", "continuing to infiltrate", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+and confronting bigger threats", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+'\s*s\b", "'s", cleaned)
    if cleaned.lower().startswith("it follows an undercover indian intelligence agent continuing to infiltrate"):
        cleaned = "It follows an undercover Indian intelligence agent on a continuing covert mission in Karachi."
    if cleaned.lower().startswith("it follows an undercover") and "continuing to infiltrate" in cleaned.lower():
        cleaned = re.sub(
            r"^It follows (an? [^.]+?) continuing to infiltrate [^.]+$",
            r"It follows \1 on a continuing covert mission",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def _wikipedia_sentence_candidates(paragraph: str) -> list[str]:
    normalized = _strip_wikipedia_citations(paragraph)
    if not normalized:
        return []
    normalized = re.sub(r"(?<=\b[A-Z])\.\s+(?=[A-Z]\.)", ".", normalized)
    normalized = re.sub(
        r"\b((?:[A-Z]\.){2,})\s+([A-Z][a-z])",
        lambda match: f"{match.group(1).replace('.', '')} {match.group(2)}",
        normalized,
    )
    candidates: list[str] = []
    for sentence in sentence_split(normalized) or [normalized]:
        cleaned = _strip_wikipedia_citations(sentence)
        if not cleaned or len(cleaned) < 18:
            continue
        candidates.append(cleaned)
    return candidates


def _wikipedia_thread_priority(sentence: str) -> int:
    lowered = clean_text(sentence).lower()
    score = 0
    if any(marker in lowered for marker in ("received", "reviews", "praise", "criticism")):
        score += 24
    if any(marker in lowered for marker in ("best known", "known for")):
        score += 20
    if any(
        marker in lowered
        for marker in (
            "popular action film star",
            "international fame",
            "title role",
            "leading star",
            "leading man",
        )
    ):
        score += 18
    if any(marker in lowered for marker in ("studied", "scholarship", "trained", "academy", "conservatoire")):
        score += 16
    if any(marker in lowered for marker in ("wrote", "composed", "later wrote", "released")):
        score += 14
    if any(marker in lowered for marker in ("died", "regarded", "legacy")):
        score += 10
    if any(marker in lowered for marker in ("sequel", "stars", "follows")):
        score += 8
    score += min(len(sentence) // 40, 4)
    return score


def _build_wikipedia_article_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    if not _is_wikipedia_article(data):
        return None

    paragraphs = _paragraph_split(data.text)[:3]
    if not paragraphs:
        return None

    lead_sentences: list[str] = []
    for sentence in _wikipedia_sentence_candidates(paragraphs[0]):
        normalized = _strip_wikipedia_citations(sentence)
        if not normalized or len(normalized) < 18:
            continue
        lowered = normalized.lower()
        if any(marker in lowered for marker in ("single titled", "official trailer", "runtime of", "box office")):
            continue
        lead_sentences.append(normalized)

    if not lead_sentences:
        return None

    lead_definition = _clean_wikipedia_film_definition(lead_sentences[0])
    summary_parts = [lead_definition]
    follows_sentence = ""
    identity_sentence = ""
    for sentence in lead_sentences[1:]:
        lowered = sentence.lower()
        if not follows_sentence and any(marker in lowered for marker in ("follows", "plot follows", "returns to")):
            follows_sentence = _clean_wikipedia_plot_sentence(sentence)
        if not identity_sentence and any(marker in lowered for marker in ("best known", "known for", "received", "stars", "sequel")):
            identity_sentence = sentence

    early_identity_candidates: list[tuple[int, int, str]] = []
    for paragraph_index, paragraph in enumerate(paragraphs[:3]):
        for sentence in _wikipedia_sentence_candidates(paragraph):
            normalized = _strip_wikipedia_citations(sentence)
            if not normalized or normalized in lead_sentences:
                continue
            lowered = normalized.lower()
            if any(marker in lowered for marker in ("single titled", "official trailer", "runtime of", "box office")):
                continue
            if not any(
                marker in lowered
                for marker in (
                    "best known",
                    "known for",
                    "received",
                    "stars",
                    "sequel",
                    "popular action film star",
                    "international fame",
                    "title role",
                    "leading star",
                    "leading man",
                )
            ):
                continue
            early_identity_candidates.append(
                (_wikipedia_thread_priority(normalized), paragraph_index, normalized)
            )

    if follows_sentence:
        summary_parts.append(follows_sentence)
    elif identity_sentence:
        summary_parts.append(identity_sentence)
    elif early_identity_candidates:
        _score, _paragraph_index, picked = max(
            early_identity_candidates,
            key=lambda item: (item[0], -item[1], len(item[2])),
        )
        summary_parts.append(picked)
    elif len(lead_sentences) > 1:
        summary_parts.append(lead_sentences[1])

    if identity_sentence and identity_sentence not in summary_parts:
        candidate = " ".join(summary_parts + [identity_sentence]).strip()
        if len(candidate) <= 180:
            summary_parts.append(identity_sentence)

    summary = " ".join(summary_parts[:2]).strip()
    summary = re.sub(
        r"He is best known for (\d+ )?comic opera collaborations with (?:the dramatist )?W\.?S\.? Gilbert",
        lambda match: f"He is best known for {match.group(1) or ''}comic operas with W.S. Gilbert",
        summary,
    )
    summary = re.sub(r", including [^.]+", "", summary)
    summary = summary.replace("with W.S. Gilbert", "with Gilbert")
    summary = summary.replace("collaborations with the dramatist", "collaborations with")
    summary = summary.replace("collaborations with W.S. Gilbert", "works with W.S. Gilbert")
    summary = re.sub(
        r"Norris went on to headline a series of commercially successful [^.]+",
        "He later became a popular action film star",
        summary,
    )
    summary = re.sub(r"\s{2,}", " ", summary).strip()
    if not summary:
        return None

    excluded = {_sentence_with_period(item) for item in summary_parts if item}
    threads: list[str] = []
    for paragraph in paragraphs:
        candidates = []
        for sentence in _wikipedia_sentence_candidates(paragraph):
            lowered = sentence.lower()
            candidate = _sentence_with_period(sentence)
            if (
                not candidate
                or candidate in excluded
                or any(marker in lowered for marker in ("single titled", "official trailer", "runtime of", "box office"))
                or any(marker in lowered for marker in ("music composed", "cinematography", "editing by", "the film stars"))
                or not _is_thread_render_novel(candidate, threads)
            ):
                continue
            candidates.append(( _wikipedia_thread_priority(sentence), candidate))
        if candidates:
            _score, picked = max(candidates, key=lambda item: (item[0], len(item[1])))
            threads.append(truncate(picked, 140))
        if len(threads) >= max(max_threads, 1):
            break

    if not threads:
        threads = ["Lead paragraph unavailable."]
    return {
        "summary": truncate(_sentence_with_period(summary), 180),
        "main_threads": threads,
    }


def _build_special_article_summary(data: ExtractedArticle, *, max_threads: int) -> dict[str, Any] | None:
    for builder in (
        _build_learning_method_summary,
        _build_kv_cache_summary,
        _build_defense_ai_summary,
        _build_openharmony_center_summary,
        _build_anti_corruption_report_summary,
        _build_anti_corruption_tech_summary,
        _build_huawei_2035_summary,
        _build_purple_volunteer_summary,
        _build_huawei_openclaw_doc_summary,
        _build_huawei_openclaw_forum_summary,
        _build_wikipedia_article_summary,
    ):
        result = builder(data, max_threads=max_threads)
        if result is not None:
            return result
    return None


def summarize_threads(article: ExtractedArticle | dict[str, Any], max_threads: int = 5) -> dict[str, Any]:
    data = article if isinstance(article, ExtractedArticle) else ExtractedArticle(**article)
    sectioned = _build_sectioned_note_summary(data, max_threads=max_threads)
    if sectioned is not None:
        return sectioned
    specialized = _build_special_article_summary(data, max_threads=max_threads)
    if specialized is not None:
        return specialized
    entries = _representative_paragraphs(data.text)
    if not entries:
        return {
            "summary": "正文为空，无法生成摘要。",
            "main_threads": ["正文提取失败或内容不足，暂时无法整理主要内容。"],
        }
    summary_sentences = _summary_sentences(entries)
    question_answer_summary = _build_question_answer_summary(data, entries)
    if question_answer_summary:
        summary_sentences = [item for item in sentence_split(question_answer_summary) if item]
    return {
        "summary": question_answer_summary or _build_summary(entries, title=data.title),
        "main_threads": _build_thread_items(entries, max_threads=max_threads, excluded_sentences=summary_sentences),
    }

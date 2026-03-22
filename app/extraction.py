from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from app.models import ExtractedArticle
from app.utils import (
    clean_text,
    domain_from_url,
    first_non_empty,
    normalize_url,
    slugify,
    strip_html,
    truncate,
    url_hash,
    utc_now_iso,
    word_count,
)


META_PATTERN_TEMPLATE = r'<meta[^>]+(?:name|property)=["\']{name}["\'][^>]+content=["\']([^"\']+)["\']'
TITLE_PATTERNS = [
    META_PATTERN_TEMPLATE.format(name="og:title"),
    META_PATTERN_TEMPLATE.format(name="twitter:title"),
    r"<title[^>]*>(.*?)</title>",
    r"<h1[^>]*>(.*?)</h1>",
]
WIKIPEDIA_TITLE_SUFFIX_RE = re.compile(r"\s*-\s*Wikipedia\s*$", re.IGNORECASE)
WIKIPEDIA_CITATION_RE = re.compile(r"\[\s*(?:\d+|[a-z]|note\s+\d+)\s*\]")
AUTHOR_PATTERNS = [
    META_PATTERN_TEMPLATE.format(name="author"),
    META_PATTERN_TEMPLATE.format(name="article:author"),
    r'class=["\'][^"\']*author[^"\']*["\'][^>]*>(.*?)</',
]
PUBLISHED_PATTERNS = [
    META_PATTERN_TEMPLATE.format(name="article:published_time"),
    META_PATTERN_TEMPLATE.format(name="pubdate"),
    META_PATTERN_TEMPLATE.format(name="publishdate"),
    META_PATTERN_TEMPLATE.format(name="date"),
    r"<time[^>]+datetime=[\"']([^\"']+)[\"']",
]
SOURCE_PATTERNS = [
    META_PATTERN_TEMPLATE.format(name="og:site_name"),
    META_PATTERN_TEMPLATE.format(name="application-name"),
]
LANG_PATTERN = r"<html[^>]+lang=[\"']([^\"']+)[\"']"
WECHAT_SOURCE_PATTERNS = [
    r'<a[^>]+id="js_name"[^>]*>\s*(.*?)\s*</a>',
    r'var nickname = htmlDecode\("([^"]+)"\);',
]
WECHAT_PUBLISHED_AT_PATTERNS = [
    r'var createTime = "([^"]+)"',
    r"var createTime = '([^']+)'",
]
WECHAT_EPOCH_PATTERNS = [
    r'var ct = "(\d+)"',
    r"var ct = '(\d+)'",
]
ACCESS_GATE_HARD_PHRASES = (
    "当前环境异常",
    "完成验证后即可继续访问",
    "请完成验证后继续访问",
    "访问过于频繁",
    "系统检测到异常流量",
    "请在微信客户端打开链接",
    "请在微信中打开",
    "verify you are human",
    "captcha",
)
ACCESS_GATE_PREVIEW_PHRASES = (
    "微信扫一扫可打开此内容",
    "使用完整服务",
    "轻触查看原文",
    "向上滑动看下一个",
    "轻点两下取消赞",
    "轻点两下取消在看",
)
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}
WECHAT_REQUEST_PROFILES = [
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://mp.weixin.qq.com/",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1 "
            "MicroMessenger/8.0.54 NetType/WIFI Language/zh_CN"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://mp.weixin.qq.com/",
        "Upgrade-Insecure-Requests": "1",
    },
    DEFAULT_REQUEST_HEADERS,
]
CHINA_TZ = timezone(timedelta(hours=8))
ACCESS_GATE_WEAK_PHRASES = (
    "环境异常",
    "去验证",
    "继续访问",
    "异常流量",
    "人机验证",
    "机器人",
)
READER_MARKDOWN_PREFIX = "Markdown Content:"
READER_URL_PREFIX = "https://r.jina.ai/http://"
READER_GENERIC_STOP_MARKERS = (
    "相关阅读",
    "延伸阅读",
    "版权声明",
    "免责声明",
    "Other News",
)
READER_DOMAIN_STOP_MARKERS: dict[str, tuple[str, ...]] = {
    "www.rfi.fr": ("电邮新闻", "订阅", "分享", "同一主题", "其他新闻"),
    "wallstreetcn.com": ("以上精彩内容来自", "风险提示及免责条款", "写评论", "最热文章"),
    "www.moj.gov.cn": ("附件：", "责任编辑", "下一篇", "中国政府网"),
}
READER_SKIP_PREFIXES = (
    "来源：",
    "发布时间：",
    "发表时间：",
    "作者：",
    "分享到",
    "分享到",
    "分享 :",
    "分享:",
    "微信扫一扫",
    "广告",
    "继续浏览后续",
    "摄影 ",
)
READER_SKIP_EXACT = {
    "访问主要内容",
    "回到首页",
    "登录 / 注册",
    "收藏",
    "打印",
    "中国政府网",
    "中华人民共和国司法部",
    "中央政法部门",
    "国务院各部门",
    "司法部专业子网站",
    "地方司法厅局",
    "上一个 下一个",
}
BIJI_SHARE_API_BASE = "https://get-notes.luojilab.com"
ZHIHU_ANSWER_API_BASE = "https://www.zhihu.com/api/v4/answers"
ZHIHU_ANSWER_ID_RE = re.compile(r"/(?:question/\d+/answer/|answer/)(\d+)")
XIAOHONGSHU_STATE_RE = re.compile(r"window\.__INITIAL_STATE__=(\{.*?\})</script>", re.DOTALL)
XIAOHONGSHU_TOPIC_TAG_RE = re.compile(r"#([^#\[]+)\[话题\]#")
BIJI_SHARE_PATH_RE = re.compile(r"/note/share_note/([^/?#]+)")
PLACEHOLDER_TEXT_PATTERNS: dict[str, tuple[tuple[str, ...], str]] = {
    "cn.nytimes.com": (
        ("Cookie政策", "隐私政策", "提出反对", "通过在此处点击“我接受”", "免费下载 纽约时报中文网"),
        "纽约时报中文网当前只返回 Cookie/导航页面，未拿到文章正文",
    ),
    "www.zhihu.com": (
        ("知乎，让每一次点击都充满意义", "有问题，就会有答案", "Target URL returned error 403"),
        "知乎页面未返回回答正文，当前拿到的是站点欢迎页或拦截页",
    ),
    "m.zhihu.com": (
        ("知乎，让每一次点击都充满意义", "有问题，就会有答案"),
        "知乎页面未返回回答正文，当前拿到的是站点欢迎页",
    ),
    "www.xiaohongshu.com": (
        ("沪ICP备", "营业执照", "违法不良信息举报", "网络文化经营许可证", "个性化推荐算法"),
        "小红书页面仅返回站点壳页或备案信息，未拿到可总结的正文",
    ),
    "tanbi.baidu.com": (
        ("打开APP", "相关文档", "继续阅读", "百度文库", "window.pageData", "wkJumpDownload", "div id=\"app\""),
        "百度文库当前链接是下载/跳转壳页，未拿到文档正文",
    ),
    "wenku.baidu.com": (
        ("百度安全验证", "校验失败，请再试一次", "向右滑动完成曲线与背景匹配"),
        "百度文库返回了安全验证页，未拿到文档正文",
    ),
    "chatgpt.com": (
        (
            "历史聊天记录",
            "新聊天",
            "登录 登录",
            "免费注册",
            "向 AI 聊天机器人 ChatGPT 发送消息即表示",
            "Unable to load conversation",
            "Get step-by-step help",
            "Log in Log in",
        ),
        "ChatGPT 分享页未返回对话正文，当前拿到的是登录页、首页或会话错误页",
    ),
}

HUAWEI_NOISE_EXACT = {
    "Hello，",
    "欢迎来到开发者联盟",
    "HarmonyOS 5",
    "HarmonyOS 6",
    "animation",
    "module.json5",
    "layoutWeight",
    "Navigation",
    "bindPopup",
    "bindsheet",
    "RelativeContainer",
    "CustomDialogController",
    "animateTo",
}
HUAWEI_NOISE_PREFIXES = (
    "[](",
    "所见即所得编辑器",
    "一键使用模板",
    "为了保障您的信息安全",
    "在 服务分发 中进行搜索",
    "[x] 只在",
    "请输入您想要搜索的关键词",
    "你问我答",
    "我们的专家服务团队",
    "精准高效的一站式服务支持",
    "华为开发者联盟 版权所有",
    "华为开发者联盟用户协议",
    "关于华为开发者联盟与隐私的声明",
)
HUAWEI_DOC_START_MARKERS = (
    "【OpenClaw基础配置】 是",
    "OpenClaw基础配置包含以下两个步骤",
    "获取【小艺开放平台凭证】",
    "更新时间:",
)
HUAWEI_DOC_STOP_MARKERS = (
    "以上内容对您是否有帮助？",
    "华为开发者联盟 版权所有",
    "在 服务分发 中进行搜索",
)
IFENG_DISCLAIMER_MARKERS = (
    "特别声明：以上作品内容",
    "Notice: The content above",
)
SOUTHCN_FOOTER_MARKERS = (
    "南方报业传媒集团简介 -",
    "本网站由南方新闻网版权所有",
)
NYT_CN_NOISE_EXACT = {
    "国际",
    "中国",
    "商业与经济",
    "镜头",
    "科技",
    "科学",
    "健康",
    "教育",
    "文化",
    "风尚",
    "旅游",
    "房地产",
    "观点与评论",
    "简繁中文",
    "简体 繁体",
    "字体大小",
    "小",
    "中",
    "大",
    "超大",
    "美国",
    "中文 中",
    "中英双语 双语",
    "英文 英",
    "广告",
    "ENGLISH (英语)",
    "ESPAÑOL (西班牙语)",
    "观点与评论 专栏作者",
    "免费下载 纽约时报中文网 iOS 和 Android App",
}
NYT_CN_NOISE_PREFIXES = (
    "纽约时报 出版语言",
)


class ExtractionError(RuntimeError):
    pass


class _MatchedClassHTMLTextExtractor(HTMLParser):
    def __init__(self, *, include_class_fragments: tuple[str, ...], exclude_tags: tuple[str, ...] = ()) -> None:
        super().__init__(convert_charrefs=True)
        self.include_class_fragments = include_class_fragments
        self.exclude_tags = set(exclude_tags)
        self.stack: list[tuple[str, str]] = []
        self.capture_depth = 0
        self.skip_depth = 0
        self.current_parts: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        class_name = dict(attrs).get("class") or ""
        self.stack.append((tag, class_name))
        if self.capture_depth == 0 and any(fragment in class_name for fragment in self.include_class_fragments):
            self.capture_depth = len(self.stack)
        if not self.capture_depth:
            return
        if tag in self.exclude_tags and self.skip_depth == 0:
            self.skip_depth = len(self.stack)
            return
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "br"} and self.skip_depth == 0:
            self.current_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        stack_depth = len(self.stack)
        if self.skip_depth == stack_depth:
            self.skip_depth = 0
        if self.capture_depth == stack_depth:
            text = clean_text("".join(self.current_parts))
            if text:
                self.blocks.append(text)
            self.capture_depth = 0
            self.current_parts = []
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.capture_depth and self.skip_depth == 0:
            self.current_parts.append(data)


def _request_json(url: str, *, headers: dict[str, str] | None = None, timeout: int = 20) -> dict[str, object]:
    request_headers = {
        "User-Agent": DEFAULT_REQUEST_HEADERS["User-Agent"],
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": DEFAULT_REQUEST_HEADERS["Accept-Language"],
    }
    if headers:
        request_headers.update(headers)
    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        payload = response.read().decode(charset, errors="replace")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"接口返回了无效 JSON：{truncate(payload, 200)}") from exc


def fetch_html(url: str, timeout: int = 20) -> str:
    fallback_html = None
    last_error: Exception | None = None
    for headers in _request_profiles_for_url(url):
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                html = response.read().decode(charset, errors="replace")
        except Exception as exc:
            last_error = exc
            continue
        if not html or not html.strip():
            continue
        text = _extract_main_text(html)
        if not _looks_like_access_gate(html, text):
            return html
        fallback_html = html
    if fallback_html is not None:
        return fallback_html
    if last_error is not None:
        raise last_error
    return ""


def _request_profiles_for_url(url: str) -> list[dict[str, str]]:
    if _is_wechat_url(url):
        return [dict(headers) for headers in WECHAT_REQUEST_PROFILES]
    return [dict(DEFAULT_REQUEST_HEADERS)]


def _is_wechat_url(url: str) -> bool:
    return domain_from_url(url) == "mp.weixin.qq.com"


def _is_biji_share_note_url(url: str) -> bool:
    return domain_from_url(url).endswith("biji.com") and "/note/share_note/" in url


def _is_zhihu_answer_url(url: str) -> bool:
    return domain_from_url(url).endswith("zhihu.com") and "/answer/" in url


def _is_xiaohongshu_url(url: str) -> bool:
    return domain_from_url(url) == "www.xiaohongshu.com" and "/discovery/item/" in url


def _is_wenxiaobai_share_url(url: str) -> bool:
    return domain_from_url(url) == "www.wenxiaobai.com" and "/share/chat/" in url


def _extract_biji_share_id(url: str) -> str:
    match = BIJI_SHARE_PATH_RE.search(urlparse(url).path)
    if not match:
        raise ExtractionError("未识别到 Get笔记分享 ID")
    return match.group(1)


def _extract_zhihu_answer_id(url: str) -> str:
    match = ZHIHU_ANSWER_ID_RE.search(urlparse(url).path)
    if not match:
        raise ExtractionError("未识别到知乎回答 ID")
    return match.group(1)


def _markdown_to_text(markdown: str) -> str:
    paragraphs: list[str] = []
    current: list[str] = []
    in_code_block = False
    for raw_line in str(markdown or "").splitlines():
        stripped = raw_line.strip()
        if re.fullmatch(r"\[\d+\]:\s*https?://\S+", stripped):
            continue
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if in_code_block:
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [clean_text(cell) for cell in stripped.strip("|").split("|")]
            cells = [cell for cell in cells if cell and set(cell) != {"-"}]
            if cells:
                current.append("；".join(cells))
            continue
        cleaned = _strip_markdown_line(raw_line)
        if not cleaned:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        cleaned = re.sub(r"\[([^\]]+)\]\[\d+\]", r"\1", cleaned)
        cleaned = re.sub(r"\(\[([^\]]+)\]\[\d+\]\)", r"\1", cleaned)
        current.append(cleaned)
    if current:
        paragraphs.append(" ".join(current))
    return clean_text("\n\n".join(paragraphs))


def _extract_wenxiaobai_text(html: str) -> str:
    parser = _MatchedClassHTMLTextExtractor(
        include_class_fragments=("markdown-body",),
        exclude_tags=("pre", "code", "script", "style", "svg"),
    )
    parser.feed(html)
    blocks = []
    for block in parser.blocks:
        cleaned = clean_text(block)
        if not cleaned:
            continue
        if "已深度思考" in cleaned:
            continue
        if cleaned in {"图表", "代码", "下载"}:
            continue
        blocks.append(cleaned)
    if not blocks:
        return ""
    return clean_text(max(blocks, key=len))


def _parse_xiaohongshu_state(html: str) -> dict[str, object]:
    match = XIAOHONGSHU_STATE_RE.search(html)
    if not match:
        raise ExtractionError("小红书页面未找到可解析的初始数据")
    raw = match.group(1).replace(":undefined", ":null").replace("=undefined", "=null")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionError("小红书页面初始数据不是合法 JSON") from exc


def _extract_xiaohongshu_payload(html: str) -> dict[str, object]:
    state = _parse_xiaohongshu_state(html)
    note_root = state.get("note") if isinstance(state, dict) else None
    if not isinstance(note_root, dict):
        raise ExtractionError("小红书页面缺少笔记数据")
    first_note_id = str(note_root.get("firstNoteId") or note_root.get("currentNoteId") or "").strip()
    detail_map = note_root.get("noteDetailMap")
    if not first_note_id or not isinstance(detail_map, dict):
        raise ExtractionError("小红书页面缺少笔记详情映射")
    note_detail = detail_map.get(first_note_id)
    if not isinstance(note_detail, dict):
        raise ExtractionError("小红书页面未返回目标笔记详情")
    note = note_detail.get("note")
    if not isinstance(note, dict):
        raise ExtractionError("小红书页面未返回目标笔记正文元数据")
    user = note.get("user") if isinstance(note.get("user"), dict) else {}
    title = clean_text(str(note.get("title") or "未命名文章"))
    desc = clean_text(str(note.get("desc") or ""))
    tag_list = note.get("tagList") if isinstance(note.get("tagList"), list) else []
    tags = [clean_text(str(item.get("name") or "")) for item in tag_list if isinstance(item, dict)]
    meaningful_desc = XIAOHONGSHU_TOPIC_TAG_RE.sub(" ", desc)
    meaningful_desc = clean_text(meaningful_desc)
    return {
        "title": title,
        "author": clean_text(str(user.get("nickname") or "")) or None,
        "published_at": datetime.fromtimestamp(
            int(note.get("time") or 0) / 1000,
            CHINA_TZ,
        ).isoformat()
        if note.get("time")
        else None,
        "text": clean_text("\n\n".join(part for part in [title, meaningful_desc, "、".join(tags)] if part)),
        "meaningful_desc": meaningful_desc,
        "tags": tags,
    }


def _invalid_content_reason(url: str, *, title: str, text: str) -> str:
    domain = domain_from_url(url)
    patterns = PLACEHOLDER_TEXT_PATTERNS.get(domain)
    if not patterns:
        return ""
    markers, reason = patterns
    hits = sum(1 for marker in markers if marker in text or marker in title)
    if domain == "www.xiaohongshu.com":
        return reason if hits >= 3 and word_count(text) < 260 else ""
    if domain in {"tanbi.baidu.com", "wenku.baidu.com"}:
        return reason if hits >= 1 else ""
    if domain == "cn.nytimes.com":
        return reason if hits >= 2 and word_count(text) < 260 else ""
    if domain == "chatgpt.com":
        return reason if hits >= 1 else ""
    return reason if hits >= 1 and word_count(text) < 160 else ""


def _search_first(patterns: list[str], html: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return clean_text(strip_html(match.group(1)))
    return None


def _extract_main_text(html: str) -> str:
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL)
    cleaned_paragraphs = [clean_text(strip_html(chunk)) for chunk in paragraphs]
    cleaned_paragraphs = [chunk for chunk in cleaned_paragraphs if len(chunk) >= 40]
    if cleaned_paragraphs:
        return "\n\n".join(cleaned_paragraphs)
    article_match = re.search(r"<article[^>]*>(.*?)</article>", html, flags=re.IGNORECASE | re.DOTALL)
    if article_match:
        return clean_text(strip_html(article_match.group(1)))
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, flags=re.IGNORECASE | re.DOTALL)
    if body_match:
        return clean_text(strip_html(body_match.group(1)))
    return clean_text(strip_html(html))


def _looks_like_access_gate(html: str, text: str) -> bool:
    normalized_html = clean_text(strip_html(html)).lower()
    normalized_text = clean_text(text).lower()
    combined = f"{normalized_html}\n{normalized_text}"
    if any(phrase.lower() in combined for phrase in ACCESS_GATE_HARD_PHRASES):
        return True
    preview_hits = sum(1 for phrase in ACCESS_GATE_PREVIEW_PHRASES if phrase.lower() in combined)
    weak_hits = sum(1 for phrase in ACCESS_GATE_WEAK_PHRASES if phrase.lower() in combined)
    text_words = word_count(normalized_text)
    if preview_hits >= 2 and text_words < 200:
        return True
    return weak_hits >= 2 and text_words < 120


def _extract_published_at(url: str, html: str) -> str | None:
    published_at = _search_first(PUBLISHED_PATTERNS, html)
    if published_at:
        return published_at
    if _is_wechat_url(url):
        display_time = _search_first(WECHAT_PUBLISHED_AT_PATTERNS, html)
        epoch = _search_first(WECHAT_EPOCH_PATTERNS, html)
        if epoch and epoch.isdigit():
            return datetime.fromtimestamp(int(epoch), CHINA_TZ).isoformat()
        if display_time:
            for pattern in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(display_time, pattern)
                    return parsed.replace(tzinfo=CHINA_TZ).isoformat()
                except ValueError:
                    continue
            return display_time
    return None


def _extract_source(url: str, html: str) -> str:
    if domain_from_url(url).endswith("wikipedia.org"):
        return "Wikipedia"
    if _is_wechat_url(url):
        return first_non_empty((_search_first(WECHAT_SOURCE_PATTERNS, html),), "微信公众平台")
    return first_non_empty((_search_first(SOURCE_PATTERNS, html), domain_from_url(url)), "未知来源")


def _sanitize_author(url: str, author: str | None, source: str) -> str | None:
    if not author:
        return None
    candidate = clean_text(author)
    if not candidate:
        return None
    if _is_wechat_url(url):
        if any(marker in candidate for marker in ("点这里关注", "点击关注", "关注→")):
            return None
        if candidate == source:
            return None
    return candidate


def _detect_language(text: str) -> str:
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh"
    if re.search(r"[A-Za-zÀ-ÿ]", text):
        return "en"
    return "unknown"


def _dedupe_preserve_order(lines: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if not line or line in seen:
            continue
        seen.add(line)
        result.append(line)
    return result


def _clean_huawei_developer_text(url: str, text: str) -> str:
    raw_lines = [clean_text(line) for line in str(text or "").splitlines()]
    lines = [line for line in raw_lines if line]

    if "/doc/" in url:
        start_index = 0
        for index, line in enumerate(lines):
            if any(marker in line for marker in HUAWEI_DOC_START_MARKERS):
                start_index = index
                break
        cleaned_lines: list[str] = []
        for line in lines[start_index:]:
            if any(marker in line for marker in HUAWEI_DOC_STOP_MARKERS):
                break
            if line in HUAWEI_NOISE_EXACT or any(line.startswith(prefix) for prefix in HUAWEI_NOISE_PREFIXES):
                continue
            if re.fullmatch(r"https?://\S+", line):
                continue
            cleaned_lines.append(line)
        return clean_text("\n\n".join(_dedupe_preserve_order(cleaned_lines)))

    if "/forum/topic/" in url:
        cleaned_lines: list[str] = []
        seen_title = False
        for line in lines:
            if re.match(r"^\d+楼 回复于", line):
                break
            if line in HUAWEI_NOISE_EXACT or any(line.startswith(prefix) for prefix in HUAWEI_NOISE_PREFIXES):
                continue
            if re.fullmatch(r"\d+", line):
                continue
            if re.fullmatch(r"https?://\S+", line):
                continue
            if not seen_title and "OpenClaw" in line and len(line) <= 40:
                seen_title = True
                cleaned_lines.append(line)
                continue
            cleaned_lines.append(line)
        return clean_text("\n\n".join(_dedupe_preserve_order(cleaned_lines)))

    return clean_text(text)


def _clean_domain_specific_text(url: str, text: str) -> str:
    domain = domain_from_url(url)
    cleaned = clean_text(text)
    if domain == "developer.huawei.com":
        cleaned = _clean_huawei_developer_text(url, cleaned)
    elif domain == "cn.nytimes.com":
        lines = [clean_text(line) for line in cleaned.splitlines() if clean_text(line)]
        start_index = 0
        for index, line in enumerate(lines):
            if "纽约时报中文网" not in line:
                continue
            title = clean_text(re.split(r"\s*-\s*纽约时报中文网", line, maxsplit=1)[0])
            if not title:
                continue
            for follow_index in range(index + 1, min(index + 40, len(lines))):
                if lines[follow_index] == title:
                    start_index = follow_index
                    break
            if start_index:
                break
        filtered: list[str] = []
        for line in lines[start_index:]:
            if line in NYT_CN_NOISE_EXACT or any(line.startswith(prefix) for prefix in NYT_CN_NOISE_PREFIXES):
                continue
            filtered.append(line)
        cleaned = clean_text("\n\n".join(_dedupe_preserve_order(filtered)))
    elif domain == "news.ifeng.com":
        paragraphs = [
            paragraph
            for paragraph in re.split(r"\n{2,}", cleaned)
            if paragraph and not any(marker in paragraph for marker in IFENG_DISCLAIMER_MARKERS)
        ]
        cleaned = clean_text("\n\n".join(paragraphs))
    elif domain == "news.southcn.com":
        for marker in SOUTHCN_FOOTER_MARKERS:
            if marker in cleaned:
                cleaned = cleaned.split(marker, 1)[0].strip()
                break
    return cleaned


def _normalize_extracted_text(url: str, text: str) -> str:
    cleaned = clean_text(text)
    cleaned = re.sub(r"\s+([,.;:!?%)\]])", r"\1", cleaned)
    cleaned = re.sub(r"([(\[])\s+", r"\1", cleaned)
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)
    if domain_from_url(url).endswith("wikipedia.org"):
        cleaned = WIKIPEDIA_CITATION_RE.sub("", cleaned)
        cleaned = re.sub(r"\[\s*\]", "", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = clean_text(cleaned)
    cleaned = _clean_domain_specific_text(url, cleaned)
    return cleaned


def _write_extracted_text(
    article: ExtractedArticle,
    *,
    raw_html_dir: Path | None,
    extracted_text_dir: Path | None,
    html: str | None = None,
) -> ExtractedArticle:
    article_hash = url_hash(article.url)
    raw_html_path = article.raw_html_path
    extracted_text_path = article.extracted_text_path
    if raw_html_dir is not None and html is not None:
        file_name = f"{slugify(article.title)}-{article_hash[:12]}.html"
        target = raw_html_dir / file_name
        target.write_text(html, encoding="utf-8")
        raw_html_path = str(target)
    if extracted_text_dir is not None:
        file_name = f"{slugify(article.title)}-{article_hash[:12]}.txt"
        target = extracted_text_dir / file_name
        target.write_text(article.text, encoding="utf-8")
        extracted_text_path = str(target)
    return ExtractedArticle(
        url=article.url,
        title=article.title,
        source=article.source,
        author=article.author,
        published_at=article.published_at,
        language=article.language,
        text=article.text,
        word_count=article.word_count,
        fetched_at=article.fetched_at,
        raw_html_path=raw_html_path,
        extracted_text_path=extracted_text_path,
        metadata=dict(article.metadata or {}),
    )


def _build_biji_share_note_article(
    url: str,
    *,
    raw_html_dir: Path | None,
    extracted_text_dir: Path | None,
    timeout: int = 20,
) -> ExtractedArticle:
    share_id = _extract_biji_share_id(url)
    detail_payload = _request_json(
        f"{BIJI_SHARE_API_BASE}/voicenotes/web/share/notes/{share_id}",
        timeout=timeout,
    )
    note_container = detail_payload.get("c")
    if not isinstance(note_container, dict):
        raise ExtractionError("Get笔记分享接口未返回正文数据")
    note = note_container.get("note")
    if not isinstance(note, dict):
        raise ExtractionError("Get笔记分享接口未返回主笔记数据")
    author_info = note_container.get("author") if isinstance(note_container.get("author"), dict) else {}

    children_payload = _request_json(
        f"{BIJI_SHARE_API_BASE}/voicenotes/web/share/notes/{share_id}/children?limit=20&since_id=&sort=create_asc",
        timeout=timeout,
    )
    children_container = children_payload.get("c")
    children = children_container.get("list") if isinstance(children_container, dict) else []
    children = children if isinstance(children, list) else []

    def _note_text(item: dict[str, object]) -> str:
        content = _markdown_to_text(str(item.get("content") or ""))
        if content:
            return content
        return clean_text(strip_html(str(item.get("body_text") or "")))

    main_text = _note_text(note)
    if not main_text:
        raise ExtractionError("Get笔记分享接口返回了空正文")

    sectioned_notes: list[dict[str, str]] = [
        {
            "kind": "main",
            "title": clean_text(str(note.get("title") or "主笔记")) or "主笔记",
            "text": main_text,
        }
    ]
    full_parts = [main_text]
    for index, child in enumerate(children, start=1):
        if not isinstance(child, dict):
            continue
        child_text = _note_text(child)
        if not child_text:
            continue
        child_title = clean_text(str(child.get("title") or f"附加笔记{index}")) or f"附加笔记{index}"
        sectioned_notes.append({"kind": "append", "title": child_title, "text": child_text})
        full_parts.append(f"附加笔记 {index}：{child_title}\n{child_text}")

    title = clean_text(str(note.get("title") or "未命名文章")) or "未命名文章"
    extracted = ExtractedArticle(
        url=url,
        title=truncate(title, 180),
        source="Get笔记",
        author=truncate(clean_text(str(author_info.get("nickname") or "")), 120) or None,
        published_at=clean_text(str(note.get("created_at") or "")) or None,
        language="zh",
        text=clean_text("\n\n".join(full_parts)),
        word_count=word_count(clean_text("\n\n".join(full_parts))),
        fetched_at=utc_now_iso(),
        metadata={
            "provider": "biji-share-note",
            "sectioned_notes": sectioned_notes,
            "append_note_count": max(0, len(sectioned_notes) - 1),
        },
    )
    extracted = _write_extracted_text(
        extracted,
        raw_html_dir=raw_html_dir,
        extracted_text_dir=extracted_text_dir,
    )
    if extracted.word_count < 20:
        raise ExtractionError("Get笔记分享正文过短，疑似抓取失败")
    return extracted


def _build_zhihu_answer_article(
    url: str,
    *,
    raw_html_dir: Path | None,
    extracted_text_dir: Path | None,
    timeout: int = 20,
) -> ExtractedArticle:
    answer_id = _extract_zhihu_answer_id(url)
    payload = _request_json(
        f"{ZHIHU_ANSWER_API_BASE}/{answer_id}?include=content,excerpt,question,author,created_time,updated_time",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
        },
        timeout=timeout,
    )
    question = payload.get("question") if isinstance(payload.get("question"), dict) else {}
    author = payload.get("author") if isinstance(payload.get("author"), dict) else {}
    html_content = str(payload.get("content") or "")
    text = clean_text(strip_html(html_content))
    title = clean_text(str(question.get("title") or payload.get("excerpt") or "未命名文章")) or "未命名文章"
    invalid_reason = _invalid_content_reason(url, title=title, text=text)
    if invalid_reason:
        raise ExtractionError(invalid_reason)
    created_time = payload.get("created_time")
    published_at = (
        datetime.fromtimestamp(int(created_time), CHINA_TZ).isoformat()
        if isinstance(created_time, (int, float))
        else None
    )
    extracted = ExtractedArticle(
        url=url,
        title=truncate(title, 180),
        source="知乎",
        author=truncate(clean_text(str(author.get("name") or "")), 120) or None,
        published_at=published_at,
        language=_detect_language(f"{title}\n{text}"),
        text=text,
        word_count=word_count(text),
        fetched_at=utc_now_iso(),
        metadata={"provider": "zhihu-answer-api", "answer_id": answer_id},
    )
    extracted = _write_extracted_text(
        extracted,
        raw_html_dir=raw_html_dir,
        extracted_text_dir=extracted_text_dir,
    )
    if extracted.word_count < 20:
        raise ExtractionError("知乎回答正文过短，疑似抓取失败")
    return extracted


def _build_article_from_html(
    url: str,
    html: str,
    *,
    raw_html_dir: Path | None,
    extracted_text_dir: Path | None,
) -> ExtractedArticle:
    if _is_xiaohongshu_url(url):
        payload = _extract_xiaohongshu_payload(html)
        if len(str(payload.get("meaningful_desc") or "")) < 20:
            raise ExtractionError("小红书页面只返回了标题和话题标签，未拿到可总结的正文文字")
        text = _normalize_extracted_text(url, str(payload.get("text") or ""))
        title = str(payload.get("title") or "未命名文章")
        source = "小红书"
        author = payload.get("author")
        published_at = payload.get("published_at")
        language = "zh"
    else:
        extracted_main_text = _extract_wenxiaobai_text(html) if _is_wenxiaobai_share_url(url) else _extract_main_text(html)
        text = _normalize_extracted_text(url, extracted_main_text)
        if domain_from_url(url) == "cn.nytimes.com":
            full_page_text = _normalize_extracted_text(url, strip_html(html))
            if word_count(full_page_text) > word_count(text):
                text = full_page_text
        if "/forum/topic/" in url and word_count(text) < 20:
            # 华为论坛正文经常被帖子日志块切碎；主提取过短时退回整页文本后再做站点清洗。
            text = _normalize_extracted_text(url, strip_html(html))
        title = first_non_empty((_search_first(TITLE_PATTERNS, html),), "未命名文章")
        if domain_from_url(url).endswith("wikipedia.org"):
            title = WIKIPEDIA_TITLE_SUFFIX_RE.sub("", title).strip()
        source = _extract_source(url, html)
        author = _sanitize_author(url, _search_first(AUTHOR_PATTERNS, html), source)
        published_at = _extract_published_at(url, html)
        language_match = re.search(LANG_PATTERN, html, flags=re.IGNORECASE)
        language = (language_match.group(1) if language_match else "unknown").split("-", 1)[0].lower()
    invalid_reason = _invalid_content_reason(url, title=title, text=text or clean_text(strip_html(html)))
    if not text:
        if invalid_reason:
            raise ExtractionError(invalid_reason)
        raise ExtractionError("无法从页面中提取正文")
    if _looks_like_access_gate(html, text):
        raise ExtractionError("页面返回访问验证或异常环境页面，未获取到文章正文")
    if invalid_reason:
        raise ExtractionError(invalid_reason)
    fetched_at = utc_now_iso()
    extracted = ExtractedArticle(
        url=url,
        title=truncate(title, 180),
        source=source,
        author=truncate(author, 120) if author else None,
        published_at=published_at,
        language=language or "unknown",
        text=text,
        word_count=word_count(text),
        fetched_at=fetched_at,
    )
    extracted = _write_extracted_text(
        extracted,
        raw_html_dir=raw_html_dir,
        extracted_text_dir=extracted_text_dir,
        html=html,
    )
    if extracted.word_count < 20:
        raise ExtractionError("提取到的正文过短，疑似抓取失败")
    return extracted


def _reader_url(url: str) -> str:
    return f"{READER_URL_PREFIX}{url}"


def _search_reader_header(name: str, text: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return None
    return clean_text(match.group(1))


def _strip_markdown_line(text: str) -> str:
    value = re.sub(r"^#{1,6}\s*", "", text)
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = value.replace("**", "").replace("__", "")
    value = re.sub(r"^[-*+]\s+", "", value)
    value = re.sub(r"^\d+\.\s+", "", value)
    return clean_text(value)


def _should_stop_reader_text(line: str, url: str) -> bool:
    if not line:
        return False
    stop_markers = READER_GENERIC_STOP_MARKERS + READER_DOMAIN_STOP_MARKERS.get(domain_from_url(url), ())
    lowered = line.lower()
    return any(marker.lower() in lowered for marker in stop_markers)


def _should_skip_reader_line(cleaned: str, raw_line: str) -> bool:
    if not cleaned:
        return True
    if raw_line.count("](") >= 2:
        return True
    if cleaned in READER_SKIP_EXACT:
        return True
    if any(cleaned.startswith(prefix) for prefix in READER_SKIP_PREFIXES):
        return True
    if cleaned.startswith("首页") and ">" in cleaned:
        return True
    if "浏览时间" in cleaned:
        return True
    if re.fullmatch(r"[A-Za-z]{1,4}", cleaned):
        return True
    if len(cleaned) <= 8 and not re.search(r"[。！？!?；;：:，,0-9]", cleaned):
        return True
    if "REUTERS -" in cleaned and re.match(r"^\d{4}年", cleaned):
        return True
    return False


def _extract_reader_text(markdown: str, *, title: str, url: str) -> str:
    raw_lines = markdown.splitlines()
    title_norm = clean_text(title).casefold()
    start_index = 0
    for index, raw_line in enumerate(raw_lines):
        cleaned = _strip_markdown_line(raw_line)
        if cleaned and cleaned.casefold() == title_norm:
            start_index = index + 1
    paragraphs: list[str] = []
    current: list[str] = []
    for raw_line in raw_lines[start_index:]:
        cleaned = _strip_markdown_line(raw_line)
        if _should_stop_reader_text(cleaned, url):
            break
        if _should_skip_reader_line(cleaned, raw_line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(cleaned)
    if current:
        paragraphs.append(" ".join(current))
    return clean_text("\n\n".join(paragraphs))


def _build_article_from_reader(
    url: str,
    *,
    raw_html_dir: Path | None,
    extracted_text_dir: Path | None,
    timeout: int = 20,
) -> ExtractedArticle:
    request = Request(_reader_url(url), headers=DEFAULT_REQUEST_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        reader_text = response.read().decode(charset, errors="replace")
    if not reader_text.strip():
        raise ExtractionError("Reader 兜底返回空内容")
    _, _, markdown = reader_text.partition(READER_MARKDOWN_PREFIX)
    markdown = markdown.lstrip()
    title = first_non_empty(
        (
            _search_reader_header("Title", reader_text),
            _search_reader_header("Page Title", reader_text),
        ),
        "未命名文章",
    )
    text = _normalize_extracted_text(url, _extract_reader_text(markdown or reader_text, title=title, url=url))
    if not text:
        raise ExtractionError("Reader 兜底未提取到正文")
    published_at = _search_reader_header("Published Time", reader_text)
    if domain_from_url(url).endswith("wikipedia.org"):
        title = WIKIPEDIA_TITLE_SUFFIX_RE.sub("", title).strip()
    invalid_reason = _invalid_content_reason(url, title=title, text=text)
    if invalid_reason:
        raise ExtractionError(invalid_reason)
    extracted = ExtractedArticle(
        url=url,
        title=truncate(title, 180),
        source="Wikipedia" if domain_from_url(url).endswith("wikipedia.org") else domain_from_url(url) or "未知来源",
        author=None,
        published_at=published_at,
        language=_detect_language(f"{title}\n{text}"),
        text=text,
        word_count=word_count(text),
        fetched_at=utc_now_iso(),
    )
    extracted = _write_extracted_text(
        extracted,
        raw_html_dir=raw_html_dir,
        extracted_text_dir=extracted_text_dir,
    )
    if extracted.word_count < 20:
        raise ExtractionError("Reader 兜底提取到的正文过短")
    return extracted


def extract_article(
    url: str,
    *,
    raw_html_dir: Path | None = None,
    extracted_text_dir: Path | None = None,
    fetcher: Callable[[str], str] | None = None,
) -> ExtractedArticle:
    normalized = normalize_url(url)
    errors: list[str] = []
    if fetcher is None:
        if _is_biji_share_note_url(normalized):
            try:
                return _build_biji_share_note_article(
                    normalized,
                    raw_html_dir=raw_html_dir,
                    extracted_text_dir=extracted_text_dir,
                )
            except Exception as exc:
                errors.append(str(exc))
        if _is_zhihu_answer_url(normalized):
            try:
                return _build_zhihu_answer_article(
                    normalized,
                    raw_html_dir=raw_html_dir,
                    extracted_text_dir=extracted_text_dir,
                )
            except Exception as exc:
                errors.append(str(exc))
    try:
        html = (fetcher or fetch_html)(normalized)
    except Exception as exc:
        errors.append(str(exc))
        html = ""
    if html and html.strip():
        try:
            return _build_article_from_html(
                normalized,
                html,
                raw_html_dir=raw_html_dir,
                extracted_text_dir=extracted_text_dir,
            )
        except Exception as exc:
            errors.append(str(exc))
    else:
        errors.append("页面返回空内容")
    if fetcher is not None:
        raise ExtractionError("；".join(dict.fromkeys(errors)))
    try:
        return _build_article_from_reader(
            normalized,
            raw_html_dir=raw_html_dir,
            extracted_text_dir=extracted_text_dir,
        )
    except Exception as exc:
        errors.append(str(exc))
    raise ExtractionError("；".join(dict.fromkeys(errors)))

from __future__ import annotations

from email.message import Message

import app.extraction as extraction
from app.db import connect_db, init_db
from app.extraction import extract_article
from app.pipeline import ingest_url


def test_extract_failure_marks_status(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    def failing_fetcher(_: str) -> str:
        raise RuntimeError("network timeout")

    result = ingest_url("https://example.com/fail", conn=conn, fetcher=failing_fetcher)
    row = conn.execute("SELECT status, error_message FROM articles LIMIT 1").fetchone()
    assert result["status"] == "extract_failed"
    assert row["status"] == "extract_failed"
    assert "timeout" in row["error_message"]


def test_access_gate_page_marks_extract_failed(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    gate_html = """
    <html>
      <head><title>环境异常</title></head>
      <body>
        <p>环境异常</p>
        <p>当前环境异常，完成验证后即可继续访问。</p>
        <p>去验证</p>
      </body>
    </html>
    """

    result = ingest_url("https://mp.weixin.qq.com/s/example", conn=conn, fetcher=lambda _: gate_html)
    row = conn.execute("SELECT status, error_message FROM articles LIMIT 1").fetchone()
    assert result["status"] == "extract_failed"
    assert row["status"] == "extract_failed"
    assert "访问验证" in row["error_message"]


def test_wechat_preview_shell_marks_extract_failed(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    shell_html = """
    <html>
      <body>
        <p>轻触查看原文</p>
        <p>向上滑动看下一个</p>
        <p>微信扫一扫可打开此内容，使用完整服务</p>
      </body>
    </html>
    """

    result = ingest_url("https://mp.weixin.qq.com/s/preview", conn=conn, fetcher=lambda _: shell_html)
    row = conn.execute("SELECT status, error_message FROM articles LIMIT 1").fetchone()
    assert result["status"] == "extract_failed"
    assert row["status"] == "extract_failed"
    assert "访问验证" in row["error_message"]


def test_extract_failure_sends_status_notice_when_delivery_enabled(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"ARTICLE_DIGEST_DB={tmp_path / 'article_digest.db'}",
                "SEND_MODE=telegram",
                "TELEGRAM_BOT_TOKEN=test-token",
                "TELEGRAM_CHAT_ID=chat-1",
            ]
        ),
        encoding="utf-8",
    )
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    sent_texts: list[str] = []

    def failing_fetcher(_: str) -> str:
        raise RuntimeError("network timeout")

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        sent_texts.append(text)
        return {"ok": True, "result": {"message_id": 101}}

    result = ingest_url(
        "https://example.com/fail-notice",
        conn=conn,
        fetcher=failing_fetcher,
        env_file=env_file,
        telegram_sender=fake_telegram_sender,
    )

    assert result["status"] == "extract_failed"
    assert result["status_notice_sent"] is True
    assert sent_texts
    assert "【文章处理异常】" in sent_texts[0]
    assert "正文抓取失败" in sent_texts[0]
    assert "网络请求超时" in sent_texts[0]


def test_wechat_mobile_profile_fallback_extracts_article(monkeypatch):
    gate_html = """
    <html>
      <head><title>环境异常</title></head>
      <body>
        <p>环境异常</p>
        <p>当前环境异常，完成验证后即可继续访问。</p>
        <p>去验证</p>
      </body>
    </html>
    """
    wechat_html = """
    <html lang="zh-CN">
      <head>
        <meta property="og:site_name" content="微信公众平台" />
      </head>
      <body>
        <h1 class="rich_media_title" id="activity-name">两会之后的2026，我们的钱要从哪里来？</h1>
        <span id="js_author_name_text">点这里关注→</span>
        <a id="js_name">刘润</a>
        <div id="js_content">
          <p>关于两会的重要性，我就不再强调了。两会期间，很多媒体，都做了说明和解析。我们也用一篇文章，分享了一点我们的看法。</p>
          <p>香帅老师，是我特别敬佩的一位老师。她是著名的经济学者，《香帅的北大金融学课》主理人。</p>
        </div>
        <script>
          var ct = "1774063100";
          var createTime = "2026-03-21 11:18";
          var nickname = htmlDecode("刘润");
          var msg_title = '两会之后的2026，我们的钱要从哪里来？'.html(false);
        </script>
      </body>
    </html>
    """

    class FakeResponse:
        def __init__(self, body: str):
            self._body = body.encode("utf-8")
            self.headers = Message()
            self.headers["Content-Type"] = "text/html; charset=utf-8"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return self._body

    def fake_urlopen(request, timeout=20):
        headers = dict(request.header_items())
        if headers.get("Referer") == "https://mp.weixin.qq.com/" and "Chrome/122.0.0.0" in headers.get("User-agent", ""):
            return FakeResponse(wechat_html)
        if "MicroMessenger" in headers.get("User-agent", ""):
            return FakeResponse(wechat_html)
        return FakeResponse(gate_html)

    monkeypatch.setattr(extraction, "urlopen", fake_urlopen)

    article = extract_article("https://mp.weixin.qq.com/s/example")
    assert article.title == "两会之后的2026，我们的钱要从哪里来？"
    assert article.source == "刘润"
    assert article.author is None
    assert article.published_at == "2026-03-21T11:18:20+08:00"
    assert "关于两会的重要性" in article.text


def test_reader_fallback_recovers_when_origin_is_blocked(monkeypatch):
    reader_text = """
Title: Those Ships Can Pass Through the Blocked Strait
Published Time: 2026-03-20T21:54:59+00:00
Markdown Content:

# Those Ships Can Pass Through the Blocked Strait

The article says shipping access through the Strait of Hormuz now depends on Iran's political stance and the flag of each vessel.

It also explains that energy transport, insurance pricing and regional security pressure are all being affected at the same time.

Other News
"""

    class FakeResponse:
        def __init__(self, body: str, content_type: str = "text/plain; charset=utf-8"):
            self._body = body.encode("utf-8")
            self.headers = Message()
            self.headers["Content-Type"] = content_type

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return self._body

    def fake_urlopen(request, timeout=20):
        if request.full_url.startswith("https://r.jina.ai/http://"):
            return FakeResponse(reader_text)
        raise RuntimeError("HTTP Error 403: Forbidden")

    monkeypatch.setattr(extraction, "urlopen", fake_urlopen)

    article = extract_article("https://www.rfi.fr/cn/test")
    assert article.title == "Those Ships Can Pass Through the Blocked Strait"
    assert article.published_at == "2026-03-20T21:54:59+00:00"
    assert "shipping access through the Strait of Hormuz" in article.text
    assert "Other News" not in article.text

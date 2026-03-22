from __future__ import annotations

import json
from email.message import Message

import pytest

import app.extraction as extraction
from app.extraction import ExtractionError, extract_article


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


def test_extract_article_prefers_biji_share_api(monkeypatch):
    detail_payload = {
        "c": {
            "author": {"nickname": "测试作者"},
            "note": {
                "title": "2026开发者混血模式指南",
                "created_at": "2026-02-21 23:55:52",
                "content": "# 主笔记\n\n主张在 12GB 显存条件下采用本地模型负责高频轻任务，云端模型负责复杂任务。",
            },
        }
    }
    children_payload = {
        "c": {
            "list": [
                {"title": "12G显存开发指南", "content": "# 附加一\n\n讲解如何分配补全和重构任务。"},
                {"title": "智能路由分流指南", "content": "# 附加二\n\n讲解如何先判断复杂度，再转给云端模型。"},
            ]
        }
    }

    def fake_urlopen(request, timeout=20):
        url = request.full_url
        if url.endswith("/voicenotes/web/share/notes/demo"):
            return FakeResponse(json.dumps(detail_payload, ensure_ascii=False), "application/json; charset=utf-8")
        if "/voicenotes/web/share/notes/demo/children" in url:
            return FakeResponse(json.dumps(children_payload, ensure_ascii=False), "application/json; charset=utf-8")
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(extraction, "urlopen", fake_urlopen)

    article = extract_article("https://www.biji.com/note/share_note/demo")

    assert article.title == "2026开发者混血模式指南"
    assert article.source == "Get笔记"
    assert article.author == "测试作者"
    assert article.metadata["provider"] == "biji-share-note"
    assert len(article.metadata["sectioned_notes"]) == 3
    assert "附加笔记 1：12G显存开发指南" in article.text


def test_extract_article_prefers_zhihu_answer_api(monkeypatch):
    payload = {
        "question": {"title": "冰心为什么讨厌林徽因？"},
        "author": {"name": "路路通"},
        "created_time": 1769019801,
        "content": "<p>回答先解释两人的关系背景。</p><p>随后讨论争议说法的来源与局限。</p>",
    }

    def fake_urlopen(request, timeout=20):
        url = request.full_url
        if url.startswith("https://www.zhihu.com/api/v4/answers/1997494503725101521"):
            return FakeResponse(json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(extraction, "urlopen", fake_urlopen)

    article = extract_article("https://www.zhihu.com/question/53101806/answer/1997494503725101521")

    assert article.title == "冰心为什么讨厌林徽因？"
    assert article.source == "知乎"
    assert article.author == "路路通"
    assert "关系背景" in article.text


def test_wenxiaobai_extraction_skips_deep_thought_and_mermaid():
    html = """
    <html>
      <body>
        <div class="OnlineThinkChatHeader_custom_markdown_body__2qfbm">
          <p>已深度思考（用时9秒）</p>
          <p>这里是推理草稿。</p>
        </div>
        <div class="markdown-body">
          <p>托福、雅思和 GRE 的核心区别在于用途不同。</p>
          <p>托福和雅思主要用于语言能力证明，GRE 更偏研究生入学能力测试。</p>
          <pre><code>flowchart TD\nA-->B</code></pre>
        </div>
      </body>
    </html>
    """

    article = extract_article(
        "https://www.wenxiaobai.com/share/chat/demo",
        fetcher=lambda _: html,
    )

    assert "已深度思考" not in article.text
    assert "flowchart TD" not in article.text
    assert "托福、雅思和 GRE 的核心区别在于用途不同" in article.text


def test_xiaohongshu_without_meaningful_desc_fails():
    state = {
        "note": {
            "firstNoteId": "note-1",
            "noteDetailMap": {
                "note-1": {
                    "note": {
                        "title": "用AI写材料的方法技巧，越用越顺手（1）",
                        "desc": "#写作干货[话题]# #笔杆子[话题]# #公文[话题]#",
                        "tagList": [{"name": "写作干货"}, {"name": "笔杆子"}],
                        "user": {"nickname": "攀山有路文为径"},
                        "time": 1774064739000,
                    }
                }
            },
        }
    }
    html = f"<html><body><script>window.__INITIAL_STATE__={json.dumps(state, ensure_ascii=False)}</script></body></html>"

    with pytest.raises(ExtractionError, match="未拿到可总结的正文文字"):
        extract_article(
            "https://www.xiaohongshu.com/discovery/item/demo",
            fetcher=lambda _: html,
        )


def test_tanbi_shell_page_is_rejected():
    html = """
    <!doctype html>
    <html lang="en">
      <head><title>百度文库</title></head>
      <body>
        <div id="app"></div>
        <script>
          window.pageData = {"title":"百度文库","docId":"f6a0a088f211f18583d049649b6648d7c1c70888"};
          window.__SYSTEM_TYPE = "android";
        </script>
        <script src="//wkstatic.bdimg.com/static/appwenku/static/h5diversionclient/views/wkJumpDownload.js"></script>
      </body>
    </html>
    """

    with pytest.raises(ExtractionError, match="下载/跳转壳页"):
        extract_article(
            "https://tanbi.baidu.com/h5apptopic/browse/wkjumpdownload?docId=f6a0a088f211f18583d049649b6648d7c1c70888",
            fetcher=lambda _: html,
        )


def test_chatgpt_login_shell_is_rejected():
    html = """
    <html>
      <head><title>聊天GPT</title></head>
      <body>
        <p>历史聊天记录</p>
        <p>新聊天</p>
        <p>登录 登录</p>
        <p>免费注册</p>
        <p>向 AI 聊天机器人 ChatGPT 发送消息即表示，你同意我们的条款。</p>
      </body>
    </html>
    """

    with pytest.raises(ExtractionError, match="登录页、首页或会话错误页"):
        extract_article(
            "https://chatgpt.com/c/69be4478-31c0-83a3-ae49-8795323411a7",
            fetcher=lambda _: html,
        )


def test_chatgpt_error_shell_is_rejected():
    html = """
    <html>
      <head><title>ChatGPT</title></head>
      <body>
        <p>Log in Log in</p>
        <p>Sign up for free</p>
        <p>Get step-by-step help</p>
        <p>Unable to load conversation 69be4478-31c0-83a3-ae49-8795323411a7</p>
      </body>
    </html>
    """

    with pytest.raises(ExtractionError, match="登录页、首页或会话错误页"):
        extract_article(
            "https://chatgpt.com/c/69be4478-31c0-83a3-ae49-8795323411a7",
            fetcher=lambda _: html,
        )


def test_nyt_cookie_shell_is_rejected():
    html = """
    <html>
      <head><title>特朗普不满以色列轰炸伊朗天然气田，美以分歧凸显</title></head>
      <body>
        <p>Cookie政策</p>
        <p>隐私政策</p>
        <p>通过在此处点击“我接受”或者“X”，您将被视为同意使用cookies。</p>
        <p>免费下载 纽约时报中文网 iOS 和 Android App</p>
      </body>
    </html>
    """

    with pytest.raises(ExtractionError, match="Cookie/导航页面"):
        extract_article(
            "https://cn.nytimes.com/usa/20260320/trump-netanyahu-iran-gas-field-attack/",
            fetcher=lambda _: html,
        )


def test_huawei_doc_cleanup_keeps_openclaw_steps():
    html = """
    <html>
      <body>
        <p>Hello，</p>
        <p>欢迎来到开发者联盟</p>
        <p>HarmonyOS 6</p>
        <p>animation</p>
        <p>OpenClaw基础配置</p>
        <p>更新时间: 2026-02-13 01:14</p>
        <p>【OpenClaw基础配置】 是专为OpenClaw模式智能体设计的核心配置。</p>
        <p>获取【小艺开放平台凭证】</p>
        <p>在OpenClaw服务器上【配置channel】</p>
        <p>以上内容对您是否有帮助？</p>
      </body>
    </html>
    """

    article = extract_article(
        "https://developer.huawei.com/consumer/cn/doc/service/open-claw-base-0000002518704040",
        fetcher=lambda _: html,
    )

    assert "欢迎来到开发者联盟" not in article.text
    assert "获取【小艺开放平台凭证】" in article.text
    assert "配置channel" in article.text


def test_huawei_forum_cleanup_keeps_issue_and_drops_replies():
    html = """
    <html>
      <body>
        <p>Hello，</p>
        <p>欢迎来到开发者联盟</p>
        <p>小艺智能体接入OpenClaw</p>
        <p>03:01:21 info [server1] WebSocket opened</p>
        <p>03:01:21 info [server1] WebSocket closed: 1000</p>
        <p>按照配置后，一直在尝试连接，断开又连接，不得已停了。</p>
        <p>4楼 回复于 2026-03-11 03:06 来自河北</p>
        <p>出一个搭建步骤吧大佬</p>
      </body>
    </html>
    """

    article = extract_article(
        "https://developer.huawei.com/consumer/cn/forum/topic/0208208462710973190?fid=0109140870620153026",
        fetcher=lambda _: html,
    )

    assert "WebSocket closed: 1000" in article.text
    assert "按照配置后，一直在尝试连接" in article.text
    assert "4楼 回复于" not in article.text

from __future__ import annotations

from app.analysis import assess_ai_likelihood, assess_credibility, summarize_threads
from app.utils import sentence_split


def test_summary_uses_whole_article_instead_of_first_paragraph_only():
    article = {
        "url": "https://example.com/full-summary",
        "title": "全文总结测试",
        "source": "测试来源",
        "author": "测试作者",
        "published_at": "2026-03-21T12:00:00+08:00",
        "language": "zh",
        "text": (
            "首先，作者从最近行业里的一次讨论开场，说明这篇文章会围绕模型服务调整继续展开。"
            "\n\n"
            "作者指出，平台准备在 2026 年第二季度把原本依赖广告补贴的模型服务改成会员制，并逐步关闭免费套餐。"
            "\n\n"
            "文中随后列出三组数据，解释成本压力、用户迁移速度和毛利率变化，说明这次调整并不是临时决定。"
            "\n\n"
            "最后文章讨论这一决定会怎样影响中小团队的接入预算、产品节奏和市场竞争。"
        ),
        "word_count": 220,
        "fetched_at": "2026-03-21T12:00:00+08:00",
    }

    result = summarize_threads(article)
    source_sentences = set(sentence_split(article["text"]))

    assert "这篇文章围绕《全文总结测试》展开" not in result["summary"]
    assert "会员制" in result["summary"] or "免费套餐" in result["summary"]
    assert "开场" not in result["summary"]
    assert len(result["main_threads"]) >= 2
    assert all(not item.startswith("主线") for item in result["main_threads"])
    assert any("预算" in item or "影响" in item for item in result["main_threads"])
    assert all(item not in result["summary"] for item in result["main_threads"][:2])
    assert all(item not in source_sentences for item in result["main_threads"][:2])
    assert any("：" in item for item in result["main_threads"][:2])


def test_credibility_reasons_hide_source_line_but_keep_external_check():
    article = {
        "url": "https://news.example.com/credibility",
        "title": "可信度测试",
        "source": "测试来源",
        "author": None,
        "published_at": "2026-03-21T12:00:00+08:00",
        "language": "zh",
        "text": (
            "文章列出 2026 年 3 月的多组公开数据，并引用两位受访者的原话，说明政策调整已经影响市场预期。"
            "\n\n"
            "文中还给出了多个时间锚点，方便外部搜索与交叉核验。"
        ),
        "word_count": 120,
        "fetched_at": "2026-03-21T12:00:00+08:00",
    }

    result = assess_credibility(article).to_dict()

    assert all("文章来源明确" not in item for item in result["reasons"])


def test_summary_filters_quote_fragments_and_threads_avoid_summary_repeat():
    article = {
        "url": "https://mp.weixin.qq.com/s/vTk1nmGzRpXXU5F9yJQEAw",
        "title": "零代码开发AI应用？这场分享会揭秘“养龙虾”的快乐！",
        "source": "萍云漫语",
        "author": None,
        "published_at": "2026-03-14T14:48:21+08:00",
        "language": "zh",
        "word_count": 1029,
        "fetched_at": "2026-03-21T12:00:00+08:00",
        "text": (
            "你是否想过，不懂编程也能开发自己的手机APP？你是否担心，AI虽然强大却充满安全风险？近日，笔者参加了一场一场别开生面的🦞使用体验分享会。"
            "主讲人以“养龙虾”为喻，用大白话讲透了人工智能的底层逻辑、本地部署的实操方法，以及如何让AI从“聊天”变成“干活”。"
            "现场干货满满，甚至有人当场立下flag：一定要亲手“养”一只属于自己的“龙虾”！"
            "\n\n"
            "“人类文明起源于语言，而编程语言、命令行都是语言的延伸。”主讲人一开场就抛出他的核心观点：自然语言、程序语言、命令行三者本质相通，而AI大模型正是打通它们的“超级翻译”。"
            " 不过，主讲人也表达了自己对现阶段AI的认识与感受，目前的AI本质是一个“大型概率模型”——它通过海量数据预测下一个最可能的字词，并不具备真正的逻辑思维和情感。"
            "理解这一点，才能既不神化AI，也不低估它的价值。"
            "\n\n"
            "什么是OpenClaw？主讲人用一句话概括：“原来是个聊天工具，现在能帮你干活了！” 他详细拆解了OpenClaw的工作流程：你说一句话，大模型（LLM）负责“听懂”你的意图，然后把任务拆解成计算机能执行的指令，调用工具完成操作，最后把结果反馈给你。"
            "整个过程就像你有了一个24小时在线的“数字员工”，你说需求，它执行，你验收。"
            "\n\n"
            "针对大家最关心的安全问题，主讲人毫不回避。他直言：“任何有用的工具都有风险，火能取暖也能烧屋，关键是如何控制风险。”"
            " 他把配置、磨合、熟悉OpenClaw的过程比作“养龙虾”——一开始你需要了解它的习性（权限控制），给它合适的工具（配置skills），让它熟悉你的数据和工作习惯。"
            "只要在安全的环境中操作，实现物理隔离，初学者完全可以零风险尝试。"
            "\n\n"
            "分享会的高潮来了！主讲人现场演示：只用一句话，让AI自动开发一个“贪吃蛇”安卓应用。AI不仅自动配置环境、编写代码，还能根据反馈不断迭代优化，全程无需人工写一行代码！"
            " 他强调，未来不需要人人都学编程，但人人都需要学会“提需求”和“判断结果”。"
            " OpenClaw本身开源免费，唯一的开销是云端大模型的API费用。"
            " 拥抱AI ，而不是畏惧它 分享时刻的最后，主讲人回归理性：AI不会让程序员失业，而是会重塑工作方式，提升效率。"
        ),
    }

    result = summarize_threads(article)
    credibility = assess_credibility(article).to_dict()
    ai_result = assess_ai_likelihood(article).to_dict()

    assert not result["summary"].startswith(("”", "“", '"'))
    assert "主讲人也表达了自己对现阶段AI的认识与感受" not in result["summary"]
    assert "概率模型" in result["summary"]
    assert ("安全" in result["summary"] or "隔离" in result["summary"] or "权限" in result["summary"])
    assert all(not item.startswith(("”", "“", '"')) for item in result["main_threads"])
    assert all(not item.startswith("你是否") for item in result["main_threads"])
    assert all(item not in result["summary"] for item in result["main_threads"])
    assert len(result["main_threads"]) >= 4
    assert any("：" in item for item in result["main_threads"][:3])
    assert credibility["score"] >= 50
    assert ai_result["score"] >= 25


def test_learning_method_article_prefers_abstractive_summary_and_structured_threads():
    article = {
        "url": "https://example.com/learn-how-to-learn",
        "title": "在AI时代：学习如何学习（一）",
        "source": "测试来源",
        "author": "测试作者",
        "published_at": "2026-03-22T12:00:00+08:00",
        "language": "zh",
        "word_count": 800,
        "fetched_at": "2026-03-22T12:00:00+08:00",
        "text": (
            "在人工智能时代，读书的主要目的，就是学习如何学习。因为知识的传递变得非常容易，“学到知识”越来越便利，“如何学习”则成了关键。"
            "\n\n"
            "在AI时代一定要学会提问题。提出问题的价值远远胜于答案本身，提问能力的实质，就是培养一个人思考的习惯。"
            "\n\n"
            "快速阅读在AI时代尤其重要。你需要通过限时通读和持续训练提升阅读速度、抓要点能力与专注力。"
            "\n\n"
            "要注意随时记录你每天的学习活动。记录会成为后续研究、写作和总结的素材来源。"
            "\n\n"
            "真正的教育包含学、思、践、悟。没有实践，很难形成真正的感知、直觉与悟性。"
            "\n\n"
            "不过还要提醒一点，与聪明人为伍的同时，一定要保持独立思考。"
        ),
    }

    result = summarize_threads(article)

    assert "获取知识会越来越容易" in result["summary"]
    assert "提问" in result["summary"]
    assert "独立思考" in result["summary"]
    assert result["main_threads"][0].startswith("学习重心：")
    assert any(item.startswith("阅读训练：") for item in result["main_threads"])
    assert any(item.startswith("实践转化：") for item in result["main_threads"])
    assert all(item not in sentence_split(article["text"]) for item in result["main_threads"][:3])


def test_kv_cache_article_uses_tradeoff_summary_and_non_extract_threads():
    article = {
        "url": "https://example.com/kv-cache",
        "title": "讲透 KV Cache 原理、工程与选型",
        "source": "测试来源",
        "author": "测试作者",
        "published_at": "2026-03-22T12:00:00+08:00",
        "language": "zh",
        "word_count": 900,
        "fetched_at": "2026-03-22T12:00:00+08:00",
        "text": (
            "没有 KV Cache，大模型推理慢到不可用；有了 KV Cache，上下文一长，显存又被撑爆。"
            "\n\n"
            "围绕这一矛盾，过去三年出现了三条路线：用 PagedAttention 等系统手段管好内存、用 GQA/MLA 等架构设计从源头压缩缓存量、用驱逐和量化在推理时动态瘦身。"
            "\n\n"
            "KV Cache 的本质，是缓存历史 Token 的 Key 和 Value，避免解码阶段对前缀的重复计算。"
            "\n\n"
            "PagedAttention、连续批处理和前缀共享，主要解决的是碎片、吞吐和重复缓存问题。"
        ),
    }

    result = summarize_threads(article)

    assert "KV Cache" in result["summary"]
    assert "降低重复计算" in result["summary"]
    assert "显存" in result["summary"]
    assert result["main_threads"][0].startswith("基本原理：")
    assert any(item.startswith("核心矛盾：") for item in result["main_threads"])
    assert any(item.startswith("系统优化：") for item in result["main_threads"])
    assert all("PagedAttention 等系统手段管好内存" not in item for item in result["main_threads"])


def test_threads_avoid_duplicate_category_lines_after_rewrite():
    article = {
        "url": "https://example.com/openclaw-dedupe",
        "title": "零代码开发AI应用？这场分享会揭秘“养龙虾”的快乐！",
        "source": "测试来源",
        "author": None,
        "published_at": "2026-03-22T12:00:00+08:00",
        "language": "zh",
        "word_count": 500,
        "fetched_at": "2026-03-22T12:00:00+08:00",
        "text": (
            "OpenClaw最核心的能力，不是单纯回答问题，而是把自然语言需求拆成具体任务，再调用工具逐步执行。"
            "\n\n"
            "AI目前更像一个概率模型，不具备真正的逻辑和情感。"
            "\n\n"
            "OpenClaw本身开源免费，主要花费来自云端模型 API；如果复杂任务交给高阶模型，简单任务切给本地模型，整体会更省钱。"
            "\n\n"
            "演示里，AI 会先创建目录、配置环境，再自动生成页面和后端接口；如果运行报错，它还会根据终端反馈继续修改，直到跑通。"
            "\n\n"
            "安全方面，建议把 AI 放在隔离环境里，只开放必要权限。"
            "\n\n"
            "对于普通人来说，更现实的用法不是自己从零写代码，而是学会把需求描述清楚，并判断结果是否符合预期。"
        ),
    }

    result = summarize_threads(article)
    cost_items = [item for item in result["main_threads"] if item.startswith("成本结构：")]

    assert len(cost_items) <= 1


def test_sectioned_notes_are_summarized_one_by_one():
    article = {
        "url": "https://www.biji.com/note/share_note/demo",
        "title": "结构化笔记测试",
        "source": "Get笔记",
        "author": "测试作者",
        "published_at": "2026-03-22T12:00:00+08:00",
        "language": "zh",
        "word_count": 600,
        "fetched_at": "2026-03-22T12:00:00+08:00",
        "text": "主笔记正文。\n\n附加笔记 1。\n\n附加笔记 2。",
        "metadata": {
            "provider": "biji-share-note",
            "sectioned_notes": [
                {
                    "kind": "main",
                    "title": "主笔记",
                    "text": "作者主张在 12GB 显存条件下采用本地模型负责高频轻任务、云端模型负责复杂任务的混合工作流。",
                },
                {
                    "kind": "append",
                    "title": "12G显存开发指南",
                    "text": "这条附加笔记重点讨论显存有限时如何选择本地代码模型、怎样分配补全和重构任务。",
                },
                {
                    "kind": "append",
                    "title": "智能路由分流指南",
                    "text": "这条附加笔记解释如何用轻量模型先判断复杂度，再把复杂请求转给更强的云端模型。",
                },
            ],
        },
    }

    result = summarize_threads(article)

    assert "12GB 显存" in result["summary"]
    assert "附加笔记进一步讨论了" in result["summary"]
    assert "《12G显存开发指南》" not in result["summary"]
    assert result["main_threads"][0].startswith("主笔记：")
    assert any(item.startswith("附加笔记 1《12G显存开发指南》：") for item in result["main_threads"])
    assert any(item.startswith("附加笔记 2《智能路由分流指南》：") for item in result["main_threads"])


def test_ai_score_detects_highly_templated_ai_guide_text():
    article = {
        "url": "https://www.biji.com/note/share_note/ai-guide",
        "title": "2026开发者混血模式完全指南",
        "source": "Get笔记",
        "author": "测试作者",
        "published_at": "2026-03-22T12:00:00+08:00",
        "language": "zh",
        "word_count": 900,
        "fetched_at": "2026-03-22T12:00:00+08:00",
        "metadata": {"provider": "biji-share-note", "append_note_count": 5},
        "text": (
            "# 🚀 2026年开发者混血模式完全指南\n\n"
            "## 💡 核心理念\n\n"
            "既然你追求效率与能力的平衡，那么混血模式就是最实用的选择。\n\n"
            "## 🏎️ 黄金组合方案\n\n"
            "| 角色 | 工具 | 职责 |\n| --- | --- | --- |\n| 本地辅助 | Qwen | 高频轻任务 |\n| 云端大脑 | Codex | 复杂重构 |\n\n"
            "## 🛠️ 操作指引\n\n"
            "第一步：部署本地快手。第二步：连接统一入口。第三步：设置智能路由。\n\n"
            "如果你愿意，我还可以继续帮你把这套流程写成更完整的终极指南。[OpenAI开发者][1]\n\n"
            "[1]: https://example.com/ref"
        ),
    }

    result = assess_ai_likelihood(article).to_dict()

    assert result["score"] >= 75
    assert result["level"] in {"较高 AI 痕迹", "中度 AI 痕迹"}


def test_openharmony_center_article_uses_structured_summary():
    article = {
        "url": "https://news.southcn.com/node/demo",
        "title": "全国首个省级开源鸿蒙适配中心在广州黄埔落地",
        "source": "南方网",
        "author": None,
        "published_at": "2026-03-22T12:00:00+08:00",
        "language": "zh",
        "word_count": 900,
        "fetched_at": "2026-03-22T12:00:00+08:00",
        "text": (
            "广东省开源鸿蒙适配中心在黄埔揭牌。该中心定位为全栈式开源鸿蒙产业协同中枢。"
            "\n\n"
            "黄埔区同步建设开源鸿蒙创新示范区，提出到2026年集聚30家以上生态企业，到2028年产业规模突破百亿元。"
            "\n\n"
            "中心将提供从芯片、板卡、整机到应用层的适配、测试认证、人才培养和生态推广服务。"
            "\n\n"
            "佳都科技的交通佳鸿方案拿到首张开源鸿蒙生态产品适配认证证书。"
        ),
    }

    result = summarize_threads(article)

    assert "开源鸿蒙适配中心" in result["summary"]
    assert "降低企业适配成本" in result["summary"]
    assert any(item.startswith("平台定位：") for item in result["main_threads"])
    assert any(item.startswith("阶段目标：") for item in result["main_threads"])


def test_huawei_openclaw_doc_article_uses_setup_summary():
    article = {
        "url": "https://developer.huawei.com/consumer/cn/doc/service/open-claw-base-0000002518704040",
        "title": "OpenClaw基础配置",
        "source": "华为开发者联盟",
        "author": None,
        "published_at": "2026-02-13T01:14:00+08:00",
        "language": "zh",
        "word_count": 500,
        "fetched_at": "2026-03-22T12:00:00+08:00",
        "text": (
            "【OpenClaw基础配置】 是专为OpenClaw模式智能体设计的核心配置。"
            "\n\n"
            "OpenClaw基础配置包含以下两个步骤：获取【小艺开放平台凭证】、在OpenClaw服务器上【配置channel】。"
            "\n\n"
            "完成上述所有配置后即可进行网页调试，并支持白名单真机测试。"
        ),
    }

    result = summarize_threads(article)

    assert "接入 OpenClaw 需要先创建平台凭证" in result["summary"]
    assert any(item.startswith("凭证准备：") for item in result["main_threads"])
    assert any(item.startswith("服务端配置：") for item in result["main_threads"])


def test_purple_volunteer_article_uses_history_summary():
    article = {
        "url": "https://example.com/purple",
        "title": "十年紫衣暖 家校同心长——回望紫衣军团的缘起与传承",
        "source": "测试来源",
        "author": None,
        "published_at": "2026-03-22T12:00:00+08:00",
        "language": "zh",
        "word_count": 900,
        "fetched_at": "2026-03-22T12:00:00+08:00",
        "text": (
            "紫衣军团最早源于浙江综评考点的家长志愿服务。"
            "\n\n"
            "2016年全国家长驰援杭州后，这支队伍正式成型。"
            "\n\n"
            "十年来，家长们始终践行“孩子毕业，家长永不毕业”的承诺。"
            "\n\n"
            "紫衣军团如今已参与招生、迎新、毕业季和家校公益等多个场景。"
        ),
    }

    result = summarize_threads(article)

    assert "紫衣军团" in result["summary"]
    assert "家校志愿网络" in result["summary"]
    assert any(item.startswith("起点形成：") for item in result["main_threads"])

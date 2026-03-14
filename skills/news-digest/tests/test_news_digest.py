import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = ROOT / "skills" / "news-digest"
SCRIPTS_DIR = SKILL_DIR / "scripts"


class NewsDigestScriptTests(unittest.TestCase):
    def run_script(self, script_name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script_name), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def write_json(self, payload: object) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            json.dump(payload, handle, ensure_ascii=False)
        return handle.name

    def test_intake_check_rejects_limit_above_max(self) -> None:
        result = self.run_script("intake_check.py", "--topic", "OpenAI", "--site", "openai.com", "--limit", "21")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--limit 必须 <= 20", result.stderr)

    def test_build_query_treats_subdomain_as_english_site(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "伊朗",
            "-s",
            "world.bbc.com",
            "--expand",
            "--auto-english",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("Iran", payload["keywordPlan"]["world.bbc.com"])

    def test_build_query_rejects_non_domain_site(self) -> None:
        result = self.run_script("build_query.py", "-k", "OpenAI", "-s", "BBC")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("站点需使用域名，如 bbc.com；收到: BBC", result.stderr)

    def test_build_query_splits_fullwidth_commas(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI，Gemini",
            "-s",
            "openai.com，blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("site:openai.com OpenAI", lines)
        self.assertIn("site:openai.com Gemini", lines)
        self.assertIn("site:blog.google OpenAI", lines)
        self.assertIn("site:blog.google Gemini", lines)

    def test_intake_check_confirm_includes_frequency_and_default_language(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "最近 24 小时",
            "--frequency",
            "一次性",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["频率"], "一次性")
        self.assertEqual(payload["confirm"]["输出语言"], "中文")

    def test_intake_check_defaults_time_range_without_asking(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertNotIn("你要看最近 24 小时、7 天，还是 30 天？", payload["missingQuestions"])
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")
        self.assertTrue(payload["defaultsApplied"]["time_range"])

    def test_intake_check_defaults_output_mode_without_asking(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "最近 7 天",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertNotIn("你更想看“总览+逐条”，还是“按主题分组+逐条”？", payload["missingQuestions"])
        self.assertEqual(payload["confirm"]["输出模式"], "摘要总览 + 逐条清单")
        self.assertTrue(payload["defaultsApplied"]["output_mode"])

    def test_intake_check_normalizes_time_range_shorthand(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "7d",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_natural_frequency_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--frequency",
            "执行一次",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["频率"], "一次性")

    def test_intake_check_rejects_unsupported_frequency(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--frequency",
            "每月",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--frequency 当前仅支持 一次性 / 每日 / 每周", result.stderr)

    def test_intake_check_rejects_non_chinese_output_language(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--language",
            "English",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--language 当前仅支持 中文", result.stderr)

    def test_intake_check_rejects_invalid_output_mode(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--output-mode",
            "乱填模式",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--output-mode 当前仅支持 摘要总览 + 逐条清单 / 按主题分组+逐条",
            result.stderr,
        )

    def test_intake_check_normalizes_natural_output_mode_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--output-mode",
            "总览+逐条",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["输出模式"], "摘要总览 + 逐条清单")

    def test_intake_check_normalizes_fullwidth_plus_output_mode(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--output-mode",
            "总览＋逐条",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["输出模式"], "摘要总览 + 逐条清单")

    def test_intake_check_normalizes_site_urls_to_domains(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "https://www.openai.com/index/policy",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["网站"], "openai.com")

    def test_intake_check_normalizes_common_media_aliases_to_domains(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "BBC,RFI,纽约时报,DW,华尔街见闻",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["confirm"]["网站"],
            "bbc.com、rfi.fr、nytimes.com、dw.com、wallstreetcn.com",
        )

    def test_intake_check_splits_fullwidth_commas(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI，Gemini",
            "--site",
            "openai.com，blog.google",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI、Gemini")
        self.assertEqual(payload["confirm"]["网站"], "openai.com、blog.google")

    def test_intake_check_rejects_non_domain_site(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "未知媒体",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("站点需使用域名，如 bbc.com；收到: 未知媒体", result.stderr)

    def test_intake_check_rejects_unknown_media_alias(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "央视新闻",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("站点需使用域名，如 bbc.com；收到: 央视新闻", result.stderr)

    def test_filter_results_keeps_same_title_across_domains(self) -> None:
        input_path = self.write_json(
            [
                {"title": "Same Title", "url": "https://bbc.com/news/a", "snippet": "a"},
                {"title": "Same Title", "url": "https://nytimes.com/world/b", "snippet": "b"},
            ]
        )
        result = self.run_script("filter_results.py", "--input", input_path, "--site", "bbc.com,nytimes.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)

    def test_filter_results_preserves_non_tracking_query_string(self) -> None:
        input_path = self.write_json(
            [
                {"title": "One", "url": "https://example.com/post?id=1&utm_source=test", "snippet": "1"},
                {"title": "Two", "url": "https://example.com/post?id=2&utm_source=test", "snippet": "2"},
            ]
        )
        result = self.run_script("filter_results.py", "--input", input_path, "--site", "example.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)
        normalized_urls = [item["normalizedUrl"] for item in payload["results"]]
        self.assertIn("https://example.com/post?id=1", normalized_urls)
        self.assertIn("https://example.com/post?id=2", normalized_urls)

    def test_filter_results_rejects_non_domain_site(self) -> None:
        input_path = self.write_json(
            [{"title": "One", "url": "https://www.bbc.com/news/a", "snippet": "1"}]
        )
        result = self.run_script("filter_results.py", "--input", input_path, "--site", "BBC")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("站点需使用域名，如 bbc.com；收到: BBC", result.stderr)

    def test_filter_results_splits_fullwidth_commas_in_sites(self) -> None:
        input_path = self.write_json(
            [
                {"title": "BBC One", "url": "https://www.bbc.com/news/a", "snippet": "1"},
                {"title": "Google One", "url": "https://blog.google/ai/x", "snippet": "2"},
            ]
        )
        result = self.run_script(
            "filter_results.py",
            "--input",
            input_path,
            "--site",
            "bbc.com，blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)

    def test_render_digest_rejects_missing_url(self) -> None:
        input_path = self.write_json({"results": [{"title": "No URL", "snippet": "missing"}]})
        result = self.run_script("render_digest.py", "--input", input_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("缺少 url", result.stderr)

    def test_render_digest_rejects_non_chinese_output_language(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                    }
                ]
            }
        )
        result = self.run_script("render_digest.py", "--input", input_path, "--language", "English")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--language 当前仅支持 中文", result.stderr)

    def test_render_digest_defaults_blank_language_to_chinese(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                    }
                ]
            }
        )
        result = self.run_script("render_digest.py", "--input", input_path, "--language", "   ")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 输出语言：中文", result.stdout)

    def test_render_digest_rejects_invalid_output_mode(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                    }
                ]
            }
        )
        result = self.run_script("render_digest.py", "--input", input_path, "--output-mode", "乱填模式")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--output-mode 当前仅支持 摘要总览 + 逐条清单 / 按主题分组+逐条",
            result.stderr,
        )

    def test_render_digest_rejects_limit_above_max(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                    }
                ]
            }
        )
        result = self.run_script("render_digest.py", "--input", input_path, "--limit", "21")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--limit 必须 <= 20", result.stderr)

    def test_render_digest_rejects_limit_below_min(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                    }
                ]
            }
        )
        result = self.run_script("render_digest.py", "--input", input_path, "--limit", "0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--limit 必须 >= 1", result.stderr)

    def test_render_digest_rejects_grouped_mode_without_topic_fields(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--output-mode",
            "按主题分组+逐条",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "按主题分组+逐条 模式要求每条结果包含 topic / queryTopic / keyword / query 字段",
            result.stderr,
        )

    def test_render_digest_normalizes_natural_output_mode_labels(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                        "topic": "OpenAI",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--output-mode",
            "按主题分组 + 逐条",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("### OpenAI", result.stdout)
        self.assertIn("- 输出模式：按主题分组+逐条", result.stdout)

    def test_render_digest_normalizes_fullwidth_plus_output_mode(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--output-mode",
            "总览＋逐条",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 输出模式：摘要总览 + 逐条清单", result.stdout)

    def test_render_digest_degrades_when_no_results(self) -> None:
        input_path = self.write_json(
            {
                "results": [],
                "discoveredResults": [
                    {"topic": "BBC", "note": "仅确认伊朗相关主题方向，未拿到稳定原文链接"}
                ],
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--keywords",
            "伊朗,战争,AI",
            "--sites",
            "bbc.com,rfi.fr,dw.com",
            "--time-range",
            "最近 7 天",
            "--frequency",
            "一次性",
            "--limit",
            "5",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## 检索参数", result.stdout)
        self.assertIn("## 已发现结果", result.stdout)
        self.assertIn("## 局限与建议", result.stdout)
        self.assertIn("- 频率：一次性", result.stdout)
        self.assertIn("- 输出语言：中文", result.stdout)
        self.assertIn("BBC：仅确认伊朗相关主题方向，未拿到稳定原文链接", result.stdout)
        self.assertNotIn("## 摘要总览", result.stdout)
        self.assertNotIn("## 文章清单", result.stdout)

    def test_render_digest_overview_contains_summary_not_only_title(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--frequency",
            "一次性",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OpenAI policy update（来源：openai.com）：policy summary from search result", result.stdout)
        self.assertIn("- 时间范围：最近 7 天", result.stdout)
        self.assertIn("- 频率：一次性", result.stdout)
        self.assertIn("- 结果数：5", result.stdout)
        self.assertIn("- 输出语言：中文", result.stdout)

    def test_render_digest_derives_source_domain_from_url_when_missing(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://www.openai.com/policy",
                        "snippet": "policy summary from search result",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OpenAI policy update（来源：openai.com）：policy summary from search result", result.stdout)
        self.assertIn("来源：openai.com ｜ 时间：时间未标注", result.stdout)
        self.assertNotIn("来源：来源未标注", result.stdout)

    def test_render_digest_normalizes_time_range_shorthand(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--time-range",
            "24h",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 24 小时", result.stdout)

    def test_render_digest_normalizes_keywords_and_sites_in_parameter_block(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--keywords",
            "OpenAI,Gemini",
            "--sites",
            "https://www.openai.com/index/policy,blog.google",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI、Gemini", result.stdout)
        self.assertIn("- 网站：openai.com、blog.google", result.stdout)

    def test_render_digest_normalizes_fullwidth_commas_in_parameter_block(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--keywords",
            "OpenAI，Gemini",
            "--sites",
            "https://www.openai.com/index/policy，blog.google",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI、Gemini", result.stdout)
        self.assertIn("- 网站：openai.com、blog.google", result.stdout)

    def test_render_digest_rejects_non_domain_site_in_parameter_block(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--sites",
            "BBC",
            "--overview-limit",
            "1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("站点需使用域名，如 bbc.com；收到: BBC", result.stderr)

    def test_render_digest_prefers_chinese_summary_fields(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "snippetZh": "OpenAI 发布了新的政策更新摘要",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--frequency",
            "一次性",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OpenAI 发布了新的政策更新摘要", result.stdout)
        self.assertNotIn("policy summary from search result", result.stdout)

    def test_render_digest_falls_back_to_original_summary_when_no_chinese_fields(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("policy summary from search result", result.stdout)
        self.assertNotIn("OpenAI 发布了新的政策更新摘要", result.stdout)

    def test_render_digest_normalizes_natural_frequency_labels(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--frequency",
            "执行一次",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 频率：一次性", result.stdout)

    def test_render_digest_rejects_unsupported_frequency(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--frequency",
            "每月",
            "--overview-limit",
            "1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--frequency 当前仅支持 一次性 / 每日 / 每周", result.stderr)


if __name__ == "__main__":
    unittest.main()

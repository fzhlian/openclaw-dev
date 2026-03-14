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

    def test_build_query_splits_ideographic_commas(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI、Gemini",
            "-s",
            "openai.com、blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("site:openai.com OpenAI", lines)
        self.assertIn("site:openai.com Gemini", lines)
        self.assertIn("site:blog.google OpenAI", lines)
        self.assertIn("site:blog.google Gemini", lines)

    def test_build_query_splits_semicolons(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI；Gemini",
            "-s",
            "openai.com；blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("site:openai.com OpenAI", lines)
        self.assertIn("site:openai.com Gemini", lines)
        self.assertIn("site:blog.google OpenAI", lines)
        self.assertIn("site:blog.google Gemini", lines)

    def test_build_query_splits_pipes(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI|Gemini",
            "-s",
            "openai.com|blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("site:openai.com OpenAI", lines)
        self.assertIn("site:openai.com Gemini", lines)
        self.assertIn("site:blog.google OpenAI", lines)
        self.assertIn("site:blog.google Gemini", lines)

    def test_build_query_splits_fullwidth_slashes(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI／Gemini",
            "-s",
            "openai.com／blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("site:openai.com OpenAI", lines)
        self.assertIn("site:openai.com Gemini", lines)
        self.assertIn("site:blog.google OpenAI", lines)
        self.assertIn("site:blog.google Gemini", lines)

    def test_build_query_splits_spaced_slashes(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI / Gemini",
            "-s",
            "openai.com / blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("site:openai.com OpenAI", lines)
        self.assertIn("site:openai.com Gemini", lines)
        self.assertIn("site:blog.google OpenAI", lines)
        self.assertIn("site:blog.google Gemini", lines)

    def test_build_query_strips_trailing_site_punctuation(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI",
            "-s",
            "openai.com.,blog.google。",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("site:openai.com OpenAI", lines)
        self.assertIn("site:blog.google OpenAI", lines)

    def test_build_query_strips_trailing_keyword_punctuation(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI。,Gemini！",
            "-s",
            "openai.com",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("site:openai.com OpenAI", lines)
        self.assertIn("site:openai.com Gemini", lines)
        self.assertNotIn("site:openai.com OpenAI。", lines)
        self.assertNotIn("site:openai.com Gemini！", lines)

    def test_build_query_deduplicates_keywords_case_insensitively(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI, openai",
            "-s",
            "openai.com",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["queries"], ["site:openai.com OpenAI"])
        self.assertEqual(payload["keywordPlan"]["openai.com"], ["OpenAI"])

    def test_build_query_normalizes_site_urls_with_default_ports(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI",
            "-s",
            "https://www.openai.com:443/index/policy,openai.com:443",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["queries"], ["site:openai.com OpenAI"])
        self.assertEqual(payload["keywordPlan"]["openai.com"], ["OpenAI"])

    def test_build_query_reports_invalid_list_file_path(self) -> None:
        result = self.run_script("build_query.py", "--keyword-file", ".", "-s", "openai.com")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("读取文件失败: .", result.stderr)

    def test_build_query_deduplicates_excludes_case_insensitively(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI",
            "-s",
            "openai.com",
            "-x",
            "ads,Ads",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["queries"], ['site:openai.com OpenAI -"ads"'])

    def test_build_query_strips_trailing_exclude_punctuation(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "OpenAI",
            "-s",
            "openai.com",
            "-x",
            "ads。,tracking！",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["queries"],
            ['site:openai.com OpenAI -"ads" -"tracking"'],
        )

    def test_build_query_strips_wrapping_quotes_and_parentheses(self) -> None:
        result = self.run_script(
            "build_query.py",
            "-k",
            "“OpenAI”",
            "-s",
            "（openai.com）",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["queries"], ["site:openai.com OpenAI"])
        self.assertEqual(payload["keywordPlan"]["openai.com"], ["OpenAI"])

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

    def test_intake_check_normalizes_natural_chinese_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "7 天",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_recent_compact_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "最近7天",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_short_recent_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "近7天",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_past_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "过去7天",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_worded_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "最近一周",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_numeric_worded_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "最近1周",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_near_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "近一周",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_month_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "最近一月",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 30 天")

    def test_intake_check_normalizes_relative_day_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "今天",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 1 天")

    def test_intake_check_normalizes_current_period_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "本周",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")

    def test_intake_check_normalizes_plain_worded_time_range_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "一周",
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

    def test_intake_check_normalizes_spaced_frequency_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--frequency",
            "每 周",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["频率"], "每周")

    def test_intake_check_normalizes_natural_periodic_frequency_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--frequency",
            "每周一次",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["频率"], "每周")

    def test_intake_check_normalizes_numeric_periodic_frequency_labels(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--frequency",
            "每周1次",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["频率"], "每周")

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

    def test_intake_check_normalizes_site_urls_with_default_ports(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "https://www.openai.com:443/index/policy,openai.com:443",
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

    def test_intake_check_deduplicates_sites_after_normalization(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "BBC,bbc.com",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["网站"], "bbc.com")

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

    def test_intake_check_splits_ideographic_commas(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI、Gemini",
            "--site",
            "openai.com、blog.google",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI、Gemini")
        self.assertEqual(payload["confirm"]["网站"], "openai.com、blog.google")

    def test_intake_check_splits_semicolons(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI；Gemini",
            "--site",
            "openai.com；blog.google",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI、Gemini")
        self.assertEqual(payload["confirm"]["网站"], "openai.com、blog.google")

    def test_intake_check_splits_pipes(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI|Gemini",
            "--site",
            "openai.com|blog.google",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI、Gemini")
        self.assertEqual(payload["confirm"]["网站"], "openai.com、blog.google")

    def test_intake_check_splits_fullwidth_slashes(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI／Gemini",
            "--site",
            "openai.com／blog.google",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI、Gemini")
        self.assertEqual(payload["confirm"]["网站"], "openai.com、blog.google")

    def test_intake_check_splits_spaced_slashes(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI / Gemini",
            "--site",
            "openai.com / blog.google",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI、Gemini")
        self.assertEqual(payload["confirm"]["网站"], "openai.com、blog.google")

    def test_intake_check_strips_trailing_site_punctuation(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com.,blog.google。",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["网站"], "openai.com、blog.google")

    def test_intake_check_strips_trailing_keyword_punctuation(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI。,Gemini！",
            "--site",
            "openai.com",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI、Gemini")

    def test_intake_check_strips_trailing_parameter_punctuation(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "最近7天。",
            "--frequency",
            "执行一次。",
            "--output-mode",
            "总览+逐条。",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")
        self.assertEqual(payload["confirm"]["频率"], "一次性")
        self.assertEqual(payload["confirm"]["输出模式"], "摘要总览 + 逐条清单")

    def test_intake_check_strips_wrapping_parameter_punctuation(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--time-range",
            "“最近7天”",
            "--frequency",
            "（执行一次）",
            "--output-mode",
            "《总览+逐条》",
            "--language",
            "“中文”",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["时间范围"], "最近 7 天")
        self.assertEqual(payload["confirm"]["频率"], "一次性")
        self.assertEqual(payload["confirm"]["输出模式"], "摘要总览 + 逐条清单")
        self.assertEqual(payload["confirm"]["输出语言"], "中文")

    def test_intake_check_strips_trailing_language_punctuation(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI",
            "--site",
            "openai.com",
            "--language",
            "中文。",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["输出语言"], "中文")

    def test_intake_check_strips_wrapping_quotes_and_parentheses(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "“OpenAI”",
            "--site",
            "（openai.com）",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI")
        self.assertEqual(payload["confirm"]["网站"], "openai.com")

    def test_intake_check_deduplicates_keywords_case_insensitively(self) -> None:
        result = self.run_script(
            "intake_check.py",
            "--topic",
            "OpenAI, openai",
            "--site",
            "openai.com",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["confirm"]["关键词"], "OpenAI")

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

    def test_filter_results_deduplicates_reordered_query_params(self) -> None:
        input_path = self.write_json(
            [
                {"title": "One", "url": "https://example.com/post?id=1&page=2", "snippet": "1"},
                {"title": "Two", "url": "https://example.com/post?page=2&id=1", "snippet": "2"},
            ]
        )
        result = self.run_script("filter_results.py", "--input", input_path, "--site", "example.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 1)
        self.assertEqual(payload["summary"]["dropped"], 1)
        self.assertEqual(payload["results"][0]["normalizedUrl"], "https://example.com/post?id=1&page=2")

    def test_filter_results_normalizes_scheme_less_urls(self) -> None:
        input_path = self.write_json(
            [
                {"title": "One", "url": "example.com/post?id=1", "snippet": "1"},
            ]
        )
        result = self.run_script("filter_results.py", "--input", input_path, "--site", "example.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 1)
        self.assertEqual(payload["results"][0]["normalizedUrl"], "https://example.com/post?id=1")

    def test_filter_results_deduplicates_http_and_https_variants(self) -> None:
        input_path = self.write_json(
            [
                {"title": "One", "url": "http://example.com/post?id=1", "snippet": "1"},
                {"title": "Two", "url": "https://example.com/post?id=1", "snippet": "2"},
            ]
        )
        result = self.run_script("filter_results.py", "--input", input_path, "--site", "example.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 1)
        self.assertEqual(payload["summary"]["dropped"], 1)
        self.assertEqual(payload["results"][0]["normalizedUrl"], "https://example.com/post?id=1")

    def test_filter_results_accepts_default_ports_as_same_domain(self) -> None:
        input_path = self.write_json(
            [
                {"title": "One", "url": "https://example.com:443/post?id=1", "snippet": "1"},
                {"title": "Two", "url": "http://example.com:80/post?id=1", "snippet": "2"},
            ]
        )
        result = self.run_script("filter_results.py", "--input", input_path, "--site", "example.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 1)
        self.assertEqual(payload["summary"]["dropped"], 1)
        self.assertEqual(payload["results"][0]["normalizedUrl"], "https://example.com/post?id=1")

    def test_filter_results_rejects_non_domain_site(self) -> None:
        input_path = self.write_json(
            [{"title": "One", "url": "https://www.bbc.com/news/a", "snippet": "1"}]
        )
        result = self.run_script("filter_results.py", "--input", input_path, "--site", "BBC")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("站点需使用域名，如 bbc.com；收到: BBC", result.stderr)

    def test_filter_results_reports_invalid_input_path(self) -> None:
        result = self.run_script("filter_results.py", "--input", ".", "--site", "bbc.com")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("读取输入 JSON 失败: .", result.stderr)

    def test_filter_results_reports_invalid_json(self) -> None:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            handle.write("not json")
        result = self.run_script("filter_results.py", "--input", handle.name, "--site", "bbc.com")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"解析输入 JSON 失败: {handle.name}", result.stderr)

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

    def test_filter_results_splits_ideographic_commas_in_sites(self) -> None:
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
            "bbc.com、blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)

    def test_filter_results_splits_semicolons_in_sites(self) -> None:
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
            "bbc.com；blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)

    def test_filter_results_splits_pipes_in_sites(self) -> None:
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
            "bbc.com|blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)

    def test_filter_results_splits_fullwidth_slashes_in_sites(self) -> None:
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
            "bbc.com／blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)

    def test_filter_results_splits_spaced_slashes_in_sites(self) -> None:
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
            "bbc.com / blog.google",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)

    def test_filter_results_strips_trailing_site_punctuation(self) -> None:
        input_path = self.write_json(
            [
                {"title": "One", "url": "https://openai.com/a", "snippet": "1"},
                {"title": "Two", "url": "https://blog.google/b", "snippet": "2"},
            ]
        )
        result = self.run_script(
            "filter_results.py",
            "--input",
            input_path,
            "--site",
            "openai.com.,blog.google。",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 2)
        self.assertEqual(payload["sites"], ["openai.com", "blog.google"])

    def test_filter_results_strips_wrapping_parentheses_from_sites(self) -> None:
        input_path = self.write_json(
            [
                {"title": "One", "url": "https://openai.com/a", "snippet": "1"},
            ]
        )
        result = self.run_script(
            "filter_results.py",
            "--input",
            input_path,
            "--site",
            "（openai.com）",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 1)
        self.assertEqual(payload["sites"], ["openai.com"])

    def test_filter_results_accepts_urls_with_trailing_dot_hosts(self) -> None:
        input_path = self.write_json(
            [
                {"title": "One", "url": "https://openai.com./a", "snippet": "1"},
            ]
        )
        result = self.run_script(
            "filter_results.py",
            "--input",
            input_path,
            "--site",
            "openai.com",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 1)
        self.assertEqual(payload["results"][0]["normalizedUrl"], "https://openai.com/a")

    def test_filter_results_deduplicates_sites_after_normalization(self) -> None:
        input_path = self.write_json(
            [{"title": "BBC One", "url": "https://www.bbc.com/news/a", "snippet": "1"}]
        )
        result = self.run_script(
            "filter_results.py",
            "--input",
            input_path,
            "--site",
            "https://www.bbc.com/news/a,bbc.com",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["sites"], ["bbc.com"])

    def test_filter_results_normalizes_site_urls_with_default_ports(self) -> None:
        input_path = self.write_json(
            [{"title": "One", "url": "https://www.openai.com/index/policy", "snippet": "1"}]
        )
        result = self.run_script(
            "filter_results.py",
            "--input",
            input_path,
            "--site",
            "https://www.openai.com:443/index/policy,openai.com:443",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["kept"], 1)
        self.assertEqual(payload["sites"], ["openai.com"])

    def test_render_digest_rejects_missing_url(self) -> None:
        input_path = self.write_json({"results": [{"title": "No URL", "snippet": "missing"}]})
        result = self.run_script("render_digest.py", "--input", input_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("缺少 url", result.stderr)

    def test_render_digest_reports_invalid_input_path(self) -> None:
        result = self.run_script("render_digest.py", "--input", ".")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("读取输入 JSON 失败: .", result.stderr)

    def test_render_digest_reports_invalid_json(self) -> None:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            handle.write("not json")
        result = self.run_script("render_digest.py", "--input", handle.name)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"解析输入 JSON 失败: {handle.name}", result.stderr)

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

    def test_render_digest_ignores_default_port_when_deriving_source_domain(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://www.openai.com:443/policy",
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
        self.assertNotIn("来源：openai.com:443", result.stdout)

    def test_render_digest_normalizes_source_domain_display(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://www.openai.com/policy",
                        "snippet": "policy summary from search result",
                        "sourceDomain": "WWW.OpenAI.COM",
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
        self.assertNotIn("WWW.OpenAI.COM", result.stdout)

    def test_render_digest_normalizes_source_domain_display_with_default_port(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://www.openai.com/policy",
                        "snippet": "policy summary from search result",
                        "sourceDomain": "WWW.OpenAI.COM:443",
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
        self.assertNotIn("来源：openai.com:443", result.stdout)

    def test_render_digest_enforces_limit_in_rendered_results(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://openai.com/policy",
                        "snippet": "policy summary from search result",
                        "matchedDomain": "openai.com",
                    },
                    {
                        "title": "OpenAI roadmap note",
                        "url": "https://openai.com/roadmap",
                        "snippet": "roadmap summary",
                        "matchedDomain": "openai.com",
                    },
                    {
                        "title": "OpenAI pricing note",
                        "url": "https://openai.com/pricing",
                        "snippet": "pricing summary",
                        "matchedDomain": "openai.com",
                    },
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--limit",
            "2",
            "--overview-limit",
            "3",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 结果数：2", result.stdout)
        self.assertIn("1. **OpenAI policy update**", result.stdout)
        self.assertIn("2. **OpenAI roadmap note**", result.stdout)
        self.assertNotIn("OpenAI pricing note", result.stdout)

    def test_render_digest_enforces_default_limit_in_rendered_results(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {"title": "t1", "url": "https://openai.com/1", "snippet": "s1", "matchedDomain": "openai.com"},
                    {"title": "t2", "url": "https://openai.com/2", "snippet": "s2", "matchedDomain": "openai.com"},
                    {"title": "t3", "url": "https://openai.com/3", "snippet": "s3", "matchedDomain": "openai.com"},
                    {"title": "t4", "url": "https://openai.com/4", "snippet": "s4", "matchedDomain": "openai.com"},
                    {"title": "t5", "url": "https://openai.com/5", "snippet": "s5", "matchedDomain": "openai.com"},
                    {"title": "t6", "url": "https://openai.com/6", "snippet": "s6", "matchedDomain": "openai.com"},
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--overview-limit",
            "10",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 结果数：5", result.stdout)
        self.assertIn("5. **t5**", result.stdout)
        self.assertNotIn("t6", result.stdout)

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

    def test_render_digest_normalizes_natural_chinese_time_range_labels(self) -> None:
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
            "7 天",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 7 天", result.stdout)

    def test_render_digest_normalizes_recent_compact_time_range_labels(self) -> None:
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
            "最近24小时",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 24 小时", result.stdout)

    def test_render_digest_normalizes_short_recent_time_range_labels(self) -> None:
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
            "近7天",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 7 天", result.stdout)

    def test_render_digest_normalizes_past_time_range_labels(self) -> None:
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
            "过去7天",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 7 天", result.stdout)

    def test_render_digest_normalizes_worded_time_range_labels(self) -> None:
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
            "最近一周",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 7 天", result.stdout)

    def test_render_digest_normalizes_numeric_worded_time_range_labels(self) -> None:
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
            "过去1个月",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 30 天", result.stdout)

    def test_render_digest_normalizes_near_time_range_labels(self) -> None:
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
            "近1个月",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 30 天", result.stdout)

    def test_render_digest_normalizes_month_time_range_labels(self) -> None:
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
            "近一月",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 30 天", result.stdout)

    def test_render_digest_normalizes_relative_day_time_range_labels(self) -> None:
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
            "昨天",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 1 天", result.stdout)

    def test_render_digest_normalizes_current_period_time_range_labels(self) -> None:
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
            "本月",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 30 天", result.stdout)

    def test_render_digest_normalizes_plain_worded_time_range_labels(self) -> None:
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
            "一个月",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 30 天", result.stdout)

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

    def test_render_digest_deduplicates_sites_after_normalization(self) -> None:
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
            "https://www.openai.com/index/policy,openai.com",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 网站：openai.com", result.stdout)

    def test_render_digest_normalizes_semicolon_separated_params(self) -> None:
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
            "OpenAI；Gemini",
            "--sites",
            "openai.com；blog.google",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI、Gemini", result.stdout)
        self.assertIn("- 网站：openai.com、blog.google", result.stdout)
        self.assertNotIn("- 网站：openai.com、openai.com", result.stdout)

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

    def test_render_digest_normalizes_pipe_separated_params(self) -> None:
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
            "OpenAI|Gemini",
            "--sites",
            "openai.com|blog.google",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI、Gemini", result.stdout)
        self.assertIn("- 网站：openai.com、blog.google", result.stdout)

    def test_render_digest_normalizes_fullwidth_slash_separated_params(self) -> None:
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
            "OpenAI／Gemini",
            "--sites",
            "openai.com／blog.google",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI、Gemini", result.stdout)
        self.assertIn("- 网站：openai.com、blog.google", result.stdout)

    def test_render_digest_normalizes_spaced_slash_separated_params(self) -> None:
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
            "OpenAI / Gemini",
            "--sites",
            "openai.com / blog.google",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI、Gemini", result.stdout)
        self.assertIn("- 网站：openai.com、blog.google", result.stdout)

    def test_render_digest_strips_trailing_site_punctuation(self) -> None:
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
            "openai.com.,blog.google。",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 网站：openai.com、blog.google", result.stdout)

    def test_render_digest_strips_trailing_keyword_punctuation(self) -> None:
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
            "OpenAI。,Gemini！",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI、Gemini", result.stdout)
        self.assertNotIn("- 关键词：OpenAI。、Gemini！", result.stdout)

    def test_render_digest_strips_trailing_parameter_punctuation(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "One",
                        "url": "https://openai.com/a",
                        "snippet": "1",
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
            "最近7天。",
            "--frequency",
            "执行一次。",
            "--output-mode",
            "总览+逐条。",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 7 天", result.stdout)
        self.assertIn("- 频率：一次性", result.stdout)
        self.assertIn("- 输出模式：摘要总览 + 逐条清单", result.stdout)

    def test_render_digest_strips_wrapping_parameter_punctuation(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "One",
                        "url": "https://openai.com/a",
                        "snippet": "1",
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
            "“最近7天”",
            "--frequency",
            "（执行一次）",
            "--output-mode",
            "《总览+逐条》",
            "--language",
            "“中文”",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 时间范围：最近 7 天", result.stdout)
        self.assertIn("- 频率：一次性", result.stdout)
        self.assertIn("- 输出模式：摘要总览 + 逐条清单", result.stdout)
        self.assertIn("- 输出语言：中文", result.stdout)

    def test_render_digest_strips_trailing_language_punctuation(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "One",
                        "url": "https://openai.com/a",
                        "snippet": "1",
                        "matchedDomain": "openai.com",
                    }
                ]
            }
        )
        result = self.run_script(
            "render_digest.py",
            "--input",
            input_path,
            "--language",
            "中文。",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 输出语言：中文", result.stdout)

    def test_render_digest_strips_wrapping_quotes_and_parentheses(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "One",
                        "url": "https://openai.com/a",
                        "snippet": "1",
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
            "“OpenAI”",
            "--sites",
            "（openai.com）",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI", result.stdout)
        self.assertIn("- 网站：openai.com", result.stdout)

    def test_render_digest_derives_source_domain_from_trailing_dot_url(self) -> None:
        input_path = self.write_json(
            {
                "results": [
                    {
                        "title": "OpenAI policy update",
                        "url": "https://www.openai.com./policy",
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
        self.assertNotIn("来源：openai.com.", result.stdout)

    def test_render_digest_normalizes_ideographic_commas_in_parameter_block(self) -> None:
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
            "OpenAI、Gemini",
            "--sites",
            "https://www.openai.com/index/policy、blog.google",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI、Gemini", result.stdout)
        self.assertIn("- 网站：openai.com、blog.google", result.stdout)

    def test_render_digest_deduplicates_keywords_case_insensitively(self) -> None:
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
            "OpenAI, openai",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 关键词：OpenAI", result.stdout)
        self.assertNotIn("- 关键词：OpenAI、openai", result.stdout)

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

    def test_render_digest_normalizes_spaced_frequency_labels(self) -> None:
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
            "每 周",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 频率：每周", result.stdout)

    def test_render_digest_normalizes_natural_periodic_frequency_labels(self) -> None:
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
            "每周一次",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 频率：每周", result.stdout)

    def test_render_digest_normalizes_numeric_periodic_frequency_labels(self) -> None:
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
            "每周1次",
            "--overview-limit",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- 频率：每周", result.stdout)

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

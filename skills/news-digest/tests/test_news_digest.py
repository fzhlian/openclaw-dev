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

    def test_intake_check_confirm_includes_frequency(self) -> None:
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

    def test_render_digest_rejects_missing_url(self) -> None:
        input_path = self.write_json({"results": [{"title": "No URL", "snippet": "missing"}]})
        result = self.run_script("render_digest.py", "--input", input_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("缺少 url", result.stderr)

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
        result = self.run_script("render_digest.py", "--input", input_path, "--overview-limit", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OpenAI policy update（来源：openai.com）：policy summary from search result", result.stdout)


if __name__ == "__main__":
    unittest.main()

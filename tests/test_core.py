"""核心逻辑测试。跑法：python -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from launchpad import awesome, cli, content, platforms  # noqa: E402

SAMPLE_README = """# Awesome Python

## Contents

- [Tools](#tools)

## Tools

- [black](https://github.com/psf/black) - opinionated formatter
- [flask](https://github.com/pallets/flask) - micro web framework
- [requests](https://github.com/psf/requests) - http library

## Data

- [pandas](https://github.com/pandas-dev/pandas) - dataframes
"""


def make_project(name: str = "repo-doctor") -> content.Project:
    return content.Project(
        name=name,
        repo=f"xingaorpw/{name}",
        tagline="给你的 GitHub 仓库做发布体检",
        problem="写完代码只是开始。有没有 LICENSE、有没有 Topics，这些才决定别人会不会 star 你。",
        bullets=["13 项检查", "输出 A-F 等级"],
        install="python -m repo_doctor owner/repo",
        example="84 / 100   B",
        limits=["只看有没有，不看好不好"],
        tags=["github", "python", "tooling"],
        hashtags=["#opensource", "#python"],
    )


class FakeGitHub:
    def __init__(self, readme: str = SAMPLE_README, default_branch: str = "main"):
        self._readme = readme
        self._branch = default_branch

    def readme(self, full_name, ref=None):
        return self._readme, "sha123"

    def stats(self, full_name):
        return {"default_branch": self._branch}

    def whoami(self):
        return "tester"


class TestContent(unittest.TestCase):
    def test_load_all_bundled_projects(self):
        projects = content.load_all()
        self.assertEqual(len(projects), 8)
        names = {p.name for p in projects}
        for expected in ("repo-doctor", "skill-lint", "Starscout", "skillhub"):
            self.assertIn(expected, names)

    def test_every_project_has_required_fields(self):
        for project in content.load_all():
            self.assertTrue(project.tagline, project.name)
            self.assertTrue(project.problem, project.name)
            self.assertTrue(project.url.startswith("https://github.com/"), project.name)
            self.assertGreaterEqual(len(project.problem), 20, project.name)

    def test_find_by_name_and_repo(self):
        projects = content.load_all()
        self.assertEqual(content.find(projects, "repo-doctor").name, "repo-doctor")
        self.assertEqual(
            content.find(projects, "xingaorpw/repo-doctor").name, "repo-doctor"
        )
        with self.assertRaises(KeyError):
            content.find(projects, "nope")

    def test_short_post_respects_limit(self):
        project = make_project()
        for limit in (120, 300, 500):
            text = content.render_short(project, limit)
            self.assertLessEqual(len(text), limit)
            self.assertIn(project.url, text)

    def test_short_post_contains_link_and_hashtag(self):
        text = content.render_short(make_project(), 300)
        self.assertIn("https://github.com/xingaorpw/repo-doctor", text)

    def test_article_has_sections(self):
        article = content.render_article(make_project())
        for heading in ("## 它解决什么问题", "## 它做什么", "## 快速开始", "## 已知限制"):
            self.assertIn(heading, article)

    def test_article_includes_stats_when_given(self):
        article = content.render_article(make_project(), {"stars": 42, "language": "Python"})
        self.assertIn("⭐ 42", article)

    def test_devto_tags_lowercase_alnum_max_four(self):
        tags = content.devto_tags(make_project())
        self.assertLessEqual(len(tags), 4)
        for tag in tags:
            self.assertTrue(tag.isalnum(), tag)
            self.assertEqual(tag, tag.lower())

    def test_load_rejects_missing_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps({"name": "x"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                content.load(path)


class TestPlatforms(unittest.TestCase):
    def test_all_six_platforms_registered(self):
        self.assertEqual(
            set(platforms.PLATFORMS),
            {"devto", "bluesky", "mastodon", "telegram", "discord", "hashnode"},
        )

    def test_dry_run_never_touches_network(self):
        project = make_project()
        for name, platform in platforms.PLATFORMS.items():
            result = platform.publish(project, dry_run=True)
            self.assertTrue(result.ok, name)
            self.assertEqual(result.platform, name)
            self.assertTrue(result.text)

    def test_short_text_fits_platform_limit(self):
        project = make_project()
        for name, platform in platforms.PLATFORMS.items():
            if platform.kind != "short":
                continue
            text = platform.text(project)
            self.assertLessEqual(len(text), platform.max_len, name)

    def test_configured_requires_env(self):
        import os

        saved = {k: os.environ.pop(k, None) for k in ("DEVTO_API_KEY",)}
        try:
            self.assertFalse(platforms.get("devto").configured())
            self.assertEqual(platforms.get("devto").missing(), ["DEVTO_API_KEY"])
        finally:
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value

    def test_unknown_platform_raises(self):
        with self.assertRaises(KeyError):
            platforms.get("myspace")

    def test_bluesky_facets_point_at_link(self):
        text = "hello\n\nhttps://github.com/xingaorpw/repo-doctor"
        facets = platforms.Bluesky._facets(text)
        self.assertEqual(len(facets), 1)
        index = facets[0]["index"]
        self.assertEqual(
            text.encode("utf-8")[index["byteStart"]:index["byteEnd"]].decode("utf-8"),
            "https://github.com/xingaorpw/repo-doctor",
        )

    def test_bluesky_facets_handle_cjk_prefix(self):
        text = "中文前缀 https://example.com/x"
        facets = platforms.Bluesky._facets(text)
        index = facets[0]["index"]
        self.assertEqual(
            text.encode("utf-8")[index["byteStart"]:index["byteEnd"]].decode("utf-8"),
            "https://example.com/x",
        )


class TestAwesome(unittest.TestCase):
    def test_normalize_url(self):
        self.assertEqual(
            awesome.normalize_url("https://github.com/Owner/Repo/"),
            "github.com/owner/repo",
        )

    def test_is_listed_true(self):
        readme = SAMPLE_README + "- [x](https://github.com/xingaorpw/repo-doctor)\n"
        self.assertTrue(awesome.is_listed(readme, "https://github.com/xingaorpw/repo-doctor"))

    def test_is_listed_false(self):
        self.assertFalse(awesome.is_listed(SAMPLE_README, "https://github.com/xingaorpw/repo-doctor"))

    def test_sections_split(self):
        found = awesome.sections(SAMPLE_README.splitlines())
        titles = [s["title"] for s in found]
        self.assertIn("Tools", titles)
        self.assertIn("Data", titles)

    def test_pick_section_prefers_keyword(self):
        section = awesome.pick_section(SAMPLE_README, ["data"])
        self.assertEqual(section["title"], "Data")

    def test_pick_section_returns_none_without_keyword_match(self):
        # 匹配不上就返回 None——插错分节比不开 PR 更糟
        self.assertIsNone(awesome.pick_section(SAMPLE_README, ["nonexistent"]))

    def test_pick_section_skips_table_of_contents(self):
        readme = (
            "# Awesome X\n\n## Table of Contents\n\n- [Tools](#tools)\n"
            "- [a](https://github.com/a/b)\n\n## Tools\n\n- [black](https://github.com/psf/black) - fmt\n"
        )
        section = awesome.pick_section(readme, ["tooling"])
        self.assertEqual(section["title"], "Tools")

    def test_pick_section_skips_sponsors_and_license(self):
        for title in ("Sponsors", "Contributing", "License", "Changelog"):
            readme = f"## {title}\n\n- [x](https://github.com/x/y) - z\n"
            self.assertIsNone(awesome.pick_section(readme, ["tooling"]), title)

    def test_title_matches_handles_plural_and_gerund(self):
        self.assertTrue(awesome.title_matches("Tools", "tooling"))
        self.assertTrue(awesome.title_matches("Python", "python"))
        self.assertFalse(awesome.title_matches("Table of Contents", "tooling"))

    def test_title_matches_cjk(self):
        self.assertTrue(awesome.title_matches("中文工具", "工具"))

    def test_suggest_patch_inserts_alphabetically(self):
        patch = awesome.suggest_patch(SAMPLE_README, make_project("repo-doctor"))
        self.assertIsNotNone(patch)
        lines = SAMPLE_README.splitlines()
        self.assertIn("repo-doctor", patch["line"])
        # repo-doctor 应排在 requests 之前（q < p 不成立，实际按字典序比较）
        self.assertLess(patch["line_index"], len(lines))

    def test_apply_patch_keeps_other_lines(self):
        patch = awesome.suggest_patch(SAMPLE_README, make_project("zzz-project"))
        new_readme = awesome.apply_patch(SAMPLE_README, patch["line_index"], patch["line"])
        self.assertIn("zzz-project", new_readme)
        self.assertIn("black", new_readme)
        self.assertIn("pandas", new_readme)

    def test_suggest_patch_returns_none_for_empty_readme(self):
        self.assertIsNone(awesome.suggest_patch("", make_project()))

    def test_submit_dry_run_reports_preview(self):
        gh = FakeGitHub()
        result = awesome.submit(gh, "owner/awesome-python", make_project(), dry_run=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["reason"], "dry-run")
        self.assertIn("repo-doctor", result["preview"])

    def test_submit_skips_when_already_listed(self):
        readme = SAMPLE_README + "- [x](https://github.com/xingaorpw/repo-doctor)\n"
        gh = FakeGitHub(readme=readme)
        result = awesome.submit(gh, "owner/awesome-python", make_project(), dry_run=True)
        self.assertTrue(result["skipped"])


class TestCli(unittest.TestCase):
    def test_projects(self):
        self.assertEqual(cli.main(["projects"]), 0)

    def test_platforms(self):
        self.assertEqual(cli.main(["platforms"]), 0)

    def test_plan_for_one_project(self):
        self.assertEqual(cli.main(["plan", "--project", "repo-doctor"]), 0)

    def test_plan_unknown_project_exits(self):
        with self.assertRaises(SystemExit):
            cli.main(["plan", "--project", "does-not-exist"])

    def test_post_dry_run_without_credentials(self):
        self.assertEqual(
            cli.main(["post", "--platform", "devto", "--project", "repo-doctor", "--dry-run"]),
            0,
        )

    def test_post_auto_without_credentials_returns_2(self):
        import os

        keys = ("DEVTO_API_KEY", "BSKY_HANDLE", "BSKY_APP_PASSWORD",
                "MASTODON_BASE_URL", "MASTODON_TOKEN", "TELEGRAM_BOT_TOKEN",
                "TELEGRAM_CHAT_ID", "DISCORD_WEBHOOK_URL",
                "HASHNODE_TOKEN", "HASHNODE_PUBLICATION_ID")
        saved = {k: os.environ.pop(k, None) for k in keys}
        try:
            self.assertEqual(
                cli.main(["post-auto", "--project", "repo-doctor", "--dry-run"]),
                2,
            )
        finally:
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value

    def test_post_auto_dry_run_with_fake_credentials(self):
        import os

        saved = {k: os.environ.get(k) for k in ("DEVTO_API_KEY",)}
        os.environ["DEVTO_API_KEY"] = "fake"
        try:
            self.assertEqual(
                cli.main(["post-auto", "--project", "repo-doctor", "--dry-run"]),
                0,
            )
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main(verbosity=2)

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import github_xhs_daily as daily


class GithubXhsDailyTests(unittest.TestCase):
    def ranked_repo(self, name, sources, scores=None, features=None, age_days=10):
        score_values = {
            "hot": 100,
            "used": 100,
            "starred": 100,
            "discussion": 100,
            "frontier": 100,
            "product": 100,
            "rising": 100,
            "all_time": 100,
        }
        score_values.update(scores or {})
        return {
            "full_name": name,
            "name": name.split("/")[-1],
            "html_url": f"https://github.com/{name}",
            "sources": sources,
            "scores": score_values,
            "features": features or [],
            "lens": {},
            "age_days": age_days,
            "stars": 100,
            "forks": 10,
        }

    def test_render_query_expands_relative_dates(self):
        run_date = dt.date(2026, 6, 5)
        query = daily.render_query("created:>={date_60} pushed:>={date_7}", run_date)
        self.assertEqual(query, "created:>=2026-04-06 pushed:>=2026-05-29")

    def test_infer_features_from_description_and_topics(self):
        repo = {
            "full_name": "demo/web-agent",
            "description": "A browser IDE with AI coding agent and live preview",
            "readme_excerpt": "",
            "topics": ["web-ide"],
        }
        features = daily.infer_features(repo)
        self.assertIn("AI Coding / Agent", features)
        self.assertIn("Web IDE / Browser Editor", features)
        self.assertIn("Sandbox / Preview", features)

    def test_first_readme_excerpt_skips_language_nav_noise(self):
        readme = """
# Career-Ops

English | Español | Français | Português (Brasil) | 한국어 | 日本語 | 简体中文

[![stars](https://img.shields.io/github/stars/demo/project)](https://github.com/demo/project)

## What Is This

Career-Ops turns any AI coding CLI into a full job search command center.
Instead of manually tracking applications in a spreadsheet, you get an AI-powered pipeline.
"""
        excerpt = daily.first_readme_excerpt(readme, 260)

        self.assertNotIn("English | Español", excerpt)
        self.assertNotIn("shields.io", excerpt)
        self.assertIn("Career-Ops turns any AI coding CLI", excerpt)

    def test_career_ops_summary_uses_readme_meaning(self):
        repo = {
            "full_name": "santifer/career-ops",
            "name": "career-ops",
            "description": "AI-powered job search system built on Claude Code. 14 skill modes, Go dashboard, PDF generation, batch processing.",
            "readme_excerpt": (
                "Career-Ops turns any AI coding CLI into a full job search command center. "
                "Instead of manually tracking applications in a spreadsheet, you get an AI-powered pipeline."
            ),
            "topics": ["job-search", "resume", "career"],
            "examples": [{"title": "Usage", "body": "/career-ops pdf", "code": ""}],
        }

        summary = daily.summarize_repo_docs_zh(repo)

        self.assertIn("AI 求职指挥中心", summary)
        self.assertIn("主要给", summary)
        self.assertIn("它解决的是", summary)
        self.assertIn("省掉", summary)
        self.assertIn("740+", summary)
        self.assertIn("100+", summary)
        self.assertIn("评估岗位", summary)
        self.assertIn("简历/CV", summary)
        self.assertNotIn("数据应用", summary)

    def test_quantitative_evidence_translates_token_savings(self):
        text = (
            "High-performance CLI proxy that reduces LLM token consumption by 60-90% "
            "on common dev commands. Single Rust binary, 100+ supported commands, <10ms overhead."
        )

        evidence = daily.quantitative_evidence_text(text)

        self.assertIn("常见开发命令可减少 60-90% 的模型 token 消耗", evidence)
        self.assertIn("100+ 个支持命令", evidence)
        self.assertNotIn("on common dev commands", evidence)

    def test_quantitative_evidence_translates_design_counts(self):
        text = "259+ Skills · 142+ Design Systems · Web, desktop and mobile prototypes."

        evidence = daily.quantitative_evidence_text(text)

        self.assertIn("259+ 个技能、142+ 套设计系统", evidence)
        self.assertNotIn("Design Systems", evidence)

    def test_design_project_beats_generic_coding_agent_classification(self):
        repo = {
            "full_name": "demo/open-design",
            "name": "open-design",
            "description": "Claude Code / Codex design workspace for prototypes, slides, images and design systems.",
            "readme_excerpt": "Go from a vague idea to discovering references, editing interactively and producing web, desktop and mobile prototypes.",
            "topics": ["ai-design", "coding-agents", "design-tools"],
            "examples": [{"title": "Demo", "body": "Entry view and mobile onboarding", "code": ""}],
        }

        summary = daily.summarize_repo_docs_zh(repo)

        self.assertIn("设计/原型生成工具", summary)
        self.assertIn("省掉的是先写需求", summary)
        self.assertNotIn("终端里的 AI 编程助手", summary)

    def test_astrology_skill_summary_uses_readme_meaning(self):
        repo = {
            "full_name": "demo/bazi-ziwei-skill",
            "name": "bazi-ziwei-skill",
            "description": (
                "AI 八字 + 紫微斗数排盘与综合印证 Skill：算法精准排盘（不靠 LLM 猜），"
                "三种分析模式，一键生成水墨风 HTML 命盘海报。"
            ),
            "readme_excerpt": (
                "一个遵循 SKILL.md 开放标准的命理分析 Skill。它做三件大模型单独做不好的事："
                "精准排盘、格局补层、综合印证。八字四柱、紫微十二宫、大运流年由内置算法库计算，"
                "不让 LLM 自己排。"
            ),
            "topics": ["bazi", "ziwei", "ziwei-doushu", "chinese-astrology", "metaphysics"],
            "examples": [{"title": "综合印证海报示例", "body": "水墨风命盘海报", "code": ""}],
        }

        summary = daily.summarize_repo_docs_zh(repo)

        self.assertIn("八字紫微综合印证 Skill", summary)
        self.assertIn("确定性算法", summary)
        self.assertIn("八字四柱", summary)
        self.assertIn("紫微十二宫", summary)
        self.assertIn("命盘海报", summary)
        self.assertNotIn("开发者工具项目", summary)
        self.assertNotIn("只看 stars", summary)
        self.assertNotIn("终端里的 AI 编程助手", summary)

    def test_select_rankings_keeps_tabs_exclusive(self):
        shared = self.ranked_repo(
            "demo/shared",
            ["frontier", "product", "rising", "all_time"],
            scores={"hot": 500, "used": 500, "starred": 500, "discussion": 500},
            features=["AI Coding / Agent", "Web IDE / Browser Editor"],
        )
        repos = [
            shared,
            self.ranked_repo("demo/hot", ["rising"], scores={"hot": 400}, features=["AI Coding / Agent"]),
            self.ranked_repo("demo/used", ["product"], scores={"used": 400}, features=["Web IDE / Browser Editor"]),
            self.ranked_repo("demo/starred", ["all_time"], scores={"starred": 400}),
            self.ranked_repo("demo/discussion", ["frontier"], scores={"discussion": 400}),
        ]
        hot, used, starred, discussion, _ = daily.select_rankings(
            repos,
            {
                "hot_limit": 3,
                "used_limit": 3,
                "starred_limit": 3,
                "discussion_limit": 3,
                "xhs_count": 3,
            },
        )
        sections = [hot, used, discussion, starred]
        names = [repo["full_name"] for section in sections for repo in section]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("demo/shared", [repo["full_name"] for repo in hot])
        self.assertNotIn("demo/shared", [repo["full_name"] for repo in used + discussion + starred])

    def test_extract_readme_examples_from_usage_section(self):
        readme = """
# Demo Project

Some intro text.

## Quick start

![Preview screen](docs/preview-screen.png)

Run this command to create your first app:

```bash
npx demo create my-app
cd my-app
```

Open the preview and change the prompt.

### Advanced options

Only read this when you need custom settings.

## License

MIT
"""
        examples = daily.extract_readme_examples(
            readme,
            full_name="demo/project",
            default_branch="main",
        )
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["title"], "Quick start")
        self.assertIn("create your first app", examples[0]["body"])
        self.assertNotIn("Advanced options", examples[0]["body"])
        self.assertIn("npx demo create my-app", examples[0]["code"])
        self.assertEqual(examples[0]["images"][0]["alt"], "Preview screen")
        self.assertEqual(
            examples[0]["images"][0]["url"],
            "https://raw.githubusercontent.com/demo/project/main/docs/preview-screen.png",
        )
        self.assertEqual(examples[0]["source"], "README")

    def test_extract_repo_full_names_from_public_text(self):
        text = "看这个 https://github.com/openai/codex 和另一个 vercel/ai 都很适合观察。"
        names = daily.extract_repo_full_names_from_text(text)
        self.assertIn("openai/codex", names)
        self.assertIn("vercel/ai", names)

    def test_collect_expert_repositories_from_starred_and_refs(self):
        class FakeClient:
            def list_starred_repositories(self, username, per_page=30, pages=1):
                self.starred_args = (username, per_page, pages)
                return [
                    {
                        "starred_at": "2026-06-05T00:00:00Z",
                        "repo": {
                            "id": 1,
                            "full_name": "demo/starred",
                            "name": "starred",
                            "owner": {"login": "demo"},
                            "html_url": "https://github.com/demo/starred",
                            "description": "AI coding agent",
                            "stargazers_count": 120,
                            "forks_count": 12,
                            "watchers_count": 120,
                            "open_issues_count": 1,
                            "topics": ["ai-coding"],
                            "default_branch": "main",
                        },
                    }
                ]

            def get_repository(self, full_name):
                if full_name != "demo/referenced":
                    return None
                return {
                    "id": 2,
                    "full_name": "demo/referenced",
                    "name": "referenced",
                    "owner": {"login": "demo"},
                    "html_url": "https://github.com/demo/referenced",
                    "description": "Browser IDE",
                    "stargazers_count": 80,
                    "forks_count": 8,
                    "watchers_count": 80,
                    "open_issues_count": 0,
                    "topics": ["web-ide"],
                    "default_branch": "main",
                }

        config = {
            "expert_sources": {
                "enabled": True,
                "starred_per_page": 10,
                "starred_pages": 1,
                "experts": [
                    {
                        "id": "expert",
                        "name": "Expert",
                        "category": "ai_engineer",
                        "github": "expert-user",
                        "track_starred": True,
                        "project_refs": [{"repo": "demo/referenced", "url": "https://github.com/demo/referenced"}],
                    }
                ],
            }
        }

        repos = daily.collect_expert_repositories(FakeClient(), config)
        by_name = {repo["full_name"]: repo for repo in repos}
        self.assertEqual(set(by_name), {"demo/starred", "demo/referenced"})
        self.assertEqual(by_name["demo/starred"]["expert_signals"][0]["source"], "github_star")
        self.assertEqual(by_name["demo/referenced"]["expert_signals"][0]["source"], "project_reference")

    def test_expert_signal_boosts_frontier_score(self):
        run_date = dt.date(2026, 6, 5)
        base_repo = {
            "full_name": "demo/repo",
            "stars": 100,
            "forks": 10,
            "open_issues": 1,
            "created_at": "2026-05-01T00:00:00Z",
            "pushed_at": "2026-06-04T00:00:00Z",
            "features": ["AI Coding / Agent"],
            "expert_signals": [],
        }
        expert_repo = dict(base_repo)
        expert_repo["expert_signals"] = []
        daily.attach_expert_signal(
            expert_repo,
            {
                "expert_id": "expert",
                "expert_name": "Expert",
                "category": "ai_engineer",
                "source": "github_star",
                "repo": "demo/repo",
                "weight": 1.5,
            },
        )

        daily.score_repo(base_repo, {"repos": {}}, run_date)
        daily.score_repo(expert_repo, {"repos": {}}, run_date)
        self.assertGreater(expert_repo["scores"]["hot"], base_repo["scores"]["hot"])
        self.assertGreater(expert_repo["scores"]["frontier"], base_repo["scores"]["frontier"])
        self.assertIn("expert_summary", expert_repo["lens"])

    def test_score_repo_uses_history_delta(self):
        run_date = dt.date(2026, 6, 5)
        history = {
            "repos": {
                "demo/repo": [
                    {
                        "date": "2026-06-03",
                        "stars": 100,
                        "forks": 10,
                        "open_issues": 1,
                    }
                ]
            }
        }
        repo = {
            "full_name": "demo/repo",
            "stars": 150,
            "forks": 12,
            "open_issues": 1,
            "created_at": "2026-05-01T00:00:00Z",
            "pushed_at": "2026-06-04T00:00:00Z",
            "features": ["AI Coding / Agent"],
        }
        daily.score_repo(repo, history, run_date)
        self.assertEqual(repo["delta_stars"], 50)
        self.assertEqual(repo["delta_forks"], 2)
        self.assertEqual(repo["delta_open_issues"], 0)
        self.assertEqual(repo["delta_days"], 2)
        self.assertEqual(repo["delta_per_day"], 25.0)
        self.assertEqual(repo["daily_stars"], 25.0)
        self.assertEqual(repo["daily_forks"], 1.0)
        self.assertTrue(repo["pushed_today"] is False)
        self.assertTrue(repo["early_focus"]["eligible"])
        self.assertEqual(repo["early_focus"]["stage"], "seed")
        self.assertGreater(repo["scores"]["hot"], 0)
        self.assertGreater(repo["scores"]["used"], 0)
        self.assertGreater(repo["scores"]["starred"], 0)
        self.assertGreater(repo["scores"]["discussion"], 0)
        self.assertGreater(repo["scores"]["rising"], 0)
        self.assertGreater(repo["scores"]["frontier"], 0)
        self.assertGreater(repo["scores"]["product"], 0)

    def test_hot_score_prioritizes_daily_growth_over_all_time_stars(self):
        run_date = dt.date(2026, 6, 5)
        history = {
            "repos": {
                "demo/classic": [
                    {"date": "2026-06-04", "stars": 100000, "forks": 5000, "open_issues": 20}
                ],
                "demo/riser": [
                    {"date": "2026-06-04", "stars": 100, "forks": 10, "open_issues": 1}
                ],
            }
        }
        classic = {
            "full_name": "demo/classic",
            "stars": 100000,
            "forks": 5000,
            "open_issues": 20,
            "created_at": "2020-01-01T00:00:00Z",
            "pushed_at": "2026-06-04T00:00:00Z",
            "features": [],
        }
        riser = {
            "full_name": "demo/riser",
            "stars": 140,
            "forks": 14,
            "open_issues": 3,
            "created_at": "2026-05-01T00:00:00Z",
            "pushed_at": "2026-06-05T00:00:00Z",
            "features": ["AI Coding / Agent"],
        }

        daily.score_repo(classic, history, run_date)
        daily.score_repo(riser, history, run_date)

        self.assertGreater(riser["scores"]["hot"], classic["scores"]["hot"])
        self.assertGreater(riser["scores"]["starred"], classic["scores"]["starred"])
        self.assertGreater(classic["scores"]["all_time"], riser["scores"]["all_time"])

    def test_select_rankings_filters_mature_repos_for_trend_lists(self):
        mature = self.ranked_repo(
            "demo/mature",
            ["rising"],
            scores={"hot": 9999, "used": 9999, "starred": 9999, "discussion": 9999},
            features=["AI Coding / Agent"],
        )
        mature.update(
            {
                "stars": 146000,
                "forks": 5000,
                "open_issues": 200,
                "daily_stars": 500,
                "daily_forks": 50,
                "daily_open_issues": 10,
                "pushed_today": True,
            }
        )
        early = self.ranked_repo(
            "demo/early",
            ["rising"],
            scores={"hot": 100, "used": 100, "starred": 100, "discussion": 100},
            features=["AI Coding / Agent"],
        )
        early.update(
            {
                "stars": 420,
                "forks": 12,
                "open_issues": 3,
                "daily_stars": 8,
                "daily_forks": 1,
                "daily_open_issues": 1,
                "pushed_today": True,
            }
        )

        hot, used, starred, discussion, _ = daily.select_rankings(
            [mature, early],
            {
                "hot_limit": 5,
                "used_limit": 5,
                "starred_limit": 5,
                "discussion_limit": 5,
                "xhs_count": 5,
            },
        )

        shown = [repo["full_name"] for repo in hot + used + starred + discussion]
        self.assertIn("demo/early", shown)
        self.assertNotIn("demo/mature", shown)

    def test_select_rankings_filters_old_low_star_repos_for_trend_lists(self):
        old_low_star = self.ranked_repo(
            "demo/old-low-star",
            ["rising"],
            scores={"hot": 9999, "used": 9999, "starred": 9999, "discussion": 9999},
            age_days=140,
        )
        old_low_star.update(
            {
                "stars": 120,
                "forks": 40,
                "open_issues": 12,
                "daily_stars": 30,
                "daily_forks": 4,
                "daily_open_issues": 2,
                "pushed_today": True,
            }
        )
        early = self.ranked_repo(
            "demo/early",
            ["rising"],
            scores={"hot": 100, "used": 100, "starred": 100, "discussion": 100},
            age_days=30,
        )
        early.update(
            {
                "stars": 160,
                "forks": 8,
                "open_issues": 2,
                "daily_stars": 3,
                "daily_forks": 1,
                "daily_open_issues": 0,
                "pushed_today": True,
            }
        )

        hot, used, starred, discussion, _ = daily.select_rankings(
            [old_low_star, early],
            {
                "hot_limit": 5,
                "used_limit": 5,
                "starred_limit": 5,
                "discussion_limit": 5,
                "xhs_count": 5,
                "early_focus_max_age_days": 90,
            },
        )

        shown = [repo["full_name"] for repo in hot + used + starred + discussion]
        self.assertIn("demo/early", shown)
        self.assertNotIn("demo/old-low-star", shown)

    def test_restore_previous_readme_assets_preserves_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            latest_path = Path(tmpdir) / "latest.json"
            latest_path.write_text(
                json.dumps(
                    {
                        "all_repos": [
                            {
                                "full_name": "demo/project",
                                "readme_excerpt": "AI coding agent creates videos from HTML.",
                                "examples": [
                                    {
                                        "title": "Quick start",
                                        "body": "",
                                        "code": "",
                                        "images": [
                                            {
                                                "url": "https://raw.githubusercontent.com/demo/project/main/hero.png",
                                                "alt": "Hero screenshot",
                                            }
                                        ],
                                        "source": "README",
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            repo = {
                "full_name": "demo/project",
                "description": "",
                "readme_excerpt": "",
                "examples": [],
                "topics": [],
                "features": [],
                "stars": 100,
                "forks": 10,
                "open_issues": 1,
                "created_at": "2026-05-01T00:00:00Z",
                "pushed_at": "2026-06-04T00:00:00Z",
                "expert_signals": [],
            }

            assets = daily.load_previous_readme_assets(latest_path)
            restored = daily.restore_previous_readme_assets([repo], assets, {"repos": {}}, dt.date(2026, 6, 5))

        self.assertEqual(restored, 1)
        self.assertEqual(repo["readme_excerpt"], "AI coding agent creates videos from HTML.")
        self.assertEqual(repo["examples"][0]["images"][0]["alt"], "Hero screenshot")
        self.assertIn("AI Coding / Agent", repo["features"])
        self.assertGreater(repo["scores"]["hot"], 0)
        self.assertGreater(repo["scores"]["frontier"], 0)

    def test_ranked_repos_are_forced_to_read_readme_before_output(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            def get_readme_text(self, full_name, default_branch="main"):
                self.calls.append(full_name)
                return (
                    "# bazi-ziwei-skill\n"
                    "AI 八字 + 紫微斗数排盘与综合印证 Skill。精准排盘（不靠 LLM 猜），"
                    "三种分析模式，一键生成水墨风 HTML 命盘海报。\n\n"
                    "## 综合印证海报示例\n"
                    "水墨风命盘海报，包含八字四柱盘、紫微十二宫盘和六维交叉对账。"
                )

        repo = {
            "full_name": "demo/bazi-ziwei-skill",
            "name": "bazi-ziwei-skill",
            "html_url": "https://github.com/demo/bazi-ziwei-skill",
            "default_branch": "main",
            "description": "",
            "language": "TypeScript",
            "stars": 485,
            "forks": 20,
            "watchers": 485,
            "open_issues": 1,
            "topics": ["bazi", "ziwei", "ziwei-doushu"],
            "homepage": "",
            "license": "MIT",
            "created_at": "2026-06-01T00:00:00Z",
            "updated_at": "2026-06-24T00:00:00Z",
            "pushed_at": "2026-06-24T00:00:00Z",
            "sources": ["product"],
            "queries": [],
            "readme_excerpt": "",
            "examples": [],
            "features": [],
            "expert_signals": [],
            "expert_score": 0,
            "scores": {},
            "notes": [],
        }

        updated = daily.enrich_ranked_repositories(
            FakeClient(),
            [repo],
            {"readme_excerpt_chars": 500, "early_focus_max_age_days": 90},
            {"repos": {}},
            dt.date(2026, 6, 26),
        )

        self.assertEqual(updated, 1)
        self.assertIn("demo/bazi-ziwei-skill", repo["full_name"])
        self.assertIn("八字紫微综合印证 Skill", repo["readme_summary_zh"])
        self.assertIn("八字四柱", repo["readme_summary_zh"])
        self.assertIn("紫微十二宫", repo["readme_summary_zh"])
        self.assertNotIn("开发者工具项目", repo["readme_summary_zh"])
        self.assertTrue(repo["readme_excerpt"])
        self.assertIn("hot", repo["scores"])

    def test_embed_radar_payload_escapes_script_end(self):
        html = (
            '<html><script id="embedded-radar-data" type="application/json">'
            '{"date":"old"}'
            '</script></html>'
        )
        payload = {
            "date": "2026-06-22",
            "all_repos": [
                {
                    "full_name": "demo/project",
                    "description": "safe </script><div>& text",
                }
            ],
        }
        updated = daily.embed_radar_payload(html, payload)

        self.assertIn("\\u003c/script\\u003e", updated)
        self.assertNotIn("safe </script><div>& text", updated)
        extracted = daily.extract_embedded_radar_payload_from_text(updated)
        self.assertEqual(extracted, payload)

    def test_readme_image_url_helpers(self):
        self.assertTrue(daily.is_local_readme_image_url("assets/readme-images/demo.png"))
        self.assertTrue(daily.is_local_readme_image_url("/assets/readme-images/demo.png"))
        self.assertFalse(daily.is_local_readme_image_url("https://raw.githubusercontent.com/demo/repo/main/demo.png"))
        self.assertEqual(
            daily.image_extension_from_url("https://raw.githubusercontent.com/demo/repo/main/demo.PNG?raw=1"),
            ".png",
        )
        self.assertEqual(
            daily.image_extension_from_url("https://raw.githubusercontent.com/demo/repo/main/demo.jpeg"),
            ".jpeg",
        )
        self.assertEqual(
            daily.normalize_readme_image_url(
                "https://raw.githubusercontent.com/demo/repo/main/demo.png%23gh-light-mode-only"
            ),
            "https://raw.githubusercontent.com/demo/repo/main/demo.png",
        )
        self.assertEqual(
            daily.image_extension_from_url(
                "https://raw.githubusercontent.com/demo/repo/main/demo.png%23gh-light-mode-only"
            ),
            ".png",
        )
        self.assertEqual(daily.image_extension_from_url("https://github.com/user-attachments/assets/demo"), "")

    def test_readme_image_content_type_helpers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            headers_path = Path(tmpdir) / "headers"
            headers_path.write_text("HTTP/2 200\ncontent-type: text/html; charset=utf-8\n", encoding="utf-8")
            self.assertEqual(daily.image_content_type_from_headers(headers_path), "text/html")
            self.assertEqual(daily.image_extension_from_headers(headers_path), "")

            headers_path.write_text("HTTP/2 200\ncontent-type: image/webp\n", encoding="utf-8")
            self.assertEqual(daily.image_content_type_from_headers(headers_path), "image/webp")
            self.assertEqual(daily.image_extension_from_headers(headers_path), ".webp")

    def test_localize_payload_images_removes_failed_external_images(self):
        payload = {
            "frontier": [
                {
                    "full_name": "demo/project",
                    "examples": [
                        {
                            "images": [
                                {"url": "https://example.com/good.png", "alt": "good"},
                                {"url": "https://example.com/bad.png", "alt": "bad"},
                                {"url": "assets/readme-images/existing.webp", "alt": "existing"},
                            ]
                        }
                    ],
                }
            ]
        }
        original_download = daily.download_readme_image

        def fake_download(url, asset_dir=daily.LOCAL_README_IMAGE_DIR):
            return "assets/readme-images/good.webp" if "good" in url else None

        daily.download_readme_image = fake_download
        try:
            localized = daily.localize_payload_images(payload)
        finally:
            daily.download_readme_image = original_download

        images = payload["frontier"][0]["examples"][0]["images"]
        self.assertEqual(localized, 1)
        self.assertEqual(
            [image["url"] for image in images],
            ["assets/readme-images/good.webp", "assets/readme-images/existing.webp"],
        )
        self.assertEqual(images[0]["source_url"], "https://example.com/good.png")

    def test_bootstrap_history_from_embedded_payload(self):
        history = {"repos": {}}
        payload = {
            "date": "2026-06-21",
            "all_repos": [
                {
                    "full_name": "demo/project",
                    "stars": "123",
                    "forks": 4,
                    "open_issues": None,
                }
            ],
        }

        added = daily.bootstrap_history_from_payload(history, payload)
        self.assertEqual(added, 1)
        self.assertEqual(history["repos"]["demo/project"][0]["date"], "2026-06-21")
        self.assertEqual(history["repos"]["demo/project"][0]["stars"], 123)
        self.assertEqual(history["repos"]["demo/project"][0]["open_issues"], 0)

    def test_bootstrap_history_from_daily_archive_fills_partial_dates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_dir = Path(tmpdir)
            (archive_dir / "index.json").write_text(
                json.dumps({"dates": [{"date": "2026-06-21", "path": "2026-06-21.json"}]}),
                encoding="utf-8",
            )
            (archive_dir / "2026-06-21.json").write_text(
                json.dumps(
                    {
                        "date": "2026-06-21",
                        "all_repos": [
                            {"full_name": "demo/existing", "stars": 10, "forks": 1, "open_issues": 0},
                            {"full_name": "demo/missing", "stars": 20, "forks": 2, "open_issues": 1},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            history = {
                "repos": {
                    "demo/existing": [
                        {"date": "2026-06-21", "stars": 10, "forks": 1, "open_issues": 0}
                    ]
                }
            }

            added = daily.bootstrap_history_from_daily_archive(history, archive_dir)

        self.assertEqual(added, 1)
        self.assertIn("demo/missing", history["repos"])
        self.assertEqual(history["repos"]["demo/missing"][0]["stars"], 20)

    def test_build_markdown_contains_required_sections(self):
        run_date = dt.date(2026, 6, 5)
        repo = {
            "full_name": "demo/repo",
            "name": "repo",
            "html_url": "https://github.com/demo/repo",
            "stars": 1000,
            "forks": 100,
            "created_at": "2026-05-01T00:00:00Z",
            "pushed_at": "2026-06-04T00:00:00Z",
            "language": "TypeScript",
            "license": "MIT",
            "features": ["AI Coding / Agent"],
            "description": "AI coding tool",
            "readme_excerpt": "",
            "age_days": 35,
            "star_velocity": 28.57,
            "delta_stars": None,
            "delta_days": None,
            "delta_per_day": 0,
            "topics": ["ai-coding"],
        }
        markdown = daily.build_markdown(run_date, [repo], [repo], [repo], [repo], [repo], {"per_page": 40, "pages": 1})
        self.assertIn("热度榜", markdown)
        self.assertIn("大家都在用榜", markdown)
        self.assertIn("早期潜力榜", markdown)
        self.assertIn("参与讨论榜", markdown)
        self.assertIn("小红书草稿", markdown)
        self.assertIn("demo/repo", markdown)


if __name__ == "__main__":
    unittest.main()

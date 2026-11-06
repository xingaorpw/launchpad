"""命令行入口。"""

from __future__ import annotations

import argparse
import sys

from . import awesome, content, platforms
from .github import GitHub, GitHubError


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def _preview(text: str, limit: int = 12) -> None:
    lines = text.splitlines()
    for line in lines[:limit]:
        print(f"    │ {line}")
    if len(lines) > limit:
        print(f"    │ …（共 {len(lines)} 行）")


def _load(args) -> list[content.Project]:
    projects = content.load_all(getattr(args, "content_dir", None))
    if not projects:
        raise SystemExit("content/ 里没有找到任何项目 JSON")
    return projects


def _select(projects: list[content.Project], name: str | None) -> list[content.Project]:
    if not name:
        return projects
    try:
        return [content.find(projects, name)]
    except KeyError as exc:
        raise SystemExit(str(exc)) from None


# ---------------- 子命令 ----------------
def cmd_projects(args) -> int:
    for project in _load(args):
        print(f"  {project.name:<20} {project.repo:<32} {project.tagline}")
    return 0


def cmd_platforms(args) -> int:
    print(f"  {'平台':<12} {'状态':<6} {'缺什么'}")
    print("  " + "-" * 60)
    for name, platform in platforms.PLATFORMS.items():
        missing = platform.missing()
        status = "✓" if not missing else "✗"
        print(f"  {name:<12} {status:<6} {', '.join(missing) or '-'}")
    print()
    print("  只列出有开放发布接口、且不需要付费或人工审核的平台。")
    print("  小红书 / 知乎 / 掘金 / 微博 / Hacker News 没有发布 API，只能手动。")
    return 0


def cmd_plan(args) -> int:
    projects = _select(_load(args), args.project)
    targets = [platforms.get(name) for name in args.platform] if args.platform else list(platforms.PLATFORMS.values())

    for project in projects:
        print(f"\n{project.name}  ·  {project.url}")
        for platform in targets:
            text = platform.text(project)
            kind = "文章" if platform.kind == "article" else "短帖"
            mark = "✓" if platform.configured() else "✗"
            print(f"\n  {mark} {platform.name:<10} [{kind}] {len(text)} 字符")
            _preview(text)
    return 0


def cmd_post(args) -> int:
    projects = _select(_load(args), args.project)
    platform = platforms.get(args.platform)

    if not platform.configured() and not args.dry_run:
        missing = ", ".join(platform.missing())
        print(f"缺少环境变量：{missing}", file=sys.stderr)
        return 2

    failures = 0
    for project in projects:
        result = platform.publish(project, dry_run=args.dry_run)
        if result.ok:
            print(f"  ✓ {project.name:<20} {result.url or '(ok)'}")
        else:
            failures += 1
            print(f"  ✗ {project.name:<20} {result.error}")
    return 1 if failures else 0


def cmd_post_auto(args) -> int:
    """发到所有已配置的平台。CI 里用这个，没配的平台自动跳过。"""
    projects = _select(_load(args), args.project)
    names = platforms.configured_platforms()

    if not names:
        print("没有任何平台配置了凭据。先看 `launchpad platforms`。", file=sys.stderr)
        return 2

    print(f"已配置平台：{', '.join(names)}")
    failures = 0
    for project in projects:
        print(f"\n{project.name}")
        for name in names:
            result = platforms.get(name).publish(project, dry_run=args.dry_run)
            if result.ok:
                print(f"  ✓ {name:<10} {result.url or '(ok)'}")
            else:
                failures += 1
                print(f"  ✗ {name:<10} {result.error}")
    return 1 if failures else 0


def cmd_awesome_scan(args) -> int:
    projects = _select(_load(args), args.project)
    gh = GitHub()

    for project in projects:
        print(f"\n{project.name}  ·  {project.url}")
        results = awesome.scan(gh, project, limit=args.limit)
        listed = [r for r in results if r["listed"]]
        patchable = [r for r in results if not r["listed"] and r["patchable"]]

        print(f"\n  已收录 {len(listed)} 个，可投稿 {len(patchable)} 个")
        for row in patchable[:5]:
            print(f"    {row['repo']}  →  分节「{row['section']}」")
            print(f"      {row['line']}")
    return 0


def cmd_awesome_submit(args) -> int:
    projects = _select(_load(args), args.project)
    gh = GitHub()

    failures = 0
    for project in projects:
        print(f"\n{project.name}  →  {args.list}")
        try:
            result = awesome.submit(gh, args.list, project, dry_run=args.dry_run)
        except GitHubError as exc:
            print(f"  ✗ {exc}")
            failures += 1
            continue

        if result.get("skipped"):
            print(f"  - 跳过：{result['reason']}")
        elif not result.get("ok"):
            print(f"  ✗ {result['reason']}")
            failures += 1
        elif args.dry_run:
            print(f"  ✓ dry-run：会在「{result['section']}」插入")
            print(f"      {result['preview']}")
        else:
            print(f"  ✓ PR：{result['pr']}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="launchpad",
        description="把 GitHub 项目发到各平台，并自动向 awesome-list 投稿",
    )
    parser.add_argument("--content-dir", default=None, help="文案目录，默认 content/")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("projects", help="列出所有项目")
    p.set_defaults(func=cmd_projects)

    p = sub.add_parser("platforms", help="查看各平台配置状态")
    p.set_defaults(func=cmd_platforms)

    p = sub.add_parser("plan", help="预览将要发布的内容（不联网）")
    p.add_argument("--project", default=None)
    p.add_argument("--platform", action="append", default=None)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("post", help="发布到某个平台")
    p.add_argument("--platform", required=True)
    p.add_argument("--project", default=None, help="不填则发布全部项目")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_post)

    p = sub.add_parser("post-auto", help="发到所有已配置的平台（CI 用）")
    p.add_argument("--project", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_post_auto)

    awesome_parser = sub.add_parser("awesome", help="awesome-list 投稿")
    awesome_sub = awesome_parser.add_subparsers(dest="awesome_command", required=True)

    p = awesome_sub.add_parser("scan", help="找候选列表并判断是否已收录")
    p.add_argument("--project", default=None)
    p.add_argument("--limit", type=int, default=8)
    p.set_defaults(func=cmd_awesome_scan)

    p = awesome_sub.add_parser("submit", help="向某个列表开 PR")
    p.add_argument("--list", required=True, help="owner/repo")
    p.add_argument("--project", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_awesome_submit)

    return parser


def main(argv: list[str] | None = None) -> int:
    _utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except GitHubError as exc:
        print(f"GitHub 错误：{exc}", file=sys.stderr)
        return 1


__all__ = ["main", "build_parser"]

"""awesome-list 投稿器。

这是唯一能持续带来自然流量的自动化渠道——比在社交平台刷帖有效得多。
维护者会审你的 PR，所以补丁必须干净：插到正确的分节、按字母序、格式跟邻居一致。
"""

from __future__ import annotations

import re
import time
from typing import Any

from .content import Project
from .github import GitHub, GitHubError

LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+\[([^\]]+)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{2,4})\s+(.*)$")

SEARCH_QUERIES = (
    "awesome {tag} in:name,description stars:>150",
    "awesome {language} in:name stars:>500",
)


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower().removeprefix("https://").removeprefix("http://")


def is_listed(readme: str, repo_url: str) -> bool:
    return normalize_url(repo_url) in normalize_url(readme)


def sections(lines: list[str]) -> list[dict[str, Any]]:
    """把 README 切成二级/三级标题分节。"""
    heads = [(i, line) for i, line in enumerate(lines) if HEADING_RE.match(line)]
    out = []
    for index, (line_no, line) in enumerate(heads):
        end = heads[index + 1][0] if index + 1 < len(heads) else len(lines)
        match = HEADING_RE.match(line)
        out.append({
            "title": match.group(2).strip() if match else "",
            "level": len(match.group(1)) if match else 2,
            "start": line_no,
            "end": end,
        })
    return out


def pick_section(readme: str, keywords: list[str]) -> dict[str, Any] | None:
    """优先找标题命中关键词的分节，其次找条目最多的分节。"""
    lines = readme.splitlines()
    all_sections = sections(lines)
    if not all_sections:
        return None

    lowered = [k.lower() for k in keywords if k]
    for section in all_sections:
        title = section["title"].lower()
        if any(keyword in title for keyword in lowered):
            return section

    def item_count(section: dict[str, Any]) -> int:
        return sum(
            1
            for line in lines[section["start"] + 1:section["end"]]
            if LIST_ITEM_RE.match(line)
        )

    best = max(all_sections, key=item_count)
    return best if item_count(best) > 0 else None


def suggest_patch(readme: str, project: Project) -> dict[str, Any] | None:
    """算出该把新条目插到第几行，返回 {line_index, line, section}。"""
    lines = readme.splitlines()
    section = pick_section(readme, [*project.tags, project.name])
    if section is None:
        return None

    start = section["start"] + 1
    end = section["end"]
    entry = f"- [{project.name}]({project.url}) - {project.tagline}"

    items: list[tuple[int, str]] = []
    for index in range(start, end):
        match = LIST_ITEM_RE.match(lines[index])
        if match:
            items.append((index, match.group(1).strip().lower()))

    target = project.name.lower()
    for index, name in items:
        if name > target:
            return {"line_index": index, "line": entry, "section": section["title"]}

    if items:
        return {"line_index": items[-1][0] + 1, "line": entry, "section": section["title"]}

    # 分节里没有条目：插在标题后第一个非空行之前
    insert_at = start
    while insert_at < end and not lines[insert_at].strip():
        insert_at += 1
    return {"line_index": insert_at, "line": entry, "section": section["title"]}


def apply_patch(readme: str, line_index: int, entry: str) -> str:
    lines = readme.splitlines()
    lines.insert(line_index, entry)
    return "\n".join(lines) + ("\n" if readme.endswith("\n") else "")


def scan(
    gh: GitHub,
    project: Project,
    limit: int = 8,
    sleep: float = 6.5,
    progress=print,
) -> list[dict[str, Any]]:
    """找候选 awesome-list，判断是否已收录，并给出插入位置。"""
    queries = []
    for tag in project.tags[:2]:
        queries.append(SEARCH_QUERIES[0].format(tag=tag, language=""))
    language = (project.tags[0] if project.tags else "")
    queries.append(f"awesome {language} in:name stars:>300")

    seen: set[str] = set()
    found: list[dict[str, Any]] = []

    for query in queries:
        try:
            repos = gh.search_repos(query, per_page=10)
        except GitHubError as exc:
            progress(f"  搜索失败：{exc}")
            continue

        for repo in repos:
            full_name = repo.get("full_name", "")
            if not full_name or full_name in seen:
                continue
            seen.add(full_name)

            try:
                readme, _ = gh.readme(full_name)
            except GitHubError:
                continue

            listed = is_listed(readme, project.url)
            patch = None if listed else suggest_patch(readme, project)
            found.append({
                "repo": full_name,
                "stars": repo.get("stargazers_count", 0),
                "url": repo.get("html_url", ""),
                "listed": listed,
                "section": (patch or {}).get("section"),
                "line": (patch or {}).get("line"),
                "patchable": patch is not None,
            })
            progress(f"  {full_name:<40} ⭐{repo.get('stargazers_count', 0):<7} "
                     f"{'已收录' if listed else ('可投稿' if patch else '找不到合适分节')}")

            if len(found) >= limit:
                return found

        time.sleep(sleep)

    return found


def submit(
    gh: GitHub,
    list_repo: str,
    project: Project,
    dry_run: bool = False,
    progress=print,
) -> dict[str, Any]:
    """fork → 建分支 → 改 README → 开 PR。"""
    readme, readme_sha = gh.readme(list_repo)

    if is_listed(readme, project.url):
        return {"ok": True, "skipped": True, "reason": "已经收录过了", "pr": ""}

    patch = suggest_patch(readme, project)
    if patch is None:
        return {"ok": False, "skipped": False, "reason": "找不到合适的插入位置", "pr": ""}

    new_readme = apply_patch(readme, patch["line_index"], patch["line"])

    if dry_run:
        return {
            "ok": True,
            "skipped": False,
            "reason": "dry-run",
            "pr": "",
            "preview": patch["line"],
            "section": patch["section"],
        }

    me = gh.whoami()
    upstream_branch = gh.stats(list_repo)["default_branch"]
    branch = f"add-{project.name}"

    progress(f"  fork {list_repo} …")
    fork_name = gh.fork(list_repo)
    if not gh.wait_for_fork(fork_name):
        return {"ok": False, "skipped": False, "reason": "fork 超时", "pr": ""}

    base_sha = gh.head_sha(list_repo, upstream_branch)
    try:
        gh.create_branch(fork_name, branch, base_sha)
    except GitHubError as exc:
        if "Reference already exists" not in str(exc):
            return {"ok": False, "skipped": False, "reason": f"建分支失败：{exc}", "pr": ""}

    gh.put_file(
        fork_name, "README.md", new_readme,
        message=f"Add {project.name}",
        branch=branch,
        sha=readme_sha,
    )

    pr = gh.open_pull(
        list_repo,
        title=f"Add {project.name}",
        head=f"{me}:{branch}",
        base=upstream_branch,
        body=(
            f"Adding [{project.name}]({project.url}) — {project.tagline}.\n\n"
            f"{project.problem.split('。')[0]}。\n\n"
            "Happy to adjust formatting or placement if needed."
        ),
    )
    return {"ok": True, "skipped": False, "reason": "", "pr": pr}


__all__ = [
    "is_listed",
    "sections",
    "pick_section",
    "suggest_patch",
    "apply_patch",
    "scan",
    "submit",
    "normalize_url",
]

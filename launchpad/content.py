"""项目文案的单一来源。

每个项目一个 JSON，存结构化字段；各平台的长短文案都由这里渲染出来，
避免同一句话在六个平台各写一遍、改的时候漏掉。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


@dataclass
class Project:
    name: str
    repo: str
    tagline: str
    problem: str
    bullets: list[str] = field(default_factory=list)
    install: str = ""
    example: str = ""
    limits: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}"

    @property
    def title(self) -> str:
        return f"{self.name} — {self.tagline}"


def load(path: str | Path) -> Project:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [k for k in ("name", "repo", "tagline", "problem") if not data.get(k)]
    if missing:
        raise ValueError(f"{path}: 缺少字段 {', '.join(missing)}")
    return Project(
        name=data["name"],
        repo=data["repo"],
        tagline=data["tagline"],
        problem=data["problem"],
        bullets=list(data.get("bullets") or []),
        install=data.get("install", ""),
        example=data.get("example", ""),
        limits=list(data.get("limits") or []),
        tags=list(data.get("tags") or []),
        hashtags=list(data.get("hashtags") or []),
    )


def load_all(directory: str | Path | None = None) -> list[Project]:
    root = Path(directory) if directory else CONTENT_DIR
    return [load(p) for p in sorted(root.glob("*.json"))]


def find(projects: list[Project], name: str) -> Project:
    for project in projects:
        if project.name == name or project.repo == name or project.repo.endswith("/" + name):
            return project
    available = ", ".join(p.name for p in projects)
    raise KeyError(f"找不到项目 {name!r}，可选：{available}")


def _fit(lines: list[str], limit: int) -> str:
    """按行累加，超长就截断——宁可少说一句，也不要被平台拒绝。"""
    out: list[str] = []
    for line in lines:
        candidate = "\n".join(out + [line])
        if len(candidate) > limit:
            break
        out.append(line)
    return "\n".join(out).strip()


def render_short(project: Project, limit: int = 300) -> str:
    """短帖：钩子 + 尽量多的正文 + 链接。

    按句累加正文，直到用掉预算为止——只取第一句信息量太低。
    """
    link = project.url
    tail = " ".join(project.hashtags[:2])
    fixed = len(project.tagline) + len(link) + len(tail) + 6  # 6 = 四个换行 + 余量
    budget = max(0, limit - fixed)

    body = ""
    for sentence in re.split(r"(?<=[。！？.!?])", project.problem):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(body) + len(sentence) > budget:
            break
        body += sentence

    lines = [project.tagline, ""]
    if body:
        lines += [body, ""]
    lines += [link]
    if tail:
        lines.append(tail)
    return _fit(lines, limit)


def render_article(project: Project, stats: dict[str, Any] | None = None) -> str:
    """长文：markdown，给 Dev.to / Hashnode 用。"""
    stats = stats or {}
    lines = [f"> {project.tagline}", "", "---", "", "## 它解决什么问题", "", project.problem, ""]

    if project.bullets:
        lines += ["## 它做什么", ""]
        lines += [f"- {b}" for b in project.bullets]
        lines.append("")

    if project.install:
        lines += ["## 快速开始", "", "```bash", project.install, "```", ""]

    if project.example:
        lines += ["## 真实输出", "", "```", project.example.strip("\n"), "```", ""]

    if project.limits:
        lines += ["## 已知限制", ""]
        lines += [f"- {item}" for item in project.limits]
        lines.append("")
        lines += ["这些不是客套话，是它现在真的做不到的事。", ""]

    if stats.get("stars") is not None:
        lines += [
            "---",
            "",
            f"仓库：[{project.repo}]({project.url}) · "
            f"⭐ {stats.get('stars', 0)} · {stats.get('language') or ''}".rstrip(" ·"),
            "",
        ]
    else:
        lines += ["---", "", f"仓库：[{project.repo}]({project.url})", ""]

    return "\n".join(lines)


def devto_tags(project: Project, limit: int = 4) -> list[str]:
    """Dev.to 要求小写字母数字，最多 4 个。"""
    tags = []
    for tag in project.tags:
        clean = "".join(ch for ch in tag.lower() if ch.isalnum())
        if clean and clean not in tags:
            tags.append(clean)
    return tags[:limit]


__all__ = [
    "Project",
    "load",
    "load_all",
    "find",
    "render_short",
    "render_article",
    "devto_tags",
    "CONTENT_DIR",
]

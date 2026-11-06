"""平台适配器。

只实现有开放发布接口、且不需要付费或人工审核的平台。
每个适配器都支持 dry-run，没配凭据时会明确告诉你缺哪个环境变量。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests

from .content import Project, devto_tags, render_article, render_short

TIMEOUT = 30


@dataclass
class PostResult:
    platform: str
    ok: bool
    url: str = ""
    text: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "ok": self.ok,
            "url": self.url,
            "text": self.text,
            "error": self.error,
        }


class Platform:
    """平台基类。"""

    name = "base"
    env: tuple[str, ...] = ()
    max_len: int = 300
    kind = "short"  # short | article

    def configured(self) -> bool:
        return all(os.environ.get(key) for key in self.env)

    def missing(self) -> list[str]:
        return [key for key in self.env if not os.environ.get(key)]

    def text(self, project: Project) -> str:
        return render_short(project, self.max_len)

    def publish(self, project: Project, dry_run: bool = False) -> PostResult:
        raise NotImplementedError


class DevTo(Platform):
    name = "devto"
    env = ("DEVTO_API_KEY",)
    kind = "article"

    def text(self, project: Project) -> str:
        return render_article(project)

    def publish(self, project: Project, dry_run: bool = False) -> PostResult:
        body = render_article(project)
        if dry_run:
            return PostResult(self.name, True, "(dry-run)", body)

        payload = {
            "article": {
                "title": project.title,
                "published": True,
                "body_markdown": body,
                "tags": devto_tags(project),
            }
        }
        try:
            resp = requests.post(
                "https://dev.to/api/articles",
                json=payload,
                headers={"api-key": os.environ["DEVTO_API_KEY"]},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            return PostResult(self.name, False, error=f"网络错误：{exc}")

        if resp.status_code not in (200, 201):
            return PostResult(self.name, False, error=f"{resp.status_code}: {resp.text[:200]}")
        return PostResult(self.name, True, resp.json().get("url", ""), body)


class Bluesky(Platform):
    name = "bluesky"
    env = ("BSKY_HANDLE", "BSKY_APP_PASSWORD")
    max_len = 300

    @staticmethod
    def _facets(text: str) -> list[dict[str, Any]]:
        """把文本里的链接变成可点击的 facet（按 UTF-8 字节偏移）。"""
        index = text.find("https://")
        if index < 0:
            return []
        end = index
        while end < len(text) and not text[end].isspace():
            end += 1
        uri = text[index:end]
        return [{
            "index": {
                "byteStart": len(text[:index].encode("utf-8")),
                "byteEnd": len(text[:end].encode("utf-8")),
            },
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": uri}],
        }]

    def publish(self, project: Project, dry_run: bool = False) -> PostResult:
        text = render_short(project, self.max_len)
        if dry_run:
            return PostResult(self.name, True, "(dry-run)", text)

        handle = os.environ["BSKY_HANDLE"]
        try:
            session = requests.post(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                json={"identifier": handle, "password": os.environ["BSKY_APP_PASSWORD"]},
                timeout=TIMEOUT,
            )
            if session.status_code != 200:
                return PostResult(self.name, False, error=f"登录失败 {session.status_code}: {session.text[:160]}")
            auth = session.json()

            record = {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "facets": self._facets(text),
                "langs": ["zh"],
            }
            created = requests.post(
                "https://bsky.social/xrpc/com.atproto.repo.createRecord",
                json={
                    "repo": auth["did"],
                    "collection": "app.bsky.feed.post",
                    "record": record,
                },
                headers={"Authorization": f"Bearer {auth['accessJwt']}"},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            return PostResult(self.name, False, error=f"网络错误：{exc}")

        if created.status_code != 200:
            return PostResult(self.name, False, error=f"{created.status_code}: {created.text[:200]}")

        uri = created.json().get("uri", "")
        rkey = uri.rsplit("/", 1)[-1]
        return PostResult(self.name, True, f"https://bsky.app/profile/{handle}/post/{rkey}", text)


class Mastodon(Platform):
    name = "mastodon"
    env = ("MASTODON_BASE_URL", "MASTODON_TOKEN")
    max_len = 500

    def publish(self, project: Project, dry_run: bool = False) -> PostResult:
        text = render_short(project, self.max_len)
        if dry_run:
            return PostResult(self.name, True, "(dry-run)", text)

        base = os.environ["MASTODON_BASE_URL"].rstrip("/")
        try:
            resp = requests.post(
                f"{base}/api/v1/statuses",
                data={"status": text},
                headers={"Authorization": f"Bearer {os.environ['MASTODON_TOKEN']}"},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            return PostResult(self.name, False, error=f"网络错误：{exc}")

        if resp.status_code not in (200, 201):
            return PostResult(self.name, False, error=f"{resp.status_code}: {resp.text[:200]}")
        return PostResult(self.name, True, resp.json().get("url", ""), text)


class Telegram(Platform):
    name = "telegram"
    env = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
    max_len = 4096

    def publish(self, project: Project, dry_run: bool = False) -> PostResult:
        text = render_short(project, self.max_len)
        if dry_run:
            return PostResult(self.name, True, "(dry-run)", text)

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                json={
                    "chat_id": os.environ["TELEGRAM_CHAT_ID"],
                    "text": text,
                    "disable_web_page_preview": False,
                },
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            return PostResult(self.name, False, error=f"网络错误：{exc}")

        if resp.status_code != 200:
            return PostResult(self.name, False, error=f"{resp.status_code}: {resp.text[:200]}")
        message_id = (resp.json().get("result") or {}).get("message_id")
        return PostResult(self.name, True, f"message_id={message_id}", text)


class Discord(Platform):
    name = "discord"
    env = ("DISCORD_WEBHOOK_URL",)
    max_len = 2000

    def publish(self, project: Project, dry_run: bool = False) -> PostResult:
        text = render_short(project, self.max_len)
        if dry_run:
            return PostResult(self.name, True, "(dry-run)", text)

        try:
            resp = requests.post(
                os.environ["DISCORD_WEBHOOK_URL"],
                json={"content": text},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            return PostResult(self.name, False, error=f"网络错误：{exc}")

        if resp.status_code not in (200, 204):
            return PostResult(self.name, False, error=f"{resp.status_code}: {resp.text[:200]}")
        return PostResult(self.name, True, "(webhook 无返回链接)", text)


class Hashnode(Platform):
    name = "hashnode"
    env = ("HASHNODE_TOKEN", "HASHNODE_PUBLICATION_ID")
    kind = "article"

    def text(self, project: Project) -> str:
        return render_article(project)

    def publish(self, project: Project, dry_run: bool = False) -> PostResult:
        body = render_article(project)
        if dry_run:
            return PostResult(self.name, True, "(dry-run)", body)

        query = """
        mutation Publish($input: PublishPostInput!) {
          publishPost(input: $input) { post { url } }
        }
        """
        variables = {
            "input": {
                "title": project.title,
                "publicationId": os.environ["HASHNODE_PUBLICATION_ID"],
                "contentMarkdown": body,
                "tags": [{"name": tag, "slug": tag} for tag in project.tags[:3]],
            }
        }
        try:
            resp = requests.post(
                "https://gql.hashnode.com",
                json={"query": query, "variables": variables},
                headers={"Authorization": os.environ["HASHNODE_TOKEN"]},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            return PostResult(self.name, False, error=f"网络错误：{exc}")

        if resp.status_code != 200:
            return PostResult(self.name, False, error=f"{resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        if data.get("errors"):
            return PostResult(self.name, False, error=str(data["errors"])[:200])
        url = ((data.get("data") or {}).get("publishPost") or {}).get("post", {}).get("url", "")
        return PostResult(self.name, True, url, body)


PLATFORMS: dict[str, Platform] = {
    p.name: p
    for p in (DevTo(), Bluesky(), Mastodon(), Telegram(), Discord(), Hashnode())
}


def get(name: str) -> Platform:
    try:
        return PLATFORMS[name]
    except KeyError:
        raise KeyError(f"未知平台 {name!r}，可选：{', '.join(PLATFORMS)}") from None


def configured_platforms() -> list[str]:
    return [name for name, platform in PLATFORMS.items() if platform.configured()]


__all__ = ["PostResult", "Platform", "PLATFORMS", "get", "configured_platforms"]

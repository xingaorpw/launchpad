"""GitHub API 的最小封装。

只做三件事：读仓库统计、读 README、开 PR。
"""

from __future__ import annotations

import base64
import os
import time
from typing import Any

import requests

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(self, token: str | None = None, session: requests.Session | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "launchpad/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = path if path.startswith("http") else f"{API}{path}"
        resp = self.session.request(
            method, url, headers=self._headers(), timeout=30, **kwargs
        )

        if resp.status_code == 404:
            raise GitHubError(f"404：{path}")
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise GitHubError("触发 GitHub 限流，配置 GITHUB_TOKEN 可提高额度")
        if resp.status_code >= 400:
            raise GitHubError(f"{resp.status_code}：{resp.text[:200]}")
        if resp.status_code == 204:
            return None
        return resp.json()

    # ---- 读 ----
    def stats(self, full_name: str) -> dict[str, Any]:
        data = self.request("GET", f"/repos/{full_name}")
        return {
            "full_name": data.get("full_name"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "language": data.get("language"),
            "description": data.get("description"),
            "topics": data.get("topics") or [],
            "default_branch": data.get("default_branch") or "main",
        }

    def readme(self, full_name: str, ref: str | None = None) -> tuple[str, str]:
        """返回 (readme 文本, blob sha)。"""
        params = {"ref": ref} if ref else None
        data = self.request("GET", f"/repos/{full_name}/readme", params=params)
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        return content, data.get("sha", "")

    def search_repos(self, query: str, per_page: int = 20) -> list[dict[str, Any]]:
        data = self.request(
            "GET", "/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page},
        )
        return data.get("items") or []

    def whoami(self) -> str:
        return self.request("GET", "/user").get("login", "")

    # ---- 写 ----
    def fork(self, full_name: str) -> str:
        data = self.request("POST", f"/repos/{full_name}/forks")
        return data.get("full_name") or full_name

    def wait_for_fork(self, fork_name: str, timeout: float = 90.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.request("GET", f"/repos/{fork_name}")
                return True
            except GitHubError:
                time.sleep(4)
        return False

    def head_sha(self, full_name: str, branch: str) -> str:
        data = self.request("GET", f"/repos/{full_name}/git/ref/heads/{branch}")
        return data["object"]["sha"]

    def create_branch(self, full_name: str, branch: str, from_sha: str) -> None:
        self.request(
            "POST", f"/repos/{full_name}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": from_sha},
        )

    def put_file(
        self,
        full_name: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str,
    ) -> None:
        self.request(
            "PUT", f"/repos/{full_name}/contents/{path}",
            json={
                "message": message,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch,
                "sha": sha,
            },
        )

    def open_pull(
        self,
        full_name: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
    ) -> str:
        data = self.request(
            "POST", f"/repos/{full_name}/pulls",
            json={"title": title, "head": head, "base": base, "body": body},
        )
        return data.get("html_url", "")


__all__ = ["GitHub", "GitHubError", "API"]

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx

from ..base import BaseCheck

logger = logging.getLogger(__name__)


class Check(BaseCheck):
    name = "GitHub Repo Commit Activity"
    comment = "Returns commit count and committers in the past year for each repo"
    depends_on = ["gh_repos"]

    async def run(self) -> dict[str, dict]:
        repos = self.ctx.data["gh_repos"]
        since = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()

        results = {}
        for url in repos:
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) < 2:
                continue
            owner, repo = parts[0], parts[1]

            try:
                total = 0
                committers: dict[str, dict] = {}
                page = 1
                while True:
                    response = await self.ctx.github_get(
                        f"https://api.github.com/repos/{owner}/{repo}/commits"
                        f"?since={since}&per_page=100&page={page}",
                    )
                    commits = response.json()
                    if not commits:
                        break
                    total += len(commits)
                    for commit in commits:
                        info = commit.get("commit", {}).get("author", {})
                        name = info.get("name", "")
                        email = info.get("email", "")
                        login = (commit.get("author") or {}).get("login", "")
                        if email and email not in committers:
                            committers[email] = {"name": name, "login": login}
                    page += 1
                results[url] = {
                    "commit_count": total,
                    "committers": [
                        {"name": c["name"], "email": email, "login": c["login"]}
                        for email, c in committers.items()
                    ],
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"{owner}/{repo}: {e}")
                results[url] = {"commit_count": -1, "committers": []}

        return results

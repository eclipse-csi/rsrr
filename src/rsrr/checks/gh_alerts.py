from typing import Any

from ..base import BaseCheck


class Check(BaseCheck):
    name = "GitHub Dependabot Alerts"
    comment = "Fetches all Dependabot alerts for a GitHub repo"

    async def run(self) -> list[dict[str, Any]]:
        if not self.ctx.gh_repo:
            raise ValueError("--gh-repo is required for this check")

        owner, repo = self.ctx.gh_repo.split("/", 1)
        alerts: list[dict[str, Any]] = []
        url = (
            f"https://api.github.com/repos/{owner}/{repo}"
            f"/dependabot/alerts?per_page=100"
        )

        while url:
            response = await self.ctx.github_get(url)
            alerts.extend(response.json())
            url = response.links.get("next", {}).get("url")

        return [
            {
                "html_url": a["html_url"],
                "state": a["state"],
                "created_at": a["created_at"],
            }
            for a in alerts
        ]

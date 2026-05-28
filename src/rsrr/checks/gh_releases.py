from collections import Counter
from typing import Any

from ..base import BaseCheck


class Check(BaseCheck):
    name = "GitHub Releases"
    comment = "Fetches all releases and counts releases per year"

    async def run(self) -> dict[str, Any]:
        if not self.ctx.gh_repo:
            raise ValueError("--gh-repo is required for this check")

        owner, repo = self.ctx.gh_repo.split("/", 1)
        releases: list[dict[str, Any]] = []
        url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=100"

        while url:
            response = await self.ctx.github_get(url)
            releases.extend(response.json())
            url = response.links.get("next", {}).get("url")

        year_counts: Counter[str] = Counter()
        for release in releases:
            published = release.get("published_at") or release.get("created_at", "")
            if published:
                year_counts[published[:4]] += 1

        return {
            "releases": [
                {
                    "html_url": r["html_url"],
                    "published_at": r["published_at"],
                }
                for r in releases
            ],
            "releases_per_year": dict(sorted(year_counts.items())),
        }

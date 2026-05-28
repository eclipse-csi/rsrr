import logging
from urllib.parse import urlparse

import httpx

from ..base import BaseCheck

logger = logging.getLogger(__name__)


class Check(BaseCheck):
    name = "GitHub Default Security Policy"
    comment = "Checks if each GitHub organization has a default SECURITY.md in its .github repo"
    depends_on = ["gh_repos"]

    async def run(self) -> dict[str, bool]:
        repos = self.ctx.data["gh_repos"]

        # Extract unique orgs from repo URLs
        orgs: set[str] = set()
        for url in repos:
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) >= 2:
                orgs.add(parts[0])

        results = {}
        for org in sorted(orgs):
            try:
                await self.ctx.github_get(
                    f"https://api.github.com/repos/{org}/.github/contents/SECURITY.md",
                )
                results[org] = True
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    results[org] = False
                else:
                    raise

        return results

import logging

from ..base import BaseCheck

logger = logging.getLogger(__name__)


class Check(BaseCheck):
    name = "GitHub Repos"
    comment = "List all GitHub repos for the project"
    depends_on = ["ef_project"]

    async def run(self) -> list[str]:
        project = self.ctx.data["ef_project"]
        ignored = set(project.get("github", {}).get("ignored_repos", []))

        # Collect explicitly listed repos
        repos: dict[str, None] = {}
        for entry in project.get("github_repos", []):
            url = entry.get("url", "").rstrip("/")
            if url:
                repos[url] = None

        # Query GitHub org for all public repos
        org = project.get("github", {}).get("org", "")
        if org:
            page = 1
            while True:
                response = await self.ctx.github_get(
                    f"https://api.github.com/orgs/{org}/repos"
                    f"?type=public&per_page=100&page={page}",
                )
                org_repos = response.json()
                if not org_repos:
                    break
                for repo in org_repos:
                    url = repo.get("html_url", "").rstrip("/")
                    if url:
                        repos[url] = None
                page += 1

        # Filter out ignored repos
        result = []
        for url in repos:
            repo_name = url.rsplit("/", 1)[-1]
            if repo_name in ignored:
                logger.info(f"Ignoring repo: {url}")
                continue
            result.append(url)

        return result

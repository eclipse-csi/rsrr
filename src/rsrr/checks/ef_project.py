import httpx
from typing import Any

from ..base import BaseCheck


class Check(BaseCheck):
    name = "EF Project"
    comment = "Get EF project API results"

    async def run(self) -> Any:
        if not self.ctx.ef_project_id_normalized:
            raise ValueError("EF project ID required (--ef-project-id)")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://projects.eclipse.org/api/projects/{self.ctx.ef_project_id_normalized}",
            )
        response.raise_for_status()
        project = response.json()[0]

        return {
            "committers": project["committers"],
            "github": project["github"],
            "github_repos": project["github_repos"],
        }

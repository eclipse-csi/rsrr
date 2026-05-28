from typing import Any
from urllib.parse import quote

import httpx

from ..base import BaseCheck

GL_API_BASE = "https://gitlab.eclipse.org/api/v4"
GL_PROJECT = "eclipsefdn/security/vulnerabilities"


class Check(BaseCheck):
    name = "EF CVEs"
    comment = (
        "Returns advisories from the EF vulnerabilities repo matching the project ID"
    )

    async def run(self) -> list[dict[str, Any]]:
        if not self.ctx.ef_project_id:
            raise ValueError("--ef-project-id is required for this check")

        headers: dict[str, str] = {}
        if self.ctx.gl_token:
            headers["PRIVATE-TOKEN"] = self.ctx.gl_token

        encoded_project = quote(GL_PROJECT, safe="")
        encoded_file = quote("advisories.json", safe="")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GL_API_BASE}/projects/{encoded_project}/repository/files/{encoded_file}/raw",
                params={"ref": "main"},
                headers=headers,
            )
        response.raise_for_status()

        advisories: list[dict[str, Any]] = response.json()
        return [a for a in advisories if a.get("project") == self.ctx.ef_project_id]

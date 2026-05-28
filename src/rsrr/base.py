from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class Context:
    ef_project_id: str | None = None
    gh_repo: str | None = None
    gh_token: str | None = None
    gl_token: str | None = None
    gl_vuln_kw: tuple[str, ...] = ()
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ef_project_id_normalized(self) -> str | None:
        if self.ef_project_id is None:
            return None
        return self.ef_project_id.replace(".", "_")

    async def github_get(self, url: str) -> httpx.Response:
        """Send an authenticated GET request to the GitHub API."""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.gh_token:
            headers["Authorization"] = f"Bearer {self.gh_token}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response


class BaseCheck(ABC):
    """Base class for all checks."""

    name: str
    comment: str
    depends_on: list[str] = []

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    @abstractmethod
    async def run(self) -> Any: ...

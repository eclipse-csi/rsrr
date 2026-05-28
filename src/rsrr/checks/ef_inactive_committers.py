import logging

from ..base import BaseCheck

logger = logging.getLogger(__name__)


class Check(BaseCheck):
    name = "EF Inactive Committers"
    comment = "Lists EF committers whose GitHub handle has no commits in the past year"
    depends_on = ["ef_committers", "gh_repo_commit_activity"]

    async def run(self) -> list[dict]:
        committers = self.ctx.data["ef_committers"]
        activity = self.ctx.data["gh_repo_commit_activity"]

        # Collect all GitHub logins that have committed in the past year
        active_logins: set[str] = set()
        for repo_data in activity.values():
            if not isinstance(repo_data, dict):
                continue
            for committer in repo_data.get("committers", []):
                login = committer.get("login", "")
                if login:
                    active_logins.add(login.lower())

        inactive = []
        for committer in committers:
            first_name = committer.get("first_name", "")
            last_name = committer.get("last_name", "")
            handle = committer.get("github_handle", "")

            if not handle:
                logger.warning(
                    f"EF committer {first_name} {last_name} has no GitHub handle"
                )
                inactive.append(
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "github_handle": "",
                        "reason": "no_github_handle",
                    }
                )
                continue

            if handle.lower() not in active_logins:
                inactive.append(
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "github_handle": handle,
                        "reason": "no_recent_commits",
                    }
                )

        return inactive

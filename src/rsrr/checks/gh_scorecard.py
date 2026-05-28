import asyncio
import os

from ..base import BaseCheck


class Check(BaseCheck):
    name = "OpenSSF Scorecard"
    comment = "Runs OpenSSF Scorecard against a GitHub repo"

    async def run(self) -> str:
        if not self.ctx.gh_repo or not self.ctx.gh_token:
            raise ValueError("--gh-repo and --gh-token are required for this check")

        env = os.environ.copy()
        env["GITHUB_AUTH_TOKEN"] = self.ctx.gh_token

        proc = await asyncio.create_subprocess_exec(
            "scorecard",
            f"--repo=github.com/{self.ctx.gh_repo}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"scorecard failed: {stderr.decode().strip()}")

        return stdout.strip().decode().splitlines()

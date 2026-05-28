import asyncio
import os
from typing import Any

from ..base import BaseCheck


class Check(BaseCheck):
    name = "Zizmor"
    comment = "Runs zizmor GitHub Actions security audit on a GitHub repo"

    async def run(self) -> list[dict[str, Any]]:
        if not self.ctx.gh_repo or not self.ctx.gh_token:
            raise ValueError("--gh-repo and --gh-token are required for this check")

        env = os.environ.copy()
        env["GH_TOKEN"] = self.ctx.gh_token

        proc = await asyncio.create_subprocess_exec(
            "zizmor",
            self.ctx.gh_repo,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate()

        # See https://docs.zizmor.sh/usage/#exit-codes
        if proc.returncode > 0 and proc.returncode < 11:
            raise RuntimeError(f"zizmor failed: {stderr.decode().strip()}")

        return stdout.strip().decode().splitlines()

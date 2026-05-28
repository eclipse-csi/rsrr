import asyncio
import tempfile

from ..base import BaseCheck


class Check(BaseCheck):
    name = "GitHub Repo Clone"
    comment = "Clones the GitHub repo into a temporary directory"

    async def run(self) -> str:
        if not self.ctx.gh_repo:
            raise ValueError("--gh-repo is required for this check")

        tmp_dir = tempfile.mkdtemp(prefix="rsrr-clone-")
        url = f"https://github.com/{self.ctx.gh_repo}.git"

        proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            "1",
            url,
            tmp_dir,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode().strip()}")

        return tmp_dir

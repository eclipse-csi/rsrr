import asyncio
import sys
import logging
import json
from pathlib import Path

import click

from .checks import Context
from .runner import discover_checks, run_checks

logger = logging.getLogger(__name__)


def get_all_checks() -> dict:
    """Discover and return all available checks."""
    checks_dir = Path(__file__).parent / "checks"
    return discover_checks(checks_dir)


@click.group(invoke_without_command=True)
@click.option("-v", "--verbose", is_flag=True, help="Enable info logging")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Rapid Security Review Runner -- Runs an extensible set of checks for
    Eclipse Foundation Rapid Security Reviews."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    pkg_logger = logging.getLogger("rsrr")
    pkg_logger.handlers.clear()
    pkg_logger.addHandler(handler)
    pkg_logger.setLevel(logging.INFO if verbose else logging.WARNING)
    pkg_logger.propagate = False

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command("list")
def list_cmd() -> None:
    """List available checks."""
    all_checks = get_all_checks()
    click.echo("Available checks:\n")
    for check_id, check_cls in sorted(all_checks.items()):
        click.echo(f"  {check_id}")
        click.echo(f"    {check_cls.name}: {check_cls.comment}")
        click.echo()


@main.command()
@click.argument("checks", nargs=-1, metavar="CHECK")
@click.option(
    "--ef-project-id",
    default=None,
    help="Eclipse Foundation project ID",
)
@click.option(
    "--gh-repo",
    default=None,
    help="GitHub repository in owner/repo format",
)
@click.option(
    "--gh-token",
    envvar="GH_TOKEN",
    default=None,
    help="GitHub API token (or set GH_TOKEN env var)",
)
@click.option(
    "--gl-token",
    envvar="GL_TOKEN",
    default=None,
    help="GitLab API token (or set GL_TOKEN env var)",
)
@click.option(
    "--gl-vuln-kw",
    multiple=True,
    help="Keywords to search in GitLab vulnerability reports (repeatable)",
)
@click.option(
    "--ctx-data",
    type=click.Path(dir_okay=False),
    default=None,
    help="JSON file to read/write context data (results are merged back into this file)",
)
def run(
    checks: tuple[str, ...],
    ef_project_id: str | None,
    gh_repo: str | None,
    gh_token: str | None,
    gl_token: str | None,
    gl_vuln_kw: tuple[str, ...],
    ctx_data: str | None,
) -> None:
    """Run checks.

    If CHECK arguments are provided, only those checks are run.
    Otherwise, all available checks are run.

    When --ctx-data is given, existing results are loaded from the file and
    checks with entries already present are skipped. After running, all
    results (old and new) are written back to the same file.
    """
    data = {}
    if ctx_data is not None and Path(ctx_data).exists():
        try:
            with open(ctx_data) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            click.echo(f"Invalid JSON in {ctx_data}: {e}", err=True)
            sys.exit(1)
        if not isinstance(data, dict):
            click.echo("--ctx-data file must contain a JSON object", err=True)
            sys.exit(1)
    ctx = Context(
        ef_project_id=ef_project_id,
        gh_repo=gh_repo,
        gh_token=gh_token,
        gl_token=gl_token,
        gl_vuln_kw=gl_vuln_kw,
        data=data,
    )
    sys.exit(asyncio.run(run_async(checks, ctx, ctx_data)))


async def run_async(
    checks: tuple[str, ...], ctx: Context, ctx_data_path: str | None
) -> int:
    all_checks = get_all_checks()

    # Filter checks if specific ones requested
    if checks:
        unknown = set(checks) - set(all_checks.keys())
        if unknown:
            click.echo(f"Unknown checks: {', '.join(sorted(unknown))}", err=True)
            click.echo("Use 'rsrr list' to see available checks", err=True)
            return 1
        checks_to_run = {k: v for k, v in all_checks.items() if k in checks}
    else:
        checks_to_run = all_checks

    if not checks_to_run:
        click.echo("No checks to run", err=True)
        return 1

    try:
        await run_checks(checks_to_run, ctx)
    except ValueError as e:
        logger.error(e)

    if ctx_data_path is not None:
        with open(ctx_data_path, "w") as f:
            json.dump(ctx.data, f, indent=2)
            f.write("\n")
    else:
        click.echo(json.dumps(ctx.data, indent=2))

    return 0


if __name__ == "__main__":
    main()

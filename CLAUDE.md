# rsrr - Rapid Security Review Runner

CLI tool for running automated checks for Eclipse Foundation Rapid Security Reviews.

## Architecture

```
src/rsrr/
  base.py            # BaseCheck ABC + Context dataclass
  checks/
    ef_project.py    # Example: fetch EF project API data
    <check_name>.py  # One file per check, each exports Check(BaseCheck)
  cli.py             # Click CLI: `rsrr list` and `rsrr run`
  runner.py          # Discovers checks, runs them in dependency waves (asyncio)
tests/
  test_base.py       # Context helper tests (e.g. github_get)
  test_cli.py        # CLI integration tests (Click CliRunner, mocked checks)
  test_runner.py     # Runner unit tests (discover, run, dependencies)
```

**Check discovery**: `runner.py` auto-discovers every `.py` file in `checks/` (except `base.py` and `__init__.py`) that exports `class Check(BaseCheck)`. The module filename (without `.py`) becomes the `check_id`.

**Dependency resolution**: Checks with `depends_on = ["other_check_id"]` run after their dependencies complete. Independent checks run in parallel via `asyncio.gather`. Results are stored in `ctx.data[check_id]`.

## Adding a Check

Create `src/rsrr/checks/<check_name>.py`:

```python
from ..base import BaseCheck

class Check(BaseCheck):
    name = "Human-readable name"
    comment = "One-line description"
    depends_on = ["ef_project"]  # optional, list of check_id strings

    async def run(self) -> Any:
        # Access dependency results via self.ctx.data["ef_project"]
        # Access project ID via self.ctx.ef_project_id
        return result  # stored in ctx.data["<check_name>"]
```

## Key Patterns

- Use `httpx.AsyncClient` for all HTTP calls (project uses httpx)
- For GitHub API requests, prefer `await self.ctx.github_get(url)` — it sets the
  `Accept: application/vnd.github.v3+json` header and an `Authorization: Bearer <token>`
  header when `ctx.gh_token` is set, and raises on non-2xx responses
- `ctx.ef_project_id_normalized` replaces `.` with `_` (required for the EF project API URL,
  e.g. `rt.ecf` → `rt_ecf`)
- EF project API: `https://projects.eclipse.org/api/projects/{ef_project_id_normalized}`
- EF project result is a list; `result[0]["github"]["org"]` gives the GitHub org name

## Commands

```bash
uv run rsrr list              # list all available checks
uv run rsrr run --ef-project-id technology.csi  # run all checks (JSON to stdout)
uv run rsrr run --ef-project-id technology.csi ef_project gh_default_security_policy  # run specific checks
uv run rsrr run --ef-project-id technology.csi --ctx-data result.json  # incremental: skip checks already in result.json, merge new results back
uv run rsrr run -v --ef-project-id technology.csi  # -v enables INFO logging on the rsrr package

just lint        # ruff check + format check
just lint-fix    # ruff check --fix + format

uv run pytest tests/           # run all tests
uv run pytest tests/ -v        # run tests with verbose output
```

## Project Setup

- **Package manager**: `uv` (lockfile: `uv.lock`)
- **Linter/formatter**: `ruff` (via `uvx`)
- **Task runner**: `just` (see `justfile`)
- **Python**: 3.13+
- **Key deps**: `click`, `httpx`
- **Test deps** (dev): `pytest`, `pytest-asyncio`

## Testing

Tests cover `cli.py`, `runner.py`, and `base.py` — not individual check implementations.

- **CLI tests** (`tests/test_cli.py`): use `click.testing.CliRunner` with `unittest.mock.patch` on `get_all_checks` to inject fake check classes. No network calls.
- **Runner tests** (`tests/test_runner.py`): use simple `BaseCheck` subclasses defined inline. `test_discover_checks` writes temp modules to `tmp_path` and runs real discovery.
- **Base tests** (`tests/test_base.py`): exercise `Context.github_get` with `httpx.AsyncClient` mocked, asserting headers (incl. `Authorization` when `gh_token` is set).
- Async tests use `@pytest.mark.asyncio` (requires `pytest-asyncio`; asyncio mode configured as `strict` in `pyproject.toml`).

## Sandbox / CI Environment

This project is developed on macOS but Claude Code runs in a Docker (Linux) sandbox.
The `.venv/` in the project root belongs to the host — **do not touch it from the sandbox**.

In the sandbox, use a separate venv via `UV_PROJECT_ENVIRONMENT`:

```bash
uv venv /tmp/rsrr-venv --python 3.13
export UV_PROJECT_ENVIRONMENT=/tmp/rsrr-venv
uv sync
uv run pytest tests/ -v   # uses /tmp/rsrr-venv
uv run rsrr list           # uses /tmp/rsrr-venv
```

Set `UV_PROJECT_ENVIRONMENT` before any `uv run`/`uv sync` command.

## Directory Notes

- `.venv/` — host-managed by uv, do not modify from sandbox/CI

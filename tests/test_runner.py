import sys
import textwrap
import types
from pathlib import Path
from typing import Any

import pytest

from rsrr.base import BaseCheck, Context
from rsrr.runner import discover_checks, run_check, run_checks


# -- Fake checks used as fixtures --


class PassingCheck(BaseCheck):
    name = "Passing"
    comment = "Always succeeds"

    async def run(self) -> Any:
        return {"ok": True}


class FailingCheck(BaseCheck):
    name = "Failing"
    comment = "Always raises"

    async def run(self) -> Any:
        raise RuntimeError("boom")


class DependentCheck(BaseCheck):
    name = "Dependent"
    comment = "Depends on passing"
    depends_on = ["passing"]

    async def run(self) -> Any:
        return {"upstream": self.ctx.data["passing"]}


class CircularA(BaseCheck):
    name = "CircularA"
    comment = ""
    depends_on = ["circular_b"]

    async def run(self) -> Any:
        return None


class CircularB(BaseCheck):
    name = "CircularB"
    comment = ""
    depends_on = ["circular_a"]

    async def run(self) -> Any:
        return None


# -- discover_checks --


def test_discover_checks(tmp_path: Path):
    """Valid check modules are discovered; non-check modules are skipped."""
    # Valid check module
    (tmp_path / "good_check.py").write_text(
        textwrap.dedent("""\
            from rsrr.base import BaseCheck
            class Check(BaseCheck):
                name = "Good"
                comment = "A good check"
                async def run(self):
                    return True
        """)
    )
    # Module without a Check class — should be skipped
    (tmp_path / "no_check.py").write_text("x = 1\n")
    # __init__.py and base.py — should be skipped
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "base.py").write_text("")

    # Register a fake parent package so importlib.import_module can resolve
    # relative imports against it.
    pkg_name = "test_discover_checks"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(tmp_path)]
    pkg.__package__ = pkg_name
    sys.modules[pkg_name] = pkg
    try:
        checks = discover_checks(tmp_path, package=pkg_name)
    finally:
        # Clean up sys.modules
        to_remove = [k for k in sys.modules if k.startswith(pkg_name)]
        for k in to_remove:
            del sys.modules[k]

    assert "good_check" in checks
    assert "no_check" not in checks
    assert "__init__" not in checks
    assert "base" not in checks


# -- run_check --


@pytest.mark.asyncio
async def test_run_check_stores_result():
    ctx = Context()
    assert await run_check("passing", PassingCheck, ctx) is True
    assert ctx.data["passing"] == {"ok": True}


@pytest.mark.asyncio
async def test_run_check_exception_handled():
    """A failing check should not propagate the exception."""
    ctx = Context()
    assert await run_check("failing", FailingCheck, ctx) is False
    assert "failing" not in ctx.data


# -- run_checks --


@pytest.mark.asyncio
async def test_run_checks_respects_dependencies():
    """DependentCheck runs after PassingCheck and can read its result."""
    checks = {
        "passing": PassingCheck,
        "dependent": DependentCheck,
    }
    ctx = Context()
    await run_checks(checks, ctx)

    assert ctx.data["passing"] == {"ok": True}
    assert ctx.data["dependent"] == {"upstream": {"ok": True}}


@pytest.mark.asyncio
async def test_run_checks_parallel_wave():
    """Independent checks run in the same wave (both complete)."""
    order = []

    class A(BaseCheck):
        name = "A"
        comment = ""

        async def run(self) -> Any:
            order.append("a")
            return "a"

    class B(BaseCheck):
        name = "B"
        comment = ""

        async def run(self) -> Any:
            order.append("b")
            return "b"

    ctx = Context()
    await run_checks({"a": A, "b": B}, ctx)

    assert set(order) == {"a", "b"}
    assert ctx.data["a"] == "a"
    assert ctx.data["b"] == "b"


@pytest.mark.asyncio
async def test_run_checks_skips_dependent_on_failure():
    """If a check fails, checks that depend on it are skipped."""

    class DependsOnFailing(BaseCheck):
        name = "DependsOnFailing"
        comment = ""
        depends_on = ["failing"]

        async def run(self) -> Any:
            return "should not run"

    ctx = Context()
    await run_checks(
        {"failing": FailingCheck, "depends_on_failing": DependsOnFailing}, ctx
    )

    assert "failing" not in ctx.data
    assert "depends_on_failing" not in ctx.data


@pytest.mark.asyncio
async def test_run_checks_skips_transitive_dependents():
    """Transitive dependents of a failed check are also skipped."""

    class Middle(BaseCheck):
        name = "Middle"
        comment = ""
        depends_on = ["failing"]

        async def run(self) -> Any:
            return "middle"

    class Leaf(BaseCheck):
        name = "Leaf"
        comment = ""
        depends_on = ["middle"]

        async def run(self) -> Any:
            return "leaf"

    ctx = Context()
    await run_checks({"failing": FailingCheck, "middle": Middle, "leaf": Leaf}, ctx)

    assert "failing" not in ctx.data
    assert "middle" not in ctx.data
    assert "leaf" not in ctx.data


@pytest.mark.asyncio
async def test_run_checks_independent_check_unaffected_by_failure():
    """A check with no dependency on the failed check still runs."""
    ctx = Context()
    await run_checks({"failing": FailingCheck, "passing": PassingCheck}, ctx)

    assert "failing" not in ctx.data
    assert ctx.data["passing"] == {"ok": True}


@pytest.mark.asyncio
async def test_run_checks_circular_dependency():
    checks = {
        "circular_a": CircularA,
        "circular_b": CircularB,
    }
    ctx = Context()
    with pytest.raises(ValueError, match="Circular or unsatisfied"):
        await run_checks(checks, ctx)


@pytest.mark.asyncio
async def test_run_checks_skips_preexisting_data():
    """Checks with pre-populated ctx.data are skipped."""
    ctx = Context(data={"passing": "cached"})
    await run_checks({"passing": PassingCheck}, ctx)
    assert ctx.data["passing"] == "cached"


@pytest.mark.asyncio
async def test_run_checks_preexisting_data_satisfies_dependency():
    """Pre-populated data counts as completed for dependency resolution."""
    ctx = Context(data={"passing": {"ok": True}})
    await run_checks({"passing": PassingCheck, "dependent": DependentCheck}, ctx)

    assert ctx.data["passing"] == {"ok": True}
    assert ctx.data["dependent"] == {"upstream": {"ok": True}}


@pytest.mark.asyncio
async def test_run_checks_empty():
    """Running with no checks completes immediately."""
    ctx = Context()
    await run_checks({}, ctx)
    assert ctx.data == {}

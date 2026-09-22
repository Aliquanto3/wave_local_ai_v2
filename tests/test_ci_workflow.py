"""Structural assertions on `.github/workflows/ci.yml`.

Parsed as YAML rather than grepped, so a reformatting of the file (key order,
quoting style) cannot fool these tests -- only the actual job/step/`needs`
structure they check.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

WORKFLOW_PATH = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
PYPROJECT_PATH = Path(__file__).parent.parent / "pyproject.toml"
# actions/checkout@v4 stays readable as a comment naming the version, but the
# pinned ref itself must be the 40-hex commit sha a tag could otherwise move.
PINNED_USES_RE = re.compile(r"^[^/]+/[^@]+@[0-9a-f]{40}$")


def _load_workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _step_names(job: dict[str, Any]) -> list[str]:
    """Every step's `name` (if any) or its `run`/`uses` command, in order."""
    names = []
    for step in job["steps"]:
        names.append(str(step.get("name") or step.get("run") or step.get("uses")))
    return names


def _every_uses(workflow: dict[str, Any]) -> list[str]:
    uses = []
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if "uses" in step:
                uses.append(step["uses"])
    return uses


def test_a_frontend_job_exists_with_the_stories_own_steps() -> None:
    workflow = _load_workflow()

    assert "frontend" in workflow["jobs"], "no 'frontend' job in ci.yml"
    job = workflow["jobs"]["frontend"]
    assert job["runs-on"] == "ubuntu-latest"

    step_text = " ".join(_step_names(job)).lower()
    for expected in [
        "checkout",
        "setup-node",
        "npm ci",
        "lint",
        "format",
        "type check",
        "test",
    ]:
        assert expected in step_text, (
            f"no step matching {expected!r} found: {step_text}"
        )


def test_the_frontend_setup_node_step_reads_the_committed_nvmrc() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["frontend"]

    setup_node_steps = [
        step for step in job["steps"] if "setup-node" in step.get("uses", "")
    ]
    assert len(setup_node_steps) == 1, "expected exactly one setup-node step"
    assert setup_node_steps[0]["with"]["node-version-file"] == "frontend/.nvmrc"


def test_the_frontend_tests_step_asks_for_coverage() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["frontend"]

    runs = " ".join(step["run"] for step in job["steps"] if step.get("run"))
    assert "--coverage" in runs


def test_the_pytest_gate_measures_branch_coverage() -> None:
    # CI runs bare `uv run pytest`, so the gate's coverage flags live in
    # pyproject's addopts: metric code is mostly early-return branches, which
    # line coverage alone counts as covered once the guard line runs.
    workflow = _load_workflow()
    runs = [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "pytest" in step.get("run", "")
    ]
    assert runs == ["uv run pytest"], runs

    pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    addopts = pyproject["tool"]["pytest"]["ini_options"]["addopts"].split()
    assert "--cov-branch" in addopts
    assert any(opt.startswith("--cov-fail-under=") for opt in addopts)


def test_frontend_is_wired_into_required() -> None:
    workflow = _load_workflow()

    required = workflow["jobs"]["required"]
    assert "frontend" in required["needs"]

    check_step = next(
        step
        for step in required["steps"]
        if "frontend" in step.get("run", "") or "frontend" in step.get("name", "")
    )
    assert "needs.frontend.result" in check_step["run"]


def test_every_uses_across_the_whole_file_is_sha_pinned() -> None:
    workflow = _load_workflow()

    unpinned = [
        uses for uses in _every_uses(workflow) if not PINNED_USES_RE.match(uses)
    ]
    assert unpinned == [], f"unpinned action reference(s): {unpinned}"

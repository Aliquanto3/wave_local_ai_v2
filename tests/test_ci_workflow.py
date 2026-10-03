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


def test_the_test_job_checks_the_bundle_is_derived() -> None:
    # The step's command is the one tests/test_bundle_merge.py proves fails a
    # hand-edited bundle; asserting it here keeps the two from drifting apart.
    workflow = _load_workflow()
    runs = [step.get("run", "") for step in workflow["jobs"]["test"]["steps"]]
    assert "uv run wave-local-ai-v2-merge-bundle --check" in runs


def test_the_release_job_runs_on_a_tag_after_test_build_and_verify_tag() -> None:
    job = _load_workflow()["jobs"]["release"]

    assert job["if"] == "startsWith(github.ref, 'refs/tags/v')"
    assert sorted(job["needs"]) == ["build", "test", "verify-tag"]


def test_only_the_release_job_may_write_contents() -> None:
    workflow = _load_workflow()

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["release"]["permissions"] == {"contents": "write"}
    writers = [
        name
        for name, job in workflow["jobs"].items()
        if job.get("permissions", {}).get("contents") == "write"
    ]
    assert writers == ["release"]


def test_publish_and_verify_tag_are_unchanged_by_the_release_job() -> None:
    jobs = _load_workflow()["jobs"]

    assert jobs["publish"]["needs"] == ["test", "build", "verify-tag"]
    assert jobs["publish"]["permissions"] == {
        "contents": "read",
        "packages": "write",
    }
    assert jobs["verify-tag"]["permissions"] == {"contents": "read"}


def test_the_release_is_created_only_after_the_archive_verifies() -> None:
    steps = _load_workflow()["jobs"]["release"]["steps"]
    runs = [" ".join(str(step.get("run", "")).split()) for step in steps]

    assemble = next(
        i
        for i, run in enumerate(runs)
        if "scripts/assemble_release_archive.py build" in run
    )
    create = next(i for i, run in enumerate(runs) if "gh release create" in run)
    assert assemble < create
    assert '--tag "$GITHUB_REF_NAME" --commit "$GITHUB_SHA"' in runs[assemble]
    assert "--verify-tag" in runs[create]
    assert '"dist/wave-local-ai-v2-${GITHUB_REF_NAME#v}.zip"' in runs[create]


def test_the_release_job_keeps_its_write_token_out_of_the_checkout() -> None:
    # `uv sync`/`uv run` execute dependency code; the write-scoped token must
    # not sit in .git/config meanwhile, and no shared cache feeds the job.
    steps = _load_workflow()["jobs"]["release"]["steps"]
    checkout = next(s for s in steps if "actions/checkout" in s.get("uses", ""))
    assert checkout["with"]["persist-credentials"] is False
    setup_uv = next(s for s in steps if "setup-uv" in s.get("uses", ""))
    assert "enable-cache" not in setup_uv.get("with", {})

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
DOCKERFILE_PATH = Path(__file__).parent.parent / "Dockerfile"
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
    # release-build's one other pytest run is the Parquet check's own
    # tests, where pyarrow is installed; it is not the coverage gate.
    workflow = _load_workflow()
    runs = {
        name: [
            step["run"]
            for step in job.get("steps", [])
            if "pytest" in step.get("run", "")
        ]
        for name, job in workflow["jobs"].items()
    }
    assert runs.pop("release-build") == [
        "uv run --group release pytest tests/test_release_parquet.py --no-cov"
    ]
    assert [run for job_runs in runs.values() for run in job_runs] == [
        "uv run pytest"
    ], runs

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


def _triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    # YAML 1.1 reads the bare key `on` as the boolean True.
    triggers: dict[str, Any] = workflow.get("on", workflow.get(True))
    return triggers


DISPATCH_OR_TAG = (
    "needs.test.result == 'success' && !cancelled() && ( "
    "(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') "
    "&& needs.build.result == 'success' && needs.verify-tag.result == 'success') "
    "|| github.event_name == 'workflow_dispatch')"
)
TAG_PUSH_ONLY = "github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')"


def test_the_release_build_runs_on_a_tag_after_test_build_and_verify_tag() -> None:
    job = _load_workflow()["jobs"]["release-build"]

    assert job["if"] == DISPATCH_OR_TAG
    assert sorted(job["needs"]) == ["build", "test", "verify-tag"]


def test_the_release_build_runs_on_demand_without_a_tag() -> None:
    workflow = _load_workflow()

    assert "workflow_dispatch" in _triggers(workflow)
    assert (
        "github.event_name == 'workflow_dispatch'"
        in (workflow["jobs"]["release-build"]["if"])
    )
    name = next(
        step
        for step in workflow["jobs"]["release-build"]["steps"]
        if step.get("name") == "Name the release"
    )
    # A tag push releases its tag; an on-demand run names the packaged version.
    assert '[ "$GITHUB_EVENT_NAME" = "push" ]' in name["run"]
    assert 'release_tag="$GITHUB_REF_NAME"' in name["run"]
    assert "build_info import version" in name["run"]
    assert 'echo "RELEASE_TAG=$release_tag" >> "$GITHUB_ENV"' in name["run"]


def test_the_on_demand_run_never_reaches_a_release_or_an_image_push() -> None:
    jobs = _load_workflow()["jobs"]

    creating = [
        name
        for name, job in jobs.items()
        for step in job.get("steps", [])
        if "gh release" in str(step.get("run", ""))
        or "release" in str(step.get("uses", "")).split("@")[0]
    ]
    assert creating == ["release-publish"]
    # Push-only: a dispatch skips the job, whatever ref it runs on.
    assert jobs["release-publish"]["if"] == TAG_PUSH_ONLY
    assert jobs["publish"]["if"] == TAG_PUSH_ONLY


def test_pyarrow_is_installed_only_inside_the_release_build_job() -> None:
    jobs = _load_workflow()["jobs"]

    installers = {
        name
        for name, job in jobs.items()
        for step in job.get("steps", [])
        if "--group release" in str(step.get("run", ""))
        or "pyarrow" in str(step.get("run", ""))
    }
    assert installers == {"release-build"}
    runs = [str(step.get("run", "")) for step in jobs["release-build"]["steps"]]
    assert "uv sync --locked --group release" in runs
    assert (
        "uv run --group release pytest tests/test_release_parquet.py --no-cov" in runs
    )
    assemble = next(r for r in runs if "assemble_release_archive.py build" in r)
    assert "--parquet" in assemble.split()
    # The image installs the runtime set alone: no dependency group.
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert "uv sync --locked --no-dev --no-editable" in dockerfile
    assert "--group" not in dockerfile and "--all-groups" not in dockerfile
    assert "pyarrow" not in dockerfile


def test_pyarrow_is_pinned_in_the_release_group_and_nowhere_else() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))

    def names(requirements: list[str]) -> list[str]:
        return [
            re.split(r"[<>=!~;\[ ]", r, maxsplit=1)[0].lower() for r in requirements
        ]

    assert "pyarrow" not in names(project["project"]["dependencies"])
    groups = project["dependency-groups"]
    assert [g for g in groups if "pyarrow" in names(groups[g])] == ["release"]
    assert re.fullmatch(r"pyarrow==\d+\.\d+\.\d+", groups["release"][0])
    # Only the default `dev` group is synced by a plain `uv sync`.
    assert project.get("tool", {}).get("uv", {}).get("default-groups") is None


def test_only_the_release_publish_job_may_write_contents() -> None:
    workflow = _load_workflow()

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["release-build"]["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["release-publish"]["permissions"] == {
        "contents": "write",
        "actions": "read",
    }
    writers = [
        name
        for name, job in workflow["jobs"].items()
        if job.get("permissions", {}).get("contents") == "write"
    ]
    assert writers == ["release-publish"]


def test_publish_and_verify_tag_are_unchanged_by_the_release_jobs() -> None:
    jobs = _load_workflow()["jobs"]

    assert jobs["publish"]["needs"] == ["test", "build", "verify-tag"]
    assert jobs["publish"]["permissions"] == {
        "contents": "read",
        "packages": "write",
    }
    assert jobs["verify-tag"]["permissions"] == {"contents": "read"}


def test_the_release_is_created_only_from_the_archive_release_build_verified() -> None:
    jobs = _load_workflow()["jobs"]
    build_steps = jobs["release-build"]["steps"]
    build_runs = [" ".join(str(s.get("run", "")).split()) for s in build_steps]
    assemble = next(
        i
        for i, run in enumerate(build_runs)
        if "assemble_release_archive.py build" in run
    )
    assert '--tag "$RELEASE_TAG" --commit "$GITHUB_SHA"' in build_runs[assemble]
    digest = next(i for i, s in enumerate(build_steps) if s.get("id") == "archive")
    upload = next(
        i
        for i, s in enumerate(build_steps)
        if "actions/upload-artifact" in s.get("uses", "")
    )
    assert assemble < digest < upload
    assert build_steps[upload]["with"]["name"] == "release-archive"
    assert jobs["release-build"]["outputs"] == {
        "archive-sha256": "${{ steps.archive.outputs.sha256 }}"
    }

    publish = jobs["release-publish"]
    assert sorted(publish["needs"]) == [
        "build",
        "release-build",
        "test",
        "verify-tag",
    ]
    runs = [" ".join(str(s.get("run", "")).split()) for s in publish["steps"]]
    download = next(i for i, run in enumerate(runs) if "gh run download" in run)
    create = next(i for i, run in enumerate(runs) if "gh release create" in run)
    assert download < create
    assert "--name release-archive" in runs[download]
    assert "sha256sum -c -" in runs[download]
    assert publish["steps"][download]["env"]["ARCHIVE_SHA256"] == (
        "${{ needs.release-build.outputs.archive-sha256 }}"
    )
    assert "--verify-tag" in runs[create]
    assert '"dist/wave-local-ai-v2-${GITHUB_REF_NAME#v}.zip"' in runs[create]


def test_the_write_token_job_runs_no_project_code() -> None:
    # Everything that executes dependency code (uv sync, pytest, pyarrow) runs
    # in release-build under a read-only token; release-publish only moves the
    # verified archive with the preinstalled gh CLI: no checkout, no action.
    steps = _load_workflow()["jobs"]["release-publish"]["steps"]
    assert [s for s in steps if "uses" in s] == []
    runs = " ".join(str(s.get("run", "")) for s in steps)
    assert "uv " not in runs and "python" not in runs


def test_the_release_build_keeps_no_token_in_the_checkout() -> None:
    # `uv sync`/`uv run` execute dependency code; no token sits in .git/config
    # meanwhile, and no shared cache feeds the job.
    steps = _load_workflow()["jobs"]["release-build"]["steps"]
    checkout = next(s for s in steps if "actions/checkout" in s.get("uses", ""))
    assert checkout["with"]["persist-credentials"] is False
    setup_uv = next(s for s in steps if "setup-uv" in s.get("uses", ""))
    assert "enable-cache" not in setup_uv.get("with", {})

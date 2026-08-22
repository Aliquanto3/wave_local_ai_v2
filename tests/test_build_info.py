from unittest.mock import MagicMock

from wave_local_ai_v2 import build_info


def test_version_reads_installed_metadata(monkeypatch) -> None:
    monkeypatch.setattr(build_info, "_installed_version", lambda name: "9.9.9")

    assert build_info.version() == "9.9.9"


def test_commit_sha_prefers_the_injected_build_value(monkeypatch) -> None:
    monkeypatch.setenv("WAVE_BUILD_SHA", "abc123")
    which = MagicMock()
    run = MagicMock()
    monkeypatch.setattr(build_info.shutil, "which", which)
    monkeypatch.setattr(build_info.subprocess, "run", run)

    assert build_info.commit_sha() == "abc123"
    assert which.called is False
    assert run.called is False


def test_commit_sha_falls_back_to_git_rev_parse(monkeypatch) -> None:
    monkeypatch.delenv("WAVE_BUILD_SHA", raising=False)
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(
        build_info.subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(stdout="deadbeef\n"),
    )

    assert build_info.commit_sha() == "deadbeef"


def test_commit_sha_asks_git_about_the_package_not_the_working_directory(
    monkeypatch,
) -> None:
    monkeypatch.delenv("WAVE_BUILD_SHA", raising=False)
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/usr/bin/git")
    seen: list[list[str]] = []

    def record(command, *args, **kwargs):
        seen.append(command)
        return MagicMock(stdout="deadbeef\n")

    monkeypatch.setattr(build_info.subprocess, "run", record)

    build_info.commit_sha()

    assert seen == [
        ["/usr/bin/git", "-C", str(build_info._PACKAGE_DIR), "rev-parse", "HEAD"]
    ]


def test_commit_sha_is_none_when_neither_surface_is_available(monkeypatch) -> None:
    monkeypatch.delenv("WAVE_BUILD_SHA", raising=False)
    monkeypatch.setattr(build_info.shutil, "which", lambda name: None)

    assert build_info.commit_sha() is None

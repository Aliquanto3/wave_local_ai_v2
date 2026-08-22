from unittest.mock import MagicMock

from wave_local_ai_v2 import build_info, provenance


def test_tree_dirty_is_false_for_a_clean_tree(monkeypatch) -> None:
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(
        build_info.subprocess, "run", lambda *a, **k: MagicMock(stdout="")
    )

    assert provenance.tree_dirty() is False


def test_tree_dirty_is_true_for_a_tracked_file_modification(monkeypatch) -> None:
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(
        build_info.subprocess,
        "run",
        lambda *a, **k: MagicMock(stdout=" M src/foo.py\n"),
    )

    assert provenance.tree_dirty() is True


def test_tree_dirty_is_false_for_untracked_files_only(monkeypatch) -> None:
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(
        build_info.subprocess,
        "run",
        lambda *a, **k: MagicMock(stdout="?? new_file.py\n"),
    )

    assert provenance.tree_dirty() is False


def test_commit_sha_and_tree_dirty_are_none_when_git_is_unavailable(
    monkeypatch,
) -> None:
    monkeypatch.delenv("WAVE_BUILD_SHA", raising=False)
    monkeypatch.setattr(build_info.shutil, "which", lambda name: None)

    assert provenance.commit_sha() is None
    assert provenance.tree_dirty() is None


def test_commit_sha_and_tree_dirty_are_none_when_git_invocation_fails(
    monkeypatch,
) -> None:
    monkeypatch.delenv("WAVE_BUILD_SHA", raising=False)
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/usr/bin/git")

    def raise_oserror(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(build_info.subprocess, "run", raise_oserror)

    assert provenance.commit_sha() is None
    assert provenance.tree_dirty() is None


def test_release_version_is_the_exact_tag_at_head(monkeypatch) -> None:
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(
        build_info.subprocess, "run", lambda *a, **k: MagicMock(stdout="v0.1.0\n")
    )

    assert provenance.release_version() == "v0.1.0"


def test_release_version_falls_back_to_packaged_version_with_untagged_suffix(
    monkeypatch,
) -> None:
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(
        build_info.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(
            build_info.subprocess.CalledProcessError(1, "git describe")
        ),
    )
    monkeypatch.setattr(build_info, "version", lambda: "0.1.0")

    assert provenance.release_version() == "0.1.0+untagged"


def test_capture_provenance_never_raises_and_degrades_to_null_on_git_failure(
    monkeypatch,
) -> None:
    monkeypatch.delenv("WAVE_BUILD_SHA", raising=False)
    monkeypatch.setattr(build_info.shutil, "which", lambda name: None)
    monkeypatch.setattr(build_info, "version", lambda: "0.1.0")

    result = provenance.capture_provenance()

    assert result == {
        "release_version": "0.1.0+untagged",
        "commit_sha": None,
        "tree_dirty": None,
    }

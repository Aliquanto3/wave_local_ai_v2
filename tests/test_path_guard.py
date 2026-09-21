from pathlib import Path

from wave_local_ai_v2.path_guard import resolve_within_root


def test_a_part_that_stays_inside_root_resolves(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    resolved = resolve_within_root(root, "a-file.json")

    assert resolved == (root / "a-file.json").resolve()


def test_a_part_that_walks_up_out_of_root_returns_none(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    escaped = tmp_path / "escaped.json"
    escaped.write_text("secret", encoding="utf-8")

    assert resolve_within_root(root, "../escaped.json") is None


def test_an_absolute_part_that_escapes_root_returns_none(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    escaped = tmp_path / "escaped.json"
    escaped.write_text("secret", encoding="utf-8")

    assert resolve_within_root(root, str(escaped)) is None


def test_a_root_relative_part_is_a_no_op(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    assert (
        resolve_within_root(root, ".", "a-file.json")
        == (root / "a-file.json").resolve()
    )

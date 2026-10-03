"""The composition check over constructed rosters, one per outcome, and over
the shipped roster as its calibration."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import composition_check

REAL_ROSTER_PATH = Path("aidd_docs/roster/models.json")
README_PATH = Path("aidd_docs/results/README.md")

LICENCE = {
    "id": "Apache-2.0",
    "client_commercial_use": True,
    "read_on": "2026-10-02",
    "source_url": "https://example.test/LICENSE",
}


def _entry(
    *,
    family: str | None = "qwen",
    kind: str = "dense",
    size_class: str | None = "~2B",
    total_params: int | None = 1_700_000_000,
    bytes_on_disk: int | None = 1_800_000_000,
    licence: dict[str, Any] | None = LICENCE,
    display_id: str = "Some Model",
) -> dict[str, Any]:
    architecture: dict[str, Any] = {
        "kind": kind,
        "expert_count": 8 if kind == "moe" else 0,
        "active_params_b": 1.0,
    }
    if total_params is not None:
        architecture["total_params"] = total_params
    entry: dict[str, Any] = {
        "repo": "fake/repo",
        "revision": "0" * 40,
        "file": "model.gguf",
        "display_id": display_id,
        "quant": "Q8_0",
        "sha256": "a" * 64,
        "architecture": architecture,
        "server_flags": {
            "n_gpu_layers": 99,
            "context_size": 4096,
            "flash_attention": "on",
            "jinja": True,
            "parallel_slots": 1,
            "load_mode": "auto",
            "sampler": {
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "min_p": 0,
                "presence_penalty": 1.5,
            },
        },
    }
    if family is not None:
        entry["family"] = family
    if size_class is not None:
        entry["size_class"] = size_class
    if bytes_on_disk is not None:
        entry["bytes_on_disk"] = bytes_on_disk
    if licence is not None:
        entry["licence"] = licence
    return entry


def _declaration(
    *,
    ladder: bool = False,
    reason: str | None = "no MoE GGUF exists in this class",
    moe_entry: str | None = None,
) -> dict[str, Any]:
    return {
        "single_family_ladder": ladder,
        "moe_sought": True,
        "moe_entry": moe_entry,
        "moe_absent_reason": reason,
    }


# One class (~2B) holding two families and a recorded MoE absence: the
# passing baseline every other test perturbs.
TWO_FAMILY_ROSTER: dict[str, Any] = {
    "roster_version": 4,
    "size_classes": {"~2B": _declaration()},
    "entries": {
        "qwen-2b": _entry(family="qwen"),
        "granite-2b": _entry(family="ibm"),
    },
}


def _run(
    tmp_path: Path, raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    path = tmp_path / "models.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    code = composition_check.main(["--roster", str(path)])
    return code, capsys.readouterr().out


def _with(**changes: Any) -> dict[str, Any]:
    raw = copy.deepcopy(TWO_FAMILY_ROSTER)
    raw.update(changes)
    return raw


def test_a_class_spanning_two_families_passes(tmp_path, capsys) -> None:
    code, out = _run(tmp_path, TWO_FAMILY_ROSTER, capsys)

    assert code == 0, out
    assert (
        "~2B: 2 entries; families: ibm, qwen; dense: yes; MoE: no; label: none" in out
    )
    assert "~0.5B: no entries (not published)" in out
    assert out.endswith(
        "PASS: every published size class spans two families or says it does not\n"
    )


def test_one_family_with_the_ladder_label_passes_as_a_labelled_ladder(
    tmp_path, capsys
) -> None:
    raw = _with(
        entries={"qwen-2b": _entry(family="qwen")},
        size_classes={"~2B": _declaration(ladder=True)},
    )

    code, out = _run(tmp_path, raw, capsys)

    assert code == 0, out
    assert "families: qwen;" in out
    assert "label: single-family ladder" in out


def test_one_family_without_the_label_fails_naming_the_class(tmp_path, capsys) -> None:
    raw = _with(entries={"qwen-2b": _entry(family="qwen")})

    code, out = _run(tmp_path, raw, capsys)

    assert code == 1
    assert (
        "size class ~2B: spans one family (qwen) without the single-family-ladder label"
        in out
    )


def test_the_ladder_label_on_a_two_family_class_fails(tmp_path, capsys) -> None:
    raw = _with(size_classes={"~2B": _declaration(ladder=True)})

    code, out = _run(tmp_path, raw, capsys)

    assert code == 1
    assert (
        "size class ~2B: is labelled a single-family ladder but spans 2 families" in out
    )


def test_no_moe_and_no_reason_fails_and_the_reason_makes_it_pass(
    tmp_path, capsys
) -> None:
    code, out = _run(
        tmp_path, _with(size_classes={"~2B": _declaration(reason=None)}), capsys
    )

    assert code == 1
    assert "size class ~2B: has no MoE represented and no reason recorded" in out

    code, out = _run(tmp_path, TWO_FAMILY_ROSTER, capsys)

    assert code == 0
    assert "MoE absence reason: no MoE GGUF exists in this class" in out


def test_a_represented_moe_needs_no_reason_and_reports_both_architectures(
    tmp_path, capsys
) -> None:
    entries = {
        **TWO_FAMILY_ROSTER["entries"],
        "lfm-moe": _entry(family="liquid", kind="moe"),
    }
    raw = _with(
        entries=entries,
        size_classes={"~2B": _declaration(reason=None, moe_entry="lfm-moe")},
    )

    code, out = _run(tmp_path, raw, capsys)

    assert code == 0, out
    assert "dense: yes; MoE: yes (lfm-moe);" in out
    assert "MoE absence reason: n/a" in out


def test_a_declared_moe_entry_that_is_not_a_moe_of_the_class_fails(
    tmp_path, capsys
) -> None:
    raw = _with(size_classes={"~2B": _declaration(moe_entry="qwen-2b")})

    code, out = _run(tmp_path, raw, capsys)

    assert code == 1
    assert "declares MoE entry qwen-2b, which is not a MoE entry of this class" in out


def test_a_moe_entry_the_declaration_omits_fails(tmp_path, capsys) -> None:
    entries = {
        **TWO_FAMILY_ROSTER["entries"],
        "lfm-moe": _entry(family="liquid", kind="moe"),
    }

    code, out = _run(tmp_path, _with(entries=entries), capsys)

    assert code == 1
    assert "holds MoE entry lfm-moe but its declaration names none" in out


def test_a_class_with_entries_and_no_declaration_fails(tmp_path, capsys) -> None:
    code, out = _run(tmp_path, _with(size_classes={}), capsys)

    assert code == 1
    assert "size class ~2B: holds entries but the roster declares nothing for it" in out
    assert "label: undeclared; MoE sought: undeclared" in out


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"family": None, "display_id": "Unknown-1B"}, "no resolvable family"),
        ({"size_class": None}, "declares no size_class"),
        ({"total_params": None}, "declares no architecture.total_params"),
        ({"bytes_on_disk": None}, "declares no bytes_on_disk"),
        ({"licence": None}, "carries no licence block"),
    ],
)
def test_an_entry_the_roster_is_silent_about_is_named_never_skipped(
    tmp_path, capsys, changes: dict[str, Any], reason: str
) -> None:
    entries = {**TWO_FAMILY_ROSTER["entries"], "silent": _entry(**changes)}

    code, out = _run(tmp_path, _with(entries=entries), capsys)

    assert code == 1
    assert re.search(rf"entry silent: {re.escape(reason)}", out), out
    assert "  silent: " in out


@pytest.mark.parametrize(
    ("declared", "total_params", "banded"),
    [
        ("~2B", 999_999_999, "~0.5B"),
        ("~0.5B", 1_000_000_000, "~2B"),
        ("~4B", 2_999_999_999, "~2B"),
        ("~2B", 3_000_000_000, "~4B"),
        ("~8B-and-up", 5_999_999_999, "~4B"),
        ("~4B", 6_000_000_000, "~8B-and-up"),
    ],
)
def test_a_class_disagreeing_with_total_params_is_named_at_each_edge(
    tmp_path, capsys, declared: str, total_params: int, banded: str
) -> None:
    entries = {
        **TWO_FAMILY_ROSTER["entries"],
        "edge": _entry(size_class=declared, total_params=total_params),
    }

    code, out = _run(tmp_path, _with(entries=entries), capsys)

    assert code == 1
    assert (
        f"entry edge: declares size class {declared} but its {total_params} total "
        f"parameters fall in {banded}"
    ) in out


@pytest.mark.parametrize(
    ("size_class", "total_params"),
    [
        ("~0.5B", 999_999_999),
        ("~2B", 1_000_000_000),
        ("~2B", 2_999_999_999),
        ("~4B", 3_000_000_000),
        ("~4B", 5_999_999_999),
        ("~8B-and-up", 6_000_000_000),
    ],
)
def test_a_class_agreeing_with_total_params_is_not_named(
    tmp_path, capsys, size_class: str, total_params: int
) -> None:
    entries = {"edge": _entry(size_class=size_class, total_params=total_params)}
    raw = {
        "roster_version": 4,
        "size_classes": {size_class: _declaration(ladder=True)},
        "entries": entries,
    }

    code, out = _run(tmp_path, raw, capsys)

    assert code == 0, out


def test_bytes_on_disk_alone_suggesting_another_class_is_not_named(
    tmp_path, capsys
) -> None:
    # 1.7B parameters in 9 GB on disk: a footprint the ~8B-and-up class would
    # hold, but bytes are published beside the class, never banded.
    entries = {
        **TWO_FAMILY_ROSTER["entries"],
        "fat": _entry(family="google", bytes_on_disk=9_000_000_000),
    }

    code, out = _run(tmp_path, _with(entries=entries), capsys)

    assert code == 0, out
    assert "9,000,000,000 bytes on disk" in out


def test_an_unloadable_roster_exits_2_and_checks_nothing(tmp_path, capsys) -> None:
    path = tmp_path / "models.json"
    path.write_text("{not json", encoding="utf-8")

    code = composition_check.main(["--roster", str(path)])

    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert "composition check: nothing checked:" in captured.err


def test_an_entry_without_a_licence_prints_no_licence_terms(tmp_path, capsys) -> None:
    entries = {**TWO_FAMILY_ROSTER["entries"], "bare": _entry(licence=None)}

    _, out = _run(tmp_path, _with(entries=entries), capsys)

    assert "  bare: ~2B; family qwen; dense; 1,700,000,000 total params; " in out
    assert "bytes on disk; no licence block" in out


# --------------------------------------------------------------------------
# Calibration: the shipped roster, before any new entry is authored.


def test_the_shipped_roster_reports_four_single_family_classes_and_fails(
    capsys,
) -> None:
    code = composition_check.main(["--roster", REAL_ROSTER_PATH.as_posix()])
    out = capsys.readouterr().out

    # A check that passes on today's four-Qwen roster is not checking the rule.
    assert code == 1
    report = composition_check.check_composition(
        composition_check.roster.load_roster(REAL_ROSTER_PATH),
        REAL_ROSTER_PATH.as_posix(),
    )
    assert [c.size_class for c in report.classes] == [
        "~0.5B",
        "~2B",
        "~4B",
        "~8B-and-up",
    ]
    for item in report.classes:
        assert item.families == ("qwen",), item.size_class
        assert (
            f"size class {item.size_class}: spans one family (qwen) without the "
            "single-family-ladder label"
        ) in out
    # The flagship resolves its family through the in-code fallback, with no
    # exception carved out for it.
    flagship = next(
        e for e in report.entries if e.entry_id == "qwen3.6-35b-a3b-ud-iq4xs"
    )
    assert flagship.family == "qwen"
    assert not [f for f in report.failures if f.subject.startswith("entry ")]


def test_the_readme_quotes_the_check_output_on_the_shipped_roster(capsys) -> None:
    composition_check.main(["--roster", REAL_ROSTER_PATH.as_posix()])
    out = capsys.readouterr().out
    readme = README_PATH.read_text(encoding="utf-8")

    match = re.search(
        r"<!-- composition-check:start -->\n```text\n(.*?)```\n<!-- composition-check:end -->",
        readme,
        re.DOTALL,
    )
    assert match is not None, "README has no composition-check block"
    assert match.group(1) == out, (
        "the README's composition section is stale: re-run "
        "`uv run wave-local-ai-v2-composition-check` and paste its output"
    )

"""The leader set: per suite and machine class, the local models not
distinguishable from the best, published as its own record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import comparison, leader_set

LAPTOP = {
    "cpu": "a cpu",
    "ram_gb": 32.0,
    "gpu_name": "a gpu",
    "os": "Windows 11",
    "gpu_driver_version": "1",
}


def _row(
    run_id: str,
    model_id: str,
    item: int,
    correct: bool | None,
    score: float | None,
    **overrides: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": "15",
        "run_id": run_id,
        "model_id": model_id,
        "provider": "local",
        "roster_entry_id": f"entry-{model_id}",
        "fiche_hash": f"fiche-{model_id}",
        "item_id": f"item-{item:02d}",
        "task_suite": "classification",
        "suite_id": "suite-a",
        "suite_version": "1",
        "prompt_set_hash": "prompt-set",
        "suite_level": "development",
        "max_output_tokens": 32,
        "stop_sequences": [],
        "context_length": 32768,
        "thinking_policy": "disabled",
        "prompt_variant_id": "baseline",
        "prompt_variant_version": "1",
        "correct": correct,
        "suite_accuracy": score,
        "partial_failure": None,
    }
    row.update(overrides)
    return row


def _batch(
    run_id: str, model_id: str, correct_count: int, **overrides: Any
) -> list[dict[str, Any]]:
    """A 20-item batch whose first `correct_count` items are correct."""
    score = overrides.pop("score", correct_count / 20)
    return [
        _row(run_id, model_id, i, i < correct_count, score, **overrides)
        for i in range(20)
    ]


class Bundle:
    """Rows, fiches and the two record directories, on disk."""

    def __init__(self, root: Path) -> None:
        self.rows_path = root / "quality.jsonl"
        self.fiches = root / "fiches"
        self.records = root / "comparisons"
        self.leader_sets = root / "leader-sets"
        self.fiches.mkdir()
        self.rows: list[dict[str, Any]] = []

    def fiche(self, fiche_hash: str, **fields: Any) -> None:
        body = {**LAPTOP, "quant": "q", **fields}
        (self.fiches / f"{fiche_hash}.json").write_text(json.dumps(body), "utf-8")

    def add(self, rows: list[dict[str, Any]]) -> None:
        self.rows.extend(rows)
        for row in rows:
            if not (self.fiches / f"{row['fiche_hash']}.json").exists():
                self.fiche(row["fiche_hash"])
        self.rows_path.write_text(
            "".join(json.dumps(row) + "\n" for row in self.rows), "utf-8"
        )

    def run(self, *extra: str) -> int:
        return comparison.main(
            [
                "--leader-sets",
                "--rows",
                str(self.rows_path),
                "--records-dir",
                str(self.records),
                "--leader-sets-dir",
                str(self.leader_sets),
                "--fiche-registry-dir",
                str(self.fiches),
                *extra,
            ]
        )

    def current(self) -> list[dict[str, Any]]:
        return leader_set.current_leader_sets(self.leader_sets)

    def files(self, directory: Path) -> dict[str, str]:
        return {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(directory.glob("*.json"))
        }


@pytest.fixture
def bundle(tmp_path: Path) -> Bundle:
    return Bundle(tmp_path)


def _statuses(record: dict[str, Any]) -> dict[str, str]:
    return {entry["model_id"]: entry["status"] for entry in record["subjects"]}


def test_two_members_one_excluded_and_the_cloud_never_listed(bundle: Bundle) -> None:
    bundle.add(_batch("run-a", "model-a", 20))
    bundle.add(_batch("run-b", "model-b", 19))
    bundle.add(_batch("run-c", "model-c", 5))
    # A cloud subject scoring higher than every local one, on the same items.
    bundle.add(_batch("run-a", "cloud-x", 20, provider="mistral", score=1.0))

    assert bundle.run() == 0

    (record,) = bundle.current()
    assert record["reference"] == {
        "run_id": "run-a",
        "model_id": "model-a",
        "suite_score": 1.0,
    }
    assert _statuses(record) == {
        "model-a": "member",
        "model-b": "member",
        "model-c": "excluded",
    }
    assert (record["member_count"], record["excluded_count"]) == (2, 1)
    assert record["not_compared_count"] == 0
    assert record["incomplete"] is False
    assert record["comparison_ran"] is True
    assert record["suite_id"] == "suite-a"
    assert record["suite_version"] == "1"
    assert record["suite_level"] == "development"
    assert record["grouping_fields"] == [
        "suite_id",
        "suite_version",
        *leader_set.MACHINE_CLASS_FIELDS,
    ]
    assert record["grouping_values"] == {
        "cpu": "a cpu",
        "ram_gb": 32.0,
        "gpu_name": "a gpu",
        "os": "Windows 11",
    }
    assert record["grouping_not_recorded"] == ["machine_id", "compute_mode"]
    assert record["tie_rule"] == leader_set.TIE_RULE
    # The verdicts are read from the suite's family, over its Holm adjustment.
    (family,) = (
        json.loads(path.read_text("utf-8")) for path in bundle.records.glob("*.json")
    )
    assert record["family_id"] == family["family_id"]
    assert family["family_size"] == 2
    assert family["multiplicity_correction"]["adjustment_size"] == 2
    excluded = next(e for e in record["subjects"] if e["model_id"] == "model-c")
    assert excluded["adjusted_p_value"] <= record["alpha"]
    assert excluded["verdict"] == comparison.VERDICT_DISTINGUISHABLE


def test_a_refused_comparison_is_not_compared_and_the_record_incomplete(
    bundle: Bundle,
) -> None:
    bundle.add(_batch("run-a", "model-a", 20))
    bundle.add(_batch("run-d", "model-d", 18, thinking_policy=None))

    assert bundle.run() == 0

    (record,) = bundle.current()
    entry = next(e for e in record["subjects"] if e["model_id"] == "model-d")
    assert entry["status"] == leader_set.STATUS_NOT_COMPARED
    assert entry["refused_fields"] == ["thinking_policy"]
    assert entry["not_compared_reason"] == "refused on thinking_policy (absent)"
    assert record["incomplete"] is True
    assert record["incomplete_reason"]


def test_an_observation_is_not_compared_naming_its_reason(bundle: Bundle) -> None:
    bundle.add(_batch("run-a", "model-a", 20))
    partial = {"provider": "local", "item_id": "item-19", "reason": "boom"}
    bundle.add(_batch("run-p", "model-p", 10, score=None, partial_failure=partial))

    assert bundle.run() == 0

    (record,) = bundle.current()
    entry = next(e for e in record["subjects"] if e["model_id"] == "model-p")
    assert entry["status"] == leader_set.STATUS_NOT_COMPARED
    assert entry["suite_score"] is None
    assert entry["not_compared_reason"].startswith("an observation, not a test")
    assert "partial" in entry["not_compared_reason"]


def test_a_tie_at_the_top_names_the_reference_by_the_stated_rule(
    bundle: Bundle,
) -> None:
    bundle.add(_batch("run-z", "model-z", 18))
    bundle.add(_batch("run-m", "model-m", 18))
    bundle.add(_batch("run-q", "model-q", 12))

    assert bundle.run() == 0

    (record,) = bundle.current()
    assert record["reference"]["run_id"] == "run-m"
    assert record["tied_at_top"] == [
        {"run_id": "run-m", "model_id": "model-m"},
        {"run_id": "run-z", "model_id": "model-z"},
    ]
    roles = {entry["run_id"]: entry["role"] for entry in record["subjects"]}
    assert roles == {"run-m": "reference", "run-q": "compared", "run-z": "compared"}


def test_a_single_local_subject_is_a_set_of_one_without_a_comparison(
    bundle: Bundle,
) -> None:
    bundle.add(_batch("run-a", "model-a", 15))
    bundle.add(_batch("run-a", "cloud-x", 19, provider="mistral", score=0.95))

    assert bundle.run() == 0

    (record,) = bundle.current()
    assert [entry["model_id"] for entry in record["subjects"]] == ["model-a"]
    assert record["comparison_ran"] is False
    assert record["no_comparison_reason"] == leader_set.NO_COMPARISON_REASON
    assert record["family_id"] is None
    assert record["alpha"] is None
    assert not bundle.records.exists()


def test_a_gpu_and_a_cpu_only_run_of_one_model_are_two_groups(
    bundle: Bundle,
) -> None:
    bundle.fiche("fiche-gpu", compute_mode="gpu", machine_id="laptop")
    bundle.fiche("fiche-cpu", compute_mode="cpu_only", machine_id="laptop")
    bundle.add(_batch("run-g", "model-a", 18, fiche_hash="fiche-gpu"))
    bundle.add(_batch("run-c", "model-a", 17, fiche_hash="fiche-cpu"))

    assert bundle.run() == 0

    records = bundle.current()
    assert len(records) == 2
    modes = sorted(record["grouping_values"]["compute_mode"] for record in records)
    assert modes == ["cpu_only", "gpu"]
    for record in records:
        assert record["grouping_not_recorded"] == []
        assert record["comparison_ran"] is False
        assert len(record["subjects"]) == 1


def test_a_grown_family_supersedes_the_leader_set_and_keeps_the_old_file(
    bundle: Bundle, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle.add(_batch("run-a", "model-a", 20))
    bundle.add(_batch("run-b", "model-b", 19))
    assert bundle.run() == 0
    old_sets = bundle.files(bundle.leader_sets)
    old_families = bundle.files(bundle.records)
    (old,) = bundle.current()

    bundle.add(_batch("run-c", "model-c", 5))
    assert bundle.run() == 0

    for name, text in old_sets.items():
        assert (bundle.leader_sets / name).read_text(encoding="utf-8") == text
    for name, text in old_families.items():
        assert (bundle.records / name).read_text(encoding="utf-8") == text
    (new,) = bundle.current()
    assert leader_set.superseded_ids(new) == [old["leader_set_id"]]
    assert len(bundle.files(bundle.leader_sets)) == 2
    family = json.loads(
        (bundle.records / Path(new_family_name(bundle, new))).read_text("utf-8")
    )
    assert family["family_size"] == 2
    assert comparison.superseded_ids(family) == [old["family_id"]]
    assert "supersedes" in capsys.readouterr().out

    # A re-run over the same bundle publishes the identical records.
    before = (bundle.files(bundle.leader_sets), bundle.files(bundle.records))
    assert bundle.run() == 0
    assert (bundle.files(bundle.leader_sets), bundle.files(bundle.records)) == before
    assert "unchanged" in capsys.readouterr().out


def new_family_name(bundle: Bundle, record: dict[str, Any]) -> str:
    (path,) = [
        path
        for path in bundle.records.glob("*.json")
        if json.loads(path.read_text("utf-8"))["family_id"] == record["family_id"]
    ]
    return path.name


def test_the_family_keeps_every_comparison_it_already_held(bundle: Bundle) -> None:
    # A comparison already published in the suite's family (local against
    # cloud) stays in it: the leader comparisons only grow the family.
    bundle.add(_batch("run-a", "model-a", 20))
    bundle.add(_batch("run-a", "cloud-x", 19, provider="mistral", score=0.95))
    bundle.add(_batch("run-b", "model-b", 19))
    assert (
        comparison.main(
            [
                "--rows",
                str(bundle.rows_path),
                "--reference",
                "run-a",
                "--reference-where",
                "model_id=model-a",
                "--candidate",
                "run-a",
                "--candidate-where",
                "model_id=cloud-x",
                "--records-dir",
                str(bundle.records),
            ]
        )
        == 0
    )

    assert bundle.run() == 0

    records = comparison.read_family_records(bundle.records)
    (head,) = [r for r in records if r["family_id"] in comparison.heads(records)]
    assert head["family_size"] == 2
    candidates = sorted(
        member["candidate_selector"]["model_id"] for member in head["members"]
    )
    assert candidates == ["cloud-x", "model-b"]
    (record,) = bundle.current()
    assert record["family_id"] == head["family_id"]


def test_a_conflicting_record_file_refuses_and_writes_nothing(
    bundle: Bundle, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle.add(_batch("run-a", "model-a", 20))
    bundle.add(_batch("run-b", "model-b", 19))
    assert bundle.run() == 0
    (path,) = bundle.leader_sets.glob("*.json")
    path.write_text("{}\n", encoding="utf-8")
    families = bundle.files(bundle.records)

    assert bundle.run() == 1

    assert "immutable" in capsys.readouterr().err
    assert bundle.files(bundle.records) == families


@pytest.mark.parametrize(
    "extra",
    [
        ("--reference", "run-a"),
        ("--comparisons", "declared.json"),
        ("--dimension", "prompt_variant"),
        ("--quantity", "item_tokens_out"),
        ("--output", "out.json"),
        ("--alpha", "1.5"),
    ],
)
def test_the_leader_set_run_refuses_a_declared_comparison_flag(
    bundle: Bundle, extra: tuple[str, ...], capsys: pytest.CaptureFixture[str]
) -> None:
    bundle.add(_batch("run-a", "model-a", 20))

    assert bundle.run(*extra) == 1

    assert capsys.readouterr().err
    assert not bundle.leader_sets.exists()


def test_unusable_rows_exit_1(bundle: Bundle) -> None:
    bundle.rows_path.write_text("not json\n", encoding="utf-8")

    assert bundle.run() == 1


def test_a_subject_publishing_two_scores_refuses_the_run(bundle: Bundle) -> None:
    rows = _batch("run-a", "model-a", 20)
    rows[0]["suite_accuracy"] = 0.5
    bundle.add(rows)

    assert bundle.run() == 1
    assert not bundle.leader_sets.exists()


def test_unplaced_and_unscored_subjects_are_named_and_publish_nothing(
    bundle: Bundle, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle.add(_batch("run-u", "model-u", 10, score=None, fiche_hash="fiche-u2"))
    (bundle.fiches / "fiche-u2.json").unlink()
    bundle.add(_batch("run-s", "model-s", 10, suite_id=None))
    bundle.add(_batch("run-f", "model-f", 10, fiche_hash=None))
    bundle.add(_batch("run-n", "model-n", 10, score=None))

    assert bundle.run() == 0

    err = capsys.readouterr().err
    assert "run run-u (model-u): its fiche fiche-u2 does not resolve" in err
    assert "run run-s (model-s): its rows do not name one suite" in err
    assert "run run-f (model-f): its rows do not cite one fiche" in err
    assert "no local subject publishes a suite score" in err
    assert leader_set.current_leader_sets(bundle.leader_sets) == []


def test_rows_without_a_local_subject_publish_nothing(
    bundle: Bundle, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle.add(_batch("run-a", "cloud-x", 19, provider="mistral", score=0.95))

    assert bundle.run() == 0

    assert "no leader set" in capsys.readouterr().out
    assert not bundle.leader_sets.exists()


def test_a_broken_leader_set_file_refuses_the_run(bundle: Bundle) -> None:
    bundle.add(_batch("run-a", "model-a", 20))
    bundle.leader_sets.mkdir()
    (bundle.leader_sets / "broken.json").write_text("{", encoding="utf-8")
    (bundle.leader_sets / "other.json").write_text('{"x": 1}', encoding="utf-8")

    assert bundle.run() == 1


def test_a_graded_suite_reads_its_suite_score(bundle: Bundle) -> None:
    graded = {
        "suite_accuracy": None,
        "metric_id": "chrf",
        "metric_version": "1",
        "metric_params": {"beta": 2},
    }
    for run_id, model_id, score in (
        ("run-a", "model-a", 0.7),
        ("run-b", "model-b", 0.6),
    ):
        bundle.add(
            [
                _row(
                    run_id,
                    model_id,
                    i,
                    False,
                    None,
                    item_score=score,
                    suite_score=score,
                    **graded,
                )
                for i in range(10)
            ]
        )

    assert bundle.run() == 0

    (record,) = bundle.current()
    assert record["score_field"] == "suite_score"
    assert record["reference"]["model_id"] == "model-a"


def test_build_record_refuses_a_group_it_cannot_read() -> None:
    subject = leader_set.Subject(
        run_id="run-a",
        model_id="model-a",
        rows=(_row("run-a", "model-a", 0, True, None),),
        score=None,
        score_field="suite_accuracy",
        fiche_hash="fiche-a",
        grouping_values={},
        grouping_not_recorded=(),
    )
    with pytest.raises(leader_set.LeaderSetError, match="no local subject"):
        leader_set.build_record(
            leader_set.Group("suite-a", "1", (subject,)), None, rows_source="rows"
        )
    scored = leader_set.Subject(**{**vars(subject), "score": 1.0})
    other = leader_set.Subject(**{**vars(subject), "run_id": "run-b", "score": 0.5})
    group = leader_set.Group("suite-a", "1", (scored, other))
    with pytest.raises(leader_set.LeaderSetError, match="reads a family record"):
        leader_set.build_record(group, None, rows_source="rows")
    family = {"family_id": "f" * 64, "alpha": 0.05, "members": []}
    with pytest.raises(leader_set.LeaderSetError, match="holds no comparison"):
        leader_set.build_record(group, family, rows_source="rows")


PUBLISHED_SETS = sorted(leader_set.LEADER_SETS_DIR.glob("*.json"))


@pytest.mark.parametrize("published", PUBLISHED_SETS, ids=lambda path: path.name)
def test_a_published_leader_set_recomputes_from_the_bundle_alone(
    published: Path, tmp_path: Path
) -> None:
    # Only what it was computed against is on file: the family records but
    # the one it cites (so the family is grown again) and the leader sets it
    # supersedes. The command cannot simply re-emit the published files.
    record = json.loads(published.read_text(encoding="utf-8"))
    records_dir = tmp_path / "comparisons"
    sets_dir = tmp_path / "leader-sets"
    records_dir.mkdir()
    sets_dir.mkdir()
    for path in comparison.COMPARISONS_DIR.glob("*.json"):
        if json.loads(path.read_text("utf-8"))["family_id"] != record["family_id"]:
            (records_dir / path.name).write_bytes(path.read_bytes())
    by_id = {
        json.loads(path.read_text("utf-8"))["leader_set_id"]: path
        for path in PUBLISHED_SETS
    }
    for superseded in leader_set.superseded_ids(record):
        (sets_dir / by_id[superseded].name).write_bytes(by_id[superseded].read_bytes())

    assert (
        comparison.main(
            [
                "--leader-sets",
                "--rows",
                record["rows_source"],
                "--records-dir",
                str(records_dir),
                "--leader-sets-dir",
                str(sets_dir),
            ]
        )
        == 0
    )

    assert (sets_dir / published.name).read_text(encoding="utf-8") == (
        published.read_text(encoding="utf-8")
    )


def test_the_bundle_publishes_the_first_real_leader_set() -> None:
    (record,) = leader_set.current_leader_sets(leader_set.LEADER_SETS_DIR)
    assert (record["suite_id"], record["suite_version"]) == (
        "classification-support-routing",
        "2",
    )
    # Two local batches of one model, tied at 0.8; the comparison between
    # them is refused on thinking_policy, so the set is incomplete.
    assert record["reference"]["suite_score"] == 0.8
    assert len(record["tied_at_top"]) == 2
    assert _statuses_by_run(record) == {
        record["reference"]["run_id"]: leader_set.STATUS_MEMBER,
        next(
            entry["run_id"]
            for entry in record["subjects"]
            if entry["role"] == leader_set.ROLE_COMPARED
        ): leader_set.STATUS_NOT_COMPARED,
    }
    assert record["incomplete"] is True
    assert record["grouping_not_recorded"] == ["machine_id", "compute_mode"]


def _statuses_by_run(record: dict[str, Any]) -> dict[str, str]:
    return {entry["run_id"]: entry["status"] for entry in record["subjects"]}


def test_a_leader_set_never_reads_a_superseded_family(
    bundle: Bundle, capsys: pytest.CaptureFixture[str]
) -> None:
    # A change of alpha alone supersedes the family; going back to the first
    # alpha would re-emit the superseded record, which no leader set reads.
    bundle.add(_batch("run-a", "model-a", 20))
    bundle.add(_batch("run-b", "model-b", 19))
    assert bundle.run() == 0
    assert bundle.run("--alpha", "0.01") == 0
    before = bundle.files(bundle.leader_sets)

    assert bundle.run() == 1

    assert "a leader set reads only a current family" in capsys.readouterr().err
    assert bundle.files(bundle.leader_sets) == before


def test_a_pair_the_family_holds_the_other_way_round_is_not_declared_twice(
    bundle: Bundle,
) -> None:
    # The family already compares model-b (reference) against model-a; the
    # leader comparison model-a against model-b is the same test, so Holm
    # must not count it twice and the leader set reads the existing member.
    bundle.add(_batch("run-a", "model-a", 20))
    bundle.add(_batch("run-b", "model-b", 19))
    declared = [
        "--rows",
        str(bundle.rows_path),
        "--reference",
        "run-b",
        "--reference-where",
        "model_id=model-b",
        "--candidate",
        "run-a",
        "--candidate-where",
        "model_id=model-a",
        "--records-dir",
        str(bundle.records),
    ]
    assert comparison.main(declared) == 0
    (published,) = comparison.read_family_records(bundle.records)

    assert bundle.run() == 0

    (family,) = comparison.read_family_records(bundle.records)
    assert family["family_id"] == published["family_id"]
    assert family["family_size"] == 1
    (record,) = bundle.current()
    assert record["family_id"] == published["family_id"]
    assert _statuses(record) == {"model-a": "member", "model-b": "member"}

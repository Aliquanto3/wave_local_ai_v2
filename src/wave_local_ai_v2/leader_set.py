"""The leader set: per suite and machine class, the local models not
distinguishable from the best.

A leader set is a published derived output (PRD Non-goals, owner answer
Q42 (a)), never computed at read time: the analysis command
(`wave-local-ai-v2-compare --leader-sets`) reads the published quality rows
and their fiches, groups the local subjects by suite and machine class, names
the best one by its published suite score, compares every other subject of
the group against it inside the suite's comparison family (Holm over that
closed family, `comparison.py`), and writes one immutable record per group to
`aidd_docs/results/leader-sets/`. A changed group is a new record superseding
the old by id; no published record is rewritten. Anyone holding the bundle
reruns the command and gets the same records.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import comparison, settings
from wave_local_ai_v2.fiche_registry import read_fiche

RECORD_TYPE = "leader_set"
RECORD_VERSION = "1"
LEADER_SETS_DIR = Path(settings.DEFAULT_LEADER_SETS_DIR)

PROVIDER_LOCAL = "local"
# The comparison family a leader set reads: the suite's model family on the
# score, Methodology 24's default family.
LEADER_DIMENSION = "model"
# The side selector that names one subject within its run, the one the
# committed family records already use.
SUBJECT_SELECTOR_FIELD = "model_id"

# The fiche fields a machine class is: the machine's hardware identity and the
# compute mode it ran in. `machine_id` and `compute_mode` are read as soon as a
# fiche carries them; a fiche without one groups it as not recorded.
MACHINE_CLASS_FIELDS: tuple[str, ...] = (
    "machine_id",
    "compute_mode",
    "cpu",
    "ram_gb",
    "gpu_name",
    "os",
)
MACHINE_CLASS_RULE = (
    "a group is one suite (id and version) on one machine class: the subjects "
    "whose fiches carry equal values for every grouping field, a field the "
    "fiche does not carry being listed as not recorded; a gpu and a cpu_only "
    "fiche of one machine differ on compute_mode, so they never share a group"
)

SCORE_FIELD_BY_SCORING_KIND: dict[str, str] = {
    comparison.SCORING_KIND_BINARY: "suite_accuracy",
    comparison.SCORING_KIND_GRADED: "suite_score",
}

TIE_RULE = (
    "the reference is the local subject with the highest published suite "
    "score in the group; among subjects tied at that score, the one whose "
    "(run_id, model_id) sorts first"
)
MEMBERSHIP_RULE = (
    "members are the reference plus every local subject whose comparison "
    "against it reads 'not distinguishable' at alpha on the family's "
    "Holm-adjusted p; 'distinguishable' is excluded; any 'not comparable' "
    "(a refusal, or an observation that is not a test) is not compared, so "
    "the record is incomplete"
)
LOCAL_ONLY_RULE = (
    "only local subjects enter a leader set: cloud subjects stay the pitch's "
    "comparators and are never members, excluded or compared here"
)

STATUS_MEMBER = "member"
STATUS_EXCLUDED = "excluded"
STATUS_NOT_COMPARED = "not compared"
ROLE_REFERENCE = "reference"
ROLE_COMPARED = "compared"

NO_COMPARISON_REASON = (
    "one local subject in the group: there is nothing to compare it against"
)

_STATUS_BY_VERDICT = {
    comparison.VERDICT_NOT_DISTINGUISHABLE: STATUS_MEMBER,
    comparison.VERDICT_DISTINGUISHABLE: STATUS_EXCLUDED,
}


class LeaderSetError(comparison.ComparisonInputError):
    """The bundle cannot produce its leader-set records."""


@dataclass(frozen=True)
class Subject:
    """One local batch: a run id and the model it ran, with its rows."""

    run_id: str
    model_id: str
    rows: tuple[dict[str, Any], ...] = field(repr=False)
    score: float | None
    score_field: str | None
    fiche_hash: str
    grouping_values: dict[str, Any]
    grouping_not_recorded: tuple[str, ...]

    @property
    def side(self) -> comparison.Side:
        return comparison.Side(self.run_id, {SUBJECT_SELECTOR_FIELD: self.model_id})

    @property
    def sort_key(self) -> tuple[str, str]:
        return (self.run_id, self.model_id)


@dataclass(frozen=True)
class Group:
    """The local subjects of one suite on one machine class."""

    suite_id: str
    suite_version: str
    subjects: tuple[Subject, ...]

    @property
    def grouping_values(self) -> dict[str, Any]:
        return self.subjects[0].grouping_values

    @property
    def grouping_not_recorded(self) -> tuple[str, ...]:
        return self.subjects[0].grouping_not_recorded

    def reference(self) -> Subject | None:
        """The best scored subject by the tie rule, `None` when none is scored."""
        scored = [subject for subject in self.subjects if subject.score is not None]
        if not scored:
            return None
        top = max(subject.score for subject in scored if subject.score is not None)
        return min(
            (subject for subject in scored if subject.score == top),
            key=lambda subject: subject.sort_key,
        )


def _single(rows: Sequence[Mapping[str, Any]], key: str) -> Any:
    """The one value `key` takes across `rows`, `None` when missing or mixed."""
    values = {json.dumps(row.get(key), sort_keys=True) for row in rows}
    return json.loads(next(iter(values))) if len(values) == 1 else None


def _suite_score(
    run_id: str, model_id: str, rows: Sequence[Mapping[str, Any]]
) -> tuple[float | None, str | None]:
    """The subject's published suite score and the field it is read from.

    A batch completed by `--resume` carries its score on the completing rows
    and none on the partial ones, so the score is the one non-null value its
    rows carry; a batch left partial carries none.
    """
    kinds = {comparison.scoring_kind(row) for row in rows}
    kind = next(iter(kinds)) if len(kinds) == 1 else None
    score_field = SCORE_FIELD_BY_SCORING_KIND.get(kind) if kind else None
    if score_field is None:
        return None, None
    scores = {row[score_field] for row in rows if row.get(score_field) is not None}
    if len(scores) > 1:
        raise LeaderSetError(
            f"run {run_id} ({model_id}) publishes more than one {score_field}: "
            + ", ".join(str(score) for score in sorted(scores))
        )
    return (next(iter(scores)) if scores else None), score_field


def machine_class(fiche: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    """The grouping values a fiche records, and the grouping fields it does not."""
    values = {key: fiche[key] for key in MACHINE_CLASS_FIELDS if key in fiche}
    not_recorded = tuple(key for key in MACHINE_CLASS_FIELDS if key not in fiche)
    return values, not_recorded


def local_subjects(
    rows: Sequence[Mapping[str, Any]], fiche_registry_dir: Path
) -> tuple[list[Subject], list[str]]:
    """Every local subject the rows hold, and why each unplaceable one is not.

    A subject is unplaceable when its rows do not name one suite or one fiche,
    or its fiche does not resolve: it has no group, so no leader set.
    """
    batches: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("provider") != PROVIDER_LOCAL:
            continue
        key = (str(row.get("run_id")), str(row.get(SUBJECT_SELECTOR_FIELD)))
        batches.setdefault(key, []).append(dict(row))
    subjects: list[Subject] = []
    unplaced: list[str] = []
    for (run_id, model_id), batch in sorted(batches.items()):
        name = f"run {run_id} ({model_id})"
        suite_id = _single(batch, "suite_id")
        suite_version = _single(batch, "suite_version")
        fiche_hash = _single(batch, "fiche_hash")
        if suite_id is None or suite_version is None:
            unplaced.append(f"{name}: its rows do not name one suite id and version")
            continue
        if not isinstance(fiche_hash, str):
            unplaced.append(f"{name}: its rows do not cite one fiche")
            continue
        fiche = read_fiche(fiche_hash, fiche_registry_dir)
        if fiche is None:
            unplaced.append(f"{name}: its fiche {fiche_hash} does not resolve")
            continue
        values, not_recorded = machine_class(fiche)
        score, score_field = _suite_score(run_id, model_id, batch)
        subjects.append(
            Subject(
                run_id=run_id,
                model_id=model_id,
                rows=tuple(batch),
                score=score,
                score_field=score_field,
                fiche_hash=fiche_hash,
                grouping_values=values,
                grouping_not_recorded=not_recorded,
            )
        )
    return subjects, unplaced


def group_subjects(subjects: Sequence[Subject]) -> list[Group]:
    """The subjects by suite and machine class, in a stable order."""
    groups: dict[tuple[str, str, str, tuple[str, ...]], list[Subject]] = {}
    for subject in subjects:
        first = subject.rows[0]
        key = (
            str(first["suite_id"]),
            str(first["suite_version"]),
            json.dumps(subject.grouping_values, sort_keys=True),
            subject.grouping_not_recorded,
        )
        groups.setdefault(key, []).append(subject)
    return [
        Group(key[0], key[1], tuple(sorted(members, key=lambda s: s.sort_key)))
        for key, members in sorted(groups.items())
    ]


def leader_comparisons(
    group: Group,
) -> list[tuple[comparison.Side, comparison.Side]]:
    """The reference against every other subject of the group."""
    reference = group.reference()
    if reference is None:
        return []
    return [
        (reference.side, subject.side)
        for subject in group.subjects
        if subject is not reference
    ]


def _side_key(
    reference: comparison.Side, candidate: comparison.Side
) -> tuple[str, str, str, str]:
    return comparison.member_key(
        {
            "reference_run_id": reference.run_id,
            "reference_selector": dict(reference.selector),
            "candidate_run_id": candidate.run_id,
            "candidate_selector": dict(candidate.selector),
        }
    )


def _subject_entry(subject: Subject) -> dict[str, Any]:
    return {
        "run_id": subject.run_id,
        "model_id": subject.model_id,
        "roster_entry_id": _single(subject.rows, "roster_entry_id"),
        "suite_score": subject.score,
    }


def _not_compared_reason(member: Mapping[str, Any]) -> str:
    if member["refusal"]:
        return "refused on " + ", ".join(
            f"{entry['field']} ({entry['reason']})" for entry in member["refusal"]
        )
    if member["observation_reason"]:
        return f"an observation, not a test: {member['observation_reason']}"
    return f"no test: {member['result']['p_value_null_reason']}"


def _compared_entry(subject: Subject, member: Mapping[str, Any]) -> dict[str, Any]:
    status = _STATUS_BY_VERDICT.get(member["verdict"], STATUS_NOT_COMPARED)
    return {
        **_subject_entry(subject),
        "role": ROLE_COMPARED,
        "status": status,
        "verdict": member["verdict"],
        "comparison_kind": member["comparison_kind"],
        "adjusted_p_value": member["adjusted_p_value"],
        "refused_fields": [entry["field"] for entry in member["refusal"]],
        "not_compared_reason": (
            _not_compared_reason(member) if status == STATUS_NOT_COMPARED else None
        ),
    }


def build_record(
    group: Group,
    family: Mapping[str, Any] | None,
    *,
    rows_source: str,
    supersedes: Sequence[str] = (),
) -> dict[str, Any]:
    """The leader-set record of one group, read from its family record.

    `family` is `None` only for a set of one, where no comparison ran.
    """
    reference = group.reference()
    if reference is None:
        raise LeaderSetError(
            f"{group.suite_id}@{group.suite_version}: no local subject of the "
            "group publishes a suite score, so none is the best"
        )
    others = [subject for subject in group.subjects if subject is not reference]
    if others and family is None:
        raise LeaderSetError("a group of several subjects reads a family record")
    members = (
        {comparison.member_key(member): member for member in family["members"]}
        if family is not None
        else {}
    )
    entries = [
        {
            **_subject_entry(reference),
            "role": ROLE_REFERENCE,
            "status": STATUS_MEMBER,
            "verdict": None,
            "comparison_kind": None,
            "adjusted_p_value": None,
            "refused_fields": [],
            "not_compared_reason": None,
        }
    ]
    for subject in others:
        # Either direction: the verdict reads a two-sided p, so a comparison
        # the family already holds the other way round is the same test.
        member = members.get(_side_key(reference.side, subject.side)) or members.get(
            _side_key(subject.side, reference.side)
        )
        if member is None:
            raise LeaderSetError(
                f"family {family['family_id'][:12] if family else None} holds no "
                f"comparison of {subject.run_id} against {reference.run_id}"
            )
        entries.append(_compared_entry(subject, member))
    counts = {
        status: sum(1 for entry in entries if entry["status"] == status)
        for status in (STATUS_MEMBER, STATUS_EXCLUDED, STATUS_NOT_COMPARED)
    }
    tied = [
        {"run_id": subject.run_id, "model_id": subject.model_id}
        for subject in group.subjects
        if subject.score is not None and subject.score == reference.score
    ]
    all_rows = [row for subject in group.subjects for row in subject.rows]
    compared = bool(others)
    body: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "record_version": RECORD_VERSION,
        "suite_id": group.suite_id,
        "suite_version": group.suite_version,
        "suite_level": _single(all_rows, "suite_level"),
        "task_suite": _single(all_rows, "task_suite"),
        "grouping_fields": ["suite_id", "suite_version", *MACHINE_CLASS_FIELDS],
        "grouping_values": dict(group.grouping_values),
        "grouping_not_recorded": list(group.grouping_not_recorded),
        "machine_class_rule": MACHINE_CLASS_RULE,
        "local_only_rule": LOCAL_ONLY_RULE,
        "score_field": reference.score_field,
        "reference": {
            "run_id": reference.run_id,
            "model_id": reference.model_id,
            "suite_score": reference.score,
        },
        "tied_at_top": tied,
        "tie_rule": TIE_RULE,
        "membership_rule": MEMBERSHIP_RULE,
        "comparison_ran": compared,
        "no_comparison_reason": None if compared else NO_COMPARISON_REASON,
        "family_id": family["family_id"] if compared and family else None,
        "alpha": family["alpha"] if compared and family else None,
        "subjects": entries,
        "member_count": counts[STATUS_MEMBER],
        "excluded_count": counts[STATUS_EXCLUDED],
        "not_compared_count": counts[STATUS_NOT_COMPARED],
        "incomplete": counts[STATUS_NOT_COMPARED] > 0,
        "incomplete_reason": (
            f"{counts[STATUS_NOT_COMPARED]} subject(s) not compared: whether "
            "they belong to the set is unknown"
            if counts[STATUS_NOT_COMPARED]
            else None
        ),
        "rows_source": rows_source,
    }
    return _identified(body, supersedes)


def _canonical(record: Mapping[str, Any]) -> str:
    return json.dumps(record, indent=2, sort_keys=True) + "\n"


def _identified(body: Mapping[str, Any], supersedes: Sequence[str]) -> dict[str, Any]:
    # Each id sits under its own `leader_set_id` key, so it reads as an id.
    record = {
        **body,
        "supersedes": [
            {"leader_set_id": record_id} for record_id in sorted(supersedes)
        ],
    }
    record["leader_set_id"] = hashlib.sha256(_canonical(record).encode()).hexdigest()
    return record


def record_text(record: Mapping[str, Any]) -> str:
    """The exact text a leader-set record file holds."""
    return _canonical(record)


def group_key(record: Mapping[str, Any]) -> tuple[Any, Any, str, tuple[str, ...]]:
    """The group a record belongs to: its suite and machine class."""
    return (
        record["suite_id"],
        record["suite_version"],
        json.dumps(record["grouping_values"], sort_keys=True),
        tuple(record["grouping_not_recorded"]),
    )


def superseded_ids(record: Mapping[str, Any]) -> list[str]:
    return [entry["leader_set_id"] for entry in record.get("supersedes", [])]


def same_content(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    """Two records equal but for their id and the ids they supersede."""
    ignored = ("leader_set_id", "supersedes")
    return {k: v for k, v in first.items() if k not in ignored} == {
        k: v for k, v in second.items() if k not in ignored
    }


def read_leader_sets(directory: Path) -> list[dict[str, Any]]:
    """Every leader-set record published under `directory`."""
    records = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise LeaderSetError(f"{path} is not JSON: {error}") from error
        if isinstance(record, dict) and record.get("record_type") == RECORD_TYPE:
            records.append(record)
    return records


def current_leader_sets(directory: Path) -> list[dict[str, Any]]:
    """The records no other record supersedes: one current record per group."""
    records = read_leader_sets(directory)
    superseded = {
        record_id for record in records for record_id in superseded_ids(record)
    }
    return sorted(
        (record for record in records if record["leader_set_id"] not in superseded),
        key=lambda record: (group_key(record), record["leader_set_id"]),
    )


def resolve_record(
    fresh: Mapping[str, Any], published: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], bool]:
    """The record to publish for a group, and whether it is already published.

    A published record of the group with equal content is returned as is (a
    re-run is identical); otherwise the fresh record supersedes every current
    record of its group by id. None is ever edited.
    """
    same_group = [
        record for record in published if group_key(record) == group_key(fresh)
    ]
    for record in same_group:
        if same_content(record, fresh):
            return dict(record), True
    superseded = {i for record in same_group for i in superseded_ids(record)}
    heads = sorted(
        record["leader_set_id"]
        for record in same_group
        if record["leader_set_id"] not in superseded
    )
    body = {
        key: value
        for key, value in fresh.items()
        if key not in ("leader_set_id", "supersedes")
    }
    return _identified(body, heads), False


def default_output_path(record: Mapping[str, Any], directory: Path) -> Path:
    name = (
        f"{record['suite_id']}@{record['suite_version']}."
        f"{record['leader_set_id'][:12]}.json"
    )
    return directory / name


# --------------------------------------------------------------------------
# The analysis command's leader-set run


def _suite_family(
    rows: Sequence[Mapping[str, Any]],
    suite: tuple[str, str],
    needed: Sequence[tuple[comparison.Side, comparison.Side]],
    published: Sequence[Mapping[str, Any]],
    *,
    alpha: float,
    rows_source: str,
) -> dict[str, Any]:
    """The suite's family grown by the leader comparisons it does not hold yet.

    The declaration is every comparison of the family's current record plus
    the leader comparisons, so the family only grows and Holm runs over the
    whole closed family.
    """
    family = [
        record
        for record in published
        if comparison.family_key(record)
        == (*suite, LEADER_DIMENSION, comparison.QUANTITY_SCORE)
    ]
    current = set(comparison.heads(family))
    declared: dict[
        tuple[str, str, str, str], tuple[comparison.Side, comparison.Side]
    ] = {}
    for record in family:
        if record["family_id"] not in current:
            continue
        for member in record["members"]:
            pair = (
                comparison.Side(
                    member["reference_run_id"], member["reference_selector"]
                ),
                comparison.Side(
                    member["candidate_run_id"], member["candidate_selector"]
                ),
            )
            declared[comparison.member_key(member)] = pair
    for reference, candidate in needed:
        # A pair the family holds in either direction is declared once, so
        # Holm never counts one comparison twice.
        if _side_key(candidate, reference) not in declared:
            declared.setdefault(_side_key(reference, candidate), (reference, candidate))
    members = [
        comparison.compare_sides(
            comparison.select_side(rows, reference),
            comparison.select_side(rows, candidate),
            reference,
            candidate,
            dimension=LEADER_DIMENSION,
            alpha=alpha,
        )
        for reference, candidate in declared.values()
    ]
    record, successors = comparison.resolve_family_record(
        members, published, alpha=alpha, rows_source=rows_source
    )
    if successors:
        raise LeaderSetError(
            f"the family this run declares for {suite[0]}@{suite[1]} is the "
            f"published record {record['family_id'][:12]}, superseded by "
            + ", ".join(i[:12] for i in successors)
            + ": a leader set reads only a current family"
        )
    return record


def publish(
    rows: Sequence[Mapping[str, Any]],
    *,
    rows_source: str,
    records_dir: Path,
    leader_sets_dir: Path,
    fiche_registry_dir: Path,
    alpha: float,
    echo: Callable[[str], None] = print,
) -> int:
    """Write every suite's grown family and every group's leader-set record.

    Every record is built before any is written, and an existing file with
    different content refuses the whole run (exit 1, nothing written).
    """
    try:
        subjects, unplaced = local_subjects(rows, fiche_registry_dir)
        groups = group_subjects(subjects)
        scored = [group for group in groups if group.reference() is not None]
        for group in groups:
            if group.reference() is None:
                print(
                    f"{group.suite_id}@{group.suite_version}: no local subject "
                    "publishes a suite score, so no leader set",
                    file=sys.stderr,
                )
        for reason in unplaced:
            print(f"not placed in any group: {reason}", file=sys.stderr)
        published_families = comparison.read_family_records(records_dir)
        families: dict[tuple[str, str], dict[str, Any]] = {}
        for suite in sorted(
            {(group.suite_id, group.suite_version) for group in scored}
        ):
            needed = [
                pair
                for group in scored
                if (group.suite_id, group.suite_version) == suite
                for pair in leader_comparisons(group)
            ]
            if needed:
                families[suite] = _suite_family(
                    rows,
                    suite,
                    needed,
                    published_families,
                    alpha=alpha,
                    rows_source=rows_source,
                )
        published_sets = read_leader_sets(leader_sets_dir)
        writes: list[tuple[Path, str, str]] = []
        for family in families.values():
            path = comparison.default_output_path(family, records_dir)
            writes.append((path, comparison.record_text(family), _family_line(family)))
        for group in scored:
            fresh = build_record(
                group,
                families.get((group.suite_id, group.suite_version)),
                rows_source=rows_source,
            )
            record, _ = resolve_record(fresh, published_sets)
            path = default_output_path(record, leader_sets_dir)
            writes.append((path, record_text(record), _leader_line(record)))
    except comparison.ComparisonInputError as error:
        print(str(error), file=sys.stderr)
        return 1
    for path, text, _ in writes:
        if path.exists() and path.read_text(encoding="utf-8") != text:
            print(
                f"{path} is already published with different content: a "
                "record is immutable; write a new one",
                file=sys.stderr,
            )
            return 1
    for path, text, line in writes:
        status = "unchanged" if path.exists() else "written"
        if status == "written":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        echo(f"{path} {status}: {line}")
    if not writes:
        echo("no local subject in the rows: no leader set")
    return 0


def _family_line(record: Mapping[str, Any]) -> str:
    supersedes = ", ".join(i[:12] for i in comparison.superseded_ids(record))
    return (
        f"family {record['family_id'][:12]} of {record['family_size']} "
        f"({record['tested_count']} tested, {record['refused_count']} refused)"
        + (f"; supersedes {supersedes}" if supersedes else "")
    )


def _leader_line(record: Mapping[str, Any]) -> str:
    members = ", ".join(
        f"{entry['run_id'][:8]} {entry['model_id']}"
        for entry in record["subjects"]
        if entry["status"] == STATUS_MEMBER
    )
    supersedes = ", ".join(i[:12] for i in superseded_ids(record))
    return (
        f"leader set {record['leader_set_id'][:12]}: members {members}; "
        f"{record['excluded_count']} excluded, "
        f"{record['not_compared_count']} not compared"
        + ("; incomplete" if record["incomplete"] else "")
        + (f"; supersedes {supersedes}" if supersedes else "")
    )

"""The campaign declaration, the run check and the completeness command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import campaigns, engines, prompt_variants
from wave_local_ai_v2.campaigns import (
    CampaignError,
    check_run,
    completeness,
    declaration_path,
    load_declaration,
    require_run_campaign,
)
from wave_local_ai_v2.settings import Settings

CAMPAIGN_ID = "engine-variant-test"
ENTRIES = ["qwen3-0.6b-q8", "qwen3-1.7b-q8"]
SUITES = ["classification-support-routing", "translation-business-short-form"]
BASELINE = prompt_variants.resolve("baseline", "1")


def _declaration(**overrides: Any) -> dict[str, Any]:
    return {
        "campaign_id": CAMPAIGN_ID,
        "description": "Test campaign.",
        "engines": ["llama.cpp"],
        "prompt_variants": [{"id": "baseline", "version": "1"}],
        "roster_entries": list(ENTRIES),
        "suites": list(SUITES),
        "machine": {"machine_id": "laptop-mobile-gpu", "compute_mode": "gpu"},
        "exclusions": [],
        **overrides,
    }


def _write(
    directory: Path, declaration: dict[str, Any], stem: str = CAMPAIGN_ID
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem}.json"
    path.write_text(json.dumps(declaration), encoding="utf-8")
    return path


def _load(tmp_path: Path, **overrides: Any) -> campaigns.CampaignDeclaration:
    return load_declaration(_write(tmp_path / "campaigns", _declaration(**overrides)))


def _row(entry: str, suite: str, run_id: str, **overrides: Any) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "campaign_id": CAMPAIGN_ID,
        "engine_id": "llama.cpp",
        "prompt_variant_id": "baseline",
        "prompt_variant_version": "1",
        "roster_entry_id": entry,
        "suite_id": suite,
        "machine_id": "laptop-mobile-gpu",
        "compute_mode": "gpu",
        **overrides,
    }


def _full_matrix() -> list[dict[str, Any]]:
    rows = []
    for index, (entry, suite) in enumerate(
        (entry, suite) for entry in ENTRIES for suite in SUITES
    ):
        # Two items per batch: a cell lists its run once.
        rows += [_row(entry, suite, f"run-{index}")] * 2
    return rows


# --- declaration ---------------------------------------------------------


def test_a_valid_declaration_loads_every_dimension(tmp_path: Path) -> None:
    declaration = _load(tmp_path)

    assert declaration.campaign_id == CAMPAIGN_ID
    assert declaration.engines == ("llama.cpp",)
    assert declaration.prompt_variants == (("baseline", "1"),)
    assert (declaration.machine_id, declaration.compute_mode) == (
        "laptop-mobile-gpu",
        "gpu",
    )
    assert len(declaration.cells()) == 1 * 1 * 2 * 2


def test_three_engines_are_refused_naming_them(tmp_path: Path) -> None:
    with pytest.raises(CampaignError, match="3 engines .*llama.cpp, ollama, vllm"):
        _load(tmp_path, engines=["llama.cpp", "ollama", "vllm"])


def test_five_variants_are_refused_naming_them(tmp_path: Path) -> None:
    variants = [{"id": f"variant-{n}", "version": "1"} for n in range(5)]

    with pytest.raises(CampaignError, match="5 prompt variants .*variant-4@1"):
        _load(tmp_path, prompt_variants=variants)


CONSTRAINED = [
    {"id": "baseline", "version": "1"},
    {"id": "constrained_output", "version": "1"},
]


def _engines_declaring(tmp_path: Path, mechanisms: dict[str, Any]) -> Path:
    raw = json.loads(Path(engines.DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"))
    raw["engines"]["llama.cpp"]["constraint_mechanisms"] = mechanisms
    path = tmp_path / "engines.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_the_constrained_variant_loads_on_an_engine_declaring_its_mechanism(
    tmp_path: Path,
) -> None:
    declaration = _load(tmp_path, prompt_variants=CONSTRAINED)

    assert ("constrained_output", "1") in declaration.prompt_variants


def test_the_constrained_variant_on_an_engine_declaring_none_is_refused(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path / "campaigns", _declaration(prompt_variants=CONSTRAINED))

    with pytest.raises(
        CampaignError,
        match="'constrained_output'.*gbnf, but engine 'llama.cpp' declares "
        "constraint mechanisms: none",
    ):
        load_declaration(path, engines_path=_engines_declaring(tmp_path, {}))


def test_an_unconstrained_variant_loads_on_an_engine_declaring_none(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path / "campaigns", _declaration())

    declaration = load_declaration(path, engines_path=_engines_declaring(tmp_path, {}))

    assert declaration.prompt_variants == (("baseline", "1"),)


@pytest.mark.parametrize(
    ("overrides", "named"),
    [
        ({"engines": ["ollama"]}, "engine id.*absent from the registry: ollama"),
        (
            {"prompt_variants": [{"id": "terse", "version": "1"}]},
            "prompt variant 'terse' is not in the registry",
        ),
        (
            {"prompt_variants": [{"id": "baseline", "version": "9"}]},
            "no registered version '9'",
        ),
        (
            {"roster_entries": ["qwen3-0.6b-q8", "no-such-entry"]},
            "roster entry id.*absent from the registry: no-such-entry",
        ),
        ({"suites": ["no-such-suite"]}, "suite id.*absent.*no-such-suite"),
        (
            {"machine": {"machine_id": "no-such-box", "compute_mode": "gpu"}},
            "'no-such-box' is not a declared machine",
        ),
        (
            {"machine": {"machine_id": "laptop-mobile-gpu", "compute_mode": "turbo"}},
            "compute mode 'turbo'",
        ),
        (
            {"machine": {"machine_id": "pro-pc-no-gpu", "compute_mode": "gpu"}},
            "gpu on machine 'pro-pc-no-gpu'",
        ),
    ],
)
def test_an_id_absent_from_its_registry_is_refused_naming_it(
    tmp_path: Path, overrides: dict[str, Any], named: str
) -> None:
    with pytest.raises(CampaignError, match=named):
        _load(tmp_path, **overrides)


def test_an_incomplete_engine_entry_refuses_the_declaration(tmp_path: Path) -> None:
    raw = json.loads(Path(engines.DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"))
    del raw["engines"]["llama.cpp"]["lifecycle"]
    incomplete = tmp_path / "engines.json"
    incomplete.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(CampaignError, match="engine registry refuses.*lifecycle"):
        load_declaration(
            _write(tmp_path / "campaigns", _declaration()), engines_path=incomplete
        )


@pytest.mark.parametrize(
    ("overrides", "named"),
    [
        ({"engines": []}, "engines must be a non-empty list"),
        (
            {"suites": [SUITES[0], SUITES[0]]},
            "declares classification-support-routing twice",
        ),
        (
            {"prompt_variants": [{"id": "baseline", "version": "1"}] * 2},
            "declares baseline@1 twice",
        ),
        ({"prompt_variants": [{"id": "baseline"}]}, "each variant is"),
        ({"machine": "laptop-mobile-gpu"}, "machine is"),
        ({"description": ""}, "description must be a non-empty string"),
        ({"harnesses": ["direct"]}, "unknown key.*harnesses"),
        ({"exclusions": {}}, "exclusions must be a list"),
    ],
)
def test_a_malformed_declaration_is_refused(
    tmp_path: Path, overrides: dict[str, Any], named: str
) -> None:
    with pytest.raises(CampaignError, match=named):
        _load(tmp_path, **overrides)


def test_a_missing_key_is_refused_naming_it(tmp_path: Path) -> None:
    declaration = _declaration()
    del declaration["suites"]

    with pytest.raises(CampaignError, match="missing: suites"):
        load_declaration(_write(tmp_path, declaration))


def test_the_file_name_and_the_id_must_match(tmp_path: Path) -> None:
    with pytest.raises(CampaignError, match="file name and the id must match"):
        load_declaration(_write(tmp_path, _declaration(), stem="another-name"))


def test_the_no_campaign_id_is_reserved(tmp_path: Path) -> None:
    with pytest.raises(CampaignError, match="'none' is reserved"):
        load_declaration(
            _write(tmp_path, _declaration(campaign_id="none"), stem="none")
        )


@pytest.mark.parametrize("content", ["not json", "[]"])
def test_an_unreadable_declaration_is_refused(tmp_path: Path, content: str) -> None:
    path = tmp_path / f"{CAMPAIGN_ID}.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(CampaignError, match=str(path.name)):
        load_declaration(path)


def test_an_absent_declaration_is_refused(tmp_path: Path) -> None:
    with pytest.raises(CampaignError, match="not readable"):
        load_declaration(tmp_path / "absent.json")


def test_an_unreadable_roster_is_refused(tmp_path: Path) -> None:
    with pytest.raises(CampaignError, match="roster refuses"):
        load_declaration(
            _write(tmp_path, _declaration()), roster_path=tmp_path / "absent.json"
        )


def test_a_campaign_id_cannot_walk_out_of_its_directory(tmp_path: Path) -> None:
    with pytest.raises(CampaignError, match="does not name a file inside"):
        declaration_path("../escape", tmp_path / "campaigns")


@pytest.mark.parametrize(
    ("exclusion", "named"),
    [
        ({"outcome": "skipped", "reason": "r", "evidence": "e"}, "outcome must be"),
        ({"outcome": "dropped", "reason": "", "evidence": "e"}, "reason must be"),
        ({"outcome": "dropped", "reason": "r"}, "evidence must be"),
        (
            {"outcome": "dropped", "reason": "r", "evidence": "e", "suite_id": "x"},
            "suite_id 'x' is not declared",
        ),
        (
            {
                "outcome": "dropped",
                "reason": "r",
                "evidence": "e",
                "prompt_variant": {"id": "baseline", "version": "2"},
            },
            "baseline@2 is not declared",
        ),
        (
            {"outcome": "dropped", "reason": "r", "evidence": "e", "why": 1},
            "unknown key",
        ),
        ("dropped", "must be an object"),
    ],
)
def test_a_malformed_exclusion_is_refused(
    tmp_path: Path, exclusion: Any, named: str
) -> None:
    with pytest.raises(CampaignError, match=named):
        _load(tmp_path, exclusions=[exclusion])


def test_a_cell_excluded_twice_is_refused(tmp_path: Path) -> None:
    refused = {
        "outcome": "refused",
        "reason": "needs 18 GB RAM",
        "evidence": "refusal record",
        "roster_entry_id": ENTRIES[1],
    }
    dropped = {
        "outcome": "dropped",
        "reason": "no mechanism",
        "evidence": "spike",
        "suite_id": SUITES[0],
    }

    with pytest.raises(CampaignError, match="covered by 2 exclusions"):
        _load(tmp_path, exclusions=[refused, dropped])


# --- run check ------------------------------------------------------------


def _check(declaration: campaigns.CampaignDeclaration, **overrides: Any) -> None:
    arguments: dict[str, Any] = {
        "engine_id": "llama.cpp",
        "prompt_variant": BASELINE,
        "roster_entry_id": ENTRIES[0],
        "suite_id": SUITES[0],
        "machine_id": "laptop-mobile-gpu",
        "compute_mode": "gpu",
        **overrides,
    }
    check_run(declaration, **arguments)


def test_a_run_inside_the_declaration_passes(tmp_path: Path) -> None:
    _check(_load(tmp_path))
    _check(_load(tmp_path), suite_id=None)


@pytest.mark.parametrize(
    ("overrides", "named"),
    [
        ({"engine_id": "ollama"}, "engine 'ollama' is not declared"),
        ({"roster_entry_id": "qwen3-4b-q4km"}, "roster entry 'qwen3-4b-q4km'"),
        ({"suite_id": "judge-probe-open-ended"}, "suite 'judge-probe-open-ended'"),
        ({"compute_mode": "cpu_only"}, "mode 'cpu_only' is not the declared"),
        ({"machine_id": "tower-desktop-gpu"}, "machine 'tower-desktop-gpu'"),
        ({"cloud_providers": {"mistral"}}, "cloud provider.*mistral"),
    ],
)
def test_a_run_outside_the_declaration_is_refused_naming_it(
    tmp_path: Path, overrides: dict[str, Any], named: str
) -> None:
    with pytest.raises(CampaignError, match=f"campaign '{CAMPAIGN_ID}'.*{named}"):
        _check(_load(tmp_path), **overrides)


def test_a_run_under_an_undeclared_variant_is_refused(
    tmp_path: Path, marking_variant: str
) -> None:
    with pytest.raises(CampaignError, match=f"prompt variant {marking_variant}@1"):
        _check(_load(tmp_path), prompt_variant=prompt_variants.resolve(marking_variant))


def test_a_run_of_an_excluded_cell_is_refused(tmp_path: Path) -> None:
    declaration = _load(
        tmp_path,
        exclusions=[
            {
                "outcome": "dropped",
                "reason": "no constraint mechanism",
                "evidence": "spike",
                "suite_id": SUITES[1],
            }
        ],
    )

    with pytest.raises(
        CampaignError, match="declared dropped: no constraint mechanism"
    ):
        _check(declaration, suite_id=SUITES[1])


def _settings(tmp_path: Path, campaign_id: str | None) -> Settings:
    return Settings(
        slm_models_dir=tmp_path,
        llama_server_path=tmp_path,
        results_path=tmp_path / "runtime.jsonl",
        campaign_id=campaign_id,
        campaigns_dir=tmp_path / "campaigns",
    )


def test_a_run_with_no_campaign_records_none(tmp_path: Path) -> None:
    campaign_id = require_run_campaign(
        _settings(tmp_path, None),
        engine_id="anything",
        prompt_variant=BASELINE,
        roster_entry_id="anything",
        suite_id=None,
        machine_id="anything",
        compute_mode="anything",
    )

    assert campaign_id == "none"


def test_a_run_under_a_campaign_records_its_id(tmp_path: Path) -> None:
    _write(tmp_path / "campaigns", _declaration())

    campaign_id = require_run_campaign(
        _settings(tmp_path, CAMPAIGN_ID),
        engine_id="llama.cpp",
        prompt_variant=BASELINE,
        roster_entry_id=ENTRIES[0],
        suite_id=SUITES[0],
        machine_id="laptop-mobile-gpu",
        compute_mode="gpu",
    )

    assert campaign_id == CAMPAIGN_ID


def test_a_named_campaign_with_no_declaration_is_refused(tmp_path: Path) -> None:
    with pytest.raises(CampaignError, match="not readable"):
        require_run_campaign(
            _settings(tmp_path, "undeclared"),
            engine_id="llama.cpp",
            prompt_variant=BASELINE,
            roster_entry_id=ENTRIES[0],
            suite_id=SUITES[0],
            machine_id="laptop-mobile-gpu",
            compute_mode="gpu",
        )


# --- completeness ---------------------------------------------------------


def test_a_full_matrix_fills_every_cell_with_its_run(tmp_path: Path) -> None:
    listing = completeness(_load(tmp_path), _full_matrix())

    assert [line.status for line in listing] == ["filled"] * 4
    assert [line.run_ids for line in listing] == [
        ("run-0",),
        ("run-1",),
        ("run-2",),
        ("run-3",),
    ]


@pytest.mark.parametrize(
    "stray",
    [
        {"campaign_id": "none"},
        {"campaign_id": "another-campaign"},
        {"compute_mode": "cpu_only"},
        {"machine_id": "tower-desktop-gpu"},
        {"prompt_variant_version": "2"},
    ],
)
def test_a_row_outside_the_campaign_fills_no_cell(
    tmp_path: Path, stray: dict[str, Any]
) -> None:
    rows = [_row(ENTRIES[0], SUITES[0], "stray-run", **stray)]

    listing = completeness(_load(tmp_path), rows)

    assert [line.status for line in listing] == ["empty"] * 4


def test_dropped_and_refused_cells_are_listed_with_their_reason(tmp_path: Path) -> None:
    declaration = _load(
        tmp_path,
        exclusions=[
            {
                "outcome": "refused",
                "reason": "needs 18 GB of RAM in cpu_only",
                "evidence": "refusal record",
                "roster_entry_id": ENTRIES[1],
            },
            {
                "outcome": "dropped",
                "reason": "no constraint mechanism",
                "evidence": "spike",
                "roster_entry_id": ENTRIES[0],
                "suite_id": SUITES[1],
            },
        ],
    )
    rows = [_row(ENTRIES[0], SUITES[0], "run-0")]

    listing = completeness(declaration, rows)

    assert [line.status for line in listing] == [
        "filled",
        "dropped",
        "refused",
        "refused",
    ]
    assert "dropped: no constraint mechanism (evidence: spike)" in listing[1].render()
    assert "refused: needs 18 GB of RAM" in listing[2].render()


def test_an_excluded_cell_holding_rows_is_contradicted(tmp_path: Path) -> None:
    declaration = _load(
        tmp_path,
        exclusions=[
            {
                "outcome": "dropped",
                "reason": "no mechanism",
                "evidence": "spike",
                "suite_id": SUITES[1],
            }
        ],
    )

    listing = completeness(declaration, _full_matrix())

    assert [line.status for line in listing] == [
        "filled",
        "contradicted",
        "filled",
        "contradicted",
    ]


# --- the command ----------------------------------------------------------


def _main(tmp_path: Path, rows: list[dict[str, Any]], **declaration: Any) -> int:
    _write(tmp_path / "campaigns", _declaration(**declaration))
    rows_path = tmp_path / "quality.jsonl"
    rows_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    try:
        campaigns.main(
            [
                "--campaign",
                CAMPAIGN_ID,
                "--campaigns-dir",
                str(tmp_path / "campaigns"),
                "--rows",
                str(rows_path),
            ]
        )
    except SystemExit as exit_:
        return int(exit_.code or 0)
    return 0


def test_the_command_passes_a_full_matrix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _main(tmp_path, _full_matrix()) == 0

    out = capsys.readouterr().out
    assert out.count("filled") == 4
    assert "runs=run-3" in out
    assert "4 declared cell(s), none empty" in out


def test_the_command_fails_naming_each_empty_cell(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = [row for row in _full_matrix() if row["run_id"] != "run-1"]

    assert _main(tmp_path, rows) == 1

    captured = capsys.readouterr()
    assert captured.out.count("empty") == 1
    assert (
        "empty cell engine=llama.cpp variant=baseline@1 "
        f"roster_entry={ENTRIES[0]} suite={SUITES[1]}"
    ) in captured.err


def test_a_dropped_cell_with_its_reason_passes_the_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = [row for row in _full_matrix() if row["run_id"] != "run-1"]
    dropped = {
        "outcome": "dropped",
        "reason": "no constraint mechanism",
        "evidence": "spike",
        "roster_entry_id": ENTRIES[0],
        "suite_id": SUITES[1],
    }

    assert _main(tmp_path, rows, exclusions=[dropped]) == 0

    assert "dropped: no constraint mechanism" in capsys.readouterr().out


def test_re_running_the_command_returns_the_same_listing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = _full_matrix()[2:]
    _main(tmp_path, rows)
    first = capsys.readouterr()
    _main(tmp_path, list(reversed(rows)))
    second = capsys.readouterr()

    assert first == second


def test_the_command_refuses_a_declaration_it_cannot_load(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _main(tmp_path, [], engines=["ollama"]) == 2
    assert "absent from the registry: ollama" in capsys.readouterr().err


def test_the_command_refuses_a_rows_file_that_does_not_exist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path / "campaigns", _declaration())
    monkeypatch.setenv("CAMPAIGNS_DIR", str(tmp_path / "campaigns"))
    monkeypatch.setenv("QUALITY_RESULTS_PATH", str(tmp_path / "absent.jsonl"))

    with pytest.raises(SystemExit) as exit_:
        campaigns.main(["--campaign", CAMPAIGN_ID])

    assert exit_.value.code == 2
    assert "absent.jsonl" in capsys.readouterr().err

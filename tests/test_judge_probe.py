import dataclasses
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2 import (
    agreement,
    google_client,
    judge,
    judge_backends,
    judge_probe,
    judge_protocol,
    mistral_client,
    row_contract,
)
from wave_local_ai_v2.judge_probe import JUDGE_PROBE_ITEMS
from wave_local_ai_v2.prompt_provenance import template_hash
from wave_local_ai_v2.results import append_row, read_rows
from wave_local_ai_v2.settings import DEFAULT_ROSTER_ENTRY_ID, Settings

FAKE_ROSTER_VERSION = 1

FAKE_ENERGY_RESULT = {
    "cpu_energy_kwh": 0.0003,
    "cpu_energy_method": "estimated_tdp",
    "gpu_energy_kwh": None,
    "gpu_energy_method": "unavailable",
    "ram_energy_kwh": 0.00012,
    "ram_energy_method": "estimated_constant",
    "energy_kwh": 0.00042,
}

GOOGLE_MODEL_INFO = {
    "version": "3.5-flash-lite-07-2026",
    "input_token_limit": 1_048_576,
}

# The subject family has to resolve for the independence rule to run at all,
# and the fixture's display_id is deliberately not one of MODEL_FAMILIES' own
# ids -- so the entry declares its family, which is the seam roster.family_of
# prefers.
FAKE_ROSTER = {
    "roster_version": FAKE_ROSTER_VERSION,
    "entries": {
        DEFAULT_ROSTER_ENTRY_ID: {
            "repo": "fake/repo",
            "revision": "main",
            "display_id": "Fake Model",
            "file": "fake.gguf",
            "quant": "UD-IQ4_XS",
            "sha256": "0" * 64,
            "family": "qwen",
            "architecture": {
                "kind": "moe",
                "expert_count": 40,
                "active_params_b": 3.1,
            },
            "server_flags": {
                "n_gpu_layers": 99,
                "context_size": 32768,
                "flash_attention": "on",
                "jinja": True,
                "parallel_slots": 1,
                "load_mode": "none",
                "sampler": {
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "top_k": 20,
                    "min_p": 0,
                    "presence_penalty": 1.5,
                },
            },
            "validated_host": {
                "n_cpu_moe": 37,
                "threads": 8,
                "fiche_summary": "fake fiche",
            },
        }
    },
}

# Ten local score pairs, then the cloud item's single Mistral score. Chosen so
# both judges vary (kappa is defined), most items sit within one point, and
# exactly one item -- index 8 -- is two points apart, so the contested rule
# and the headline exclusion are exercised rather than assumed.
LOCAL_MISTRAL_SCORES = ["5", "4", "3", "5", "4", "3", "5", "4", "3", "5"]
LOCAL_GOOGLE_SCORES = ["5", "4", "4", "5", "3", "3", "5", "4", "5", "5"]
CLOUD_MISTRAL_SCORE = "4"
CONTESTED_INDEX = 8


def _write_fake_roster(tmp_path: Path) -> Path:
    roster_path = tmp_path / "roster.json"
    roster_path.write_text(json.dumps(FAKE_ROSTER))
    return roster_path


def _mistral_reply(content: str) -> dict[str, object]:
    return {
        "content": content,
        "endpoint": mistral_client.CHAT_COMPLETIONS_URL,
        "finish_reason": "stop",
        "generated_tokens": 1,
        "prompt_tokens": 120,
        "total_tokens": 121,
    }


def _google_reply(content: str, generated_tokens: int = 1) -> dict[str, object]:
    return {
        "content": content,
        "endpoint": google_client.GENERATE_URL,
        "finish_reason": "STOP",
        "generated_tokens": generated_tokens,
        "prompt_tokens": 130,
        "total_tokens": 130 + generated_tokens,
        "model_version": GOOGLE_MODEL_INFO["version"],
    }


FAKE_CHAT_TEMPLATE = "{% for m in messages %}<|im_start|>{{ m.content }}{% endfor %}"


def _fake_render(prompt: str) -> str:
    return "<|im_start|>user\n" + prompt + " <|im_end|>"


def _local_post_router():
    """Route a stubbed local POST by endpoint: render, then answer."""

    def route(url, *args, **kwargs):
        if url.endswith("/apply-template"):
            payload: dict = {
                "prompt": _fake_render(kwargs["json"]["messages"][0]["content"])
            }
        else:
            payload = {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": ("Here is a clearer, more considerate version.")
                        },
                    }
                ],
                "usage": {"completion_tokens": 11, "prompt_tokens": 23},
            }
        return MagicMock(
            status_code=200, json=lambda: payload, raise_for_status=lambda: None
        )

    return route


@pytest.fixture
def stubbed_probe(tmp_path, monkeypatch):
    """Stub every I/O boundary the probe touches: no process, no socket, no call."""
    monkeypatch.setattr("sys.argv", ["wave-local-ai-v2-judge-probe"])
    probe_path = tmp_path / "judge-probe-reference.jsonl"
    quality_results_path = tmp_path / "quality.jsonl"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True)
    (model_dir / FAKE_ROSTER["entries"][DEFAULT_ROSTER_ENTRY_ID]["file"]).write_text("")
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    fake_settings = Settings(
        slm_models_dir=model_dir,
        llama_server_path=server_path,
        results_path=tmp_path / "runtime.jsonl",
        quality_results_path=quality_results_path,
        judge_probe_reference_path=probe_path,
        roster_path=_write_fake_roster(tmp_path),
        fiche_registry_dir=tmp_path / "fiches",
        quality_reference_path=tmp_path / "quality-reference.jsonl",
        mistral_api_key="fake-key",  # pragma: allowlist secret
        google_api_key="fake-google-key",  # pragma: allowlist secret
    )

    # Mutable reply lists the tests reshape before calling _run. The mistral
    # list carries eleven entries (ten local items plus the cloud item); the
    # google one ten, since the Google judge never scores the Google subject.
    # Read cyclically rather than popped, so a test that runs the probe twice
    # (resume) does not exhaust them; one full run consumes each list exactly
    # once, so a single run's positions line up with the item order.
    replies = {
        "mistral_judge": [*LOCAL_MISTRAL_SCORES, CLOUD_MISTRAL_SCORE],
        "google_judge": list(LOCAL_GOOGLE_SCORES),
        "google_subject": "Dear client, Friday remains the delivery date.",
    }
    served = {"mistral_judge": 0, "google_judge": 0}

    def _next(queue_name: str) -> str:
        queue = replies[queue_name]
        content = queue[served[queue_name] % len(queue)]
        served[queue_name] += 1
        return str(content)

    def mistral_complete(prompt, api_key, **kwargs):
        return _mistral_reply(_next("mistral_judge"))

    def google_complete(prompt, api_key, **kwargs):
        # The judge call and the subject generation reach the same client
        # function; the cap each was sent is what tells them apart, and it is
        # a real difference (one integer versus open-ended prose), not a test
        # convenience.
        if kwargs["max_tokens"] == judge_probe.JUDGE_MAX_TOKENS:
            return _google_reply(_next("google_judge"))
        return _google_reply(str(replies["google_subject"]), generated_tokens=12)

    fake_process = MagicMock(pid=1234)
    patches = {
        "load_settings": patch(
            "wave_local_ai_v2.judge_probe.load_settings", return_value=fake_settings
        ),
        "probe_build": patch(
            "wave_local_ai_v2.judge_probe.build_probe.probe_build",
            return_value="b10537",
        ),
        "capture_fiche": patch(
            "wave_local_ai_v2.judge_probe.capture_fiche",
            return_value={
                "cpu": "x",
                "ram_gb": 32.0,
                "gpu_name": "y",
                "gpu_driver_version": "1.2.3",
                "os": "z",
                "cuda_ceiling": "12.4",
            },
        ),
        "running_server": patch("wave_local_ai_v2.judge_probe.server.running_server"),
        # The probe's subject generation goes through the shared local client
        # now: two POSTs per item (render, then answer) plus one /props GET
        # for the whole batch.
        "post": patch(
            "wave_local_ai_v2.local_client.requests.post",
            side_effect=_local_post_router(),
        ),
        "props": patch(
            "wave_local_ai_v2.local_client.requests.get",
            return_value=MagicMock(
                status_code=200,
                json=lambda: {"chat_template": FAKE_CHAT_TEMPLATE},
                raise_for_status=lambda: None,
            ),
        ),
        "mistral_check_model": patch(
            "wave_local_ai_v2.judge_probe.mistral_client.check_model_available",
            return_value=None,
        ),
        "google_check_model": patch(
            "wave_local_ai_v2.judge_probe.google_client.check_model_available",
            return_value=dict(GOOGLE_MODEL_INFO),
        ),
        "google_check_context_fits": patch(
            "wave_local_ai_v2.judge_probe.google_client.check_context_fits",
            return_value=None,
        ),
        # One patch per client function, shared by the judge backend and (for
        # google) the subject generation -- both reach the same module object.
        "mistral_complete": patch(
            "wave_local_ai_v2.mistral_client.complete_prompt",
            side_effect=mistral_complete,
        ),
        "google_complete": patch(
            "wave_local_ai_v2.google_client.complete_prompt",
            side_effect=google_complete,
        ),
        "energy": patch(
            "wave_local_ai_v2.judge_probe.measure_energy",
            side_effect=lambda fn, **kwargs: (fn(), dict(FAKE_ENERGY_RESULT)),
        ),
        # Otherwise every test would burn the configured pacing interval on
        # every one of the twenty-two paced calls.
        "sleep": patch("wave_local_ai_v2.judge_probe.time.sleep", return_value=None),
        "capture_provenance": patch(
            "wave_local_ai_v2.judge_probe.provenance.capture_provenance",
            return_value={
                "release_version": "v0.1.0",
                "commit_sha": "deadbeef",
                "tree_dirty": False,
            },
        ),
    }
    started = {name: p.start() for name, p in patches.items()}
    started["running_server"].return_value.__enter__.return_value = fake_process
    started["running_server"].return_value.__exit__.return_value = False

    yield probe_path, quality_results_path, started, replies

    for p in patches.values():
        p.stop()


# --------------------------------------------------------------------------
# The item set itself
# --------------------------------------------------------------------------


def test_the_item_set_is_ten_items_split_four_three_three() -> None:
    assert len(JUDGE_PROBE_ITEMS) == 10
    languages = [item["language"] for item in JUDGE_PROBE_ITEMS]
    assert languages.count("en") == 4
    assert languages.count("fr") == 3
    assert languages.count("de") == 3


def test_every_item_is_hand_written_uncontaminated_and_uniquely_identified() -> None:
    ids = [item["item_id"] for item in JUDGE_PROBE_ITEMS]
    assert len(set(ids)) == len(ids)
    for item in JUDGE_PROBE_ITEMS:
        assert item["provenance"] == "hand_written"
        assert item["contamination_risk"] is False
        assert item["prompt"].strip()


def test_no_item_carries_an_expected_label_or_any_scoring_key() -> None:
    # An item with a label would make the probe a task suite; the rubric is
    # the only scoring rule it has.
    forbidden = {"expected_label", "label", "expected", "answer", "scoring"}
    for item in JUDGE_PROBE_ITEMS:
        assert forbidden.isdisjoint(item.keys())


def test_no_two_items_share_the_same_prompt_text() -> None:
    prompts = [item["prompt"] for item in JUDGE_PROBE_ITEMS]
    assert len(set(prompts)) == len(prompts)


def test_the_named_cloud_subject_item_is_one_of_the_items() -> None:
    ids = {item["item_id"] for item in JUDGE_PROBE_ITEMS}
    assert judge_probe.CLOUD_SUBJECT_ITEM_ID in ids


# --------------------------------------------------------------------------
# The happy path, end to end
# --------------------------------------------------------------------------


def test_a_stubbed_run_writes_eleven_contract_valid_rows(stubbed_probe) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    rows = read_rows(probe_path)
    assert len(rows) == 11
    providers = [row["provider"] for row in rows]
    assert providers.count("local") == 10
    assert providers.count("google") == 1
    for row in rows:
        # Asserted explicitly as well as through append_row, so a contract
        # failure names the field rather than surfacing as a missing file.
        row_contract.validate_row("quality", row)
        assert row["schema_version"] == row_contract.SCHEMA_VERSION
        assert row["task_suite"] == "judge-probe"
        assert row["suite_id"] == judge_probe.SUITE_ID
        assert row["prompt_set_hash"] == judge_probe.PROMPT_SET_HASH


def test_the_ten_local_rows_carry_two_judges_and_one_batch_agreement(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    local_rows = [row for row in read_rows(probe_path) if row["provider"] == "local"]
    assert len(local_rows) == 10
    agreements = {json.dumps(row["agreement"], sort_keys=True) for row in local_rows}
    # One and the same batch figure on every row, never a per-item null.
    assert len(agreements) == 1
    for row in local_rows:
        assert row["single_judge"] is False
        assert row["single_judge_reason"] is None
        assert len(row["judges"]) == 2
        assert {record["provider"] for record in row["judges"]} == {
            "mistral",
            "google",
        }
        block = row["agreement"]
        assert block is not None
        assert block["statistic"] == agreement.AGREEMENT_STATISTIC_KAPPA_QUADRATIC
        assert block["value"] is not None
        assert block["value_null_reason"] is None
        assert block["n_items"] == 10
        assert block["n_items_excluded"] == 0
        assert row["agreement_statistic"] == block["statistic"]


def test_the_contested_item_is_marked_and_excluded_from_the_headline(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    rows_by_item = {
        row["item_id"]: row
        for row in read_rows(probe_path)
        if row["provider"] == "local"
    }
    contested_id = JUDGE_PROBE_ITEMS[CONTESTED_INDEX]["item_id"]
    contested_row = rows_by_item[contested_id]
    assert contested_row["contested"] is True
    assert contested_row["contested_reason"] == (
        agreement.CONTESTED_REASON_ORDINAL_DELTA
    )
    others = [row for iid, row in rows_by_item.items() if iid != contested_id]
    assert all(row["contested"] is False for row in others)
    # The headline is a batch figure too, and it excludes exactly the
    # contested item.
    assert {row["judged_headline_excluded_n"] for row in rows_by_item.values()} == {1}


def test_the_cloud_subject_row_is_flagged_single_judge_with_its_reason(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    google_rows = [row for row in read_rows(probe_path) if row["provider"] == "google"]
    assert len(google_rows) == 1
    row = google_rows[0]
    assert row["item_id"] == judge_probe.CLOUD_SUBJECT_ITEM_ID
    assert row["model_id"] == google_client.MODEL
    assert row["single_judge"] is True
    assert row["single_judge_reason"] == judge.SINGLE_JUDGE_REASON_CLOUD_SUBJECT
    assert row["agreement"] is None
    assert row["agreement_statistic"] is None
    assert len(row["judges"]) == 1
    assert row["judges"][0]["provider"] == "mistral"
    assert row["judges"][0]["model_id"] == mistral_client.MODEL
    assert row["judge_egress"]["providers"] == ["mistral"]
    assert row["judge_egress"]["judge_call_count"] == 1


def test_every_row_publishes_null_labels_and_a_real_subject_output(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    for row in read_rows(probe_path):
        assert row["expected_label"] is None
        assert row["predicted_label"] is None
        assert row["correct"] is None
        assert row["suite_accuracy"] is None
        assert row["language_breakdown"] is None
        assert row["subject_output"].strip()


def test_every_row_says_it_is_indicative_and_why(stubbed_probe) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    for row in read_rows(probe_path):
        assert row["indicative"] is True
        assert any("below the minimum of 20" in r for r in row["indicative_reasons"])


def test_every_row_carries_a_not_comparable_verdict_naming_why(stubbed_probe) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    for row in read_rows(probe_path):
        assert row["verdict"]["verdict"] == "not_comparable"
        assert row["verdict"]["reference_run_id"] is None
        assert "no label and no score" in row["verdict"]["reason"]


def test_all_eleven_rows_share_one_run_id_and_one_fiche(stubbed_probe) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    rows = read_rows(probe_path)
    assert len({row["run_id"] for row in rows}) == 1
    assert len({row["fiche_hash"] for row in rows}) == 1
    assert all(row["resumed"] is False for row in rows)


def test_the_local_server_is_launched_once_for_the_whole_probe(stubbed_probe) -> None:
    _, _, started, _ = stubbed_probe

    judge_probe._run()

    assert started["running_server"].call_count == 1
    # Two POSTs per item -- render, then answer -- and one /props GET for the
    # whole batch.
    assert started["post"].call_count == 2 * len(JUDGE_PROBE_ITEMS)
    assert started["props"].call_count == 1


def test_the_local_and_cloud_rows_record_their_own_call_paths(stubbed_probe) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    rows = read_rows(probe_path)
    for row in (r for r in rows if r["provider"] == "local"):
        assert row["endpoint"] == "/v1/chat/completions"
        assert row["prompt_template_id"] == "llamacpp-model-chat-template"
        assert row["prompt_template_hash"] == template_hash(FAKE_CHAT_TEMPLATE)
        assert row["prompt_capture"] == "reconstructed"
    for row in (r for r in rows if r["provider"] == "google"):
        assert row["endpoint"] == google_client.GENERATE_URL
        assert row["prompt_template_id"] == "google-generatecontent-user-part"
        assert row["prompt_template_hash"] is not None


def test_the_local_probe_row_publishes_the_rendered_prompt_and_the_policy(
    stubbed_probe,
) -> None:
    """The defect's own fact, on the second writer.

    The call-path fields above say the row was produced through a template;
    this says the string it published is the rendered one and not the item
    text `_build_row` falls back to when no prompt is passed. The policy is
    on every row of the batch, the cloud one included, because it is what the
    probe suite declared rather than what a provider did.
    """
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    prompts_by_item = {item["item_id"]: item["prompt"] for item in JUDGE_PROBE_ITEMS}
    rows = read_rows(probe_path)
    local_rows = [row for row in rows if row["provider"] == "local"]
    assert local_rows
    for row in local_rows:
        item_prompt = prompts_by_item[row["item_id"]]
        assert row["prompt"] == _fake_render(item_prompt)
        assert row["prompt"] != item_prompt
    for row in rows:
        assert row["thinking_policy"] == "disabled"


def test_every_generation_asks_for_open_ended_prose_not_a_label(
    stubbed_probe,
) -> None:
    _, _, started, _ = stubbed_probe

    judge_probe._run()

    chat_calls = [
        call
        for call in started["post"].call_args_list
        if call.args[0].endswith("/v1/chat/completions")
    ]
    assert len(chat_calls) == len(JUDGE_PROBE_ITEMS)
    for call in chat_calls:
        assert call.kwargs["json"]["max_tokens"] == judge_probe.MAX_OUTPUT_TOKENS
        assert call.kwargs["json"]["temperature"] == 0
    subject_calls = [
        call
        for call in started["google_complete"].call_args_list
        if call.kwargs["max_tokens"] != judge_probe.JUDGE_MAX_TOKENS
    ]
    assert len(subject_calls) == 1
    assert subject_calls[0].kwargs["max_tokens"] == judge_probe.MAX_OUTPUT_TOKENS


def test_the_judge_calls_are_paced_and_counted(stubbed_probe) -> None:
    _, _, started, _ = stubbed_probe

    judge_probe._run()

    # Eleven Mistral calls (ten local items plus the cloud item), and eleven
    # Google ones (ten judge calls plus the one subject generation).
    assert started["mistral_complete"].call_count == 11
    assert started["google_complete"].call_count == 11
    assert started["sleep"].called


def test_a_probe_run_never_touches_the_quality_results_store(stubbed_probe) -> None:
    _, quality_results_path, _, _ = stubbed_probe

    judge_probe._run()

    assert not quality_results_path.exists()


# --------------------------------------------------------------------------
# The three languages, read off the rows
# --------------------------------------------------------------------------


def test_each_row_names_the_judge_prompt_shell_of_its_own_language(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    rows = read_rows(probe_path)
    languages_seen = set()
    for row in rows:
        language = row["language"]
        languages_seen.add(language)
        assert row["judge_prompt_language"] == language
        assert row["judge_prompt_id"] == judge_protocol.JUDGE_TEMPLATE_IDS[language]
        assert (
            row["judge_prompt_template_hash"]
            == judge_protocol.JUDGE_TEMPLATE_HASHES[language]
        )
    assert languages_seen == {"en", "fr", "de"}

    english_hash = judge_protocol.JUDGE_TEMPLATE_HASHES["en"]
    for row in rows:
        if row["language"] != "en":
            assert row["judge_prompt_template_hash"] != english_hash


def test_the_rubric_provenance_is_the_generic_shipped_one(stubbed_probe) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    for row in read_rows(probe_path):
        assert row["rubric_id"] == "open-ended-quality-1to5"
        assert row["rubric_version"] == judge_probe.RUBRIC.version
        assert row["rubric_kind"] == "ordinal_1_5"


# --------------------------------------------------------------------------
# A judge reply that does not parse
# --------------------------------------------------------------------------


def test_an_unparseable_judge_reply_is_a_missing_judgement_not_a_zero(
    stubbed_probe,
) -> None:
    probe_path, _, _, replies = stubbed_probe
    prose = "The answer reads well and does what was asked."
    replies["google_judge"][2] = prose

    judge_probe._run()

    rows_by_item = {
        row["item_id"]: row
        for row in read_rows(probe_path)
        if row["provider"] == "local"
    }
    affected = rows_by_item[JUDGE_PROBE_ITEMS[2]["item_id"]]
    google_record = next(
        record for record in affected["judges"] if record["provider"] == "google"
    )
    assert google_record["score"] is None
    assert google_record["failure_reason"] == judge.FAILURE_REASON_JUDGE_UNPARSEABLE
    assert google_record["raw_text"] == prose
    # Dropped from the statistic, never coerced to 0.
    assert affected["agreement"]["n_items"] == 9
    assert affected["agreement"]["n_items_excluded"] == 1
    assert affected["contested"] is False


def test_a_judge_that_runs_out_of_retries_names_the_item_and_the_provider(
    stubbed_probe, capsys
) -> None:
    # A live-run finding: `retry budget exhausted after 4 retries` alone told
    # the operator neither which provider gave up nor where, and the probe
    # writes no row until a whole batch is judged, so nothing on disk carried
    # the run_id either.
    probe_path, _, started, _ = stubbed_probe

    def rate_limited_judge(prompt, api_key, **kwargs):
        if kwargs["max_tokens"] == judge_probe.JUDGE_MAX_TOKENS:
            raise google_client.RetryableRequestError(
                "rate limited", status_code=429, retry_after_s=0
            )
        return _google_reply("ok", generated_tokens=12)

    started["google_complete"].side_effect = rate_limited_judge

    with pytest.raises(SystemExit) as exit_info:
        judge_probe.main()

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    first_item_id = JUDGE_PROBE_ITEMS[0]["item_id"]
    assert (
        f"judge call failed on item {first_item_id!r} at provider google"
        in captured.err
    )
    assert "retry budget exhausted" in captured.err
    assert not probe_path.exists()
    # Printed before anything could fail, so --resume has an id to be given.
    assert captured.out.splitlines()[0].startswith("run_id=")


def test_the_run_id_is_printed_before_the_batches(stubbed_probe, capsys) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    lines = capsys.readouterr().out.splitlines()
    run_id = read_rows(probe_path)[0]["run_id"]
    assert lines[0] == f"run_id={run_id}"


# --------------------------------------------------------------------------
# The refusals
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("google_api_key", "", "GOOGLE_API_KEY is not set"),
        ("mistral_api_key", "", "MISTRAL_API_KEY is not set"),
        (
            "quality_providers",
            frozenset({"local", "mistral"}),
            "google is not enabled in QUALITY_PROVIDERS",
        ),
    ],
)
def test_a_missing_judge_refuses_the_run_before_anything_is_generated(
    stubbed_probe, capsys, field, value, expected
) -> None:
    probe_path, _, started, _ = stubbed_probe
    started["load_settings"].return_value = dataclasses.replace(
        started["load_settings"].return_value, **{field: value}
    )

    with pytest.raises(SystemExit) as exit_info:
        judge_probe.main()

    assert exit_info.value.code == 1
    assert expected in capsys.readouterr().err
    assert not probe_path.exists()
    assert started["running_server"].call_count == 0
    assert started["mistral_check_model"].call_count == 0
    assert started["google_check_model"].call_count == 0


# --------------------------------------------------------------------------
# Resume
# --------------------------------------------------------------------------


def test_resume_against_a_complete_run_makes_no_call_and_appends_nothing(
    stubbed_probe, capsys
) -> None:
    probe_path, _, started, _ = stubbed_probe
    run_id = "probe-resume-complete"

    judge_probe._run(resume_run_id=run_id)
    assert len(read_rows(probe_path)) == 11
    started["mistral_complete"].reset_mock()
    started["google_complete"].reset_mock()
    started["running_server"].reset_mock()

    judge_probe._run(resume_run_id=run_id)

    assert started["mistral_complete"].call_count == 0
    assert started["google_complete"].call_count == 0
    assert started["running_server"].call_count == 0
    stderr = capsys.readouterr().err
    assert f"local skipped: run {run_id} already complete" in stderr
    assert f"google skipped: run {run_id} already complete" in stderr
    assert len(read_rows(probe_path)) == 11


def test_resume_with_a_never_used_run_id_behaves_like_a_fresh_run(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe
    run_id = "probe-never-seen"

    judge_probe._run(resume_run_id=run_id)

    rows = read_rows(probe_path)
    assert len(rows) == 11
    assert all(row["run_id"] == run_id for row in rows)
    assert all(row["resumed"] is True for row in rows)


# --------------------------------------------------------------------------
# The command's own surface
# --------------------------------------------------------------------------


def test_parse_args_defaults_resume_to_none() -> None:
    assert judge_probe._parse_args([]).resume is None


def test_parse_args_reads_the_resume_flag() -> None:
    assert judge_probe._parse_args(["--resume", "run-123"]).resume == "run-123"


def test_help_names_the_probe_and_its_resume_flag(capsys) -> None:
    with pytest.raises(SystemExit):
        judge_probe._parse_args(["--help"])

    out = capsys.readouterr().out
    assert "wave-local-ai-v2-judge-probe" in out
    assert "--resume" in out


def test_the_probe_never_hands_the_google_judge_a_google_subject() -> None:
    # The refusal is the behaviour, not a code path to route around: proving
    # it here means the probe's own single-judge row can never be the product
    # of a silent filter.
    google_judge = judge.Judge(
        model_id=google_client.MODEL,
        provider=judge_backends.PROVIDER_GOOGLE,
        family="google",
        backend=lambda prompt: (_ for _ in ()).throw(
            AssertionError("the refused judge must never be called")
        ),
    )
    with pytest.raises(judge.JudgeFamilyCollisionError):
        judge.select_judges("google", [google_judge])


def test_a_pre_seeded_partial_batch_is_refused_rather_than_duplicated(
    stubbed_probe, capsys
) -> None:
    probe_path, _, started, _ = stubbed_probe
    run_id = "probe-resume-partial"
    judge_probe._run(resume_run_id=run_id)
    rows = read_rows(probe_path)
    kept = [row for row in rows if row["provider"] == "local"][:4]
    probe_path.write_text(
        "".join(f"{json.dumps(row)}\n" for row in kept), encoding="utf-8"
    )
    started["mistral_complete"].reset_mock()

    judge_probe._run(resume_run_id=run_id)

    stderr = capsys.readouterr().err
    assert f"local skipped: run {run_id} is partially written (4/10 items)" in stderr
    # The google half had no rows left on disk, so it re-ran and appended one.
    assert len(read_rows(probe_path)) == len(kept) + 1


def test_a_row_written_by_the_probe_round_trips_through_append_row(
    stubbed_probe, tmp_path
) -> None:
    # append_row is the contract gate; a probe row must pass it standing
    # alone, not only as part of the run that produced it.
    probe_path, _, _, _ = stubbed_probe
    judge_probe._run()
    row = read_rows(probe_path)[0]

    elsewhere = tmp_path / "copy.jsonl"
    append_row(elsewhere, "quality", row)

    assert read_rows(elsewhere) == [row]

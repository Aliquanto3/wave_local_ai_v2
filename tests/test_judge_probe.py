import dataclasses
import json
from importlib import metadata
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from conftest import mark_prompt
from store_fixtures import ROSTER_REQUIREMENTS, single_refusal, write_raised_roster

from wave_local_ai_v2 import (
    agreement,
    google_client,
    judge,
    judge_backends,
    judge_probe,
    judge_protocol,
    local_client,
    mistral_client,
    quality_cli,
    row_contract,
    scoring,
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
            "requirements": ROSTER_REQUIREMENTS,
            "family": "qwen",
            "thinking_control": {"chat_template_kwargs": {"enable_thinking": False}},
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
        # The pinned model's real shape: no thoughtsTokenCount and a total of
        # prompt + candidates, so the client derives 0 from the totals.
        "reasoning_tokens": 0,
        "reasoning_tokens_derived": True,
    }


FAKE_CHAT_TEMPLATE = "{% for m in messages %}<|im_start|>{{ m.content }}{% endfor %}"


def _fake_render(prompt: str) -> str:
    return "<|im_start|>user\n" + prompt + " <|im_end|>"


# What the stubbed tokenizer counts every rendered item to.
FAKE_ITEM_PROMPT_TOKENS = 20


def _local_post_router(finish_reason: str = "stop"):
    """Route a stubbed local POST by endpoint: render, then answer."""

    def route(url, *args, **kwargs):
        if url.endswith("/apply-template"):
            rendered = _fake_render(kwargs["json"]["messages"][0]["content"])
            # A template that honours the declared control renders the
            # verification's probe differently without it.
            if "chat_template_kwargs" not in kwargs["json"]:
                rendered += "<think>"
            payload: dict = {"prompt": rendered}
        else:
            payload = {
                "choices": [
                    {
                        "finish_reason": finish_reason,
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
        machine_id="laptop-mobile-gpu",
        compute_mode="gpu",
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
            "wave_local_ai_v2.build_probe.probe_build",
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
        # The item's own rendered prompt under the model's tokenizer, counted
        # once per item; `local_client.count_tokens` is covered on its own.
        "count_tokens": patch(
            "wave_local_ai_v2.judge_probe.local_client.count_tokens",
            return_value=FAKE_ITEM_PROMPT_TOKENS,
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


def test_each_probe_row_records_its_subject_egress_apart_from_the_judges(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    for row in read_rows(probe_path):
        expected = "none" if row["provider"] == "local" else row["provider"]
        assert row["subject_egress"] == expected
        # Judging sent the item off the machine either way: recorded in the
        # judge block's own egress record, never folded into the subject's.
        assert row["judge_egress"]["item_left_machine"] is True


def test_each_probe_row_carries_its_own_subject_generation_figures(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    rows = read_rows(probe_path)
    local_rows = [row for row in rows if row["provider"] == "local"]
    cloud_rows = [row for row in rows if row["provider"] != "local"]
    for position, row in enumerate(local_rows):
        assert (row["item_tokens_in"], row["item_tokens_out"]) == (23, 11)
        # The stubbed engine reports no timings block: null with its reason.
        assert row["item_ttft_ms"] is None
        assert row["item_ttft_ms_null_reason"] == "not_reported_by_engine"
        assert row["item_first_in_batch"] is (position == 0)
    assert len(cloud_rows) == 1
    assert cloud_rows[0]["item_ttft_ms_null_reason"] == "not_reported_by_provider"
    assert cloud_rows[0]["item_first_in_batch"] is True


def test_each_probe_row_names_direct_and_its_measured_overhead(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    rows = read_rows(probe_path)
    assert {row["harness_id"] for row in rows} == {"direct"}
    assert {row["harness_version"] for row in rows} == {metadata.version("requests")}
    local_rows = [row for row in rows if row["provider"] == "local"]
    cloud_rows = [row for row in rows if row["provider"] != "local"]
    # The engine's 23 prompt tokens minus the item's own counted prompt.
    for row in local_rows:
        assert row["harness_prompt_overhead"] == {
            "tokens": 23 - FAKE_ITEM_PROMPT_TOKENS,
            "null_reason": None,
        }
    assert cloud_rows[0]["harness_prompt_overhead"] == {
        "tokens": None,
        "null_reason": "item_prompt_not_counted",
    }


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
        # The probe declares no level: the gate certifies it at development,
        # its behaviour before levels existed.
        assert row["suite_level"] == "development"
        assert row["item_licence"] == "CC-BY-4.0"
        assert row["item_source"] is None
        assert row["item_source_revision"] is None


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
    # Two POSTs per item -- render, then answer -- plus the thinking control's
    # two probe renders, and one /props GET for the whole batch.
    assert started["post"].call_count == 2 * len(JUDGE_PROBE_ITEMS) + 2
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


def test_local_probe_rows_name_the_engine_and_the_cloud_row_states_none(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    rows = read_rows(probe_path)
    assert {
        (row["provider"], row["engine_id"], row["engine_build"]) for row in rows
    } == {("local", "llama.cpp", "b10537"), ("google", "not_applicable", None)}
    assert {
        (row["provider"], row["machine_id"], row["compute_mode"]) for row in rows
    } == {
        ("local", "laptop-mobile-gpu", "gpu"),
        ("google", "not_applicable", "not_applicable"),
    }
    assert {row["campaign_id"] for row in rows} == {"none"}
    assert {
        (row["provider"], row["profile_id"].endswith("@laptop-mobile-gpu/gpu"))
        for row in rows
    } == {("local", True), ("google", False)}
    assert {row["profile_id"] for row in rows if row["provider"] == "google"} == {
        "not_applicable"
    }


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


def test_every_probe_row_names_the_baseline_variant_and_its_authored_prompt(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    prompts_by_item = {item["item_id"]: item["prompt"] for item in JUDGE_PROBE_ITEMS}
    rows = read_rows(probe_path)
    assert {row["provider"] for row in rows} == {"local", "google"}
    for row in rows:
        assert row["prompt_variant_id"] == "baseline"
        assert row["prompt_variant_version"] == "1"
        assert row["prompt_before_template"] == prompts_by_item[row["item_id"]]


def test_the_probe_subject_is_sent_the_variant_and_the_judges_the_authored_text(
    stubbed_probe, marking_variant, monkeypatch
) -> None:
    probe_path, _, started, _ = stubbed_probe
    monkeypatch.setattr(judge_probe, "PROMPT_VARIANT_ID", marking_variant)

    judge_probe._run()

    marked = [mark_prompt(item["prompt"]) for item in JUDGE_PROBE_ITEMS]
    local_inputs = [
        call.kwargs["json"]["messages"][0]["content"]
        for call in started["post"].call_args_list
    ]
    # The batch opens on the thinking control's verification: one fixed
    # message rendered with and without the control.
    assert local_inputs[:2] == [local_client.THINKING_PROBE_MESSAGE] * 2
    local_inputs = local_inputs[2:]
    # Rendered, then answered: each marked prompt reaches both local calls.
    assert local_inputs[0::2] == marked
    assert local_inputs[1::2] == marked
    subject_calls = [
        call
        for call in started["google_complete"].call_args_list
        if call.kwargs["max_tokens"] != judge_probe.JUDGE_MAX_TOKENS
    ]
    cloud_item = judge_probe._item_by_id(judge_probe.CLOUD_SUBJECT_ITEM_ID)
    assert [call.args[0] for call in subject_calls] == [
        mark_prompt(cloud_item["prompt"])
    ]
    # The scorer is untouched: no judge was handed the variant's output.
    judge_calls = [
        *started["mistral_complete"].call_args_list,
        *(
            call
            for call in started["google_complete"].call_args_list
            if call.kwargs["max_tokens"] == judge_probe.JUDGE_MAX_TOKENS
        ),
    ]
    assert judge_calls
    assert all("[marked]" not in call.args[0] for call in judge_calls)
    assert any(cloud_item["prompt"] in call.args[0] for call in judge_calls)

    for row in read_rows(probe_path):
        assert row["prompt_variant_id"] == marking_variant
        assert row["prompt_before_template"].startswith("[marked] ")


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
        ("machine_id", None, "MACHINE_ID is not set"),
        ("compute_mode", "hybrid", "COMPUTE_MODE='hybrid'"),
        ("campaign_id", "some-campaign", "the judge probe runs under no campaign"),
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
    written = read_rows(probe_path)
    assert len(written) == 11
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


def test_a_resume_reads_the_judge_call_provenance_back_unchanged(
    stubbed_probe,
) -> None:
    probe_path, _, started, _ = stubbed_probe
    run_id = "probe-resume-provenance"
    judge_probe._run(resume_run_id=run_id)
    written = read_rows(probe_path)
    started["mistral_complete"].reset_mock()
    started["google_complete"].reset_mock()

    judge_probe._run(resume_run_id=run_id)

    # No judge call is re-issued, and every record keeps its five fields.
    assert started["mistral_complete"].call_count == 0
    assert started["google_complete"].call_count == 0
    read_back = read_rows(probe_path)
    assert read_back == written
    by_provider = {
        record["provider"]: record
        for row in read_back
        if row["provider"] == "local"
        for record in row["judges"]
    }
    assert by_provider["mistral"]["answering_provider"] == "mistral"
    assert by_provider["google"]["answering_provider"] == "google"
    for record in by_provider.values():
        assert record["answering_provider_source"] == "direct_endpoint"
        assert record["reasoning_effort"] == "not_sent"
    assert by_provider["mistral"]["reasoning_tokens"] is None
    assert by_provider["mistral"]["reasoning_tokens_null_reason"] == (
        "provider_reports_no_reasoning_count"
    )
    assert by_provider["google"]["reasoning_tokens"] == 0
    assert by_provider["google"]["reasoning_tokens_source"] == "derived_from_totals"


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


def _fail_mistral_judge_on_call(started: dict, failing_call: int) -> dict:
    """Make the `failing_call`-th Mistral judge call (1-based) fail, unretried.

    A 400, not a 429: a non-retryable provider error stops the batch on its
    first attempt, so the item it failed on is exactly the one this names.
    Returns the counter, so a test can later restore the normal replies.
    """
    normal = started["mistral_complete"].side_effect
    state = {"calls": 0, "armed": True}

    def failing(prompt, api_key, **kwargs):
        state["calls"] += 1
        if state["armed"] and state["calls"] == failing_call:
            raise mistral_client.MistralRequestError("bad request")
        return normal(prompt, api_key, **kwargs)

    started["mistral_complete"].side_effect = failing
    return state


def _judge_calls(started: dict) -> tuple[int, int]:
    """(mistral judge calls, google judge calls) issued so far."""
    google_judge = sum(
        1
        for call in started["google_complete"].call_args_list
        if call.kwargs["max_tokens"] == judge_probe.JUDGE_MAX_TOKENS
    )
    return started["mistral_complete"].call_count, google_judge


def test_a_judge_failure_mid_batch_persists_the_judged_items_as_partial(
    stubbed_probe, capsys
) -> None:
    probe_path, _, started, _ = stubbed_probe
    run_id = "probe-partial"
    # The fifth local item's Mistral judge call fails: items 1-4 are judged.
    _fail_mistral_judge_on_call(started, 5)

    with pytest.raises(judge_probe.JudgeCallError):
        judge_probe._run(resume_run_id=run_id)

    rows = read_rows(probe_path)
    failing_item = JUDGE_PROBE_ITEMS[4]["item_id"]
    assert [row["item_id"] for row in rows] == [
        item["item_id"] for item in JUDGE_PROBE_ITEMS[:4]
    ]
    for row in rows:
        assert row["partial_failure"]["provider"] == "mistral"
        assert row["partial_failure"]["item_id"] == failing_item
        # A partial batch publishes no headline over the items that finished.
        assert row["judged_headline_score"] is None
    stderr = capsys.readouterr().err
    assert f"local partial: run {run_id} stopped at item {failing_item!r}" in stderr


def test_a_judged_batch_resumed_mid_way_issues_no_judge_call_already_recorded(
    stubbed_probe,
) -> None:
    probe_path, _, started, _ = stubbed_probe
    # The uninterrupted reference, under its own run_id in the same store.
    judge_probe._run(resume_run_id="probe-uninterrupted")
    uninterrupted = [
        row
        for row in read_rows(probe_path)
        if row["provider"] == "local" and row["run_id"] == "probe-uninterrupted"
    ]

    run_id = "probe-interrupted"
    started["mistral_complete"].reset_mock()
    state = _fail_mistral_judge_on_call(started, 5)
    with pytest.raises(judge_probe.JudgeCallError):
        judge_probe._run(resume_run_id=run_id)
    before = [row for row in read_rows(probe_path) if row["run_id"] == run_id]
    assert len(before) == 4

    state["armed"] = False
    started["mistral_complete"].reset_mock()
    started["google_complete"].reset_mock()
    judge_probe._run(resume_run_id=run_id)

    # Six local items left, each judged once by each judge, plus the cloud
    # item's single Mistral judgement: nothing already on a row is re-paid.
    assert _judge_calls(started) == (6 + 1, 6)
    rows = [row for row in read_rows(probe_path) if row["run_id"] == run_id]
    local = [row for row in rows if row["provider"] == "local"]
    item_ids = [row["item_id"] for row in local]
    assert sorted(item_ids) == sorted(item["item_id"] for item in JUDGE_PROBE_ITEMS)
    assert len(item_ids) == len(set(item_ids))
    # The rows already written are untouched by the resume.
    assert rows[:4] == before
    # The completing rows publish what the uninterrupted batch published.
    completing = local[4:]
    for row in completing:
        assert row["partial_failure"] is None
        assert row["agreement"] == uninterrupted[0]["agreement"]
        assert row["judged_headline_score"] == uninterrupted[0]["judged_headline_score"]
        assert row["failure_counts"] == uninterrupted[0]["failure_counts"]
    assert {row["item_id"] for row in local if row["contested"]} == {
        row["item_id"] for row in uninterrupted if row["contested"]
    }


def test_every_probe_row_names_the_budget_derived_from_the_items_it_judges(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe

    judge_probe._run()

    # Eleven items draw on both providers: max(4, ceil(11 * 0.2)) = 4.
    for row in read_rows(probe_path):
        assert row["retry_budget"] == {"mistral": 4, "google": 4}
        assert row["partial_failure"] is None


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


# --------------------------------------------------------------------------
# Parity with the quality harness
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["LOCAL_SAMPLING", "GOOGLE_SAMPLING", "REQUEST_TIMEOUT_S", "_RETRY_BASE_DELAY_S"],
)
def test_the_probe_generates_under_the_quality_harness_own_settings(name) -> None:
    # The two CLIs deliberately do not import each other, so this test is
    # what holds the "same value, same role" comments to account.
    assert getattr(judge_probe, name) == getattr(quality_cli, name), (
        f"judge_probe.{name} drifted from quality_cli.{name}: change both or neither"
    )


def test_the_probe_seed_is_the_quality_seed() -> None:
    assert judge_probe.PROBE_SEED == quality_cli.QUALITY_SEED, (
        "judge_probe.PROBE_SEED drifted from quality_cli.QUALITY_SEED"
    )


def test_a_local_generation_cut_off_at_the_cap_is_recorded_as_truncated(
    stubbed_probe,
) -> None:
    probe_path, _, started, _ = stubbed_probe
    started["post"].side_effect = _local_post_router(finish_reason="length")

    judge_probe._run()

    local_rows = [
        row
        for row in read_rows(probe_path)
        if row["provider"] == judge_probe.PROVIDER_LOCAL
    ]
    assert len(local_rows) == len(JUDGE_PROBE_ITEMS)
    for row in local_rows:
        assert row["failure_reason"] == scoring.FAILURE_REASON_TRUNCATED_MAX_TOKENS


def test_a_thinking_control_the_template_ignores_refuses_the_probe(
    stubbed_probe,
) -> None:
    probe_path, _, started, _ = stubbed_probe

    def ignoring_template(url, *args, **kwargs):
        payload = {"prompt": _fake_render(kwargs["json"]["messages"][0]["content"])}
        return MagicMock(
            status_code=200, json=lambda: payload, raise_for_status=lambda: None
        )

    started["post"].side_effect = ignoring_template

    with pytest.raises(local_client.ThinkingControlRefused):
        judge_probe._run()

    # The two probe renders and nothing after them: no item was generated or
    # judged, and no row was written.
    assert started["post"].call_count == 2
    assert started["mistral_complete"].call_count == 0
    assert read_rows(probe_path) == []


def _keep_four_local_rows(probe_path: Path, edit) -> list[dict]:
    """Leave four local rows of the run on disk, each passed through `edit`."""
    kept = [edit(row) for row in read_rows(probe_path) if row["provider"] == "local"][
        :4
    ]
    probe_path.write_text(
        "".join(f"{json.dumps(row)}\n" for row in kept), encoding="utf-8"
    )
    return kept


def _judged_by_another_model(row: dict) -> dict:
    judges = [dict(record) for record in row["judges"]]
    judges[0]["model_id"] = "mistral-small-2501"
    return {**row, "judges": judges}


@pytest.mark.parametrize(
    ("edit", "named"),
    [
        (_judged_by_another_model, "judge_model_ids="),
        (lambda row: {**row, "model_id": "Another Model"}, "model_id="),
        (lambda row: {**row, "suite_version": "0"}, "suite_version="),
        # A local batch resumed under another engine build would publish one
        # agreement over two builds.
        (lambda row: {**row, "engine_build": "b1"}, "engine_build="),
        (lambda row: {**row, "engine_id": "ollama"}, "engine_id="),
        (lambda row: {**row, "compute_mode": "cpu_only"}, "compute_mode="),
    ],
)
def test_a_probe_resume_over_rows_of_another_configuration_is_refused(
    stubbed_probe, capsys, edit, named
) -> None:
    probe_path, _, started, _ = stubbed_probe
    run_id = "probe-other-config"
    judge_probe._run(resume_run_id=run_id)
    kept = _keep_four_local_rows(probe_path, edit)
    started["mistral_complete"].reset_mock()
    started["google_complete"].reset_mock()
    started["running_server"].reset_mock()

    with (
        patch("sys.argv", ["wave-local-ai-v2-judge-probe", "--resume", run_id]),
        pytest.raises(SystemExit) as exit_info,
    ):
        judge_probe.main()

    assert exit_info.value.code == 1
    stderr = capsys.readouterr().err
    assert f"refusing --resume {run_id}: the local batch's" in stderr
    assert named in stderr
    assert started["running_server"].call_count == 0
    assert started["mistral_complete"].call_count == 0
    assert started["google_complete"].call_count == 0
    assert read_rows(probe_path) == kept


def test_a_probe_resume_under_the_same_configuration_completes_the_batch(
    stubbed_probe,
) -> None:
    probe_path, _, _, _ = stubbed_probe
    run_id = "probe-same-config"
    judge_probe._run(resume_run_id=run_id)
    _keep_four_local_rows(probe_path, lambda row: row)

    judge_probe._run(resume_run_id=run_id)

    rows = read_rows(probe_path)
    local = [row for row in rows if row["provider"] == "local"]
    assert len(local) == len(JUDGE_PROBE_ITEMS)
    assert local[-1]["partial_failure"] is None
    assert local[-1]["agreement"]["n_items"] == len(JUDGE_PROBE_ITEMS)


def test_a_run_below_its_declared_minimum_refuses_before_the_weights_and_any_spawn(
    stubbed_probe, tmp_path, capsys
) -> None:
    probe_path, quality_results_path, started, _ = stubbed_probe
    settings = started["load_settings"].return_value
    # The weights are absent too: the RAM refusal must not be masked by them.
    (
        settings.slm_models_dir
        / FAKE_ROSTER["entries"][DEFAULT_ROSTER_ENTRY_ID]["file"]
    ).unlink()
    started["load_settings"].return_value = dataclasses.replace(
        settings,
        roster_path=write_raised_roster(FAKE_ROSTER, tmp_path),
        machine_results_root=tmp_path / "refusals",
    )

    with pytest.raises(SystemExit) as exit_info:
        judge_probe.main()

    assert exit_info.value.code == 1
    err = capsys.readouterr().err
    assert "refused:" in err and "ram_gb" in err and "compute mode 'gpu'" in err
    assert "model file not found" not in err
    started["running_server"].assert_not_called()
    started["probe_build"].assert_not_called()
    record = single_refusal(tmp_path / "refusals", "laptop-mobile-gpu")
    assert record["requirement"] == "ram_gb"
    assert record["profile_id"] == f"{DEFAULT_ROSTER_ENTRY_ID}@laptop-mobile-gpu/gpu"
    assert not probe_path.exists()
    assert not quality_results_path.exists()

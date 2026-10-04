"""The four routes, the key gate and the read-only posture, over temp stores.

The two client kinds are driven through `TestClient(app, client=...)`, which
starlette assigns straight to `scope["client"]` -- so the loopback and the
non-loopback paths are both exercised without monkeypatching anything.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import textwrap
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from starlette.testclient import TestClient
from store_fixtures import ROSTER_ENTRY_ID, RUN_ID, make_row, write_store

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_dev_cert import generate_cert

from wave_local_ai_v2 import (
    demo_console,
    read_model,
    results,
    roster,
    row_contract,
    service,
    suite_registry,
)
from wave_local_ai_v2.settings import ServiceSettings, SettingsError

API_KEY = "a-service-key"  # pragma: allowlist secret
LOOPBACK = ("127.0.0.1", 12345)
REMOTE = ("192.168.1.50", 12345)
DASHBOARD_ORIGIN = "http://dashboard.example"
ENTRY_DOCUMENT_TEXT = "<html>the dashboard entry</html>"
ROUTES = (
    "/api/runs",
    f"/api/runs/{RUN_ID}/quality",
    f"/api/runs/{RUN_ID}/runtime",
    f"/api/runs/{RUN_ID}/energy?store=runtime",
    "/api/overview/quality",
    "/api/overview/runtime",
)
NON_GET_METHODS = ("post", "put", "patch", "delete")


@pytest.fixture
def dashboard_bundle_dir(tmp_path: Path) -> Path:
    """A temp bundle dir with an entry document and a hashed asset."""
    root = tmp_path / "dashboard-dist"
    assets = root / "assets"
    assets.mkdir(parents=True)
    (root / "index.html").write_text(ENTRY_DOCUMENT_TEXT, encoding="utf-8")
    (assets / "app.deadbeef.js").write_text("console.log(1)", encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def _tls_pem() -> tuple[bytes, bytes]:
    # Generated once: RSA key generation is the slow part, and `main()` loads
    # the pair for real before it serves, so placeholder bytes would not do.
    return generate_cert([])


@pytest.fixture
def tls_pair(tmp_path: Path, _tls_pem: tuple[bytes, bytes]) -> tuple[Path, Path]:
    """A real, loadable on-disk cert/key pair."""
    certfile = tmp_path / "cert.pem"
    keyfile = tmp_path / "key.pem"
    certfile.write_bytes(_tls_pem[0])
    keyfile.write_bytes(_tls_pem[1])
    return certfile, keyfile


@pytest.fixture
def settings(
    bundle: dict[str, Path],
    dashboard_bundle_dir: Path,
    tls_pair: tuple[Path, Path],
) -> ServiceSettings:
    write_store(bundle["runtime"], [make_row("runtime")])
    write_store(bundle["quality"], [make_row("quality")])
    certfile, keyfile = tls_pair
    return ServiceSettings(
        api_key=API_KEY,
        host="127.0.0.1",
        port=8000,
        schema_floor="7",
        runtime_results_path=bundle["runtime"],
        quality_results_path=bundle["quality"],
        fiche_registry_dir=bundle["fiches"],
        roster_path=bundle["roster"],
        suite_definitions_dir=bundle["suites"],
        leader_sets_dir=bundle["leader_sets"],
        dashboard_bundle_dir=dashboard_bundle_dir,
        dashboard_origin=DASHBOARD_ORIGIN,
        tls_certfile=certfile,
        tls_keyfile=keyfile,
        machine_registry_path=bundle["machines"],
    )


@pytest.fixture
def local(settings: ServiceSettings):  # type: ignore[no-untyped-def]
    with TestClient(service.create_app(settings), client=LOOPBACK) as client:
        yield client


@pytest.fixture
def remote(settings: ServiceSettings):  # type: ignore[no-untyped-def]
    with TestClient(service.create_app(settings), client=REMOTE) as client:
        yield client


# --------------------------------------------------------------------------
# The four routes
# --------------------------------------------------------------------------


def test_the_runtime_route_resolves_the_rows_machine_from_its_registry(
    local: TestClient, settings: ServiceSettings
) -> None:
    body = local.get(f"/api/runs/{RUN_ID}/runtime").json()
    machine = body["entries"][0]["machine"]
    assert machine["machine_id"] == "laptop-mobile-gpu"
    assert machine["facts"]["memory_type"]["value"] == "DDR4"

    settings.machine_registry_path.write_text("{}", encoding="utf-8")
    body = local.get(f"/api/runs/{RUN_ID}/runtime").json()
    assert body["entries"][0]["machine"] == {
        "absent": True,
        "reason": "pointer_unresolved",
        "detail": {"pointer": "machine_id", "value": "laptop-mobile-gpu"},
    }


def test_the_runs_route_answers_two_named_collections(local: TestClient) -> None:
    body = local.get("/api/runs").json()

    assert set(body) == {"runtime_runs", "quality_runs"}
    for collection in body.values():
        assert collection["schema_floor"] == "7"
        assert collection["unreadable"] == []
    assert body["runtime_runs"]["runs"][0]["run_id"] == RUN_ID


def test_the_quality_route_answers_one_entry_per_row_with_its_shape(
    local: TestClient,
) -> None:
    body = local.get(f"/api/runs/{RUN_ID}/quality").json()

    assert body["score_shapes"] == ["exact_match"]
    assert body["entries"][0]["score_shape"] == "exact_match"
    # An absence crosses the JSON boundary wearing its marker.
    assert body["entries"][0]["judge"]["agreement"]["absent"] is True


def test_the_quality_route_names_a_field_the_floor_predates_over_http(
    bundle: dict[str, Path], dashboard_bundle_dir: Path, tls_pair: tuple[Path, Path]
) -> None:
    # A "7"-floor row: schema_version "7" for real (not just a floor param
    # over an "11" row), and thinking_policy dropped entirely -- the one
    # field this store's own schema genuinely predates (see plan.md's
    # Decisions). The four other story-named fields stay on the row, proving
    # the route carries them as real values rather than as an accidental
    # absence sharing the same floor.
    row = make_row("quality", schema_version="7")
    del row["thinking_policy"]
    write_store(bundle["quality"], [row])
    write_store(bundle["runtime"], [make_row("runtime", schema_version="7")])
    certfile, keyfile = tls_pair
    settings = ServiceSettings(
        api_key=API_KEY,
        host="127.0.0.1",
        port=8000,
        schema_floor="7",
        runtime_results_path=bundle["runtime"],
        quality_results_path=bundle["quality"],
        fiche_registry_dir=bundle["fiches"],
        roster_path=bundle["roster"],
        suite_definitions_dir=bundle["suites"],
        leader_sets_dir=bundle["leader_sets"],
        dashboard_bundle_dir=dashboard_bundle_dir,
        dashboard_origin=DASHBOARD_ORIGIN,
        tls_certfile=certfile,
        tls_keyfile=keyfile,
    )

    with TestClient(service.create_app(settings), client=LOOPBACK) as client:
        body = client.get(f"/api/runs/{RUN_ID}/quality").json()

    entry = body["entries"][0]
    assert entry["thinking_policy"] == {
        "absent": True,
        "reason": "predates_schema",
        "detail": {"row_schema_version": "7"},
    }
    for field in ("contamination_risk", "indicative_reasons", "failure_counts"):
        value = entry[field]
        is_absent = isinstance(value, dict) and value.get("absent") is True
        assert not is_absent, f"{field} is unexpectedly absent"


def test_the_runtime_route_answers_with_the_fiche_beside_the_row(
    local: TestClient,
) -> None:
    body = local.get(f"/api/runs/{RUN_ID}/runtime").json()

    assert body["entries"][0]["fiche"] == {"cpu": "a cpu", "gpu": "a gpu"}


def test_the_energy_route_answers_three_channels_each_beside_its_label(
    local: TestClient,
) -> None:
    body = local.get(f"/api/runs/{RUN_ID}/energy?store=runtime").json()

    assert set(body["entries"][0]["channels"]) == {"cpu", "gpu", "ram"}
    assert body["entries"][0]["channels"]["gpu"]["energy_method"] == "nvml_sampled"


def test_the_overview_quality_route_answers_one_use_case_per_task_suite(
    local: TestClient,
) -> None:
    response = local.get("/api/overview/quality")
    body = response.json()

    assert body["store"] == "quality"
    assert body["use_cases"]
    use_case = body["use_cases"][0]
    assert set(use_case) == {"task_suite", "leader", "cloud_comparators"}
    assert use_case["leader"]["absent"] is True
    # Structural, not just top-level: a runtime field nested inside a member
    # or a comparator entry must fail this too.
    runtime_only = sorted(
        row_contract.REQUIRED_FIELDS["runtime"]
        - row_contract.REQUIRED_FIELDS["quality"]
    )
    assert not any(f'"{name}"' in response.text for name in runtime_only)


def test_the_overview_runtime_route_answers_one_entry_per_roster_entry(
    local: TestClient,
) -> None:
    response = local.get("/api/overview/runtime")
    body = response.json()

    assert body["store"] == "runtime"
    entry = body["entries"][0]
    assert entry["roster_entry_id"] == ROSTER_ENTRY_ID
    assert set(entry) == {"roster_entry_id", "runtime_headline", "energy_headline"}
    # Structural, not just top-level: a quality-only field nested anywhere in
    # the entry must fail this too.
    quality_only = sorted(
        row_contract.REQUIRED_FIELDS["quality"]
        - row_contract.REQUIRED_FIELDS["runtime"]
    )
    assert not any(f'"{name}"' in response.text for name in quality_only)


def test_the_overview_routes_carry_no_identity_from_the_other_store(
    bundle: dict[str, Path], dashboard_bundle_dir: Path, tls_pair: tuple[Path, Path]
) -> None:
    # A runtime-only roster_entry_id would pass a plain key-set or field-name
    # check, since `roster_entry_id` is a name both stores share -- this
    # proves the *value* from one store's rows never reaches the other
    # route's response, the way `test_read_model.py`'s counterpart does over
    # the read model directly.
    write_store(bundle["quality"], [make_row("quality")])
    write_store(
        bundle["runtime"], [make_row("runtime", roster_entry_id="only-runtime")]
    )
    certfile, keyfile = tls_pair
    settings = ServiceSettings(
        api_key=API_KEY,
        host="127.0.0.1",
        port=8000,
        schema_floor="7",
        runtime_results_path=bundle["runtime"],
        quality_results_path=bundle["quality"],
        fiche_registry_dir=bundle["fiches"],
        roster_path=bundle["roster"],
        suite_definitions_dir=bundle["suites"],
        leader_sets_dir=bundle["leader_sets"],
        dashboard_bundle_dir=dashboard_bundle_dir,
        dashboard_origin=DASHBOARD_ORIGIN,
        tls_certfile=certfile,
        tls_keyfile=keyfile,
    )
    with TestClient(service.create_app(settings), client=LOOPBACK) as client:
        quality_text = client.get("/api/overview/quality").text
        runtime_text = client.get("/api/overview/runtime").text

    assert "only-runtime" not in quality_text
    assert ROSTER_ENTRY_ID not in runtime_text


@pytest.mark.parametrize("query", ["", "?store=both", "?store=", "?store=Runtime"])
def test_the_energy_store_must_be_named_and_recognised(
    local: TestClient, query: str
) -> None:
    response = local.get(f"/api/runs/{RUN_ID}/energy{query}")

    assert response.status_code == 422
    assert "store" in response.text


@pytest.mark.parametrize(
    ("path", "store"),
    [
        ("quality", "quality"),
        ("runtime", "runtime"),
        ("energy?store=runtime", "runtime"),
        ("energy?store=quality", "quality"),
    ],
)
def test_an_unknown_run_is_a_404_naming_the_run_and_the_store(
    local: TestClient, path: str, store: str
) -> None:
    response = local.get(f"/api/runs/no-such-run/{path}")

    detail = response.json()["detail"]
    assert response.status_code == 404
    assert "no-such-run" in detail
    assert f"{store} store" in detail
    # Not an empty list: a store holding no row for this run and a run that
    # exists are different facts.
    assert response.json() != {"entries": []}


def test_no_response_body_carries_both_a_quality_and_a_runtime_field(
    local: TestClient, bundle: dict[str, Path]
) -> None:
    # Made structurally rather than by eye: the two names come from the
    # contract's own difference between the kinds, so a schema change moves
    # this assertion with it.
    runtime_only = sorted(
        row_contract.REQUIRED_FIELDS["runtime"]
        - row_contract.REQUIRED_FIELDS["quality"]
    )
    # Less the keys of the roster-entry identity block both stores' views
    # resolve `roster_entry_id` into: the entry's `family` is the model's,
    # not a quality-store field, even though a quality row (schema "19") now
    # also carries its subject's family under the same name.
    entry_keys = set(
        read_model.resolve_roster_entry(
            {"roster_entry_id": ROSTER_ENTRY_ID},
            roster.load_roster(bundle["roster"]),
        )
    )
    quality_only = sorted(
        row_contract.REQUIRED_FIELDS["quality"]
        - row_contract.REQUIRED_FIELDS["runtime"]
        - entry_keys
    )
    assert runtime_only and quality_only

    for route in ROUTES:
        text = local.get(route).text
        carries_runtime = any(f'"{name}"' in text for name in runtime_only)
        carries_quality = any(f'"{name}"' in text for name in quality_only)
        assert not (carries_runtime and carries_quality), (
            f"{route} composes the two stores"
        )


# --------------------------------------------------------------------------
# Methods
# --------------------------------------------------------------------------


@pytest.mark.parametrize("client_name", ["local", "remote"])
@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("method", NON_GET_METHODS)
def test_every_non_get_method_answers_405_from_either_client(
    request: pytest.FixtureRequest, client_name: str, route: str, method: str
) -> None:
    client: TestClient = request.getfixturevalue(client_name)

    response = getattr(client, method)(route)

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"


# --------------------------------------------------------------------------
# The key gate
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("127.0.0.1", True),
        ("127.9.9.9", True),
        ("::1", True),
        ("192.168.1.50", False),
        ("testclient", False),
        ("", False),
        (None, False),
    ],
)
def test_is_loopback_client_fails_closed_on_anything_it_cannot_parse(
    host: str | None, expected: bool
) -> None:
    assert service.is_loopback_client(host) is expected


def test_a_loopback_client_is_answered_without_a_header(local: TestClient) -> None:
    assert local.get("/api/runs").status_code == 200


def test_a_non_loopback_client_without_the_key_is_refused(remote: TestClient) -> None:
    response = remote.get("/api/runs")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing or invalid X-API-Key"
    assert API_KEY not in response.text


def test_a_non_loopback_client_with_a_wrong_key_is_refused(remote: TestClient) -> None:
    response = remote.get("/api/runs", headers={"X-API-Key": "wrong"})

    assert response.status_code == 401
    assert response.json()["detail"] == "missing or invalid X-API-Key"
    assert API_KEY not in response.text


def test_a_missing_and_a_wrong_key_answer_byte_identical_bodies(
    remote: TestClient,
) -> None:
    # The acceptance is indistinguishability, not merely the string chosen.
    missing = remote.get("/api/runs")
    wrong = remote.get("/api/runs", headers={"X-API-Key": "wrong"})

    assert missing.status_code == wrong.status_code == 401
    assert missing.content == wrong.content


def test_an_unparsable_client_host_is_refused(settings: ServiceSettings) -> None:
    # TestClient's own default, `("testclient", 50000)`, is not a parsable IP.
    with TestClient(service.create_app(settings)) as client:
        assert client.get("/api/runs").status_code == 401


def test_a_non_ascii_key_header_is_refused_not_a_500(remote: TestClient) -> None:
    # `hmac.compare_digest` raises `TypeError` on a `str` carrying a non-ASCII
    # character, and starlette decodes header values as latin-1 -- so one byte
    # from any remote client used to take the refusal path out through a 500
    # with a traceback. The comparison is on bytes, so this is a plain 401.
    response = remote.get("/api/runs", headers={b"x-api-key": b"cl\xe9-invalide"})

    assert response.status_code == 401
    assert response.json()["detail"] == "missing or invalid X-API-Key"


@pytest.mark.parametrize("path", ["/openapi.json", "/docs", "/redoc"])
def test_the_schema_and_docs_surfaces_are_not_mounted_by_fastapi(
    remote: TestClient, path: str
) -> None:
    # `openapi_url`/`docs_url`/`redoc_url` are `None`: FastAPI itself never
    # registers these, so what answers here is the same SPA catch-all that
    # answers any other unknown non-`/api` path -- never the schema or its
    # parameter list, and never gated behind the key (the dashboard shell
    # carries no secret).
    response = remote.get(path)
    assert response.status_code == 200
    assert response.text == ENTRY_DOCUMENT_TEXT


def test_the_same_request_with_the_key_gets_the_loopback_body(
    local: TestClient, remote: TestClient
) -> None:
    keyed = remote.get("/api/runs", headers={"X-API-Key": API_KEY})

    assert keyed.status_code == 200
    assert keyed.json() == local.get("/api/runs").json()


@pytest.mark.parametrize("route", ROUTES)
def test_every_api_route_is_gated_not_only_the_index(
    remote: TestClient, route: str
) -> None:
    assert remote.get(route).status_code == 401


def test_create_app_refuses_to_build_without_a_key(settings: ServiceSettings) -> None:
    keyless = ServiceSettings(**{**vars(settings), "api_key": ""})

    with pytest.raises(SettingsError, match="SERVICE_API_KEY"):
        service.create_app(keyless)


def test_no_response_body_anywhere_contains_the_key(
    local: TestClient, remote: TestClient
) -> None:
    for route in ROUTES:
        assert API_KEY not in local.get(route).text
        assert API_KEY not in remote.get(route).text
        assert API_KEY not in remote.get(route, headers={"X-API-Key": API_KEY}).text


def test_the_key_appears_in_no_logged_or_printed_record(
    monkeypatch,
    settings: ServiceSettings,
    local: TestClient,
    remote: TestClient,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Loading settings, the startup print, a served request (loopback and
    # remote-with-the-right-key) and a refused one (remote, wrong key) -- the
    # literal key value is searched for, not inferred from reading the
    # middleware.
    monkeypatch.setattr(service, "load_service_settings", lambda: settings)
    monkeypatch.setattr(service, "_serve", lambda *a, **k: None)
    caplog.set_level("DEBUG")

    assert service.main() == 0
    assert local.get("/api/runs").status_code == 200
    assert remote.get("/api/runs", headers={"X-API-Key": API_KEY}).status_code == 200
    assert remote.get("/api/runs", headers={"X-API-Key": "wrong"}).status_code == 401

    captured = capsys.readouterr()
    assert API_KEY not in captured.out + captured.err
    assert API_KEY not in caplog.text


# --------------------------------------------------------------------------
# The serving entry
# --------------------------------------------------------------------------


def test_the_serve_entry_refuses_to_start_without_a_key(
    monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def refuse() -> ServiceSettings:
        raise SettingsError("SERVICE_API_KEY is not set")

    bound: list[Any] = []
    monkeypatch.setattr(service, "load_service_settings", refuse)
    monkeypatch.setattr(service, "_serve", lambda *a, **k: bound.append(a))

    exit_code = service.main()

    assert exit_code == 1
    assert "SERVICE_API_KEY is not set" in capsys.readouterr().err
    assert bound == [], "no socket may be bound on the refusal path"


@pytest.mark.parametrize("breakage", ["swapped", "not-pem"])
def test_the_serve_entry_refuses_an_unloadable_tls_pair_before_announcing(
    monkeypatch,
    settings: ServiceSettings,
    capsys: pytest.CaptureFixture[str],
    breakage: str,
) -> None:
    if breakage == "swapped":
        broken = replace(
            settings,
            tls_certfile=settings.tls_keyfile,
            tls_keyfile=settings.tls_certfile,
        )
    else:
        settings.tls_certfile.write_text("not a certificate", encoding="utf-8")
        broken = settings
    bound: list[Any] = []
    monkeypatch.setattr(service, "load_service_settings", lambda: broken)
    monkeypatch.setattr(service, "_serve", lambda *a, **k: bound.append(a))

    exit_code = service.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "SERVICE_TLS_CERTFILE/SERVICE_TLS_KEYFILE" in captured.err
    assert "serving" not in captured.out
    assert API_KEY not in captured.out + captured.err
    assert bound == [], "no socket may be bound on the refusal path"


def test_the_serve_entry_prints_the_address_and_floor_and_never_the_key(
    monkeypatch, settings: ServiceSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    served: list[dict[str, Any]] = []
    monkeypatch.setattr(service, "load_service_settings", lambda: settings)
    monkeypatch.setattr(service, "_serve", lambda app, **kwargs: served.append(kwargs))

    assert service.main() == 0

    printed = capsys.readouterr().out
    assert served == [
        {
            "host": "127.0.0.1",
            "port": 8000,
            "proxy_headers": False,
            "ssl_certfile": settings.tls_certfile,
            "ssl_keyfile": settings.tls_keyfile,
        }
    ]
    assert "https://127.0.0.1:8000" in printed
    assert "schema floor 7" in printed
    assert API_KEY not in printed


def test_the_serve_entry_disables_uvicorns_proxy_header_middleware(
    monkeypatch, settings: ServiceSettings
) -> None:
    # The gate reads `scope["client"]` and nothing else, which is only true of
    # the running process while this stays off: uvicorn defaults it to `True`,
    # and `ProxyHeadersMiddleware` then rewrites `scope["client"]` from
    # `X-Forwarded-For` before any route or dependency sees it. A loopback
    # client sending the header would be refused, and a remote one forging
    # `127.0.0.1` would need only a widened `FORWARDED_ALLOW_IPS` -- which
    # uvicorn reads from the same environment `load_dotenv()` populates -- to
    # be handed the keyless path.
    served: list[dict[str, Any]] = []
    monkeypatch.setattr(service, "load_service_settings", lambda: settings)
    monkeypatch.setattr(service, "_serve", lambda app, **kwargs: served.append(kwargs))

    service.main()

    assert served[0]["proxy_headers"] is False


# --------------------------------------------------------------------------
# Serving the dashboard bundle
# --------------------------------------------------------------------------


def test_root_serves_the_bundles_entry_document(local: TestClient) -> None:
    response = local.get("/")

    assert response.status_code == 200
    assert response.text == ENTRY_DOCUMENT_TEXT


def test_an_unknown_client_route_falls_back_to_the_entry_document(
    local: TestClient,
) -> None:
    response = local.get("/some/client/route")

    assert response.status_code == 200
    assert response.text == ENTRY_DOCUMENT_TEXT


def test_a_built_asset_is_served_from_the_bundle(local: TestClient) -> None:
    response = local.get("/assets/app.deadbeef.js")

    assert response.status_code == 200
    assert "console.log(1)" in response.text


def test_an_unknown_api_path_is_404_json_never_the_entry_document(
    local: TestClient,
) -> None:
    response = local.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"]
    assert ENTRY_DOCUMENT_TEXT not in response.text


def test_a_preflight_from_another_origin_is_not_granted(local: TestClient) -> None:
    response = local.options(
        "/api/runs",
        headers={
            "Origin": "http://not-the-dashboard.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_a_preflight_from_the_configured_origin_is_granted(
    local: TestClient,
) -> None:
    response = local.options(
        "/api/runs",
        headers={
            "Origin": DASHBOARD_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers["access-control-allow-origin"] == DASHBOARD_ORIGIN


# --------------------------------------------------------------------------
# Read-only
# --------------------------------------------------------------------------


def test_the_whole_suite_of_requests_leaves_every_store_byte_identical(
    local: TestClient, settings: ServiceSettings
) -> None:
    store_paths = [settings.runtime_results_path, settings.quality_results_path]
    root = settings.runtime_results_path.parent
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in store_paths
    }
    listing_before = sorted(entry.name for entry in root.iterdir())

    for route in ROUTES:
        local.get(route)

    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in store_paths
    } == before
    assert sorted(entry.name for entry in root.iterdir()) == listing_before


@pytest.mark.parametrize("route", ROUTES)
def test_every_route_still_answers_with_append_row_made_to_raise(
    monkeypatch, settings: ServiceSettings, route: str
) -> None:
    def explode(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("a read-only service must not write a row")

    monkeypatch.setattr(results, "append_row", explode)

    with TestClient(service.create_app(settings), client=LOOPBACK) as client:
        assert client.get(route).status_code == 200


# --------------------------------------------------------------------------
# The demo console
# --------------------------------------------------------------------------

CONSOLE_OPTIONS = "/api/console/options"
CONSOLE_MACHINE = "laptop-mobile-gpu"
QUALITY_SUITE = "classification-support-routing"
RUNTIME_BODY: dict[str, Any] = {
    "kind": "runtime",
    "roster_entry_id": ROSTER_ENTRY_ID,
    "machine_id": CONSOLE_MACHINE,
    "compute_mode": "gpu",
}


def demo(settings: ServiceSettings) -> ServiceSettings:
    """`settings` with demo mode on, on a declared machine."""
    return replace(settings, demo_mode=True, machine_id=CONSOLE_MACHINE)


@pytest.fixture
def demo_local(settings: ServiceSettings):  # type: ignore[no-untyped-def]
    demo_console.release()
    app = service.create_app(demo(settings))
    with TestClient(app, client=LOOPBACK) as client:
        yield client
    demo_console.release()


def test_the_console_refuses_a_keyless_loopback_client(demo_local: TestClient) -> None:
    # Unlike the read routes, loopback is no bypass here.
    response = demo_local.get(CONSOLE_OPTIONS)

    assert response.status_code == 401
    assert response.json() == {"detail": "missing or invalid X-API-Key"}


def test_the_console_refuses_a_wrong_key_from_loopback(demo_local: TestClient) -> None:
    response = demo_local.get(CONSOLE_OPTIONS, headers={"X-API-Key": "wrong"})

    assert response.status_code == 401


def test_the_console_is_a_403_naming_the_variable_when_demo_mode_is_off(
    local: TestClient,
) -> None:
    response = local.get(CONSOLE_OPTIONS, headers={"X-API-Key": API_KEY})

    assert response.status_code == 403
    assert "SERVICE_DEMO_MODE" in response.json()["detail"]


def test_a_keyless_request_is_a_401_even_when_demo_mode_is_off(
    local: TestClient,
) -> None:
    # The key gate runs first: demo mode's state is not observable keyless.
    assert local.get(CONSOLE_OPTIONS).status_code == 401


def test_the_console_options_answer_the_declared_sets(demo_local: TestClient) -> None:
    response = demo_local.get(CONSOLE_OPTIONS, headers={"X-API-Key": API_KEY})

    assert response.status_code == 200
    body = response.json()
    assert body["kinds"] == ["runtime", "quality"]
    assert body["suites"] == suite_registry.registered_ids()
    assert body["roster_entries"] == [ROSTER_ENTRY_ID]
    assert body["machine_id"] == CONSOLE_MACHINE
    assert {p["compute_mode"] for p in body["profiles"][ROSTER_ENTRY_ID]} == {
        "gpu",
        "cpu_only",
    }
    assert body["holder"] is None


def test_the_console_options_name_the_current_holder(demo_local: TestClient) -> None:
    demo_console.try_acquire(
        demo_console.RunHolder(
            kind="runtime",
            suite=None,
            roster_entry_id=ROSTER_ENTRY_ID,
            profile_id="p",
            started_at="2026-09-24T10:00:00+00:00",
        )
    )

    body = demo_local.get(CONSOLE_OPTIONS, headers={"X-API-Key": API_KEY}).json()

    assert body["holder"]["kind"] == "runtime"
    assert body["holder"]["roster_entry_id"] == ROSTER_ENTRY_ID


def test_an_unreadable_roster_is_a_named_503_not_a_crash(
    settings: ServiceSettings, tmp_path: Path
) -> None:
    broken = replace(demo(settings), roster_path=tmp_path / "missing-roster.json")
    with TestClient(service.create_app(broken), client=LOOPBACK) as client:
        response = client.get(CONSOLE_OPTIONS, headers={"X-API-Key": API_KEY})

    assert response.status_code == 503
    assert "missing-roster.json" in response.json()["detail"]


CONSOLE_RUNS = "/api/console/runs"
KEYED = {"X-API-Key": API_KEY}
STUB_RUN_ID = "0123456789abcdef0123456789abcdef"


def stub_cli(monkeypatch, code: str) -> None:
    """Make the console launch `python -c code` in place of the real CLI."""
    monkeypatch.setattr(
        demo_console,
        "command_for",
        lambda _request: ([sys.executable, "-u", "-c", textwrap.dedent(code)], {}),
    )


def ndjson(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines()]


def test_a_console_run_streams_its_lines_then_its_exit(
    demo_local: TestClient, monkeypatch
) -> None:
    stub_cli(monkeypatch, f'print("{STUB_RUN_ID}"); print("working")')

    started = demo_local.post(
        CONSOLE_RUNS,
        json=RUNTIME_BODY,
        headers=KEYED,
    )
    assert started.status_code == 200
    launch_id = started.json()["launch_id"]

    events = ndjson(
        demo_local.get(f"{CONSOLE_RUNS}/{launch_id}/stream", headers=KEYED).text
    )

    assert events[:2] == [{"line": STUB_RUN_ID}, {"line": "working"}]
    assert events[-1]["final"]["exit_code"] == 0


@pytest.mark.parametrize(
    "body",
    [
        {**RUNTIME_BODY, "shell": "yes"},
        {**RUNTIME_BODY, "kind": "quality", "suite": "bogus"},
        {**RUNTIME_BODY, "roster_entry_id": "a|b"},
        {**RUNTIME_BODY, "machine_id": "tower-desktop-gpu"},
        {**RUNTIME_BODY, "compute_mode": "gpu; calc"},
        "runtime",
    ],
)
def test_a_console_request_outside_the_declared_sets_is_a_422_with_no_spawn(
    demo_local: TestClient, monkeypatch, body: object
) -> None:
    spawned: list[object] = []
    monkeypatch.setattr(
        demo_console.subprocess, "Popen", lambda *a, **k: spawned.append(a)
    )

    response = demo_local.post(CONSOLE_RUNS, json=body, headers=KEYED)

    assert response.status_code == 422
    assert spawned == []
    assert demo_console.current_holder() is None


def test_a_second_run_is_refused_naming_the_first_and_spawns_nothing(
    demo_local: TestClient, monkeypatch
) -> None:
    holder = demo_console.RunHolder(
        kind="quality",
        suite=QUALITY_SUITE,
        roster_entry_id=ROSTER_ENTRY_ID,
        profile_id=f"{ROSTER_ENTRY_ID}@{CONSOLE_MACHINE}/gpu",
        started_at="2026-09-24T10:00:00+00:00",
    )
    demo_console.try_acquire(holder)
    demo_console.record_run_id(STUB_RUN_ID)
    spawned: list[object] = []
    monkeypatch.setattr(
        demo_console.subprocess, "Popen", lambda *a, **k: spawned.append(a)
    )

    response = demo_local.post(
        CONSOLE_RUNS,
        json=RUNTIME_BODY,
        headers=KEYED,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["holder"] == {
        "session": "run",
        "kind": "quality",
        "suite": QUALITY_SUITE,
        "roster_entry_id": ROSTER_ENTRY_ID,
        "profile_id": f"{ROSTER_ENTRY_ID}@{CONSOLE_MACHINE}/gpu",
        "started_at": "2026-09-24T10:00:00+00:00",
        "run_id": STUB_RUN_ID,
    }
    assert spawned == []


def test_a_launch_failure_frees_the_console_and_names_the_cause(
    demo_local: TestClient, monkeypatch
) -> None:
    def cannot_start(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("no such interpreter")

    monkeypatch.setattr(demo_console.subprocess, "Popen", cannot_start)

    response = demo_local.post(
        CONSOLE_RUNS,
        json=RUNTIME_BODY,
        headers=KEYED,
    )

    assert response.status_code == 500
    assert "no such interpreter" in response.json()["detail"]
    assert demo_console.current_holder() is None


def test_an_unknown_launch_id_is_a_404(demo_local: TestClient) -> None:
    response = demo_local.get(f"{CONSOLE_RUNS}/nope/stream", headers=KEYED)

    assert response.status_code == 404


def test_the_run_routes_are_keyed_and_demo_gated_too(
    local: TestClient, demo_local: TestClient
) -> None:
    body = RUNTIME_BODY

    assert demo_local.post(CONSOLE_RUNS, json=body).status_code == 401
    assert demo_local.get(f"{CONSOLE_RUNS}/x/stream").status_code == 401
    assert local.post(CONSOLE_RUNS, json=body, headers=KEYED).status_code == 403


def test_shutting_the_service_down_stops_a_running_child(
    settings: ServiceSettings, monkeypatch
) -> None:
    demo_console.release()
    stub_cli(monkeypatch, "import time; print('up'); time.sleep(60)")
    stopped: list[int] = []
    real_stop_child = demo_console.stop_child

    def spy(process: Any) -> None:
        stopped.append(process.pid)
        real_stop_child(process)

    monkeypatch.setattr(demo_console, "stop_child", spy)

    app = service.create_app(demo(settings))
    with TestClient(app, client=LOOPBACK) as client:
        response = client.post(
            CONSOLE_RUNS,
            json=RUNTIME_BODY,
            headers=KEYED,
        )
        assert response.status_code == 200

    assert len(stopped) == 1
    demo_console.release()


def test_the_stream_reaches_a_real_http_client_line_by_line(
    settings: ServiceSettings, monkeypatch
) -> None:
    # A real uvicorn over a real socket: `TestClient` collects the whole body
    # before returning it, so it cannot tell a streamed response from a
    # buffered one.
    demo_console.release()
    stub_cli(
        monkeypatch,
        f"""
        import time
        print("{STUB_RUN_ID}")
        time.sleep(1.5)
        print("after the pause")
        """,
    )
    config = uvicorn.Config(
        service.create_app(demo(settings)),
        host="127.0.0.1",
        port=0,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        port = server.servers[0].sockets[0].getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=base, headers=KEYED) as client:
            launch_id = client.post(
                CONSOLE_RUNS,
                json=RUNTIME_BODY,
            ).json()["launch_id"]
            arrivals: list[tuple[dict[str, Any], float]] = []
            with client.stream("GET", f"{CONSOLE_RUNS}/{launch_id}/stream") as stream:
                for line in stream.iter_lines():
                    arrivals.append((json.loads(line), time.monotonic()))
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        demo_console.release()

    assert [event for event, _ in arrivals][:2] == [
        {"line": STUB_RUN_ID},
        {"line": "after the pause"},
    ]
    assert arrivals[1][1] - arrivals[0][1] > 1.0


def run_to_final(client: TestClient, body: dict[str, Any]) -> dict[str, Any]:
    launch_id = client.post(CONSOLE_RUNS, json=body, headers=KEYED).json()["launch_id"]
    events = ndjson(
        client.get(f"{CONSOLE_RUNS}/{launch_id}/stream", headers=KEYED).text
    )
    final: dict[str, Any] = events[-1]["final"]
    return final


@pytest.mark.parametrize("kind", ["runtime", "quality"])
def test_a_landed_rows_final_event_is_the_existing_view_route_payload(
    demo_local: TestClient, settings: ServiceSettings, monkeypatch, kind: str
) -> None:
    store = (
        settings.runtime_results_path
        if kind == "runtime"
        else settings.quality_results_path
    )
    write_store(store, [make_row(kind), make_row(kind, run_id=STUB_RUN_ID)])
    stub_cli(monkeypatch, f'print("{STUB_RUN_ID}")')
    body: dict[str, Any] = {**RUNTIME_BODY, "kind": kind}
    if kind == "quality":
        body["suite"] = QUALITY_SUITE

    final = run_to_final(demo_local, body)

    route_payload = demo_local.get(f"/api/runs/{STUB_RUN_ID}/{kind}").json()
    assert final["ok"] is True
    assert final["run_id"] == STUB_RUN_ID
    assert json.dumps(final["view"]) == json.dumps(route_payload)


def test_exit_zero_without_a_landed_row_surfaces_the_routes_404_detail(
    demo_local: TestClient, monkeypatch
) -> None:
    stub_cli(monkeypatch, f'print("{STUB_RUN_ID}")')

    final = run_to_final(demo_local, RUNTIME_BODY)

    route = demo_local.get(f"/api/runs/{STUB_RUN_ID}/runtime")
    assert route.status_code == 404
    assert final["ok"] is False
    assert final["view"] is None
    assert final["missing"] == route.json()["detail"]


def test_a_failed_runs_final_event_carries_its_exit_code_and_error_line(
    demo_local: TestClient, monkeypatch
) -> None:
    stub_cli(
        monkeypatch,
        f"""
        import sys
        print("{STUB_RUN_ID}")
        print("error: disk full", file=sys.stderr)
        sys.exit(3)
        """,
    )

    final = run_to_final(demo_local, RUNTIME_BODY)

    assert final["exit_code"] == 3
    assert final["error_line"] == "error: disk full"
    assert final["view"] is None


# Write-mode markers for `open()`/`Path.open()`: any of these in a mode string.
WRITE_MODE_CHARS = set("wax+")
WRITE_METHODS = {"write_text", "write_bytes"}
WRITERS = {"append_row", "write_fiche"}


def write_paths_in(module_path: Path) -> list[str]:
    """Every writer reference or write-mode open in one module's source."""
    found: list[str] = []
    for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Name) and node.id in WRITERS:
            found.append(f"name {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr in WRITERS | WRITE_METHODS:
            found.append(f"attribute {node.attr}")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module == "wave_local_ai_v2.results"
        ):
            found.append(f"import from results: {[a.name for a in node.names]}")
        elif isinstance(node, ast.alias) and node.name in WRITERS:
            found.append(f"import {node.name}")
        elif isinstance(node, ast.Call):
            func = node.func
            name = (
                func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            )
            if name != "open":
                continue
            modes = [
                arg.value
                for arg in [
                    *node.args[1:],
                    *(k.value for k in node.keywords if k.arg == "mode"),
                ]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            ]
            if any(WRITE_MODE_CHARS & set(mode) for mode in modes):
                found.append(f"open in mode {modes}")
    return found


def test_no_demo_module_reaches_a_writer_or_opens_a_file_for_writing() -> None:
    package = Path(service.__file__).parent

    for module in ("demo_console.py", "playground.py", "service.py"):
        assert write_paths_in(package / module) == [], module


def test_the_structural_scan_would_catch_a_writer(tmp_path: Path) -> None:
    # The scan itself must bite, or the test above proves nothing.
    source = (
        "from wave_local_ai_v2.results import append_row\n"
        "open(path, 'a')\n"
        "path.write_text('x')\n"
    )
    probe = tmp_path / "probe.py"
    probe.write_text(source, encoding="utf-8")

    found = write_paths_in(probe)

    assert len(found) == 4


@pytest.mark.parametrize("method", ["get", "post"])
def test_an_unreadable_machine_registry_is_a_named_503_with_no_spawn(
    settings: ServiceSettings, tmp_path: Path, monkeypatch, method: str
) -> None:
    spawned: list[object] = []
    monkeypatch.setattr(
        demo_console.subprocess, "Popen", lambda *a, **k: spawned.append(a)
    )
    broken = replace(demo(settings), machine_registry_path=tmp_path / "gone.json")
    with TestClient(service.create_app(broken), client=LOOPBACK) as client:
        if method == "get":
            response = client.get(CONSOLE_OPTIONS, headers=KEYED)
        else:
            response = client.post(CONSOLE_RUNS, json=RUNTIME_BODY, headers=KEYED)

    assert response.status_code == 503
    assert "gone.json" in response.json()["detail"]
    assert spawned == []


def test_stopping_the_service_with_a_stream_open_stops_the_child_first(
    settings: ServiceSettings, monkeypatch
) -> None:
    # A real uvicorn: its own `shutdown` drains open connections before the
    # lifespan event, so a stream held open by a browser would otherwise keep
    # the service, and the child, alive for the whole run.
    demo_console.release()
    stub_cli(monkeypatch, "import time; print('up', flush=True); time.sleep(60)")
    app = service.create_app(demo(settings))
    server = service._ConsoleStoppingServer(
        uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"), app
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    streamed: list[str] = []
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        port = server.servers[0].sockets[0].getsockname()[1]
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", headers=KEYED, timeout=30
        ) as client:
            launch_id = client.post(CONSOLE_RUNS, json=RUNTIME_BODY).json()["launch_id"]
            [run] = app.state.console_runs.values()
            with client.stream("GET", f"{CONSOLE_RUNS}/{launch_id}/stream") as stream:
                lines = stream.iter_lines()
                streamed.append(next(lines))
                stopped_at = time.monotonic()
                server.should_exit = True
                streamed.extend(lines)
            thread.join(timeout=20)
            elapsed = time.monotonic() - stopped_at
    finally:
        server.should_exit = True
        thread.join(timeout=20)
        demo_console.release()

    assert json.loads(streamed[0]) == {"line": "up"}
    assert run.process.poll() is not None
    assert json.loads(streamed[-1])["final"]["exit_code"] != 0
    assert not thread.is_alive()
    assert elapsed < 20


class _FakeProcess:
    pid = 0


def _app_with_a_run(monkeypatch) -> tuple[FastAPI, list[object]]:
    app = FastAPI()
    run = SimpleNamespace(process=_FakeProcess())
    app.state.console_runs = {"L1": run}
    stopped: list[object] = []
    monkeypatch.setattr(demo_console, "stop_child", stopped.append)
    return app, stopped


def test_the_serve_entry_stops_a_child_on_a_forced_exit_too(monkeypatch) -> None:
    # A second Ctrl+C sets `force_exit`, which skips the lifespan event; the
    # serve entry's `finally` still stops the child.
    app, stopped = _app_with_a_run(monkeypatch)

    def forced(self: uvicorn.Server, sockets: object = None) -> None:
        self.started = True
        raise KeyboardInterrupt

    monkeypatch.setattr(service._ConsoleStoppingServer, "run", forced)

    service._serve(app, host="127.0.0.1", port=0)

    assert stopped == [app.state.console_runs["L1"].process]


def test_the_serve_entry_exits_with_uvicorns_startup_failure_code(
    monkeypatch,
) -> None:
    app, stopped = _app_with_a_run(monkeypatch)
    monkeypatch.setattr(service._ConsoleStoppingServer, "run", lambda self: None)

    with pytest.raises(SystemExit) as exc_info:
        service._serve(app, host="127.0.0.1", port=0)

    assert exc_info.value.code == 3
    assert len(stopped) == 1

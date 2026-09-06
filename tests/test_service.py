"""The four routes, the key gate and the read-only posture, over temp stores.

The two client kinds are driven through `TestClient(app, client=...)`, which
starlette assigns straight to `scope["client"]` -- so the loopback and the
non-loopback paths are both exercised without monkeypatching anything.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient
from store_fixtures import RUN_ID, make_row, write_store

from wave_local_ai_v2 import results, row_contract, service
from wave_local_ai_v2.settings import ServiceSettings, SettingsError

API_KEY = "a-service-key"  # pragma: allowlist secret
LOOPBACK = ("127.0.0.1", 12345)
REMOTE = ("192.168.1.50", 12345)
ROUTES = (
    "/api/runs",
    f"/api/runs/{RUN_ID}/quality",
    f"/api/runs/{RUN_ID}/runtime",
    f"/api/runs/{RUN_ID}/energy?store=runtime",
)
NON_GET_METHODS = ("post", "put", "patch", "delete")


@pytest.fixture
def settings(bundle: dict[str, Path]) -> ServiceSettings:
    write_store(bundle["runtime"], [make_row("runtime")])
    write_store(bundle["quality"], [make_row("quality")])
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
    local: TestClient,
) -> None:
    # Made structurally rather than by eye: the two names come from the
    # contract's own difference between the kinds, so a schema change moves
    # this assertion with it.
    runtime_only = sorted(
        row_contract.REQUIRED_FIELDS["runtime"]
        - row_contract.REQUIRED_FIELDS["quality"]
    )
    quality_only = sorted(
        row_contract.REQUIRED_FIELDS["quality"]
        - row_contract.REQUIRED_FIELDS["runtime"]
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
    assert response.json()["detail"] == "missing X-API-Key"
    assert API_KEY not in response.text


def test_a_non_loopback_client_with_a_wrong_key_is_refused(remote: TestClient) -> None:
    response = remote.get("/api/runs", headers={"X-API-Key": "wrong"})

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid X-API-Key"
    assert API_KEY not in response.text


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
    assert response.json()["detail"] == "invalid X-API-Key"


@pytest.mark.parametrize("path", ["/openapi.json", "/docs", "/redoc"])
def test_the_schema_and_docs_surfaces_are_not_mounted_at_all(
    remote: TestClient, path: str
) -> None:
    # FastAPI mounts these at the root, outside the gated `/api` router, so
    # leaving them on would answer a keyless non-loopback client with the whole
    # route list and its parameters -- not "route absence and nothing else".
    assert remote.get(path).status_code == 404


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
    monkeypatch.setattr(service.uvicorn, "run", lambda *a, **k: bound.append(a))

    exit_code = service.main()

    assert exit_code == 1
    assert "SERVICE_API_KEY is not set" in capsys.readouterr().err
    assert bound == [], "no socket may be bound on the refusal path"


def test_the_serve_entry_prints_the_address_and_floor_and_never_the_key(
    monkeypatch, settings: ServiceSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    served: list[dict[str, Any]] = []
    monkeypatch.setattr(service, "load_service_settings", lambda: settings)
    monkeypatch.setattr(
        service.uvicorn, "run", lambda app, **kwargs: served.append(kwargs)
    )

    assert service.main() == 0

    printed = capsys.readouterr().out
    assert served == [{"host": "127.0.0.1", "port": 8000, "proxy_headers": False}]
    assert "http://127.0.0.1:8000" in printed
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
    monkeypatch.setattr(
        service.uvicorn, "run", lambda app, **kwargs: served.append(kwargs)
    )

    service.main()

    assert served[0]["proxy_headers"] is False


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

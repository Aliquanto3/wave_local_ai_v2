"""The read-only results service: four `GET` routes over the two stores.

Read-only in the strict sense the story asks for. This module imports only
read paths -- `read_model`, which itself imports no writer -- so
`results.append_row`, `fiche_registry.write_fiche` and `suite_snapshot`'s
exporter are not reachable from a request at all. Nothing here opens a file
for writing, and no route registers a method other than `GET`.

Nothing here logs the API key, the `X-API-Key` header, or the settings object
that carries the key.
"""

from __future__ import annotations

import hmac
import ipaddress
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request

from wave_local_ai_v2 import read_model, roster
from wave_local_ai_v2.settings import (
    ServiceSettings,
    SettingsError,
    load_service_settings,
)

# The header name a non-loopback client presents the key in -- a header name,
# not a key. No key value exists anywhere in this repository.
API_KEY_HEADER = "X-API-Key"  # pragma: allowlist secret
STORE_RUNTIME = "runtime"
STORE_QUALITY = "quality"
# The energy route's two accepted stores, as a `Literal` so FastAPI itself
# answers 422 naming the parameter and the values it accepts. A missing or
# unrecognised value is a named refusal, never a guess: both row kinds carry
# the same thirteen energy fields, so probing one store then the other would
# make the service read both to answer one view and leave the response
# ambiguous about which store a number came from.
EnergyStore = Literal["runtime", "quality"]


def is_loopback_client(host: str | None) -> bool:
    """Whether `host` is the machine's own loopback address.

    Fails closed on anything it cannot parse. `TestClient`'s default client
    host is the literal string `"testclient"`, and a real deployment sitting
    behind something unexpected must not be handed the keyless path by
    accident -- an unparsable peer is treated as remote, not as local.

    Reads no proxy header. `X-Forwarded-For` and its relatives are
    attacker-controlled, and this epic excludes any reverse-proxy posture, so
    the peer address is the only input.
    """
    if host is None:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback


def _require_key(
    request: Request,
    settings: ServiceSettings,
    presented_key: str | None,
) -> None:
    """Refuse a non-loopback request that does not present the matching key.

    The 401 body names which of the two refusals applies and carries no key
    material, no store path and no traceback.
    """
    client = request.client
    if is_loopback_client(None if client is None else client.host):
        return
    if presented_key is None:
        raise HTTPException(status_code=401, detail=f"missing {API_KEY_HEADER}")
    # `compare_digest`, never `==`: a byte-by-byte comparison that short
    # circuits leaks the key's prefix to anyone who can time the response.
    if not hmac.compare_digest(presented_key, settings.api_key):
        raise HTTPException(status_code=401, detail=f"invalid {API_KEY_HEADER}")


def _not_found(run_id: str, store: str, floor: str) -> HTTPException:
    """The 404 for a run the named store does not carry.

    Not an empty list: a store holding no row for this run and a run that
    exists are different facts, and a caller handed `[]` cannot tell them
    apart.
    """
    return HTTPException(
        status_code=404,
        detail=(
            f"no row of the {store} store at or above schema floor {floor} "
            f"carries run_id {run_id!r}"
        ),
    )


def create_app(settings: ServiceSettings) -> FastAPI:
    """Build the app over `settings`, refusing to build without a key.

    A second, in-process assertion of the startup rule `load_service_settings`
    already makes: an app built in a test, or embedded in another process,
    cannot skip it.
    """
    if not settings.api_key:
        raise SettingsError("SERVICE_API_KEY is not set")

    app = FastAPI(
        title="wave-local-ai-v2 results service",
        description=(
            "Read-only views over the runtime and quality stores. Every field "
            "a row does not carry is reported as a named absence."
        ),
    )

    def key_gate(
        request: Request,
        x_api_key: Annotated[str | None, Header()] = None,
    ) -> None:
        _require_key(request, settings, x_api_key)

    # A router dependency, not HTTP middleware. Middleware runs *before*
    # routing, so a non-loopback `POST /api/runs` would answer 401 and the
    # story's "every non-GET method answers 405" would be false off loopback.
    # A router dependency runs after the router has resolved the method, so
    # 405 stays 405 for every client and the key still gates every `/api/*`
    # route that exists. The stated cost: an unknown `/api/...` path answers
    # 404 without the key check, disclosing route absence and nothing else.
    api = APIRouter(prefix="/api", dependencies=[Depends(key_gate)])

    def loaded_roster() -> roster.RosterFile | None:
        return read_model.load_roster_file(settings.roster_path)

    def store_path(store: str) -> Path:
        return (
            settings.runtime_results_path
            if store == STORE_RUNTIME
            else settings.quality_results_path
        )

    @api.get("/runs")
    def get_runs() -> dict[str, Any]:
        """The run index: two separately named collections, never one array.

        The one route that reads both files, and it composes nothing: no
        entry of one collection is joined to, ordered against or summed with
        the other.
        """
        return read_model.to_jsonable(
            read_model.runs_view(
                settings.runtime_results_path,
                settings.quality_results_path,
                settings.schema_floor,
                loaded_roster(),
            )
        )

    @api.get("/runs/{run_id}/quality")
    def get_quality(run_id: str) -> dict[str, Any]:
        """The quality table for one run, over the quality store only."""
        view = read_model.quality_view(
            settings.quality_results_path,
            run_id,
            settings.schema_floor,
            loaded_roster(),
            settings.suite_definitions_dir,
            settings.fiche_registry_dir,
        )
        if view is None:
            raise _not_found(run_id, STORE_QUALITY, settings.schema_floor)
        return read_model.to_jsonable(view)

    @api.get("/runs/{run_id}/runtime")
    def get_runtime(run_id: str) -> dict[str, Any]:
        """The runtime table for one run, with each row's fiche beside it."""
        view = read_model.runtime_view(
            settings.runtime_results_path,
            run_id,
            settings.schema_floor,
            settings.fiche_registry_dir,
            loaded_roster(),
        )
        if view is None:
            raise _not_found(run_id, STORE_RUNTIME, settings.schema_floor)
        return read_model.to_jsonable(view)

    @api.get("/runs/{run_id}/energy")
    def get_energy(run_id: str, store: EnergyStore) -> dict[str, Any]:
        """The per-run energy detail over the store the caller names."""
        view = read_model.energy_view(
            store_path(store), run_id, settings.schema_floor, store
        )
        if view is None:
            raise _not_found(run_id, store, settings.schema_floor)
        return read_model.to_jsonable(view)

    # No CORS configuration here, deliberately: the single-origin topology and
    # CORS-as-defence-in-depth belong to the story that serves the bundle, and
    # a permissive default added now is the kind of thing that survives to
    # production unreviewed.
    app.include_router(api)
    return app


def main() -> int:
    """Load the settings, build the app, and serve it over plain HTTP.

    A missing key returns 1 with its message on stderr and binds no socket.
    Plain HTTP: TLS is a later story in this epic, and no certificate setting
    is read here (see `settings.DEFAULT_SERVICE_SCHEMA_FLOOR`'s neighbours).
    """
    try:
        settings = load_service_settings()
    except SettingsError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    app = create_app(settings)
    # The bound address and the floor in force, and nothing else. Never the
    # key, never its length.
    print(
        f"serving http://{settings.host}:{settings.port} "
        f"at schema floor {settings.schema_floor}"
    )
    uvicorn.run(app, host=settings.host, port=settings.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())

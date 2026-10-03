"""The results service: `GET` routes over the two stores, plus the demo console.

Read-only in the strict sense the story asks for. This module imports only
read paths -- `read_model`, which itself imports no writer -- so
`results.append_row`, `fiche_registry.write_fiche` and `suite_snapshot`'s
exporter are not reachable from a request at all. Nothing here opens a file
for writing. The one non-`GET` route, `POST /api/console/runs`, exists only
with demo mode on and writes nothing itself: it starts the unchanged CLI as a
child process (`demo_console`), and the row that run produces is the one the
CLI appends.

Nothing here logs the API key, the `X-API-Key` header, or the settings object
that carries the key.
"""

from __future__ import annotations

import asyncio
import hmac
import ipaddress
import json
import socket
import ssl
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import uvicorn
from fastapi import (
    APIRouter,
    Body,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.config import STARTUP_FAILURE

from wave_local_ai_v2 import demo_console, machines, read_model, roster
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
    the peer address is the only input. That property is *owned* by `main()`,
    not assumed: uvicorn wraps an app in `ProxyHeadersMiddleware` by default
    and would overwrite `scope["client"]` from `X-Forwarded-For` before this
    function ever sees it, so `main()` turns it off explicitly.
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
    """Refuse a non-loopback request that does not present the matching key."""
    client = request.client
    if is_loopback_client(None if client is None else client.host):
        return
    _require_matching_key(settings, presented_key)


def _require_matching_key(settings: ServiceSettings, presented_key: str | None) -> None:
    """Refuse a request that does not present the matching key, from any client.

    The one place key bytes are compared. The 401 body is byte-identical
    whether the key is absent or wrong -- a client must not be able to tell
    the two reasons apart -- and carries no key material, no store path and
    no traceback.
    """
    refusal = HTTPException(
        status_code=401, detail=f"missing or invalid {API_KEY_HEADER}"
    )
    if presented_key is None:
        raise refusal
    # `compare_digest`, never `==`: a byte-by-byte comparison that short
    # circuits leaks the key's prefix to anyone who can time the response.
    #
    # Compared as *bytes*, never as the decoded strings: `compare_digest`
    # raises `TypeError` on a `str` carrying a non-ASCII character, and
    # starlette decodes header values as latin-1 -- so one non-ASCII byte in
    # the header would take the refusal path out through a 500 with a
    # traceback instead of the named 401 below. Re-encoding latin-1 recovers
    # exactly the bytes the client sent.
    if not hmac.compare_digest(
        presented_key.encode("latin-1"), settings.api_key.encode("utf-8")
    ):
        raise refusal


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

    # The one console run this app launched, if any: only one runs at a time,
    # so the latest is the only one a stream can follow.
    console_runs: dict[str, demo_console.ConsoleRun] = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        # On shutdown, a running child is stopped through its own graceful
        # path, so its llama-server is torn down rather than orphaned.
        for run in console_runs.values():
            demo_console.stop_child(run.process)

    app = FastAPI(
        lifespan=lifespan,
        title="wave-local-ai-v2 results service",
        description=(
            "Read-only views over the runtime and quality stores. Every field "
            "a row does not carry is reported as a named absence."
        ),
        # No schema and no interactive docs. FastAPI mounts `/openapi.json`,
        # `/docs` and `/redoc` at the root, *outside* the gated `/api` router,
        # so leaving them on would answer any keyless non-loopback client with
        # the whole route list and its parameters. The four routes are
        # documented in `aidd_docs/memory/cli.md` and nothing consumes the
        # schema, so the surface is removed rather than gated.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
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

    @api.get("/comparisons")
    def get_comparisons() -> dict[str, Any]:
        """Every roster model, side by side, over the same items of each suite.

        The one route in the quality family scoped to no single `run_id`:
        the comparison is store-wide by construction, reading only
        `quality_results_path`.
        """
        return read_model.to_jsonable(
            read_model.comparison_view(
                settings.quality_results_path,
                settings.schema_floor,
                loaded_roster(),
                settings.suite_definitions_dir,
                settings.fiche_registry_dir,
            )
        )

    @api.get("/overview/quality")
    def get_overview_quality() -> dict[str, Any]:
        """One entry per use case present in the quality store, store-wide."""
        return read_model.to_jsonable(
            read_model.overview_quality_view(
                settings.quality_results_path,
                settings.schema_floor,
                loaded_roster(),
                settings.suite_definitions_dir,
                settings.fiche_registry_dir,
                settings.leader_sets_dir,
            )
        )

    @api.get("/overview/runtime")
    def get_overview_runtime() -> dict[str, Any]:
        """One runtime/energy headline per roster entry, over the runtime store only."""
        return read_model.to_jsonable(
            read_model.overview_runtime_view(
                settings.runtime_results_path,
                settings.schema_floor,
                settings.fiche_registry_dir,
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
        """The runtime table for one run, each row's fiche and machine beside it."""
        view = read_model.runtime_view(
            settings.runtime_results_path,
            run_id,
            settings.schema_floor,
            settings.fiche_registry_dir,
            loaded_roster(),
            read_model.load_machine_registry(settings.machine_registry_path),
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

    app.include_router(api)
    # Where the serving entry finds the running child on shutdown.
    app.state.console_runs = console_runs
    app.include_router(
        _console_router(settings, console_runs, get_quality, get_runtime)
    )

    # Restricted to the one configured dashboard origin, defence-in-depth
    # only: the shipped topology is single-origin (the browser and `/api`
    # share host:port), so this has nothing to permit in production and
    # exists only to fail closed if that topology is ever violated.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.dashboard_origin],
        allow_methods=["GET"],
        allow_headers=[API_KEY_HEADER],
    )

    # The bundle is served last: `/api` is registered above, so it is tried
    # first and is never shadowed. Never committed (plan.md's Decisions): a
    # fresh checkout with no `npm run build` yet simply has nothing to mount
    # or serve here, and every non-`/api` request 404s instead of crashing
    # startup.
    assets_dir = settings.dashboard_bundle_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="dashboard-assets")

    entry_document = settings.dashboard_bundle_dir / "index.html"

    @app.get("/{full_path:path}")
    def serve_dashboard_entry(full_path: str) -> FileResponse:
        # `/api/*` is already exhausted by the router above: reaching here
        # with an `api/` prefix means no route matched it, and it must stay a
        # 404 rather than fall back to the entry document -- an unknown API
        # path must never leak HTML.
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail=f"no such route: /{full_path}")
        if not entry_document.is_file():
            raise HTTPException(status_code=404, detail="dashboard bundle is not built")
        return FileResponse(entry_document)

    return app


def _console_router(
    settings: ServiceSettings,
    console_runs: dict[str, demo_console.ConsoleRun],
    get_quality: Callable[[str], dict[str, Any]],
    get_runtime: Callable[[str], dict[str, Any]],
) -> APIRouter:
    """The demo console's routes: options, start a run, follow its stream.

    The key gate ignores loopback: the console starts processes on this
    machine, so it is gated stricter than the read routes. It runs before the
    demo-mode gate, so a keyless request is a 401 whether or not demo mode is
    on and cannot probe which it is.
    """

    def console_key_gate(
        x_api_key: Annotated[str | None, Header()] = None,
    ) -> None:
        _require_matching_key(settings, x_api_key)

    def require_demo_mode() -> None:
        if not settings.demo_mode:
            raise HTTPException(
                status_code=403,
                detail="demo mode is off on this machine (SERVICE_DEMO_MODE)",
            )

    console = APIRouter(
        prefix="/api/console",
        dependencies=[Depends(console_key_gate), Depends(require_demo_mode)],
    )

    @console.get("/options")
    def get_console_options() -> dict[str, Any]:
        """The declared choices a console run is drawn from, and who holds it."""
        try:
            return demo_console.options_payload(settings, demo_console.current_holder())
        except (roster.RosterError, machines.MachineRegistryError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @console.post("/runs")
    def post_console_run(payload: Annotated[Any, Body()] = None) -> dict[str, Any]:
        """Start one run from declared choices, or name who holds the console."""
        try:
            request = demo_console.validate_request(payload, settings)
        except demo_console.ConsoleRequestError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (roster.RosterError, machines.MachineRegistryError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        holder = demo_console.RunHolder(
            kind=request.kind,
            suite=request.suite,
            roster_entry_id=request.roster_entry_id,
            profile_id=request.profile_id,
            started_at=datetime.now(UTC).isoformat(),
        )
        occupied_by = demo_console.try_acquire(holder)
        if occupied_by is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "a run is in progress",
                    "holder": asdict(occupied_by),
                },
            )
        try:
            run = demo_console.start_run(request)
        except OSError as exc:
            demo_console.release()
            raise HTTPException(
                status_code=500, detail=f"the run could not be started: {exc}"
            ) from exc
        console_runs.clear()
        console_runs[run.launch_id] = run
        return {"launch_id": run.launch_id, "profile_id": request.profile_id}

    @console.get("/runs/{launch_id}/stream")
    def stream_console_run(launch_id: str) -> StreamingResponse:
        """The run's merged output as NDJSON lines, then one final event."""
        run = console_runs.get(launch_id)
        if run is None:
            raise HTTPException(
                status_code=404, detail=f"no console run with launch_id {launch_id!r}"
            )

        def read_back(kind: str, run_id: str) -> tuple[dict[str, Any] | None, str]:
            # The very route functions `GET /api/runs/{run_id}/quality|runtime`
            # answer with, so the final event carries every label they carry
            # and a missing row is their own 404 detail, not a new message.
            route = get_quality if kind == demo_console.KIND_QUALITY else get_runtime
            try:
                return route(run_id), ""
            except HTTPException as exc:
                return None, str(exc.detail)

        def events() -> Iterator[str]:
            for line in run.follow():
                yield json.dumps({"line": line}) + "\n"
            yield json.dumps({"final": demo_console.final_event(run, read_back)}) + "\n"

        return StreamingResponse(events(), media_type="application/x-ndjson")

    return console


def _stop_console_runs(app: FastAPI) -> None:
    """Stop the console child `app` launched, if one is still running."""
    runs: dict[str, demo_console.ConsoleRun] = getattr(app.state, "console_runs", {})
    for run in list(runs.values()):
        demo_console.stop_child(run.process)


class _ConsoleStoppingServer(uvicorn.Server):
    """uvicorn's server, stopping the console child before it drains connections.

    uvicorn's own `shutdown` waits for every open connection before it sends
    the lifespan shutdown event, and a browser following a run's stream holds
    one open until the child exits: stopped with a stream open, the service
    would wait out the whole run, and a second Ctrl+C (`force_exit`) skips the
    lifespan event altogether. Stopping the child first ends its stream, so the
    connection closes and the drain proceeds.
    """

    def __init__(self, config: uvicorn.Config, app: FastAPI) -> None:
        super().__init__(config)
        self._app = app

    async def shutdown(self, sockets: list[socket.socket] | None = None) -> None:
        # In a worker thread: the graceful stop can wait `GRACE_S`, and the
        # event loop must keep serving the stream that is being ended.
        await asyncio.to_thread(_stop_console_runs, self._app)
        await super().shutdown(sockets)


def _serve(app: FastAPI, **options: Any) -> None:
    """`uvicorn.run`'s single-process path, on the console-stopping server.

    The `finally` is the backstop for every other exit (a force exit, an
    exception out of the loop): no console child outlives the service.
    """
    server = _ConsoleStoppingServer(uvicorn.Config(app, **options), app)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        _stop_console_runs(app)
    if not server.started:
        sys.exit(STARTUP_FAILURE)


def main() -> int:
    """Load the settings, build the app, and serve it over TLS.

    A missing key or TLS cert/key pair returns 1 with its message on stderr
    and binds no socket. TLS is unconditional -- on loopback included -- the
    same posture `load_service_settings` already takes for `SERVICE_API_KEY`.

    A pair that exists but cannot be loaded (swapped files, a directory, not
    PEM) is refused the same way, before the `serving https://` line: uvicorn
    would otherwise load it only inside `run`, after that line already
    claimed the service was up, and fail with a bare traceback.
    """
    try:
        settings = load_service_settings()
    except SettingsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(
            settings.tls_certfile, settings.tls_keyfile
        )
    except (ssl.SSLError, OSError) as exc:
        print(
            "SERVICE_TLS_CERTFILE/SERVICE_TLS_KEYFILE do not form a loadable "
            f"TLS cert/key pair: {exc}",
            file=sys.stderr,
        )
        return 1

    app = create_app(settings)
    # The bound address and the floor in force, and nothing else. Never the
    # key, never its length.
    print(
        f"serving https://{settings.host}:{settings.port} "
        f"at schema floor {settings.schema_floor}"
    )
    # `proxy_headers=False` is what makes `is_loopback_client`'s "the peer
    # address is the only input" true of the running process. uvicorn's own
    # default is `True`, which wraps the app in `ProxyHeadersMiddleware` and
    # rewrites `scope["client"]` from `X-Forwarded-For` -- turning a loopback
    # client that happens to send the header into a refused one, and putting
    # the key gate's only input one `FORWARDED_ALLOW_IPS` value away from
    # being client-supplied. This epic has no reverse-proxy posture, so the
    # middleware has nothing to do here but weaken the gate.
    _serve(
        app,
        host=settings.host,
        port=settings.port,
        proxy_headers=False,
        ssl_certfile=settings.tls_certfile,
        ssl_keyfile=settings.tls_keyfile,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Running the demo: TLS, the key, and a second laptop

The path a consultant actually runs, end to end: a key, a bind address, a
certificate, then the service — followed by what the second machine (the one
watching the pitch, not running the benchmark) does to reach it. Assumes
`docs/setup.md`'s section 1.1 has already produced `frontend/dist/`.

## 1. Generate a key

The service refuses to start without `SERVICE_API_KEY`, on a loopback bind
included. Generate one — never a value this doc ships:

```sh
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put it in `.env` as `SERVICE_API_KEY=<the generated value>`.

## 2. Choose the bind address

Set `SERVICE_HOST` to the bench machine's actual LAN IP (e.g. `192.168.1.50`)
— not `0.0.0.0`. The second laptop reaches the service at this address, and
the certificate generated in the next step must cover it.

## 3. Generate or obtain the certificate

Self-signed, one command, valid for `127.0.0.1`, `localhost` and every
`--host` passed:

```sh
uv run python scripts/generate_dev_cert.py --host <the LAN IP from step 2>
```

Writes `dev-certs/cert.pem` and `dev-certs/key.pem` (gitignored). Point
`.env` at them:

```
SERVICE_TLS_CERTFILE=dev-certs/cert.pem
SERVICE_TLS_KEYFILE=dev-certs/key.pem
```

Already have an operator-provided certificate instead? Point
`SERVICE_TLS_CERTFILE`/`SERVICE_TLS_KEYFILE` at that pair and skip the
generator.

Re-running the generator overwrites the pair rather than refusing — a
re-issued cert (a new LAN IP, an expired one) is this same one-command retry,
not a manual delete-first step.

## 4. Start the service

```sh
uv run wave-local-ai-v2-serve
```

Prints `serving https://<host>:<port> at schema floor <floor>` once bound.

## 5. The second machine

1. **Trust the self-signed cert once.** Either import `dev-certs/cert.pem`
   into the OS/browser trust store, or open `https://<bench-ip>:<port>` once
   and accept the browser's self-signed warning — both are one-time steps,
   and the documented fallback is the browser warning: click through it once
   per browser per machine.
2. Open `https://<bench-ip>:<port>`. With no key held in this browser tab's
   session, the dashboard renders a dialog labeled **"API key required"**
   stating "This dashboard needs the service's API key" — nothing else: no
   path, no store location, no hint whether a prior attempt was absent or
   wrong.
3. Enter the key from step 1. A wrong key clears it and re-shows the same
   dialog with **"The service refused that key. Enter it again."** — this is
   the expected refusal, recognizable mid-pitch rather than mistaken for a
   bug. Re-entering the correct key proceeds to the dashboard.

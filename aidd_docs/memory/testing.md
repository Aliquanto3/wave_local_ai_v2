# Testing

How the project is tested: the layers, the tools, and the conventions.

## Strategy

- Unit tests cover pure logic (scoring functions, metric parsers, flag builders).
- No integration or e2e tests yet; the benchmark runner itself is the integration harness.

## Tools

- pytest — test runner and assertion library
- mypy — catches type errors before tests run

## Conventions

- Tests live under `tests/`, mirroring `src/wave_local_ai_v2/`.
- Test files named `test_<module>.py`.
- No tests should start a real llama.cpp server or call live cloud APIs; stub the HTTP client.

## Run

- `uv run pytest`

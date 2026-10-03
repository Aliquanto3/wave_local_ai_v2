"""The run profile registry: the host-fitted launch settings of one
(roster entry x machine x compute mode) triple, declared as named data.

One resolution order, stated here and in `docs/setup.md` section 4:

1. the roster entry's own default (`server_flags.n_gpu_layers`; no
   `--n-cpu-moe` and no thread count are model-intrinsic, so the roster has
   none);
2. the profile: the per-(machine, mode) default in `defaults`, with any value
   the entry overrides for that (machine, mode) in `entries` laid over it;
3. the operator's explicit override (`SERVER_N_CPU_MOE`, `SERVER_THREADS`),
   applied last and recorded on every row as a deviation from the profile.

So a fifth roster entry needs no hand-written profile unless it differs: every
declared (machine, mode) is a profile of every entry. A triple whose
(machine, mode) is not declared has no profile and is refused before any
server starts, naming the triple and the profiles that do exist.

Every value is `{value, source, read_from}` under the machine registry's
honesty discipline: `declared` was read or fitted (`read_from` names where),
`not_yet_declared` nobody has read (value `null`, `read_from` names what it
awaits). A run under a profile with an undeclared value refuses unless the
operator overrides that value, and the row then says so.

`server.build_flags` is the only flag builder; it takes the `ResolvedProfile`
this module returns as a required argument, so no launch can fall back to
another machine's values.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import machines, roster

DEFAULT_REGISTRY_PATH = "aidd_docs/roster/profiles.json"

# The three launch values a profile may set. `n_gpu_layers` overrides the
# roster's model-intrinsic default; the other two are host-fitted only.
PROFILE_SETTINGS: tuple[str, ...] = ("n_gpu_layers", "n_cpu_moe", "threads")
# The values an operator may override, with the variable that carries each.
OPERATOR_OVERRIDES: dict[str, str] = {
    "n_cpu_moe": "SERVER_N_CPU_MOE",
    "threads": "SERVER_THREADS",
}

# What `profile_overrides` records as the profile's side of an override whose
# profile value nobody has declared yet.
PROFILE_VALUE_NOT_YET_DECLARED = machines.SOURCE_NOT_YET_DECLARED

_FACT_FIELDS = ("value", "source", "read_from")


class ProfileError(roster.RosterError):
    """Raised when the registry is malformed or a triple cannot be resolved.

    A `RosterError`: like a dense entry handed `--n-cpu-moe`, a triple with no
    profile is a launch that cannot be built, refused before any spawn by the
    same handler in every writer.
    """


@dataclass(frozen=True)
class ProfileRegistry:
    registry_version: int
    # (machine_id, compute_mode) -> setting -> fact
    defaults: dict[tuple[str, str], dict[str, dict[str, Any]]]
    # entry_id -> (machine_id, compute_mode) -> setting -> fact
    entries: dict[str, dict[tuple[str, str], dict[str, dict[str, Any]]]]


@dataclass(frozen=True)
class ResolvedProfile:
    """The launch values one run is executed under, after the full resolution."""

    profile_id: str
    entry_id: str
    machine_id: str
    compute_mode: str
    n_gpu_layers: int
    # `None`: no `--n-cpu-moe` on the command line at all.
    n_cpu_moe: int | None
    threads: int
    # setting -> {"profile": <profile value, null, or not_yet_declared>,
    # "operator": <value>}; empty when the run is the profile as declared.
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def cpu_only(self) -> bool:
        return self.compute_mode == machines.COMPUTE_MODE_CPU_ONLY


def profile_id_for(entry_id: str, machine_id: str, compute_mode: str) -> str:
    """The name of the profile of one triple."""
    return f"{entry_id}@{machine_id}/{compute_mode}"


def load_registry(path: Path) -> ProfileRegistry:
    """Parse `path`, refusing any malformed block by name."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfileError(f"profile registry not readable at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(
            f"profile registry at {path} is not valid JSON: {exc}"
        ) from exc
    if (
        not isinstance(raw, dict)
        or not {
            "registry_version",
            "defaults",
            "entries",
        }
        <= raw.keys()
    ):
        raise ProfileError(
            f"profile registry at {path} must be an object with "
            "'registry_version', 'defaults' and 'entries'"
        )
    version = raw["registry_version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise ProfileError(
            f"profile registry at {path}: 'registry_version' must be an integer, "
            f"got {version!r}"
        )
    defaults = _parse_modes("defaults", raw["defaults"])
    if not defaults:
        raise ProfileError(f"profile registry at {path}: 'defaults' declares nothing")
    for (machine_id, mode), values in defaults.items():
        where = f"defaults.{machine_id}.{mode}"
        if "threads" not in values:
            raise ProfileError(f"{where} declares no 'threads' value")
        _check_mode_values(where, mode, values)

    raw_entries = raw["entries"]
    if not isinstance(raw_entries, dict):
        raise ProfileError("'entries' must be an object")
    entries: dict[str, dict[tuple[str, str], dict[str, dict[str, Any]]]] = {}
    for entry_id, raw_entry in raw_entries.items():
        overrides = _parse_modes(f"entries.{entry_id}", raw_entry)
        for key, values in overrides.items():
            where = f"entries.{entry_id}.{key[0]}.{key[1]}"
            if key not in defaults:
                raise ProfileError(
                    f"{where} overrides a (machine, mode) with no declared "
                    "default profile: declare the default first"
                )
            _check_mode_values(where, key[1], values)
        entries[entry_id] = overrides
    return ProfileRegistry(registry_version=version, defaults=defaults, entries=entries)


def _parse_modes(
    where: str, raw: Any
) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    """`{machine_id: {mode: {setting: fact}}}` flattened to (machine, mode) keys."""
    if not isinstance(raw, dict):
        raise ProfileError(f"'{where}' must be an object")
    result: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for machine_id, modes in raw.items():
        if not isinstance(modes, dict) or not modes:
            raise ProfileError(f"'{where}.{machine_id}' must be a non-empty object")
        for mode, values in modes.items():
            at = f"{where}.{machine_id}.{mode}"
            if mode not in machines.COMPUTE_MODES:
                raise ProfileError(
                    f"'{at}': {mode!r} is not a compute mode "
                    f"({' or '.join(machines.COMPUTE_MODES)})"
                )
            if not isinstance(values, dict):
                raise ProfileError(f"'{at}' must be an object")
            for name, fact in values.items():
                _check_fact(f"{at}.{name}", name, fact)
            result[(machine_id, mode)] = {
                name: dict(fact) for name, fact in values.items()
            }
    return result


def _check_fact(where: str, name: str, fact: Any) -> None:
    if name not in PROFILE_SETTINGS:
        raise ProfileError(
            f"'{where}' is not a profile setting ({', '.join(PROFILE_SETTINGS)})"
        )
    if not isinstance(fact, dict) or set(fact) != set(_FACT_FIELDS):
        raise ProfileError(f"'{where}' must be an object of {', '.join(_FACT_FIELDS)}")
    source, value, read_from = fact["source"], fact["value"], fact["read_from"]
    if not isinstance(read_from, str) or not read_from.strip():
        raise ProfileError(f"'{where}': 'read_from' must be a non-empty string")
    if source == machines.SOURCE_NOT_YET_DECLARED:
        if value is not None:
            raise ProfileError(
                f"'{where}' is {source!r} but carries a value ({value!r}): a value "
                "nobody has read is never published"
            )
        return
    if source != machines.SOURCE_DECLARED:
        raise ProfileError(
            f"'{where}': 'source' must be one of "
            f"{sorted(machines.FACT_SOURCES)}, got {source!r}"
        )
    minimum = 1 if name == "threads" else 0
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ProfileError(
            f"'{where}' must declare an integer of at least {minimum}, got {value!r}"
        )


def _check_mode_values(where: str, mode: str, values: dict[str, Any]) -> None:
    """A `cpu_only` profile puts every layer on the CPU and offloads no experts."""
    if mode != machines.COMPUTE_MODE_CPU_ONLY:
        return
    if "n_cpu_moe" in values:
        raise ProfileError(
            f"'{where}' declares n_cpu_moe under 'cpu_only': every layer is "
            "already on the CPU, and --n-cpu-moe 0 would mean the opposite"
        )
    layers = values.get("n_gpu_layers")
    if layers is not None and layers.get("value") != 0:
        raise ProfileError(
            f"'{where}' declares n_gpu_layers {layers.get('value')!r} under "
            "'cpu_only': the mode puts every layer on the CPU (0)"
        )


@lru_cache(maxsize=1)
def tracked_registry() -> ProfileRegistry:
    """The tracked registry, loaded once per process."""
    return load_registry(Path(DEFAULT_REGISTRY_PATH))


def resolve_for_run(
    entry: roster.RosterEntry,
    machine_id: str,
    compute_mode: str,
    *,
    operator_n_cpu_moe: int | None,
    operator_threads: int | None,
) -> ResolvedProfile:
    """`resolve` against the tracked registry: what every writer calls."""
    return resolve(
        tracked_registry(),
        entry,
        machine_id,
        compute_mode,
        operator_n_cpu_moe=operator_n_cpu_moe,
        operator_threads=operator_threads,
    )


def declared_profiles(registry: ProfileRegistry, entry_id: str) -> list[str]:
    """Every profile id declared for `entry_id`, sorted."""
    return sorted(profile_id_for(entry_id, m, mode) for m, mode in registry.defaults)


def resolve(
    registry: ProfileRegistry,
    entry: roster.RosterEntry,
    machine_id: str,
    compute_mode: str,
    *,
    operator_n_cpu_moe: int | None = None,
    operator_threads: int | None = None,
) -> ResolvedProfile:
    """Resolve one triple: entry default, then profile, then operator override.

    Raises `ProfileError` for a triple with no declared profile (naming it and
    the entry's declared profiles) and for a profile value nobody has declared
    that the operator did not override.
    """
    key = (machine_id, compute_mode)
    profile_id = profile_id_for(entry.entry_id, machine_id, compute_mode)
    if key not in registry.defaults:
        declared = ", ".join(declared_profiles(registry, entry.entry_id))
        raise ProfileError(
            f"no run profile is declared for (roster entry {entry.entry_id!r}, "
            f"machine {machine_id!r}, compute mode {compute_mode!r}); the "
            f"profiles declared for this entry are: {declared}"
        )
    facts = dict(registry.defaults[key])
    facts.update(registry.entries.get(entry.entry_id, {}).get(key, {}))

    # 1. entry default, 2. profile.
    values: dict[str, Any] = {
        "n_gpu_layers": entry.server_flags["n_gpu_layers"],
        "n_cpu_moe": None,
    }
    pending: dict[str, str] = {}
    for name, fact in facts.items():
        if fact["source"] == machines.SOURCE_NOT_YET_DECLARED:
            values[name] = PROFILE_VALUE_NOT_YET_DECLARED
            pending[name] = fact["read_from"]
        else:
            values[name] = fact["value"]

    # 3. operator override, recorded against the profile's own value.
    overrides: dict[str, dict[str, Any]] = {}
    for name, operator in (
        ("n_cpu_moe", operator_n_cpu_moe),
        ("threads", operator_threads),
    ):
        if operator is None:
            continue
        overrides[name] = {"profile": values[name], "operator": operator}
        values[name] = operator
        pending.pop(name, None)

    if pending:
        missing = "; ".join(
            f"{name} ({read_from})" for name, read_from in sorted(pending.items())
        )
        variables = [
            OPERATOR_OVERRIDES[n] for n in sorted(pending) if n in OPERATOR_OVERRIDES
        ]
        hint = (
            f"; set {', '.join(variables)} to run with an operator override"
            if variables
            else ""
        )
        raise ProfileError(
            f"run profile {profile_id!r} has no declared value for: {missing}{hint}"
        )
    return ResolvedProfile(
        profile_id=profile_id,
        entry_id=entry.entry_id,
        machine_id=machine_id,
        compute_mode=compute_mode,
        n_gpu_layers=values["n_gpu_layers"],
        n_cpu_moe=values["n_cpu_moe"],
        threads=values["threads"],
        overrides=overrides,
    )

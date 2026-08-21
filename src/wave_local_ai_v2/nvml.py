"""Shared NVML session handling: init/handle/shutdown in one place.

Both `hardware.py` (fiche capture) and `gpu.py` (per-run stats) need a short-lived
NVML session around one or two queries. Neither leaves a global handle open across
the process lifetime -- NVML is initialized and shut down for each call site's use,
per the architecture memory's guidance to keep GPU measurement best-effort.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


@contextmanager
def nvml_device(device_index: int = 0) -> Iterator[Any]:
    """Yield the NVML device handle for `device_index`, init/shutdown scoped to the call."""
    import pynvml

    pynvml.nvmlInit()
    try:
        yield pynvml.nvmlDeviceGetHandleByIndex(device_index)
    finally:
        pynvml.nvmlShutdown()


def decode_nvml_str(value: bytes | str) -> str:
    """NVML string fields come back as bytes on some driver/binding combinations."""
    return value.decode() if isinstance(value, bytes) else value

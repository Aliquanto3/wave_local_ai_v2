"""Emissions: the offline factor/region as configured values, the local
Scope-2 conversion, and the Scope-3 cloud-inference estimate.

The default `EMISSION_FACTOR_KG_PER_KWH` (in `settings.py`) traces to
`.venv/Lib/site-packages/codecarbon/data/private_infra/global_energy_mix.json`'s
`"FRA"` entry: `carbon_intensity` = 56.039 gCO2eq/kWh (year 2023), i.e.
0.056039 kg/kWh.

Scope 2 (local): CodeCarbon measures `energy_kwh` on this machine; this
module converts it to `emissions_kg` with the configured factor -- one
arithmetic source, not CodeCarbon's own internal emissions figure.

Scope 3 (cloud): no on-machine energy exists to attribute to a network call.
`scope3_cloud_emissions` estimates both energy and emissions from a
Wh-per-token rate and the same emission factor. The two scopes are not
like-for-like -- see `SCOPE_COMPARABILITY_NOTE`.
"""

from __future__ import annotations

EMISSIONS_SCOPE_2 = "scope_2"
EMISSIONS_SCOPE_3 = "scope_3"
SCOPE3_FORMULA_ID = "scope3-v1-wh-per-token"
SCOPE_COMPARABILITY_NOTE = (
    "not like-for-like: no local Scope-3 component exists yet "
    "(facility overhead, hardware amortization)"
)


def local_emissions(energy_kwh: float | None, factor_kg_per_kwh: float) -> float | None:
    """Scope-2 emissions from a measured local `energy_kwh`.

    Returns `None` when `energy_kwh` is `None` (the tracker was unavailable --
    no fabricated emissions off a missing measurement).
    """
    if energy_kwh is None:
        return None
    return energy_kwh * factor_kg_per_kwh


def scope3_cloud_emissions(
    total_tokens: int, wh_per_token: float, factor_kg_per_kwh: float
) -> tuple[float, float]:
    """Scope-3 energy and emissions estimate for a cloud batch, from its total
    token count.

    Returns `(energy_kwh_estimate, emissions_kg)`.
    """
    energy_kwh_estimate = total_tokens * wh_per_token / 1000
    emissions_kg = energy_kwh_estimate * factor_kg_per_kwh
    return energy_kwh_estimate, emissions_kg

"""Block CI on unwaived high-severity dependency vulnerabilities.

Runs `pip-audit` over the locked dependencies, resolves each finding's
severity via the OSV API (pip-audit itself never reports severity), and
fails closed: a HIGH/CRITICAL finding, or one whose severity can't be
resolved, blocks unless a current, not-over-90-days waiver entry in
docs/dependency-waivers.yml covers it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import requests
import yaml

WAIVERS_PATH = (
    Path(__file__).resolve().parent.parent / "docs" / "dependency-waivers.yml"
)
OSV_VULN_URL = "https://api.osv.dev/v1/vulns/{id}"
BLOCKING_SEVERITIES = {"HIGH", "CRITICAL", "UNKNOWN"}
MAX_WAIVER_DAYS = 90


def run_pip_audit() -> dict[str, Any]:
    """Run pip-audit over the locked dependencies and return its parsed JSON.

    `pip-audit --locked` only reads PEP 751 `pylock.toml` files, not `uv.lock`
    directly, so `uv.lock` is exported to one in a scratch directory first —
    this is what makes pip-audit see the exact locked dependency set,
    including platform-marker-only packages that may not be installed here.
    """
    with tempfile.TemporaryDirectory() as scratch_dir:
        export = subprocess.run(
            [
                "uv",
                "export",
                "--format",
                "pylock.toml",
                "-o",
                f"{scratch_dir}/pylock.toml",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if export.returncode != 0:
            raise RuntimeError(f"uv export failed: {export.stderr}")

        result = subprocess.run(
            [
                "uv",
                "run",
                "pip-audit",
                "--format",
                "json",
                "--progress-spinner",
                "off",
                "--locked",
                "-s",
                "osv",
                scratch_dir,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    if result.returncode not in (0, 1):
        # 0 = no vulnerabilities, 1 = vulnerabilities found; anything else is a tool failure.
        raise RuntimeError(f"pip-audit failed: {result.stderr}")
    output: dict[str, Any] = json.loads(result.stdout)
    return output


def resolve_severity(vuln_id: str) -> str:
    """Resolve an advisory's severity via the OSV API, or "UNKNOWN" if absent."""
    response = requests.get(OSV_VULN_URL.format(id=vuln_id), timeout=30)
    if not response.ok:
        return "UNKNOWN"
    data = response.json()
    severity = data.get("database_specific", {}).get("severity")
    if not severity:
        return "UNKNOWN"
    return str(severity).upper()


def load_waivers(path: Path) -> list[dict[str, Any]]:
    """Parse the waiver file into its list of entries."""
    with path.open("r", encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}
    waivers: list[dict[str, Any]] = content.get("waivers", []) or []
    return waivers


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=UTC).date()


def waiver_rejection(entry: dict[str, Any], today: date) -> str | None:
    """Return why a waiver entry is invalid, or None when it is currently valid.

    The reason is what the run prints, so an expired or over-long entry is
    named rather than silently reading as "no waiver at all".
    """
    opened = _as_date(entry["opened"])
    expiry = _as_date(entry["expiry"])
    if expiry < today:
        return f"expired {expiry.isoformat()}"
    lifetime = (expiry - opened).days
    if lifetime > MAX_WAIVER_DAYS:
        return f"lifetime {lifetime} days > {MAX_WAIVER_DAYS}"
    return None


def evaluate_waiver(entry: dict[str, Any], today: date) -> bool:
    """Return whether a waiver entry is currently valid: not expired, not over 90 days."""
    return waiver_rejection(entry, today) is None


def _matching_entries(
    package: str, vuln_id: str, waivers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        entry
        for entry in waivers
        if entry.get("package") == package and entry.get("id") == vuln_id
    ]


def _finding_waiver(
    package: str, vuln_id: str, waivers: list[dict[str, Any]], today: date
) -> dict[str, Any] | None:
    for entry in _matching_entries(package, vuln_id, waivers):
        if evaluate_waiver(entry, today):
            return entry
    return None


def select_blocking(
    findings: list[dict[str, Any]], waivers: list[dict[str, Any]], today: date
) -> list[dict[str, Any]]:
    """Keep findings that are blocking severity and have no valid matching waiver."""
    blocking: list[dict[str, Any]] = []
    for finding in findings:
        severity = finding["severity"]
        if severity not in BLOCKING_SEVERITIES:
            continue
        waiver = _finding_waiver(finding["package"], finding["id"], waivers, today)
        if waiver is None:
            blocking.append(finding)
    return blocking


def _collect_findings(audit_output: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for dependency in audit_output.get("dependencies", []):
        package = dependency.get("name", "<unknown>")
        for vuln in dependency.get("vulns", []):
            vuln_id = vuln["id"]
            findings.append(
                {
                    "package": package,
                    "id": vuln_id,
                    "severity": resolve_severity(vuln_id),
                }
            )
    return findings


def main() -> int:
    audit_output = run_pip_audit()
    findings = _collect_findings(audit_output)
    waivers = load_waivers(WAIVERS_PATH)
    today = datetime.now(tz=UTC).date()
    blocking = select_blocking(findings, waivers, today)

    blocking_keys = {(finding["package"], finding["id"]) for finding in blocking}
    for finding in findings:
        package, vuln_id = finding["package"], finding["id"]
        if (package, vuln_id) in blocking_keys:
            rejections = [
                reason
                for entry in _matching_entries(package, vuln_id, waivers)
                if (reason := waiver_rejection(entry, today)) is not None
            ]
            status = (
                f"BLOCKING (waiver {'; '.join(rejections)})"
                if rejections
                else "BLOCKING (no waiver)"
            )
        elif finding["severity"] in BLOCKING_SEVERITIES:
            status = "waived"
        else:
            status = "below-threshold"
        print(f"{package} {vuln_id} severity={finding['severity']} {status}")

    if not findings:
        print("no findings")

    if blocking:
        print(f"{len(blocking)} blocking finding(s), no valid waiver")
        return 1

    print("no blocking findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())

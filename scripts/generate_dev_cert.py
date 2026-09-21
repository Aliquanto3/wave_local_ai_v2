"""Generate a self-signed TLS certificate for the demo service.

One command, self-signed, valid for the addresses the demo actually uses:
`127.0.0.1` and `localhost` always, plus every `--host` value the operator
passes -- the second laptop's LAN address must be a name the certificate
actually covers, or the browser's one-time trust step fails.

Re-running overwrites rather than refusing: a re-issued cert is a documented
retry, not a manual delete-first step.
"""

from __future__ import annotations

import argparse
import datetime
import ipaddress
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

DEFAULT_OUT_DIR = "dev-certs"
SUBJECT_NAME = "wave-local-ai-v2 demo"
# Under the CA/Browser Forum's public-cert ceiling, though this cert is never
# publicly trusted -- a sane default rather than an arbitrary one.
VALIDITY_DAYS = 397


def _san_entry(host: str) -> x509.GeneralName:
    try:
        return x509.IPAddress(ipaddress.ip_address(host))
    except ValueError:
        return x509.DNSName(host)


def generate_cert(hosts: list[str]) -> tuple[bytes, bytes]:
    """Build a self-signed RSA cert/key pair, PEM-encoded.

    The SAN carries `127.0.0.1`, `localhost` and every entry of `hosts`, each
    parsed as an `ipaddress` when it parses as one, else as a DNS name.
    """
    san_hosts = ["127.0.0.1", "localhost", *hosts]
    san = x509.SubjectAlternativeName([_san_entry(host) for host in san_hosts])

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, SUBJECT_NAME)]
    )
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=VALIDITY_DAYS))
        .add_extension(san, critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        action="append",
        default=[],
        help="an address the certificate must cover (repeatable)",
    )
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help=f"directory to write cert.pem/key.pem into (default: {DEFAULT_OUT_DIR})",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cert_pem, key_pem = generate_cert(args.host)

    cert_path = out_dir / "cert.pem"
    key_path = out_dir / "key.pem"
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)

    print(cert_path)
    print(key_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

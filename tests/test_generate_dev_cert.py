import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from cryptography import x509
from generate_dev_cert import generate_cert, main


def test_generate_cert_san_covers_loopback_localhost_and_every_host() -> None:
    cert_pem, _key_pem = generate_cert(["192.168.1.50"])

    certificate = x509.load_pem_x509_certificate(cert_pem)
    san = certificate.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value
    ip_names = {str(ip) for ip in san.get_values_for_type(x509.IPAddress)}
    dns_names = set(san.get_values_for_type(x509.DNSName))

    assert "127.0.0.1" in ip_names
    assert "192.168.1.50" in ip_names
    assert "localhost" in dns_names


def test_the_generated_pair_loads_into_a_real_ssl_context(tmp_path: Path) -> None:
    cert_pem, key_pem = generate_cert(["127.0.0.1"])
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))


def test_main_writes_cert_and_key_and_prints_only_their_paths(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    out_dir = tmp_path / "dev-certs"
    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_dev_cert.py", "--host", "127.0.0.1", "--out-dir", str(out_dir)],
    )

    exit_code = main()

    assert exit_code == 0
    assert (out_dir / "cert.pem").is_file()
    assert (out_dir / "key.pem").is_file()
    printed = capsys.readouterr().out
    assert str(out_dir / "cert.pem") in printed
    assert str(out_dir / "key.pem") in printed


def test_re_running_overwrites_rather_than_refusing(
    tmp_path: Path, monkeypatch
) -> None:
    out_dir = tmp_path / "dev-certs"
    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_dev_cert.py", "--host", "127.0.0.1", "--out-dir", str(out_dir)],
    )

    assert main() == 0
    first = (out_dir / "cert.pem").read_bytes()
    assert main() == 0
    second = (out_dir / "cert.pem").read_bytes()

    assert first != second

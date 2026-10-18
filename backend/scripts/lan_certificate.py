"""Create a private local CA and an HTTPS certificate for one LAN IPv4 address."""

from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address, ip_address
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def lan_ip(value: str) -> IPv4Address:
    address = ip_address(value)
    if not isinstance(address, IPv4Address) or address.is_unspecified or address.is_multicast or not (
        address.is_private or address.is_loopback
    ):
        raise ValueError("Use a private or loopback IPv4 address assigned to this desktop")
    return address


def _write_private(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)


def ensure_certificate(host: str, directory: Path) -> tuple[Path, Path, Path]:
    address = lan_ip(host)
    ca_certificate = directory / "lan-ca.pem"
    ca_private_key = directory / "lan-ca-key.pem"
    server_certificate = directory / "lan-server.pem"
    server_private_key = directory / "lan-server-key.pem"
    files = (ca_certificate, ca_private_key, server_certificate, server_private_key)
    if any(path.exists() for path in files):
        if not all(path.is_file() for path in files):
            raise RuntimeError("Incomplete LAN certificate set; inspect .certs before retrying")
        certificate = x509.load_pem_x509_certificate(server_certificate.read_bytes())
        names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        if address not in names.get_values_for_type(x509.IPAddress):
            raise RuntimeError("Existing LAN certificate is for a different IP address")
        if certificate.not_valid_after_utc <= datetime.now(timezone.utc):
            raise RuntimeError("Existing LAN certificate has expired")
        return ca_certificate, server_certificate, server_private_key

    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Offline AI Learning LAN CA")])
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, str(address))])
    ca_cert = (
        x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=1825))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                                     key_encipherment=False, data_encipherment=False,
                                     key_agreement=False, key_cert_sign=True, crl_sign=True,
                                     encipher_only=False, decipher_only=False), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    server_cert = (
        x509.CertificateBuilder().subject_name(server_name).issuer_name(ca_name)
        .public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.SubjectAlternativeName([
            x509.IPAddress(address), x509.IPAddress(ip_address("127.0.0.1")),
            x509.DNSName("localhost"),
        ]), critical=False)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                                     key_encipherment=True, data_encipherment=False,
                                     key_agreement=False, key_cert_sign=False, crl_sign=False,
                                     encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    _write_private(ca_private_key, ca_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    _write_private(server_private_key, server_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    ca_certificate.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    server_certificate.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    return ca_certificate, server_certificate, server_private_key

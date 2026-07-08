#!/usr/bin/env python3
"""Builds the CA bundle Heather packages for CDSO pipeline runtime."""

# Standard library imports.
from os import environ
from pathlib import Path
from ssl import get_default_verify_paths


OUTPUT_PATH = Path("heather/certs/cdso-ca-bundle.pem")
DEFAULT_CERT_PATHS = [
    "/etc/ssl/certs/ca-certificates.crt",
    "/usr/local/share/ca-certificates/dod.crt",
    "/usr/local/share/ca-certificates/wcf.crt",
]
DOD_CERT_FILENAMES = {"dod.crt", "wcf.crt"}


def main() -> None:
    """Writes a combined system plus CDSO DoD CA bundle for package data."""
    bundle_parts = []
    seen_paths = set()
    dod_cert_seen = False

    for cert_path in get_candidate_cert_paths():
        resolved_path = cert_path.resolve()

        if resolved_path in seen_paths:
            continue

        seen_paths.add(resolved_path)

        if cert_path.is_file() is False:
            continue

        cert_content = cert_path.read_text(encoding="utf-8").strip()

        if cert_content == "":
            continue

        if cert_path.name in DOD_CERT_FILENAMES:
            dod_cert_seen = True

        bundle_parts.append(f"# Source: {cert_path}\n{cert_content}\n")

    if len(bundle_parts) == 0:
        raise RuntimeError("No CA certificate sources were found.")

    if environ.get("HEATHER_REQUIRE_DOD_CERTS") == "1" and dod_cert_seen is False:
        raise RuntimeError(
            "HEATHER_REQUIRE_DOD_CERTS=1 but no CDSO DoD certificate files were found."
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(bundle_parts), encoding="utf-8")
    print(f"Built Heather CA bundle: {OUTPUT_PATH}")


def get_candidate_cert_paths() -> list[Path]:
    """Returns ordered CA bundle/certificate paths available in CI."""
    cert_paths = []

    for environment_name in [
        "HEATHER_CA_BUNDLE_SOURCE",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
    ]:
        environment_value = environ.get(environment_name, "").strip()

        if environment_value != "":
            cert_paths.append(Path(environment_value))

    default_verify_path = get_default_verify_paths().cafile

    if default_verify_path is not None:
        cert_paths.append(Path(default_verify_path))

    for default_cert_path in DEFAULT_CERT_PATHS:
        cert_paths.append(Path(default_cert_path))

    try:
        # Third party imports.
        import certifi

        cert_paths.append(Path(certifi.where()))
    except Exception:
        pass

    return cert_paths


if __name__ == "__main__":
    main()

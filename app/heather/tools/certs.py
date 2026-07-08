# Standard library imports.
from importlib.resources import files
from os import environ
from pathlib import Path


CA_BUNDLE_ENV_VARS = [
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
]
PACKAGED_CA_BUNDLE = Path("certs") / "cdso-ca-bundle.pem"


def configure_packaged_ca_bundle() -> str:
    """Configures Python HTTP clients to trust Heather's packaged CA bundle."""
    ca_bundle_path = get_ca_bundle_path()

    if ca_bundle_path == "":
        return ""

    for environment_name in CA_BUNDLE_ENV_VARS:
        if environ.get(environment_name, "").strip() == "":
            environ[environment_name] = ca_bundle_path

    return ca_bundle_path


def get_ca_bundle_path() -> str:
    """Returns the explicit or packaged CA bundle path Heather should use."""
    configured_bundle_path = environ.get("HEATHER_CA_BUNDLE", "").strip()

    if configured_bundle_path != "":
        return configured_bundle_path

    local_bundle_path = Path(__file__).resolve().parents[1] / PACKAGED_CA_BUNDLE

    if local_bundle_path.is_file():
        return str(local_bundle_path)

    try:
        packaged_bundle_path = files("heather")
    except ModuleNotFoundError:
        return ""

    for path_part in PACKAGED_CA_BUNDLE.parts:
        packaged_bundle_path = packaged_bundle_path.joinpath(path_part)

    if packaged_bundle_path.is_file() is False:
        return ""

    return str(Path(str(packaged_bundle_path)))

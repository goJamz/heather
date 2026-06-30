# Standard library imports.
from os import environ, getenv

# Third party imports.
from gitlab import Gitlab


def get_gitlab_client():
    GITLAB_API_ENDPOINT = environ["GITLAB_API_ENDPOINT"]
    GITLAB_API_TOKEN = environ["GITLAB_API_TOKEN"]
    CURL_CA_BUNDLE = getenv(
        "CURL_CA_BUNDLE",
        "/usr/local/share/ca-certificates/DoD_certs_all.crt",
    )
    return Gitlab(
        GITLAB_API_ENDPOINT, private_token=GITLAB_API_TOKEN, ssl_verify=CURL_CA_BUNDLE
    )

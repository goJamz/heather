# Standard library imports.
from os import environ

# Third party imports.
from azure.identity import (
    AzureAuthorityHosts,
    DefaultAzureCredential,
    get_bearer_token_provider,
)
from langchain_openai import AzureChatOpenAI


def get_azure_openai_model():
    # Get environment variables.
    AZURE_OPENAI_API_VERSION = environ["AZURE_OPENAI_API_VERSION"]
    AZURE_OPENAI_ENDPOINT = environ["AZURE_OPENAI_ENDPOINT"]
    AZURE_OPENAI_DEPLOYMENT = environ["AZURE_OPENAI_DEPLOYMENT"]
    AZURE_TOKEN_SCOPES = environ["AZURE_TOKEN_SCOPES"]

    # Get an authorization token provider.
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(authority=AzureAuthorityHosts.AZURE_GOVERNMENT),
        AZURE_TOKEN_SCOPES,
    )

    # Authenticate with the Azure OpenAI service.
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_ad_token_provider=token_provider,
    )

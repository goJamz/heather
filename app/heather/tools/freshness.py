# Standard library imports.
from datetime import datetime, timezone
from os import getenv
from time import monotonic, sleep

# Local imports.
from constants import GL_ISSUES_COMPLETION_CHECKER_RID, GL_ISSUES_RID
from tools.vantage import get_vantage_client


DEFAULT_POLL_SECONDS = 60
DEFAULT_TIMEOUT_SECONDS = 2700


def wait_for_fresh_gl_issues(
    poll_seconds: int | None = None, timeout_seconds: int | None = None
) -> None:
    """Waits until gl-issues is newer than the completion-checker dataset."""
    poll_seconds = poll_seconds or get_int_env(
        env_var_name="HEATHER_FRESHNESS_POLL_SECONDS",
        default_value=DEFAULT_POLL_SECONDS,
    )
    timeout_seconds = timeout_seconds or get_int_env(
        env_var_name="HEATHER_FRESHNESS_TIMEOUT_SECONDS",
        default_value=DEFAULT_TIMEOUT_SECONDS,
    )

    vantage_client = get_vantage_client()
    validate_remote_configuration(vantage_client=vantage_client)
    foundry_client = vantage_client.client
    branch_name = vantage_client.branch_name
    deadline = monotonic() + timeout_seconds
    poll_count = 0

    print(
        "[*] Waiting for fresh gl-issues: "
        f"branch={branch_name}, poll_seconds={poll_seconds}, "
        f"timeout_seconds={timeout_seconds}, "
        "checker=gl-issues-completion-checker"
    )

    while True:
        poll_count = poll_count + 1
        gl_time = latest_committed_transaction_time(
            client=foundry_client,
            dataset_rid=GL_ISSUES_RID,
            branch_name=branch_name,
        )
        checker_time = latest_committed_transaction_time(
            client=foundry_client,
            dataset_rid=GL_ISSUES_COMPLETION_CHECKER_RID,
            branch_name=branch_name,
        )

        if gl_time is not None and checker_time is not None and gl_time > checker_time:
            print(
                "[+] gl-issues is fresh: "
                f"gl_issues={format_time(gl_time)}, "
                f"checker={format_time(checker_time)}, "
                f"poll_count={poll_count}"
            )
            return

        remaining_seconds = int(deadline - monotonic())

        print(
            "[*] gl-issues not fresh yet: "
            f"gl_issues={format_time(gl_time)}, "
            f"checker={format_time(checker_time)}, "
            f"poll_count={poll_count}, "
            f"remaining_seconds={max(remaining_seconds, 0)}"
        )

        if remaining_seconds <= 0:
            raise TimeoutError(
                "Timed out waiting for fresh gl-issues. "
                f"gl_issues={format_time(gl_time)}, "
                f"checker={format_time(checker_time)}"
            )

        sleep(min(poll_seconds, remaining_seconds))


def latest_committed_transaction_time(
    client, dataset_rid: str, branch_name: str = "master"
) -> datetime | None:
    branch = client.datasets.Dataset.Branch.get(dataset_rid, branch_name)
    transaction_rid = getattr(branch, "transaction_rid", None)

    if transaction_rid is None:
        return None

    transaction = client.datasets.Dataset.Transaction.get(dataset_rid, transaction_rid)

    if status_text(getattr(transaction, "status", "")) != "COMMITTED":
        return None

    return transaction_time(transaction=transaction)


def transaction_time(transaction) -> datetime | None:
    closed_time = coerce_datetime(getattr(transaction, "closed_time", None))

    if closed_time is not None:
        return closed_time

    return coerce_datetime(getattr(transaction, "created_time", None))


def coerce_datetime(value) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    value_text = str(value).strip()

    if value_text == "":
        return None

    value_text = value_text.replace("Z", "+00:00")
    parsed_value = datetime.fromisoformat(value_text)

    if parsed_value.tzinfo is None:
        return parsed_value.replace(tzinfo=timezone.utc)

    return parsed_value.astimezone(timezone.utc)


def status_text(value) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value).split(".")[-1].upper()


def validate_remote_configuration(vantage_client) -> None:
    if vantage_client.hostname == "":
        raise RuntimeError("FOUNDRY_HOSTNAME or VANTAGE_HOSTNAME is required.")

    if vantage_client.token == "":
        raise RuntimeError("FOUNDRY_TOKEN or VANTAGE_TOKEN is required.")


def format_time(value: datetime | None) -> str:
    if value is None:
        return "not ready"

    return value.isoformat()


def get_int_env(env_var_name: str, default_value: int) -> int:
    configured_value = getenv(env_var_name, "").strip()

    if configured_value == "":
        return default_value

    return int(configured_value)

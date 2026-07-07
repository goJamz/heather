# Standard library imports.
from datetime import datetime, timezone
from os import getenv
from time import monotonic, sleep

# Local imports.
from constants import GL_ISSUES_RID
from tools.vantage import get_vantage_client


UPSTREAM_DATASETS = [
    ("ticket-data", "ri.foundry.main.dataset.e2c6e35f-ee6a-421b-98fd-09118ea28a7a"),
    ("tag-data", "ri.foundry.main.dataset.a13f1900-12e2-4134-a444-79b8229f5cd2"),
    ("contact-data", "ri.foundry.main.dataset.e9a5ada6-79f8-421d-a76d-d185cc471ee6"),
    ("wec-data", "ri.foundry.main.dataset.ff4265c7-2926-46fe-b4b3-7d7a89cb90e6"),
    ("activity-data", "ri.foundry.main.dataset.9f374a13-6f3e-4c39-98f1-2872ac1cc5b2"),
    ("tech-eval-data", "ri.foundry.main.dataset.b75c311b-8dbd-49ca-9f7b-e29f7cf617f0"),
    (
        "tech-eval-status-update-data",
        "ri.foundry.main.dataset.d4643d15-6617-4d2a-b8c1-471703d113b8",
    ),
    (
        "implementation-data",
        "ri.foundry.main.dataset.eb747c3f-2055-4a87-9a4d-26ef73d1e6e6",
    ),
    (
        "implementation-status-update-data",
        "ri.foundry.main.dataset.cc4b771a-8979-4ae3-939b-80111d6d1553",
    ),
    ("aar-data", "ri.foundry.main.dataset.d09f72a0-b360-4a49-9638-daf48df769bb"),
]

DEFAULT_POLL_SECONDS = 60
DEFAULT_TIMEOUT_SECONDS = 2700


def wait_for_fresh_gl_issues(
    poll_seconds: int | None = None, timeout_seconds: int | None = None
) -> None:
    """Waits until gl-issues is newer than every upstream Scarab dataset."""
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
        f"timeout_seconds={timeout_seconds}"
    )

    while True:
        poll_count = poll_count + 1
        gl_time = latest_committed_transaction_time(
            client=foundry_client,
            dataset_rid=GL_ISSUES_RID,
            branch_name=branch_name,
        )
        upstream_times = get_upstream_transaction_times(
            client=foundry_client,
            branch_name=branch_name,
        )
        newest_upstream_name, newest_upstream_time = newest_upstream(
            upstream_times=upstream_times
        )
        missing_dataset_names = [
            dataset_name
            for dataset_name, committed_time in upstream_times.items()
            if committed_time is None
        ]

        if (
            gl_time is not None
            and newest_upstream_time is not None
            and len(missing_dataset_names) == 0
            and gl_time > newest_upstream_time
        ):
            print(
                "[+] gl-issues is fresh: "
                f"gl_issues={format_time(gl_time)}, "
                f"newest_upstream={newest_upstream_name} "
                f"{format_time(newest_upstream_time)}, "
                f"poll_count={poll_count}"
            )
            return

        remaining_seconds = int(deadline - monotonic())

        print(
            "[*] gl-issues not fresh yet: "
            f"gl_issues={format_time(gl_time)}, "
            f"newest_upstream={newest_upstream_name} "
            f"{format_time(newest_upstream_time)}, "
            f"missing={format_missing_dataset_names(missing_dataset_names)}, "
            f"poll_count={poll_count}, "
            f"remaining_seconds={max(remaining_seconds, 0)}"
        )

        if remaining_seconds <= 0:
            raise TimeoutError(
                "Timed out waiting for fresh gl-issues. "
                f"gl_issues={format_time(gl_time)}, "
                f"newest_upstream={newest_upstream_name} "
                f"{format_time(newest_upstream_time)}, "
                f"missing={format_missing_dataset_names(missing_dataset_names)}"
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


def get_upstream_transaction_times(
    client, branch_name: str
) -> dict[str, datetime | None]:
    upstream_times = {}

    for dataset_name, dataset_rid in UPSTREAM_DATASETS:
        upstream_times[dataset_name] = latest_committed_transaction_time(
            client=client,
            dataset_rid=dataset_rid,
            branch_name=branch_name,
        )

    return upstream_times


def newest_upstream(
    upstream_times: dict[str, datetime | None]
) -> tuple[str, datetime | None]:
    committed_times = [
        (dataset_name, committed_time)
        for dataset_name, committed_time in upstream_times.items()
        if committed_time is not None
    ]

    if len(committed_times) == 0:
        return "none", None

    return max(committed_times, key=lambda item: item[1])


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


def format_missing_dataset_names(dataset_names: list[str]) -> str:
    if len(dataset_names) == 0:
        return "none"

    return ", ".join(dataset_names)


def get_int_env(env_var_name: str, default_value: int) -> int:
    configured_value = getenv(env_var_name, "").strip()

    if configured_value == "":
        return default_value

    return int(configured_value)

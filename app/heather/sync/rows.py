# Standard library imports.
from datetime import datetime, timezone
from hashlib import sha256
from json import dumps, loads
from os import getenv

# Local imports.
from constants import DEFAULT_BOARD_COLUMN_LABELS
from tools.description import get_external_key_marker

def build_state_row(
    gl_issue_row: dict, gitlab_issue, user_notes: list, run_timestamp: str
) -> dict:
    """Builds one heather-gitlab-state row."""

    issue_data = gitlab_issue.asdict()
    external_key = str(gl_issue_row.get("external_key", "")).strip()
    description = issue_data.get("description", "") or ""
    labels = issue_data.get("labels", []) or []
    assignees = issue_data.get("assignees", []) or []
    external_key_found = (
        get_external_key_marker(external_key=external_key) in description
    )
    sync_status = "ok"

    if external_key_found is False:
        sync_status = "warning"

    return {
        "external_key": external_key,
        "source_system": gl_issue_row.get("source_system", "MCSC/SPEAR"),
        "source_ticket_id": gl_issue_row.get("source_ticket_id", ""),
        "gitlab_project_id": issue_data.get("project_id", ""),
        "gitlab_issue_id": issue_data.get("id", ""),
        "gitlab_iid": issue_data.get("iid", ""),
        "gitlab_web_url": issue_data.get("web_url", ""),
        "gitlab_title": issue_data.get("title", ""),
        "gitlab_state": issue_data.get("state", ""),
        "gitlab_board_column": get_board_column(
            labels=labels, state=issue_data.get("state", "")
        ),
        "gitlab_labels_json": dumps(labels),
        "gitlab_assignees_json": dumps(assignees),
        "gitlab_created_time": issue_data.get("created_at", ""),
        "gitlab_updated_time": issue_data.get("updated_at", ""),
        "gitlab_closed_time": issue_data.get("closed_at", "") or "",
        "gitlab_comment_count": len(user_notes),
        "heather_managed": True,
        "external_key_found": external_key_found,
        "last_seen_time": run_timestamp,
        "last_synced_time": run_timestamp,
        "sync_status": sync_status,
        "sync_error": "",
    }

def build_comment_rows(
    gl_issue_row: dict, gitlab_issue, user_notes: list, run_timestamp: str
) -> list[dict]:
    """Builds heather-gitlab-comments rows for one GitLab issue."""

    issue_data = gitlab_issue.asdict()
    comment_rows = []
    note_data = {}
    note_id = ""
    note_body = ""
    created_time = ""
    updated_time = ""
    project_id = issue_data.get("project_id", "")

    for user_note in user_notes:
        note_data = user_note.asdict()
        note_id = str(note_data.get("id", ""))
        note_body = note_data.get("body", "") or ""
        created_time = note_data.get("created_at", "") or ""
        updated_time = note_data.get("updated_at", "") or ""

        comment_rows.append(
            {
                "note_key": f"gitlab-note-{project_id}-{note_id}",
                "external_key": gl_issue_row.get("external_key", ""),
                "source_ticket_id": gl_issue_row.get("source_ticket_id", ""),
                "gitlab_project_id": project_id,
                "gitlab_iid": issue_data.get("iid", ""),
                "gitlab_issue_id": issue_data.get("id", ""),
                "gitlab_note_id": note_id,
                "gitlab_note_url": build_note_url(
                    issue_url=issue_data.get("web_url", ""), note_id=note_id
                ),
                "author_username": note_data.get("author", {}).get("username", ""),
                "author_name": note_data.get("author", {}).get("name", ""),
                "body": note_body,
                "is_system": False,
                "is_edited": created_time != updated_time,
                "created_time": created_time,
                "updated_time": updated_time,
                "comment_hash": hash_comment_body(body=note_body),
                "last_seen_time": run_timestamp,
                "last_synced_time": run_timestamp,
                "sync_status": "ok",
                "sync_error": "",
            }
        )

    return comment_rows

def build_error_state_row(
    gl_issue_row: dict, run_timestamp: str, sync_error: str
) -> dict:
    """Builds a state row when one source row cannot be processed."""

    return {
        "external_key": gl_issue_row.get("external_key", ""),
        "source_system": gl_issue_row.get("source_system", "MCSC/SPEAR"),
        "source_ticket_id": gl_issue_row.get("source_ticket_id", ""),
        "gitlab_project_id": getenv("GITLAB_PROJECT_ID", ""),
        "gitlab_issue_id": "",
        "gitlab_iid": "",
        "gitlab_web_url": "",
        "gitlab_title": "",
        "gitlab_state": "",
        "gitlab_board_column": "",
        "gitlab_labels_json": dumps([]),
        "gitlab_assignees_json": dumps([]),
        "gitlab_created_time": "",
        "gitlab_updated_time": "",
        "gitlab_closed_time": "",
        "gitlab_comment_count": 0,
        "heather_managed": False,
        "external_key_found": False,
        "last_seen_time": run_timestamp,
        "last_synced_time": run_timestamp,
        "sync_status": "error",
        "sync_error": sync_error,
    }

def get_board_column(labels: list, state: str) -> str:
    """Infers the visible board column from known board-column labels."""

    configured_columns = get_configured_board_columns()

    for label in labels:
        if label in configured_columns:
            return label

    if state == "closed":
        return "Done"

    return ""

def get_configured_board_columns() -> list:
    """Reads known GitLab board column labels from the environment when provided."""

    configured_value = getenv("HEATHER_BOARD_COLUMN_LABELS_JSON", "")

    if configured_value == "":
        return DEFAULT_BOARD_COLUMN_LABELS

    try:
        configured_columns = loads(configured_value)
    except Exception:
        return DEFAULT_BOARD_COLUMN_LABELS

    if isinstance(configured_columns, list):
        return configured_columns

    return DEFAULT_BOARD_COLUMN_LABELS

def build_note_url(issue_url: str, note_id: str) -> str:
    """Builds a GitLab note deep link."""

    if issue_url == "" or note_id == "":
        return ""

    return f"{issue_url}#note_{note_id}"

def hash_comment_body(body: str) -> str:
    """Hashes a GitLab user comment body for edit detection."""

    return sha256(body.encode("UTF-8")).hexdigest()

def get_current_timestamp() -> str:
    """Returns the current UTC timestamp in ISO 8601 format."""

    return datetime.now(timezone.utc).isoformat()

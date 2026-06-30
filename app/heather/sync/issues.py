# Standard library imports.
from os import getenv

# Local imports.
from constants import HEATHER_CREATED_LABEL
from sync.labels import (
    build_gitlab_issue_labels,
    dedupe_labels,
    get_existing_project_label_name,
)
from sync.titles import build_gitlab_issue_title
from tools.description import (
    build_issue_description,
    get_external_key_marker,
    replace_heather_managed_block,
)

def find_gitlab_issue_by_external_key(gitlab_project, external_key: str):
    """Finds an existing GitLab issue by Heather's durable external key marker."""

    marker = get_external_key_marker(external_key=external_key)
    candidate_issues = gitlab_project.issues.list(
        search=external_key,
        state="all",
        get_all=True,
    )
    issue_description = ""

    for candidate_issue in candidate_issues:
        issue_description = candidate_issue.asdict().get("description", "") or ""

        if marker in issue_description:
            return candidate_issue

    return None

def create_gitlab_issue(
    gitlab_project,
    gl_issue_row: dict,
    ai_transcription_check: str = "",
    ai_comment_digest: str = "",
):
    """Creates one missing GitLab issue from one gl-issues row."""

    title = build_gitlab_issue_title(gl_issue_row=gl_issue_row)
    heather_created_label = get_existing_project_label_name(
        gitlab_project=gitlab_project,
        label_name=HEATHER_CREATED_LABEL,
    )
    issue_labels = build_gitlab_issue_labels(
        gitlab_project=gitlab_project,
        gl_issue_row=gl_issue_row,
        existing_labels=[],
    )
    issue_description = build_issue_description(
        gl_issue_row=gl_issue_row,
        ai_transcription_check=ai_transcription_check,
        ai_comment_digest=ai_comment_digest,
    )
    issue_payload = {
        "title": title,
        "description": issue_description,
    }
    gitlab_epic_id = get_gitlab_epic_id()

    if title == "":
        source_ticket_id = gl_issue_row.get("source_ticket_id", "")
        issue_payload["title"] = f"ADOC Ticket #{source_ticket_id}"

    issue_payload["labels"] = dedupe_labels([heather_created_label] + issue_labels)

    if gitlab_epic_id is not None:
        issue_payload["epic_id"] = gitlab_epic_id

    return gitlab_project.issues.create(issue_payload)

def get_gitlab_epic_id() -> int | None:
    """Reads the optional GitLab epic id Heather assigns new issues to."""

    raw_epic_id = getenv("GITLAB_EPIC_ID", "").strip()

    if raw_epic_id == "":
        return None

    try:
        return int(raw_epic_id)
    except ValueError as error:
        raise ValueError("GITLAB_EPIC_ID must be a numeric GitLab epic id") from error

def update_gitlab_issue_managed_block(
    gitlab_issue,
    gl_issue_row: dict,
    ai_transcription_check: str = "",
    ai_comment_digest: str = "",
):
    """Reconciles source-owned fields on an existing Heather-tracked issue.

    Heather refreshes only its managed description block. It does not overwrite
    human text outside the managed block and does not change labels.
    """

    issue_data = gitlab_issue.asdict()
    existing_description = issue_data.get("description", "") or ""
    new_description = replace_heather_managed_block(
        existing_description=existing_description,
        gl_issue_row=gl_issue_row,
        ai_transcription_check=ai_transcription_check,
        ai_comment_digest=ai_comment_digest,
    )
    description_changed = new_description != existing_description

    if description_changed is True:
        gitlab_issue.description = new_description

    if description_changed is True:
        gitlab_issue.save()

    return gitlab_issue

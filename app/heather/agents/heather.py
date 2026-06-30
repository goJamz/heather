# Standard library imports.
from datetime import datetime, timezone
from hashlib import sha256
from json import dumps, loads
from os import environ, getenv

# Local imports.
from constants import (
    ADOC_TICKET_TYPE_LABEL,
    DEFAULT_BOARD_COLUMN_LABELS,
    GL_ISSUES_RID,
    HEATHER_CREATED_LABEL,
    HEATHER_GITLAB_COMMENTS_COLUMNS,
    HEATHER_GITLAB_COMMENTS_FILE_PATH,
    HEATHER_GITLAB_COMMENTS_RID,
    HEATHER_GITLAB_STATE_COLUMNS,
    HEATHER_GITLAB_STATE_FILE_PATH,
    HEATHER_GITLAB_STATE_RID,
    STAGE_LABEL_BY_SOURCE_STAGE,
    STAGE_LABELS,
)
from tools.client import get_gitlab_client
from tools.ai import get_ai_comment_digest, get_ai_transcription_check
from tools.description import (
    build_source_comment_note_body,
    build_issue_description,
    get_external_key_marker,
    is_heather_source_comment_note,
    replace_heather_managed_block,
    should_refresh_managed_block,
)
from tools.vantage import get_vantage_client


def run_heather(
    dry_run: bool = False,
    write_vantage: bool = True,
    use_ai_check: bool = False,
    use_ai_comment_digest: bool = False,
) -> None:
    """Runs Heather's deterministic GitLab synchronization workflow."""

    gitlab_client = get_gitlab_client()
    vantage_client = get_vantage_client()
    gitlab_project = gitlab_client.projects.get(id=environ["GITLAB_PROJECT_ID"])
    gl_issue_rows = vantage_client.read_table(dataset_rid=GL_ISSUES_RID)
    state_rows = []
    comment_rows = []
    processed_external_keys = set()
    created_count = 0
    updated_count = 0
    unchanged_count = 0
    skipped_count = 0
    error_count = 0
    run_timestamp = get_current_timestamp()

    print(f"[*] Heather loaded {len(gl_issue_rows)} gl-issues rows from Vantage")

    for gl_issue_row in gl_issue_rows:
        external_key = str(gl_issue_row.get("external_key", "")).strip()

        if external_key == "":
            error_count = error_count + 1
            print("[!] Skipping gl-issues row with empty external_key")
            continue

        if external_key in processed_external_keys:
            skipped_count = skipped_count + 1
            print(f"[*] Skipping duplicate gl-issues row: {external_key}")
            continue

        processed_external_keys.add(external_key)

        try:
            gitlab_issue = find_gitlab_issue_by_external_key(
                gitlab_project=gitlab_project, external_key=external_key
            )
            issue_already_existed = gitlab_issue is not None
            managed_update_applied = False
            label_update_applied = False

            if gitlab_issue is None:
                if dry_run:
                    created_count = created_count + 1
                    print(f"[DRY RUN] Would create GitLab issue for {external_key}")
                    continue

                ai_transcription_check = get_ai_transcription_check(
                    gl_issue_row=gl_issue_row, use_ai_check=use_ai_check
                )
                ai_comment_digest = get_ai_comment_digest(
                    gl_issue_row=gl_issue_row,
                    use_ai_comment_digest=use_ai_comment_digest,
                )
                gitlab_issue = create_gitlab_issue(
                    gitlab_project=gitlab_project,
                    gl_issue_row=gl_issue_row,
                    ai_transcription_check=ai_transcription_check,
                    ai_comment_digest=ai_comment_digest,
                )
                created_count = created_count + 1
                print(f"[+] Created GitLab issue for {external_key}")
                hydrated_issue = gitlab_project.issues.get(id=gitlab_issue.iid)
            else:
                hydrated_issue = gitlab_project.issues.get(id=gitlab_issue.iid)

                if should_refresh_managed_block(
                    issue_description=hydrated_issue.asdict().get("description", "") or "",
                    gl_issue_row=gl_issue_row,
                ):
                    if dry_run:
                        managed_update_applied = True
                        updated_count = updated_count + 1
                        print(
                            "[DRY RUN] Would update Heather-managed block for "
                            f"{external_key}"
                        )
                    else:
                        ai_transcription_check = get_ai_transcription_check(
                            gl_issue_row=gl_issue_row,
                            use_ai_check=use_ai_check,
                        )
                        ai_comment_digest = get_ai_comment_digest(
                            gl_issue_row=gl_issue_row,
                            use_ai_comment_digest=use_ai_comment_digest,
                        )
                        hydrated_issue = update_gitlab_issue_managed_block(
                            gitlab_issue=hydrated_issue,
                            gl_issue_row=gl_issue_row,
                            ai_transcription_check=ai_transcription_check,
                            ai_comment_digest=ai_comment_digest,
                        )
                        managed_update_applied = True
                        updated_count = updated_count + 1
                        print(f"[~] Updated Heather-managed block for {external_key}")
                else:
                    unchanged_count = unchanged_count + 1
                    print(f"[*] Existing GitLab issue unchanged for {external_key}")

                label_update_needed = reconcile_gitlab_issue_labels(
                    gitlab_project=gitlab_project,
                    gitlab_issue=hydrated_issue,
                    gl_issue_row=gl_issue_row,
                    dry_run=dry_run,
                )

                if label_update_needed is True:
                    label_update_applied = True

                    if managed_update_applied is False:
                        updated_count = updated_count + 1

                        if unchanged_count > 0:
                            unchanged_count = unchanged_count - 1

                    if dry_run:
                        print(f"[DRY RUN] Would update labels for {external_key}")
                    else:
                        print(f"[~] Updated labels for {external_key}")

            if dry_run is False:
                source_comment_note_changed = sync_source_comment_note(
                    gitlab_issue=hydrated_issue,
                    gl_issue_row=gl_issue_row,
                )

                if source_comment_note_changed is True:
                    if (
                        issue_already_existed is True
                        and managed_update_applied is False
                        and label_update_applied is False
                    ):
                        updated_count = updated_count + 1
                        if unchanged_count > 0:
                            unchanged_count = unchanged_count - 1

                    print(f"[~] Synced source comment note for {external_key}")

            gitlab_notes = hydrated_issue.notes.list(get_all=True)
            user_notes = get_user_notes(gitlab_notes=gitlab_notes)

            state_rows.append(
                build_state_row(
                    gl_issue_row=gl_issue_row,
                    gitlab_issue=hydrated_issue,
                    user_notes=user_notes,
                    run_timestamp=run_timestamp,
                )
            )

            comment_rows.extend(
                build_comment_rows(
                    gl_issue_row=gl_issue_row,
                    gitlab_issue=hydrated_issue,
                    user_notes=user_notes,
                    run_timestamp=run_timestamp,
                )
            )
        except Exception as error:
            error_count = error_count + 1
            print(f"[!] Error processing {external_key}: {error}")
            state_rows.append(
                build_error_state_row(
                    gl_issue_row=gl_issue_row,
                    run_timestamp=run_timestamp,
                    sync_error=str(error),
                )
            )

    if dry_run:
        print(
            "[*] Dry run complete. "
            "No GitLab issues or Vantage datasets were changed."
        )
    elif write_vantage:
        vantage_client.upload_rows(
            dataset_rid=HEATHER_GITLAB_STATE_RID,
            file_path=HEATHER_GITLAB_STATE_FILE_PATH,
            columns=HEATHER_GITLAB_STATE_COLUMNS,
            rows=state_rows,
        )
        vantage_client.upload_rows(
            dataset_rid=HEATHER_GITLAB_COMMENTS_RID,
            file_path=HEATHER_GITLAB_COMMENTS_FILE_PATH,
            columns=HEATHER_GITLAB_COMMENTS_COLUMNS,
            rows=comment_rows,
        )
        print("[*] Heather wrote GitLab state and comment snapshots to Vantage")
    else:
        vantage_client.write_local_rows(
            file_path=HEATHER_GITLAB_STATE_FILE_PATH,
            columns=HEATHER_GITLAB_STATE_COLUMNS,
            rows=state_rows,
        )
        vantage_client.write_local_rows(
            file_path=HEATHER_GITLAB_COMMENTS_FILE_PATH,
            columns=HEATHER_GITLAB_COMMENTS_COLUMNS,
            rows=comment_rows,
        )
        print("[*] Heather wrote local state and comment snapshots only")

    print(
        "[*] Heather complete: "
        f"created={created_count}, "
        f"updated={updated_count}, "
        f"unchanged={unchanged_count}, "
        f"skipped={skipped_count}, "
        f"errors={error_count}"
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


def reconcile_gitlab_issue_labels(
    gitlab_project,
    gitlab_issue,
    gl_issue_row: dict,
    dry_run: bool = False,
) -> bool:
    """Reconciles Heather-managed labels on an existing GitLab issue."""

    issue_data = gitlab_issue.asdict()
    existing_labels = issue_data.get("labels", []) or []
    reconciled_labels = build_gitlab_issue_labels(
        gitlab_project=gitlab_project,
        gl_issue_row=gl_issue_row,
        existing_labels=existing_labels,
    )

    if reconciled_labels == existing_labels:
        return False

    if dry_run is False:
        gitlab_issue.labels = reconciled_labels
        gitlab_issue.save()

    return True


def build_gitlab_issue_labels(
    gitlab_project,
    gl_issue_row: dict,
    existing_labels: list,
) -> list:
    """Builds the GitLab labels Heather manages for a source row."""

    required_labels = get_required_gitlab_issue_label_names(gitlab_project=gitlab_project)
    stage_label = get_gitlab_stage_label_name(
        gitlab_project=gitlab_project,
        source_stage=gl_issue_row.get("stage", ""),
    )
    labels = [
        label
        for label in existing_labels
        if str(label or "").strip() not in STAGE_LABELS
    ]

    return dedupe_labels(labels + required_labels + [stage_label])


def get_required_gitlab_issue_label_names(gitlab_project) -> list:
    """Returns required existing GitLab labels Heather applies to all issues."""

    return [
        get_existing_project_label_name(
            gitlab_project=gitlab_project,
            label_name=ADOC_TICKET_TYPE_LABEL,
        )
    ]


def get_gitlab_stage_label_name(gitlab_project, source_stage: str) -> str:
    """Maps a source stage value to an existing GitLab stage label."""

    normalized_source_stage = str(source_stage or "").strip()

    if normalized_source_stage == "":
        return ""

    stage_label = STAGE_LABEL_BY_SOURCE_STAGE.get(normalized_source_stage, "")

    if stage_label == "":
        return ""

    return get_existing_project_label_name(
        gitlab_project=gitlab_project,
        label_name=stage_label,
    )


def dedupe_labels(labels: list) -> list:
    """Keeps label order stable while removing duplicates and empty values."""

    deduped_labels = []

    for label in labels:
        normalized_label = str(label or "").strip()

        if normalized_label == "":
            continue

        if normalized_label in deduped_labels:
            continue

        deduped_labels.append(normalized_label)

    return deduped_labels


def build_gitlab_issue_title(gl_issue_row: dict) -> str:
    """Builds the GitLab issue title Heather should use for this source row."""

    raw_title = normalize_title_text(value=gl_issue_row.get("title", ""))
    source_ticket_id = get_source_ticket_id(gl_issue_row=gl_issue_row)

    if raw_title == "":
        if source_ticket_id != "":
            return f"ADOC Ticket #{source_ticket_id}"

        return ""

    return remove_redundant_customer_segment_from_title(
        title=raw_title,
        gl_issue_row=gl_issue_row,
    )


def remove_redundant_customer_segment_from_title(
    title: str, gl_issue_row: dict
) -> str:
    """Drops the generated customer/person segment from ADOC ticket titles."""

    source_ticket_id = get_source_ticket_id(gl_issue_row=gl_issue_row)
    prefix = f"ADOC Ticket #{source_ticket_id} - "

    if source_ticket_id == "" or title.startswith(prefix) is False:
        return title

    title_parts = [part.strip() for part in title[len(prefix) :].split(" - ")]
    title_parts = [part for part in title_parts if part != ""]

    if len(title_parts) < 2:
        return title

    if is_redundant_title_customer_segment(
        title_segment=title_parts[0], gl_issue_row=gl_issue_row
    ):
        return f"{prefix}{' - '.join(title_parts[1:])}".strip()

    return title


def is_redundant_title_customer_segment(
    title_segment: str, gl_issue_row: dict
) -> bool:
    """Checks whether a title segment duplicates source customer/person data."""

    normalized_title_segment = normalize_comparison_text(value=title_segment)
    source_customer_values = [
        gl_issue_row.get("customer", ""),
        gl_issue_row.get("customer_name", ""),
        gl_issue_row.get("requester", ""),
        gl_issue_row.get("created_by", ""),
        gl_issue_row.get("assignee", ""),
    ]
    source_customer_value = ""

    if normalized_title_segment == "":
        return False

    for source_customer_value in source_customer_values:
        if normalized_title_segment == normalize_comparison_text(
            value=source_customer_value
        ):
            return True

    return "'" in str(title_segment) or "," in str(title_segment)


def get_source_ticket_id(gl_issue_row: dict) -> str:
    """Gets the preferred ticket id for title construction."""

    source_ticket_id = str(gl_issue_row.get("source_ticket_id", "")).strip()

    if source_ticket_id != "":
        return source_ticket_id

    return str(gl_issue_row.get("ticket_id", "")).strip()


def normalize_title_text(value) -> str:
    """Normalizes whitespace in GitLab titles."""

    return " ".join(str(value or "").strip().split())


def normalize_comparison_text(value) -> str:
    """Normalizes text for conservative generated-title comparisons."""

    return "".join(
        character.lower()
        for character in str(value or "")
        if character.isalnum()
    )


def sync_source_comment_note(gitlab_issue, gl_issue_row: dict) -> bool:
    """Creates or updates Heather's authoritative source comment GitLab note."""

    note_body = build_source_comment_note_body(gl_issue_row=gl_issue_row)
    gitlab_notes = gitlab_issue.notes.list(get_all=True)
    existing_source_note = find_source_comment_note(gitlab_notes=gitlab_notes)

    if note_body == "":
        return False

    if existing_source_note is None:
        gitlab_issue.notes.create({"body": note_body})
        return True

    if (existing_source_note.asdict().get("body", "") or "") == note_body:
        return False

    existing_source_note.body = note_body
    existing_source_note.save()

    return True


def find_source_comment_note(gitlab_notes: list):
    """Finds Heather's source comment transcript note when one exists."""

    for gitlab_note in gitlab_notes:
        if is_heather_source_comment_note(
            note_body=gitlab_note.asdict().get("body", "") or ""
        ):
            return gitlab_note

    return None


def get_existing_project_label_name(gitlab_project, label_name: str) -> str:
    """Returns an existing project or inherited group label without creating it."""

    expected_label_name = str(label_name or "").strip()
    project_labels = gitlab_project.labels.list(
        search=expected_label_name,
        include_ancestor_groups=True,
        get_all=True,
    )
    project_label_name = ""

    for project_label in project_labels:
        project_label_name = str(project_label.asdict().get("name", "")).strip()

        if project_label_name == expected_label_name:
            return project_label_name

    raise ValueError(
        f"Required GitLab project or group label does not exist: {expected_label_name}"
    )


def get_user_notes(gitlab_notes: list) -> list:
    """Keeps GitLab-native user comments and drops system notes."""

    user_notes = []
    note_data = {}
    note_body = ""

    for gitlab_note in gitlab_notes:
        note_data = gitlab_note.asdict()
        note_body = note_data.get("body", "") or ""

        if note_data.get("system", False) is True:
            continue

        if is_heather_source_comment_note(note_body=note_body):
            continue

        user_notes.append(gitlab_note)

    return user_notes


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

# Standard library imports.
from os import environ

# Local imports.
from constants import (
    GL_ISSUES_RID,
    HEATHER_GITLAB_COMMENTS_COLUMNS,
    HEATHER_GITLAB_COMMENTS_FILE_PATH,
    HEATHER_GITLAB_COMMENTS_RID,
    HEATHER_GITLAB_STATE_COLUMNS,
    HEATHER_GITLAB_STATE_FILE_PATH,
    HEATHER_GITLAB_STATE_RID,
)
from sync.issues import (
    create_gitlab_issue,
    find_gitlab_issue_by_external_key,
    update_gitlab_issue_managed_block,
)
from sync.labels import reconcile_gitlab_issue_labels
from sync.notes import get_user_notes, sync_source_comment_note
from sync.rows import (
    build_comment_rows,
    build_error_state_row,
    build_state_row,
    get_current_timestamp,
)
from tools.ai import get_ai_comment_digest
from tools.client import get_gitlab_client
from tools.description import should_refresh_managed_block
from tools.vantage import get_vantage_client

def run_heather(
    dry_run: bool = False,
    write_vantage: bool = True,
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

                ai_comment_digest = get_ai_comment_digest(
                    gl_issue_row=gl_issue_row,
                    use_ai_comment_digest=use_ai_comment_digest,
                )
                gitlab_issue = create_gitlab_issue(
                    gitlab_project=gitlab_project,
                    gl_issue_row=gl_issue_row,
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
                        ai_comment_digest = get_ai_comment_digest(
                            gl_issue_row=gl_issue_row,
                            use_ai_comment_digest=use_ai_comment_digest,
                        )
                        hydrated_issue = update_gitlab_issue_managed_block(
                            gitlab_issue=hydrated_issue,
                            gl_issue_row=gl_issue_row,
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

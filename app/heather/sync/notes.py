# Local imports.
from tools.description import (
    build_source_comment_note_body,
    is_heather_source_comment_note,
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

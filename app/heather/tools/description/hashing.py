# Standard library imports.
from hashlib import sha256
from json import dumps

# Local imports.
from tools.description.markers import get_existing_content_hash

NON_SYNC_TRIGGER_FIELDS = [
    "content_hash",
    "external_key",
    "source_system",
    "source_ticket_id",
    "ticket_id",
    "title",
    "labels_json",
    "created_date",
    "updated_date",
    "comment_count",
    "metadata_json",
]
HEATHER_RENDERED_FIELDS_EXCLUDED_FROM_VANTAGE_HASH = [
    "tech_eval_updates_json",
    "implementation_updates_json",
    "aar_scheduled_date",
    "aar_policy_process_improvements",
    "aar_skills_needed",
    "aar_roles_needed",
    "aar_aiml_potential",
    "aar_strategic_alignment",
    "aar_notes",
]

SOURCE_RENDER_FORMAT_VERSION = (
    "heather-managed-description-v12-top-level-section-headings"
)

def get_source_content_hash(gl_issue_row: dict) -> str:
    """Builds Heather's source-content sync hash for one gl-issues row.

    Vantage owns the source-content hash. Heather mixes in its render format so
    issue descriptions refresh when Heather's GitLab rendering changes.
    """

    source_content_hash = normalize_hash_value(
        value=gl_issue_row.get("content_hash", "")
    )
    hash_payload = {
        "__heather_render_format_version": SOURCE_RENDER_FORMAT_VERSION,
    }
    field_name = ""

    if source_content_hash != "":
        hash_payload["vantage_content_hash"] = source_content_hash
        for field_name in HEATHER_RENDERED_FIELDS_EXCLUDED_FROM_VANTAGE_HASH:
            hash_payload[field_name] = normalize_hash_value(
                value=gl_issue_row.get(field_name, "")
            )

        return sha256(
            dumps(hash_payload, sort_keys=True, ensure_ascii=False).encode("UTF-8")
        ).hexdigest()

    for field_name in sorted(gl_issue_row.keys()):
        if field_name in NON_SYNC_TRIGGER_FIELDS:
            continue

        hash_payload[field_name] = normalize_hash_value(
            value=gl_issue_row.get(field_name, "")
        )

    return sha256(
        dumps(
            hash_payload,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        ).encode("UTF-8")
    ).hexdigest()

def get_source_comments_hash(gl_issue_row: dict) -> str:
    """Builds a deterministic hash for the authoritative source comment note."""

    hash_payload = {
        "__heather_source_comments_note_version": SOURCE_RENDER_FORMAT_VERSION,
        "comments_json": normalize_hash_value(
            value=gl_issue_row.get("comments_json", "[]")
        ),
    }

    return sha256(
        dumps(hash_payload, sort_keys=True, ensure_ascii=False).encode("UTF-8")
    ).hexdigest()

def normalize_hash_value(value) -> str:
    """Normalizes dataframe/CSV values before source-content hashing."""

    if value is None:
        return ""

    return str(value).strip()

def should_refresh_managed_block(issue_description: str, gl_issue_row: dict) -> bool:
    """Checks whether Vantage source content changed since the last sync."""

    existing_content_hash = get_existing_content_hash(
        issue_description=issue_description
    )
    current_content_hash = get_source_content_hash(gl_issue_row=gl_issue_row)

    if existing_content_hash == "":
        return True

    return existing_content_hash != current_content_hash

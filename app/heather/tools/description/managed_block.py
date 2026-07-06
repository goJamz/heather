# Local imports.
from constants import HEATHER_MANAGED_END_MARKER, HEATHER_MANAGED_START_MARKER
from tools.description.hashing import get_source_content_hash
from tools.description.markers import get_content_hash_marker, get_external_key_marker
from tools.description.sections import format_source_description

def build_issue_description(
    gl_issue_row: dict,
    ai_comment_digest: str = "",
) -> str:
    """Builds the full description for a Heather-created issue."""

    external_key = gl_issue_row.get("external_key", "").strip()
    marker = get_external_key_marker(external_key=external_key)
    managed_block = build_managed_description_block(
        gl_issue_row=gl_issue_row,
        ai_comment_digest=ai_comment_digest,
    )

    return f"{marker}\n\n{managed_block}\n"

def build_managed_description_block(
    gl_issue_row: dict,
    ai_comment_digest: str = "",
) -> str:
    """Builds only Heather's managed description block."""

    managed_body = build_managed_description_body(
        gl_issue_row=gl_issue_row,
        ai_comment_digest=ai_comment_digest,
    )

    return (
        f"{HEATHER_MANAGED_START_MARKER}\n"
        f"{managed_body}\n"
        f"{HEATHER_MANAGED_END_MARKER}"
    )

def build_managed_description_body(
    gl_issue_row: dict,
    ai_comment_digest: str = "",
) -> str:
    """Builds the source-owned content Heather may safely refresh."""

    source_description = format_source_description(gl_issue_row=gl_issue_row)
    generated_sections = get_generated_description_sections(
        ai_comment_digest=ai_comment_digest,
    )
    content_hash = get_source_content_hash(gl_issue_row=gl_issue_row)
    managed_body_parts = [get_content_hash_marker(content_hash=content_hash)]

    if source_description != "":
        managed_body_parts.append(source_description)

    managed_body_parts.extend(generated_sections)

    return "\n\n---\n\n".join(managed_body_parts).strip()

def get_generated_description_sections(
    ai_comment_digest: str = "",
) -> list[str]:
    """Returns generated helper sections in the desired issue-body order."""

    generated_sections = []

    if str(ai_comment_digest or "").strip() != "":
        generated_sections.append(str(ai_comment_digest).strip())

    return generated_sections

def replace_heather_managed_block(
    existing_description: str,
    gl_issue_row: dict,
    ai_comment_digest: str = "",
) -> str:
    """Refreshes only Heather's managed block while preserving human content."""

    description = str(existing_description or "")
    new_managed_block = build_managed_description_block(
        gl_issue_row=gl_issue_row,
        ai_comment_digest=ai_comment_digest,
    )
    start_index = description.find(HEATHER_MANAGED_START_MARKER)
    end_index = description.find(HEATHER_MANAGED_END_MARKER)
    external_key = str(gl_issue_row.get("external_key", "")).strip()
    external_key_marker = get_external_key_marker(external_key=external_key)

    if start_index >= 0 and end_index > start_index:
        end_index = end_index + len(HEATHER_MANAGED_END_MARKER)
        return (
            description[:start_index]
            + new_managed_block
            + description[end_index:]
        ).strip()

    if external_key_marker in description:
        return f"{description.strip()}\n\n{new_managed_block}".strip()

    return f"{external_key_marker}\n\n{new_managed_block}\n\n{description.strip()}".strip()

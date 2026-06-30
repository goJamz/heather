# Standard library imports.
from hashlib import sha256
from json import JSONDecodeError, dumps, loads
from re import search, sub

# Local imports.
from constants import (
    HEATHER_CONTENT_HASH_MARKER_TEMPLATE,
    HEATHER_EXTERNAL_KEY_MARKER_TEMPLATE,
    HEATHER_MANAGED_END_MARKER,
    HEATHER_MANAGED_START_MARKER,
    HEATHER_SOURCE_COMMENTS_HASH_MARKER_TEMPLATE,
    HEATHER_SOURCE_COMMENTS_NOTE_MARKER,
)


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

SOURCE_RENDER_FORMAT_VERSION = (
    "heather-managed-description-v6-ticket-information-and-stakeholders"
)
SOURCE_DESCRIPTION_HEATHER_OUTPUT_SIGNALS = [
    "<!-- heather:",
    "## Heather Source Metadata",
    "## Heather Transcription QA",
    "## Heather Comment Digest",
    "## MCSC/SPEAR Source Comments",
]
TICKET_INFORMATION_FIELDS = [
    ("Customer", "customer"),
    ("Alt. POC", "alternate_point_of_contact"),
    ("Organization", "customer_org"),
    ("Stage", "stage"),
    ("ADOC Assigned", "assignee"),
]
SOURCE_TEXT_SECTIONS = [
    ("Purpose", "description"),
    ("Technical Requirements", "technical_requirements"),
    ("Policies Involved", "policies_involved"),
    ("Decision", "decision"),
    ("Roadblocks", "roadblocks"),
    ("Success Definition", "success_definition"),
    ("Attempted Solutions", "attempted_solutions"),
    ("Meeting Notes", "meeting_notes"),
    ("Resolution", "resolution"),
    ("Solution Implemented", "solution_implemented"),
    ("Solution Documentation", "solution_documentation"),
    ("Solution Obstacles", "solution_obstacles"),
    ("Lessons Learned", "lessons_learned"),
    ("Solution Applicability", "solution_applicability"),
]


def get_external_key_marker(external_key: str) -> str:
    """Builds the hidden marker Heather uses to identify one source ticket."""

    return HEATHER_EXTERNAL_KEY_MARKER_TEMPLATE.format(external_key=external_key)


def get_content_hash_marker(content_hash: str) -> str:
    """Builds the hidden marker Heather uses to detect source-content changes."""

    return HEATHER_CONTENT_HASH_MARKER_TEMPLATE.format(content_hash=content_hash)


def get_source_comments_hash_marker(content_hash: str) -> str:
    """Builds the hidden marker Heather uses for the source comments note."""

    return HEATHER_SOURCE_COMMENTS_HASH_MARKER_TEMPLATE.format(
        content_hash=content_hash
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


def get_existing_content_hash(issue_description: str) -> str:
    """Finds the first Heather content hash marker in an existing description."""

    description = str(issue_description or "")
    content_hash_match = search(
        r"<!--\s*heather:content_hash=([^\s]+)\s*-->",
        description,
    )

    if content_hash_match is None:
        return ""

    return content_hash_match.group(1).strip()


def parse_json_array(value: str) -> list:
    """Parses a JSON array field from Vantage."""

    parsed_value = []
    cleaned_value = ""

    if value is None:
        return parsed_value

    cleaned_value = str(value).strip()
    if cleaned_value == "":
        return parsed_value

    try:
        loaded_value = loads(cleaned_value)
    except JSONDecodeError:
        return parsed_value

    if isinstance(loaded_value, list):
        parsed_value = loaded_value

    return parsed_value


def build_issue_description(
    gl_issue_row: dict,
    ai_transcription_check: str = "",
    ai_comment_digest: str = "",
) -> str:
    """Builds the full description for a Heather-created issue."""

    external_key = gl_issue_row.get("external_key", "").strip()
    marker = get_external_key_marker(external_key=external_key)
    managed_block = build_managed_description_block(
        gl_issue_row=gl_issue_row,
        ai_transcription_check=ai_transcription_check,
        ai_comment_digest=ai_comment_digest,
    )

    return f"{marker}\n\n{managed_block}\n"


def build_managed_description_block(
    gl_issue_row: dict,
    ai_transcription_check: str = "",
    ai_comment_digest: str = "",
) -> str:
    """Builds only Heather's managed description block."""

    managed_body = build_managed_description_body(
        gl_issue_row=gl_issue_row,
        ai_transcription_check=ai_transcription_check,
        ai_comment_digest=ai_comment_digest,
    )

    return (
        f"{HEATHER_MANAGED_START_MARKER}\n"
        f"{managed_body}\n"
        f"{HEATHER_MANAGED_END_MARKER}"
    )


def build_managed_description_body(
    gl_issue_row: dict,
    ai_transcription_check: str = "",
    ai_comment_digest: str = "",
) -> str:
    """Builds the source-owned content Heather may safely refresh."""

    source_description = format_source_description(gl_issue_row=gl_issue_row)
    generated_sections = get_generated_description_sections(
        ai_transcription_check=ai_transcription_check,
        ai_comment_digest=ai_comment_digest,
    )
    content_hash = get_source_content_hash(gl_issue_row=gl_issue_row)
    managed_body_parts = [get_content_hash_marker(content_hash=content_hash)]

    if source_description != "":
        managed_body_parts.append(
            insert_generated_sections_after_meeting_notes(
                source_description=source_description,
                generated_sections=generated_sections,
            )
        )
    else:
        managed_body_parts.extend(generated_sections)

    return "\n\n---\n\n".join(managed_body_parts).strip()


def get_generated_description_sections(
    ai_transcription_check: str = "",
    ai_comment_digest: str = "",
) -> list[str]:
    """Returns generated helper sections in the desired issue-body order."""

    generated_sections = []

    if str(ai_transcription_check or "").strip() != "":
        generated_sections.append(str(ai_transcription_check).strip())

    if str(ai_comment_digest or "").strip() != "":
        generated_sections.append(str(ai_comment_digest).strip())

    return generated_sections


def format_source_description(gl_issue_row: dict) -> str:
    """Renders source-owned gl-issues fields as GitLab markdown."""

    sections = []
    raw_source_description = get_source_field_text(
        gl_issue_row=gl_issue_row, field_name="description"
    )

    validate_source_description(source_description=raw_source_description)

    sections.append(build_ticket_information_section(gl_issue_row=gl_issue_row))
    sections.append(build_stakeholders_section(gl_issue_row=gl_issue_row))

    for heading, field_name in SOURCE_TEXT_SECTIONS:
        sections.append(
            build_text_section(
                gl_issue_row=gl_issue_row,
                heading=heading,
                field_name=field_name,
            )
        )

    return "\n\n".join(section for section in sections if section != "").strip()


def build_ticket_information_section(gl_issue_row: dict) -> str:
    """Builds the top ticket summary table from selected source fields."""

    rows = []
    field_value = ""

    for label, field_name in TICKET_INFORMATION_FIELDS:
        if field_name == "alternate_point_of_contact":
            field_value = get_alternate_point_of_contact(gl_issue_row=gl_issue_row)
        else:
            field_value = get_source_field_text(
                gl_issue_row=gl_issue_row,
                field_name=field_name,
            )

        if field_value != "":
            rows.append(
                "| "
                f"{format_markdown_table_cell(label)}"
                " | "
                f"{format_markdown_table_cell(field_value)}"
                " |"
            )

    if len(rows) == 0:
        return ""

    return "\n".join(
        [
            "## Ticket Information",
            "| Field | Value |",
            "| --- | --- |",
            *rows,
        ]
    )


def build_stakeholders_section(gl_issue_row: dict) -> str:
    """Builds a stakeholders section from contacts_json."""

    contacts = parse_json_array(value=gl_issue_row.get("contacts_json", "[]"))
    rows = []
    contact_name = ""
    contact_details = ""

    for contact in contacts:
        if not isinstance(contact, dict):
            continue

        if str(contact.get("type", "")).strip().lower() != "stakeholder":
            continue

        contact_name = str(contact.get("name", "")).strip()
        contact_details = format_contact_details(contact=contact)

        if contact_name == "" and contact_details == "":
            continue

        rows.append(
            "| "
            f"{format_markdown_table_cell(contact_name)}"
            " | "
            f"{format_markdown_table_cell(contact_details)}"
            " |"
        )

    if len(rows) == 0:
        return ""

    return "\n".join(
        [
            "## Stakeholders",
            "| Name | Details |",
            "| --- | --- |",
            *rows,
        ]
    )


def get_alternate_point_of_contact(gl_issue_row: dict) -> str:
    """Returns the first alternate point of contact from contacts_json."""

    contacts = parse_json_array(value=gl_issue_row.get("contacts_json", "[]"))
    contact_type = ""

    for contact in contacts:
        if not isinstance(contact, dict):
            continue

        contact_type = str(contact.get("type", "")).strip().lower()

        if contact_type == "alternate point of contact":
            return format_contact_summary(contact=contact)

    return ""


def format_contact_summary(contact: dict) -> str:
    """Formats one contact as a compact, readable table value."""

    contact_name = str(contact.get("name", "")).strip()
    contact_details = format_contact_details(contact=contact)

    if contact_name == "":
        return contact_details

    if contact_details == "":
        return contact_name

    return f"{contact_name} - {contact_details}"


def format_contact_details(contact: dict) -> str:
    """Formats non-name contact fields while dropping empty/None values."""

    detail_values = []
    field_name = ""
    field_value = ""

    for field_name in ["title", "organization", "email", "phone"]:
        field_value = str(contact.get(field_name, "")).strip()

        if field_value == "" or field_value.lower() == "none":
            continue

        detail_values.append(field_value)

    return ", ".join(detail_values)


def format_markdown_table_cell(value: str) -> str:
    """Normalizes text for safe rendering inside a GitLab markdown table cell."""

    return str(value or "").replace("|", "\\|").replace("\n", "<br>")


def build_text_section(gl_issue_row: dict, heading: str, field_name: str) -> str:
    """Builds a markdown section from a source text field."""

    field_value = get_source_field_text(
        gl_issue_row=gl_issue_row, field_name=field_name
    )

    if field_value == "":
        return ""

    return f"## {heading}\n{field_value}"


def get_source_field_text(gl_issue_row: dict, field_name: str) -> str:
    """Returns a normalized source field string."""

    field_value = gl_issue_row.get(field_name, "")

    if field_value is None:
        return ""

    return sub(r"\n{3,}", "\n\n", str(field_value).strip()).strip()


def validate_source_description(source_description: str) -> None:
    """Rejects Vantage descriptions that already contain Heather output."""

    description = str(source_description or "")
    signal = ""

    for signal in SOURCE_DESCRIPTION_HEATHER_OUTPUT_SIGNALS:
        if signal in description:
            raise ValueError(
                "gl-issues.description contains Heather-generated output "
                f"({signal}). Fix the Vantage transform so the description is "
                "source-owned ticket content only."
            )


def insert_generated_sections_after_meeting_notes(
    source_description: str, generated_sections: list[str]
) -> str:
    """Places generated helper sections immediately after Meeting Notes."""

    description = str(source_description or "").strip()
    generated_body = "\n\n---\n\n".join(
        section.strip() for section in generated_sections if section.strip() != ""
    )

    if description == "" or generated_body == "":
        return description

    heading_match = search(
        r"(?im)^\s*#{1,6}\s+Meeting Notes\s*$",
        description,
    )

    if heading_match is not None:
        return insert_after_markdown_section(
            source_description=description,
            section_body_start=heading_match.end(),
            insertion=generated_body,
        )

    field_match = search(
        r"(?im)^\s*[-*]?\s*\*{0,2}Meeting Notes\*{0,2}\s*:\s*.*$",
        description,
    )

    if field_match is not None:
        return (
            description[: field_match.end()]
            + "\n\n---\n\n"
            + generated_body
            + description[field_match.end() :]
        ).strip()

    return f"{description}\n\n---\n\n{generated_body}".strip()


def insert_after_markdown_section(
    source_description: str, section_body_start: int, insertion: str
) -> str:
    """Inserts text after a markdown section and before the next heading."""

    description = str(source_description or "")
    next_heading_match = search(
        r"(?im)^\s*#{1,6}\s+.+$",
        description[section_body_start:],
    )
    insertion_text = f"\n\n---\n\n{insertion}\n\n"

    if next_heading_match is None:
        return f"{description.rstrip()}{insertion_text}".strip()

    next_heading_start = section_body_start + next_heading_match.start()

    return (
        description[:next_heading_start].rstrip()
        + insertion_text
        + description[next_heading_start:].lstrip()
    ).strip()


def replace_heather_managed_block(
    existing_description: str,
    gl_issue_row: dict,
    ai_transcription_check: str = "",
    ai_comment_digest: str = "",
) -> str:
    """Refreshes only Heather's managed block while preserving human content."""

    description = str(existing_description or "")
    new_managed_block = build_managed_description_block(
        gl_issue_row=gl_issue_row,
        ai_transcription_check=ai_transcription_check,
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


def should_refresh_managed_block(issue_description: str, gl_issue_row: dict) -> bool:
    """Checks whether Vantage source content changed since the last sync."""

    existing_content_hash = get_existing_content_hash(
        issue_description=issue_description
    )
    current_content_hash = get_source_content_hash(gl_issue_row=gl_issue_row)

    if existing_content_hash == "":
        return True

    return existing_content_hash != current_content_hash


def build_source_comment_note_body(gl_issue_row: dict) -> str:
    """Formats authoritative MCSC/SPEAR source comments as one GitLab note."""

    comments = parse_json_array(value=gl_issue_row.get("comments_json", "[]"))
    formatted_comments = []
    comment_date = ""
    comment_author = ""
    comment_type = ""
    comment_body = ""

    if len(comments) == 0:
        return ""

    for comment in comments:
        if not isinstance(comment, dict):
            continue

        comment_date = str(comment.get("date", "")).strip()
        comment_author = str(comment.get("author", "")).strip()
        comment_type = str(comment.get("comment_type", "")).strip()
        comment_body = str(comment.get("comment", "")).strip()

        if comment_body == "":
            continue

        formatted_comments.append(
            "\n".join(
                [
                    (
                        f"### {comment_type}"
                        if comment_type != ""
                        else "### Source Comment"
                    ),
                    f"- **Date:** {comment_date}" if comment_date != "" else "",
                    f"- **Author:** {comment_author}" if comment_author != "" else "",
                    "",
                    comment_body,
                ]
            ).strip()
        )

    if len(formatted_comments) == 0:
        return ""

    return "\n".join(
        [
            HEATHER_SOURCE_COMMENTS_NOTE_MARKER,
            get_source_comments_hash_marker(
                content_hash=get_source_comments_hash(gl_issue_row=gl_issue_row)
            ),
            "",
            "## MCSC/SPEAR Authoritative Source Comments",
            "",
            "> Authoritative source comment transcript from MCSC/SPEAR. "
            "Heather maintains this GitLab note from Vantage `comments_json`.",
            "",
            "\n\n".join(formatted_comments),
        ]
    )


def is_heather_source_comment_note(note_body: str) -> bool:
    """Returns whether a GitLab note is Heather's source comment transcript."""

    return HEATHER_SOURCE_COMMENTS_NOTE_MARKER in str(note_body or "")

# Standard library imports.
from json import JSONDecodeError, loads
from re import sub

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

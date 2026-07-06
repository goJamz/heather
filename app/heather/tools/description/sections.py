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
NOT_YET_DEFINED = "Not yet defined"
WEC_FIELDS = [
    ("Meeting Notes", "meeting_notes"),
    ("Roadblocks", "roadblocks"),
    ("Attempted Solutions", "attempted_solutions"),
]
TECH_EVAL_FIELDS = [
    ("Technical Requirements", "technical_requirements"),
    ("Policies Involved", "policies_involved"),
    ("Decision", "decision"),
]
TECH_IMPLEMENTATION_FIELDS = [
    ("Solution Implemented", "solution_implemented"),
    ("Solution Obstacles", "solution_obstacles"),
    ("Lessons Learned", "lessons_learned"),
    ("Solution Applicability", "solution_applicability"),
]
AAR_FIELDS = [
    ("Scheduled Date", "aar_scheduled_date"),
    ("Policy and Process Improvements", "aar_policy_process_improvements"),
    ("Skills Needed", "aar_skills_needed"),
    ("Roles Needed", "aar_roles_needed"),
    ("AI/ML Potential", "aar_aiml_potential"),
    ("Strategic Alignment", "aar_strategic_alignment"),
    ("Notes", "aar_notes"),
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
    sections.append(build_workflow_section("WEC", WEC_FIELDS, gl_issue_row))
    sections.append(
        build_workflow_section(
            "Tech Eval",
            TECH_EVAL_FIELDS,
            gl_issue_row,
            extra_sections=[
                build_status_updates_section(
                    heading="Technical Evaluation Status Updates",
                    field_name="tech_eval_updates_json",
                    gl_issue_row=gl_issue_row,
                )
            ],
        )
    )
    sections.append(
        build_workflow_section(
            "Tech Implementation",
            TECH_IMPLEMENTATION_FIELDS,
            gl_issue_row,
            extra_sections=[
                build_status_updates_section(
                    heading="Implementation Status Updates",
                    field_name="implementation_updates_json",
                    gl_issue_row=gl_issue_row,
                )
            ],
        )
    )
    sections.append(build_aar_section(gl_issue_row=gl_issue_row))

    return "\n\n".join(section for section in sections if section != "").strip()

def build_ticket_information_section(gl_issue_row: dict) -> str:
    """Builds the top ticket summary section from selected source fields."""

    rows = []
    field_value = ""
    section_parts = []

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

    section_parts.append(
        "\n".join(
            [
                "## Ticket Information",
                "| Field | Value |",
                "| --- | --- |",
                *rows,
            ]
        )
    )
    section_parts.append(build_stakeholders_section(gl_issue_row=gl_issue_row))
    section_parts.append(
        build_text_section(
            gl_issue_row=gl_issue_row,
            heading="Purpose",
            field_name="description",
            heading_level=3,
            fallback=NOT_YET_DEFINED,
        )
    )
    section_parts.append(
        build_text_section(
            gl_issue_row=gl_issue_row,
            heading="Success Definition",
            field_name="success_definition",
            heading_level=3,
            fallback=NOT_YET_DEFINED,
        )
    )
    section_parts.append(
        build_text_section(
            gl_issue_row=gl_issue_row,
            heading="Resolution",
            field_name="resolution",
            heading_level=3,
            fallback=NOT_YET_DEFINED,
        )
    )

    return "\n\n".join(part for part in section_parts if part != "").strip()

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
        return f"### Stakeholders\n{NOT_YET_DEFINED}"

    return "\n".join(
        [
            "### Stakeholders",
            "| Name | Details |",
            "| --- | --- |",
            *rows,
        ]
    )

def build_workflow_section(
    heading: str,
    fields: list[tuple[str, str]],
    gl_issue_row: dict,
    extra_sections: list[str] | None = None,
) -> str:
    """Builds one top-level workflow section from source fields."""

    section_parts = [f"## {heading}"]
    field_heading = ""
    field_name = ""

    for field_heading, field_name in fields:
        section_parts.append(
            build_text_section(
                gl_issue_row=gl_issue_row,
                heading=field_heading,
                field_name=field_name,
                heading_level=3,
                fallback=NOT_YET_DEFINED,
            )
        )

    if extra_sections is not None:
        section_parts.extend(extra_sections)

    return "\n\n".join(part for part in section_parts if part != "").strip()

def build_status_updates_section(
    heading: str,
    field_name: str,
    gl_issue_row: dict,
) -> str:
    """Builds a markdown table from a status update JSON array field."""

    updates = parse_json_array(value=gl_issue_row.get(field_name, "[]"))
    rows = []
    update_date = ""
    update_status = ""
    update_notes = ""

    for update in updates:
        if not isinstance(update, dict):
            continue

        update_date = str(update.get("date", "")).strip()
        update_status = str(update.get("status", "")).strip()
        update_notes = str(update.get("notes", "")).strip()

        if update_date == "" and update_status == "" and update_notes == "":
            continue

        rows.append(
            "| "
            f"{format_markdown_table_cell(update_date)}"
            " | "
            f"{format_markdown_table_cell(update_status)}"
            " | "
            f"{format_markdown_table_cell(update_notes)}"
            " |"
        )

    if len(rows) == 0:
        return f"### {heading}\n{NOT_YET_DEFINED}"

    return "\n".join(
        [
            f"### {heading}",
            "| Date | Status | Notes |",
            "| --- | --- | --- |",
            *rows,
        ]
    )

def build_aar_section(gl_issue_row: dict) -> str:
    """Builds the AAR source-field section from structured gl-issues columns."""

    rows = []
    label = ""
    field_name = ""
    field_value = ""

    for label, field_name in AAR_FIELDS:
        field_value = get_source_field_text(
            gl_issue_row=gl_issue_row,
            field_name=field_name,
        )
        if field_value == "":
            field_value = NOT_YET_DEFINED

        rows.append(
            "| "
            f"{format_markdown_table_cell(label)}"
            " | "
            f"{format_markdown_table_cell(field_value)}"
            " |"
        )

    return "\n".join(
        [
            "## AAR",
            "| Field | Value |",
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

def build_text_section(
    gl_issue_row: dict,
    heading: str,
    field_name: str,
    heading_level: int = 2,
    fallback: str = "",
) -> str:
    """Builds a markdown section from a source text field."""

    field_value = get_source_field_text(
        gl_issue_row=gl_issue_row, field_name=field_name
    )

    if field_value == "":
        field_value = fallback

    if field_value == "":
        return ""

    heading_prefix = "#" * heading_level

    return f"{heading_prefix} {heading}\n{field_value}"

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

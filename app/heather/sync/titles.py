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

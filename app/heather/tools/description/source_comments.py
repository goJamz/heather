# Local imports.
from constants import HEATHER_SOURCE_COMMENTS_NOTE_MARKER
from tools.description.hashing import get_source_comments_hash
from tools.description.markers import get_source_comments_hash_marker
from tools.description.sections import parse_json_array

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

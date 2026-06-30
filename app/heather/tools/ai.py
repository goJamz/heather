# Standard library imports.
from json import JSONDecodeError, dumps, loads
from os import getenv

# Third party imports.
from langchain.messages import HumanMessage

# Local imports.
from models.azure import get_azure_openai_model


AI_TRANSCRIPTION_CHECK_FIELDS = [
    "external_key",
    "source_ticket_id",
    "title",
    "status",
    "priority",
    "customer_org",
    "location",
    "category",
    "mission_priority",
    "stage",
    "tags",
    "technical_requirements",
    "policies_involved",
    "decision",
    "roadblocks",
    "success_definition",
    "attempted_solutions",
    "meeting_notes",
    "resolution",
    "solution_implemented",
    "solution_documentation",
    "solution_obstacles",
    "lessons_learned",
    "solution_applicability",
    "comment_count",
]

AI_COMMENT_DIGEST_FIELDS = [
    "external_key",
    "source_ticket_id",
    "title",
    "status",
    "category",
    "customer_org",
    "comments_json",
    "comment_count",
]


def get_ai_transcription_check(gl_issue_row: dict, use_ai_check: bool = False) -> str:
    """Builds a small optional AI QA note without changing source content."""
    if should_run_ai_check(use_ai_check=use_ai_check) is False:
        return ""

    try:
        model = get_azure_openai_model()
        response = model.invoke(
            [HumanMessage(content=build_ai_check_prompt(gl_issue_row=gl_issue_row))]
        )
        return format_ai_check_response(content=getattr(response, "content", ""))
    except Exception as error:
        print(f"[!] Heather AI transcription QA skipped: {error}")
        return ""


def get_ai_comment_digest(
    gl_issue_row: dict, use_ai_comment_digest: bool = False
) -> str:
    """Builds an optional AI digest of only MCSC/SPEAR source comments."""
    if should_run_ai_comment_digest(
        use_ai_comment_digest=use_ai_comment_digest
    ) is False:
        return ""

    if has_source_comments(gl_issue_row=gl_issue_row) is False:
        return ""

    try:
        model = get_azure_openai_model()
        response = model.invoke(
            [
                HumanMessage(
                    content=build_ai_comment_digest_prompt(gl_issue_row=gl_issue_row)
                )
            ]
        )
        return format_ai_comment_digest_response(
            content=getattr(response, "content", "")
        )
    except Exception as error:
        print(f"[!] Heather AI source comment digest skipped: {error}")
        return ""


def should_run_ai_check(use_ai_check: bool = False) -> bool:
    """Returns whether Heather should call Azure OpenAI for transcription QA."""
    configured_value = getenv("HEATHER_ENABLE_AI_CHECK", "").lower()

    if use_ai_check is True:
        return True

    return configured_value in ["1", "true", "yes"]


def should_run_ai_comment_digest(use_ai_comment_digest: bool = False) -> bool:
    """Returns whether Heather should call Azure OpenAI for comment digests."""
    configured_value = getenv("HEATHER_ENABLE_AI_COMMENT_DIGEST", "").lower()

    if use_ai_comment_digest is True:
        return True

    return configured_value in ["1", "true", "yes"]


def build_ai_check_prompt(gl_issue_row: dict) -> str:
    """Builds a narrow prompt for non-authoritative transcription QA."""
    reduced_row = {}

    for field_name in AI_TRANSCRIPTION_CHECK_FIELDS:
        reduced_row[field_name] = gl_issue_row.get(field_name, "")

    return "\n".join(
        [
            "You are Heather's AI-assisted transcription QA check.",
            "Heather is not a ticket summarizer in this mode.",
            "Do not summarize the ticket.",
            "Do not rewrite source content. Do not add facts. Do not make decisions.",
            "Only inspect the provided fields for obvious missing or unclear "
            "transcription fields.",
            "Return at most three short markdown bullets.",
            "If nothing obvious is missing, return exactly: "
            "- No obvious transcription gaps detected.",
            "",
            "Source fields:",
            dumps(reduced_row, indent=2, ensure_ascii=False),
        ]
    )


def build_ai_comment_digest_prompt(gl_issue_row: dict) -> str:
    """Builds a narrow prompt for summarizing only source comments."""
    reduced_row = {}

    for field_name in AI_COMMENT_DIGEST_FIELDS:
        reduced_row[field_name] = gl_issue_row.get(field_name, "")

    return "\n".join(
        [
            "You are Heather's AI-assisted MCSC/SPEAR source comment digest.",
            "Summarize only the comments_json content provided below.",
            "Do not summarize the whole ticket.",
            "Do not use outside knowledge.",
            "Do not create lessons learned, EXSUM language, recommendations, "
            "decisions, labels, assignees, or workflow status.",
            "Do not add facts that are not explicitly present in the comments.",
            "Preserve chronology when dates are available.",
            "Write in simple markdown for a GitLab issue.",
            "Do not wrap the response in a fenced code block.",
            "Return this exact structure:",
            "## Heather Comment Digest",
            "",
            "> Non-authoritative digest of MCSC/SPEAR source comments. "
            "Comment Timeline, Main Thread, and Follow-up Signals are generated "
            "by Heather. The raw comments remain authoritative.",
            "",
            "### Comment Timeline",
            "- 3 to 7 short bullets using only the comments.",
            "",
            "### Main Thread",
            "1 to 3 short bullets describing the main operational thread from the "
            "comments only.",
            "",
            "### Follow-up Signals",
            "- List only explicit follow-up items from the comments, or write: "
            "None called out in source comments.",
            "",
            "Source comment fields:",
            dumps(reduced_row, indent=2, ensure_ascii=False),
        ]
    )


def format_ai_check_response(content: str) -> str:
    """Formats the AI response for the Heather-managed issue description block."""
    cleaned_content = str(content).strip()

    if cleaned_content == "":
        return ""

    return "\n".join(
        [
            "## Heather Transcription QA",
            "",
            "> Non-authoritative check. Source fields remain authoritative.",
            "",
            cleaned_content,
        ]
    )


def format_ai_comment_digest_response(content: str) -> str:
    """Formats the AI comment digest for the Heather-managed description block."""
    cleaned_content = strip_markdown_code_fence(content=str(content).strip())

    if cleaned_content == "":
        return ""

    if cleaned_content.startswith("## Heather Comment Digest"):
        return cleaned_content

    return "\n".join(
        [
            "## Heather Comment Digest",
            "",
            "> Non-authoritative digest of MCSC/SPEAR source comments. "
            "Comment Timeline, Main Thread, and Follow-up Signals are generated "
            "by Heather. The raw comments remain authoritative.",
            "",
            cleaned_content,
        ]
    )


def strip_markdown_code_fence(content: str) -> str:
    """Removes a single surrounding markdown fence from model output."""

    cleaned_content = str(content or "").strip()
    lines = cleaned_content.splitlines()
    opening_fence = ""

    if len(lines) < 2:
        return cleaned_content

    opening_fence = lines[0].strip().lower()

    if opening_fence not in ["```", "```markdown", "```md"]:
        return cleaned_content

    if lines[-1].strip() != "```":
        return cleaned_content

    return "\n".join(lines[1:-1]).strip()


def has_source_comments(gl_issue_row: dict) -> bool:
    """Returns whether the gl-issues row has at least one source comment."""
    comments = []
    comments_json = gl_issue_row.get("comments_json", "[]")

    if comments_json is None:
        return False

    try:
        comments = loads(str(comments_json).strip())
    except JSONDecodeError:
        return False

    return isinstance(comments, list) and len(comments) > 0

# Standard library imports.
from re import search

# Local imports.
from constants import (
    HEATHER_CONTENT_HASH_MARKER_TEMPLATE,
    HEATHER_EXTERNAL_KEY_MARKER_TEMPLATE,
    HEATHER_SOURCE_COMMENTS_HASH_MARKER_TEMPLATE,
    HEATHER_SOURCE_COMMENTS_NOTE_MARKER,
)

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

def is_heather_source_comment_note(note_body: str) -> bool:
    """Returns whether a GitLab note is Heather's source comment transcript."""

    return HEATHER_SOURCE_COMMENTS_NOTE_MARKER in str(note_body or "")

# Dataset RIDs.
GL_ISSUES_RID = "ri.foundry.main.dataset.dd9699c3-69f7-4fb4-be28-853da6071536"
GL_ISSUES_COMPLETION_CHECKER_RID = (
    "ri.foundry.main.dataset.d12a2687-2461-49df-adef-1b9fdd6abab6"
)
HEATHER_GITLAB_STATE_RID = "ri.foundry.main.dataset.a53196d5-3001-4863-a907-67874dec6b29"
HEATHER_GITLAB_COMMENTS_RID = "ri.foundry.main.dataset.da001bdc-0d6c-4922-82c4-24b5d111ebf6"

# Local snapshot file paths used when --skip-vantage-write is enabled.
HEATHER_GITLAB_STATE_FILE_PATH = "heather-gitlab-state.csv"
HEATHER_GITLAB_COMMENTS_FILE_PATH = "heather-gitlab-comments.csv"

# GitLab issue markers.
HEATHER_EXTERNAL_KEY_MARKER_TEMPLATE = "<!-- heather:external_key={external_key} -->"
HEATHER_CONTENT_HASH_MARKER_TEMPLATE = "<!-- heather:content_hash={content_hash} -->"
HEATHER_MANAGED_START_MARKER = "<!-- heather:managed:start -->"
HEATHER_MANAGED_END_MARKER = "<!-- heather:managed:end -->"
HEATHER_SOURCE_COMMENTS_NOTE_MARKER = "<!-- heather:source_comments -->"
HEATHER_SOURCE_COMMENTS_HASH_MARKER_TEMPLATE = (
    "<!-- heather:source_comments_hash={content_hash} -->"
)
HEATHER_CREATED_LABEL = "Heather"
ADOC_TICKET_TYPE_LABEL = "Type::ADOC Ticket"

# Source stage labels Heather manages on GitLab issues.
STAGE_LABEL_BY_SOURCE_STAGE = {
    "Closed": "Stage::Closed",
    "Warfighter Engagement Cell": "Stage::WEC",
    "Finish Cell - Technical Evaluation": "Stage::TechEval",
    "Finish Cell - Implementation": "Stage::Implementation",
    "After Action Review (AAR)": "Stage::AAR",
    "Partner Escalated": "Stage::Escalated",
}
STAGE_LABELS = list(STAGE_LABEL_BY_SOURCE_STAGE.values())

# Known board column labels.
DEFAULT_BOARD_COLUMN_LABELS = ["To Do", "In Progress", "Review", "Blocked", "Done"]

# Heather output schemas.
HEATHER_GITLAB_STATE_COLUMNS = [
    "external_key",
    "source_system",
    "source_ticket_id",
    "gitlab_project_id",
    "gitlab_issue_id",
    "gitlab_iid",
    "gitlab_web_url",
    "gitlab_title",
    "gitlab_state",
    "gitlab_board_column",
    "gitlab_labels_json",
    "gitlab_assignees_json",
    "gitlab_created_time",
    "gitlab_updated_time",
    "gitlab_closed_time",
    "gitlab_comment_count",
    "heather_managed",
    "external_key_found",
    "last_seen_time",
    "last_synced_time",
    "sync_status",
    "sync_error",
]

HEATHER_GITLAB_COMMENTS_COLUMNS = [
    "note_key",
    "external_key",
    "source_ticket_id",
    "gitlab_project_id",
    "gitlab_iid",
    "gitlab_issue_id",
    "gitlab_note_id",
    "gitlab_note_url",
    "author_username",
    "author_name",
    "body",
    "is_system",
    "is_edited",
    "created_time",
    "updated_time",
    "comment_hash",
    "last_seen_time",
    "last_synced_time",
    "sync_status",
    "sync_error",
]

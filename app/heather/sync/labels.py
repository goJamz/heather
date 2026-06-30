# Local imports.
from constants import (
    ADOC_TICKET_TYPE_LABEL,
    STAGE_LABEL_BY_SOURCE_STAGE,
    STAGE_LABELS,
)

def reconcile_gitlab_issue_labels(
    gitlab_project,
    gitlab_issue,
    gl_issue_row: dict,
    dry_run: bool = False,
) -> bool:
    """Reconciles Heather-managed labels on an existing GitLab issue."""

    issue_data = gitlab_issue.asdict()
    existing_labels = issue_data.get("labels", []) or []
    reconciled_labels = build_gitlab_issue_labels(
        gitlab_project=gitlab_project,
        gl_issue_row=gl_issue_row,
        existing_labels=existing_labels,
    )

    if reconciled_labels == existing_labels:
        return False

    if dry_run is False:
        gitlab_issue.labels = reconciled_labels
        gitlab_issue.save()

    return True

def build_gitlab_issue_labels(
    gitlab_project,
    gl_issue_row: dict,
    existing_labels: list,
) -> list:
    """Builds the GitLab labels Heather manages for a source row."""

    required_labels = get_required_gitlab_issue_label_names(gitlab_project=gitlab_project)
    stage_label = get_gitlab_stage_label_name(
        gitlab_project=gitlab_project,
        source_stage=gl_issue_row.get("stage", ""),
    )
    labels = [
        label
        for label in existing_labels
        if str(label or "").strip() not in STAGE_LABELS
    ]

    return dedupe_labels(labels + required_labels + [stage_label])

def get_required_gitlab_issue_label_names(gitlab_project) -> list:
    """Returns required existing GitLab labels Heather applies to all issues."""

    return [
        get_existing_project_label_name(
            gitlab_project=gitlab_project,
            label_name=ADOC_TICKET_TYPE_LABEL,
        )
    ]

def get_gitlab_stage_label_name(gitlab_project, source_stage: str) -> str:
    """Maps a source stage value to an existing GitLab stage label."""

    normalized_source_stage = str(source_stage or "").strip()

    if normalized_source_stage == "":
        return ""

    stage_label = STAGE_LABEL_BY_SOURCE_STAGE.get(normalized_source_stage, "")

    if stage_label == "":
        return ""

    return get_existing_project_label_name(
        gitlab_project=gitlab_project,
        label_name=stage_label,
    )

def get_existing_project_label_name(gitlab_project, label_name: str) -> str:
    """Returns an existing project or inherited group label without creating it."""

    expected_label_name = str(label_name or "").strip()
    project_labels = gitlab_project.labels.list(
        search=expected_label_name,
        include_ancestor_groups=True,
        get_all=True,
    )
    project_label_name = ""

    for project_label in project_labels:
        project_label_name = str(project_label.asdict().get("name", "")).strip()

        if project_label_name == expected_label_name:
            return project_label_name

    raise ValueError(
        f"Required GitLab project or group label does not exist: {expected_label_name}"
    )

def dedupe_labels(labels: list) -> list:
    """Keeps label order stable while removing duplicates and empty values."""

    deduped_labels = []

    for label in labels:
        normalized_label = str(label or "").strip()

        if normalized_label == "":
            continue

        if normalized_label in deduped_labels:
            continue

        deduped_labels.append(normalized_label)

    return deduped_labels

# HEATHER

Heather is a lightweight GitLab synchronization app for ADOC. It reads Vantage
`gl-issues`, creates or reconciles GitLab issues, and writes GitLab state plus
user comments back to Heather-owned Vantage snapshot datasets.

Heather is not Gandalf. It does not create lessons learned, recommendations,
EXSUMs, white papers, assignments, workflow movement, or closure decisions.

## Maintainer Architecture

For a file-by-file module map and orchestration notes, see
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Data Flow

```text
Vantage gl-issues
    -> Heather
    -> ADOC GitLab issues
    -> heather-gitlab-state
    -> heather-gitlab-comments
```

| Dataset | Direction | RID |
|---|---|---|
| `gl-issues` | Vantage -> Heather | `ri.foundry.main.dataset.dd9699c3-69f7-4fb4-be28-853da6071536` |
| `heather-gitlab-state` | Heather -> Vantage | `ri.foundry.main.dataset.a53196d5-3001-4863-a907-67874dec6b29` |
| `heather-gitlab-comments` | Heather -> Vantage | `ri.foundry.main.dataset.da001bdc-0d6c-4922-82c4-24b5d111ebf6` |

The two `heather-*` datasets are full current-state snapshots. Production
Vantage writes are Parquet snapshots on `master`. Local inspection mode writes
CSV files under `.data/`.

## Sync Rules

Heather identifies source tickets with:

```text
external_key = mcsc-spear-<source_ticket_id>
```

Each Heather-created issue contains:

```markdown
<!-- heather:external_key=mcsc-spear-1256795 -->
<!-- heather:managed:start -->
<!-- heather:content_hash=<source-content hash> -->
Heather-managed source content.
<!-- heather:managed:end -->
```

Rules:

- Create only when no GitLab issue exists for `external_key`.
- Reconcile existing Heather-tracked issues every run.
- Refresh only Heather-managed description content when source content changes.
- Apply the existing `Heather`, `Type::ADOC Ticket`, and mapped `Stage::...` labels to newly created issues.
- Do not assign users, move board columns, close, or reopen issues.
- Reconcile the required `Type::ADOC Ticket` label and Heather-managed `Stage::...` labels on existing issues.
- Preserve human description text outside Heather's managed block.
- Preserve human GitLab comments.

## GitLab Output Shape

Issue titles are normalized from generated Vantage titles. For example:

```text
ADOC Ticket #1232696 - ANDRE' Michell - CASCOM LDT Requires Elevated Infrastructure access in Vantage
```

becomes:

```text
ADOC Ticket #1232696 - CASCOM LDT Requires Elevated Infrastructure access in Vantage
```

Description behavior:

- Heather renders structured `gl-issues` fields into GitLab markdown.
- `gl-issues.description` is clean purpose text and cannot contain Heather output.
- Visible `Ticket ID` is not rendered because the ticket number is in the title.
- Heather Comment Digest is placed after the AAR section when present.
- Authoritative MCSC/SPEAR source comments are stored in one Heather-managed GitLab note, not in the description.
- Heather's source-comment transcript note is excluded from `heather-gitlab-comments`.

## AI Comment Digest

Heather builds a Heather Comment Digest from `comments_json` when source
comments are present. The digest does not make decisions, assign users, change
workflow status, or add facts outside the provided source fields.

## Environment

Required GitLab variables:

```bash
export GITLAB_API_TOKEN="<KEY>"
export GITLAB_API_ENDPOINT="https://code.cdso.army.mil"
export GITLAB_PROJECT_ID="<ADOC GitLab project ID>"
export GITLAB_EPIC_ID="<Heather GitLab epic ID>"
```

Required Vantage variables:

```bash
export FOUNDRY_HOSTNAME="vantage.army.mil"
export FOUNDRY_TOKEN="<KEY>"
```

Common optional variables:

```bash
export FOUNDRY_BRANCH_ID="master"
export FOUNDRY_TRANSACTION_TYPE="SNAPSHOT"
export FOUNDRY_VERIFY="false"
export HEATHER_BOARD_COLUMN_LABELS_JSON='["To Do", "In Progress", "Review", "Blocked", "Done"]'
```

Azure/OpenAI variables:

```bash
export AZURE_TENANT_ID="<TENANT ID>"
export AZURE_CLIENT_ID="<CLIENT ID>"
export AZURE_CLIENT_SECRET="<CLIENT SECRET>"
export AZURE_TOKEN_SCOPES="https://cognitiveservices.azure.us/.default"
export AZURE_OPENAI_API_VERSION="2024-02-01"
export AZURE_OPENAI_ENDPOINT="https://<RESOURCE>.openai.azure.us/"
export AZURE_OPENAI_DEPLOYMENT="<DEPLOYMENT>"
```

## Run

```bash
uv sync
uv run python heather/main.py
uv run python heather/main.py --dry-run
uv run python heather/main.py --skip-vantage-write
```

Local input/output mode:

```bash
export HEATHER_GL_ISSUES_CSV="./sample-gl-issues.csv"
export HEATHER_LOCAL_OUTPUT_DIRECTORY=".data"
uv run python heather/main.py --dry-run
```

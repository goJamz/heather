# Heather Data Layer Reference

**Project:** ADOC / DMC Automation Pipeline  
**Component:** Heather — GitLab synchronization agent  
**Scope:** The three Vantage datasets Heather depends on, their schemas, field relationships, Heather operating behavior, and idempotency rules.  
**Companion document:** `adoc_project_context.md` captures the larger ADOC mission and pipeline context. This document adds dataset-level detail.

---

## 1. Overview

Heather sits between the Vantage data layer and the ADOC GitLab issue board. It operates in two directions:

```text
Direction 1: Vantage -> GitLab
Read gl-issues, create missing GitLab issues, and reconcile Heather-managed source content on existing issues.

Direction 2: GitLab -> Vantage
Read current GitLab issue state and GitLab user comments, then write them back into Heather-owned Vantage tables.
```

Heather touches three Vantage datasets:

| Dataset | Direction | Role |
|---|---|---|
| `gl-issues` | Vantage -> Heather | GitLab-ready ticket rows produced by the Vantage transform. Heather reads this table to create missing GitLab issues and reconcile Heather-managed source content. |
| `heather-gitlab-state` | Heather -> Vantage | Current-state snapshot of each Heather-tracked GitLab issue. |
| `heather-gitlab-comments` | Heather -> Vantage | GitLab-native user comments captured from Heather-tracked issues. |

`gl-issues` is Vantage transform-owned. The two `heather-*` datasets are Heather-owned output datasets. Heather is the runtime writer for those output datasets through the Foundry dataset API.

---

## 2. Dataset Identity

| Dataset | Path | RID |
|---|---|---|
| `gl-issues` | `/Army_NIPR/ADOC/data/GitlabIssues/gl-issues` | `ri.foundry.main.dataset.dd9699c3-69f7-4fb4-be28-853da6071536` |
| `heather-gitlab-state` | `/Army_NIPR/ADOC/data/GitlabIssues/heather-gitlab-state` | `ri.foundry.main.dataset.a53196d5-3001-4863-a907-67874dec6b29` |
| `heather-gitlab-comments` | `/Army_NIPR/ADOC/data/GitlabIssues/heather-gitlab-comments` | `ri.foundry.main.dataset.da001bdc-0d6c-4922-82c4-24b5d111ebf6` |

---

## 3. Dataset Relationship Model

```text
MCSC/SPEAR
    ↓
Scarab source datasets
    ↓
Vantage transform
    ↓
gl-issues
    ↓
Heather creates missing GitLab issues and reconciles managed content
    ↓
ADOC GitLab issue board
    ↓
Heather reads GitLab state/comments
    ↓
heather-gitlab-state
heather-gitlab-comments
```

Primary join key:

```text
gl-issues.external_key
    ↔ heather-gitlab-state.external_key
    ↔ heather-gitlab-comments.external_key
```

Example:

```text
source_system = "MCSC/SPEAR"
source_ticket_id = "1256795"
external_key = "mcsc-spear-1256795"
```

Every Heather-tracked GitLab issue should include this hidden marker in the issue description:

```markdown
<!-- heather:external_key=mcsc-spear-1256795 -->
```

---

## 4. `gl-issues` — Heather Input Table

**Produced by:** Vantage transform  
**Direction:** Vantage -> Heather  
**Grain:** One row per MCSC/SPEAR ticket  
**Heather use:** Source of truth for creating missing GitLab issues and refreshing Heather-managed source content  

### 4.1 Schema

| # | Column | Type | Notes |
|---:|---|---|---|
| 1 | `external_key` | String | Durable sync key. Format: `mcsc-spear-<source_ticket_id>`. |
| 2 | `source_system` | String | Constant: `MCSC/SPEAR`. |
| 3 | `source_ticket_id` | String | String form of MCSC/SPEAR ticket ID. |
| 4 | `ticket_id` | Integer | Numeric MCSC/SPEAR ticket ID. |
| 5 | `content_hash` | String | Vantage SHA-256 hash of syncable source content. |
| 6 | `title` | String | Generated GitLab issue title. |
| 7 | `description` | String | Clean purpose/source narrative text rendered by Heather. |
| 8 | `status` | String | MCSC/SPEAR source workflow status. Not the GitLab board column. |
| 9 | `priority` | String | Derived priority value. |
| 10 | `assignee` | String | MCSC/SPEAR assignee display name. Source metadata only. |
| 11 | `labels_json` | String | JSON array of source labels. Empty value is `[]`. Heather does not apply these labels to GitLab issues. |
| 12 | `created_date` | String | Source ticket created timestamp. |
| 13 | `updated_date` | String | Source ticket updated timestamp. |
| 14 | `customer` | String | Customer name. |
| 15 | `customer_org` | String | Customer organization/unit. |
| 16 | `location` | String | Customer/location field. |
| 17 | `category` | String | Ticket category. |
| 18 | `mission_priority` | String | Mission priority. |
| 19 | `stage` | String | MCSC/SPEAR source stage. |
| 20 | `tags` | String | Source tags/systems. |
| 21 | `technical_requirements` | String | Technical requirements. |
| 22 | `policies_involved` | String | Related policy information. |
| 23 | `decision` | String | Technical evaluation decision. |
| 24 | `roadblocks` | String | Current or captured roadblocks. |
| 25 | `success_definition` | String | WEC success definition. |
| 26 | `attempted_solutions` | String | Attempted solutions. |
| 27 | `meeting_notes` | String | Intake or ticket meeting notes. |
| 28 | `resolution` | String | Final/source resolution field. |
| 29 | `solution_implemented` | String | Implemented solution. |
| 30 | `solution_documentation` | String | Additional solution documentation. |
| 31 | `solution_obstacles` | String | Obstacles during implementation. |
| 32 | `lessons_learned` | String | Source lessons learned. |
| 33 | `solution_applicability` | String | Where the solution applies. |
| 34 | `comments_json` | String | JSON array of MCSC/SPEAR source comments. Empty value is `[]`. |
| 35 | `comment_count` | Long | Number of MCSC/SPEAR source comments. |
| 36 | `contacts_json` | String | JSON array of contacts. Empty value is `[]`. |
| 37 | `metadata_json` | String | JSON object for additional metadata. Empty value is `{}`. |

### 4.2 `comments_json` Shape

`gl-issues.comments_json` stores MCSC/SPEAR source comments. Heather writes these authoritative comments into one Heather-managed GitLab note on the issue. The GitLab issue description may include a non-authoritative Heather summary of these comments when the AI comment digest is enabled, but the authoritative source comment transcript is not embedded in the description.

Expected element shape:

```json
{
  "source_comment_id": "1256795-0003",
  "source_ticket_id": "1256795",
  "date": "...",
  "author": "...",
  "comment_type": "...",
  "comment": "...",
  "comment_hash": "..."
}
```

### 4.3 `content_hash`

`content_hash` is used for deterministic source-content change detection. Vantage computes it from syncable content fields that Heather renders or maintains in GitLab, such as description, source status, priority, customer fields, technical fields, solution fields, and MCSC/SPEAR source comments. `labels_json` is not a GitLab label sync signal for Heather.

It does not include fields that should not independently trigger content updates, such as `title`, `external_key`, `source_system`, `source_ticket_id`, `ticket_id`, timestamps, `comment_count`, `metadata_json`, or `content_hash` itself.

### 4.4 `contacts_json`

`gl-issues.contacts_json` stores contact records from the source ticket. Heather renders the first contact with `type = "Alternate Point of Contact"` as `Alt. POC` in the `Ticket Information` section. Contacts with `type = "Stakeholder"` are rendered in a separate `Stakeholders` section. Other contact types are currently ignored by the GitLab issue renderer.

---

## 5. `heather-gitlab-state` — GitLab Issue State Write-Back

**Written by:** Heather  
**Direction:** GitLab -> Vantage  
**Grain:** One row per Heather-tracked GitLab issue  
**Write pattern:** Current-state snapshot. Each Heather run refreshes the latest observed issue state.  
**Scope:** Option A — Heather-tracked issues only. Orphan, hand-created, and non-Heather issues are excluded unless Heather has taken them over with a valid `external_key`.

### 5.1 Schema

| # | Column | Type | Notes |
|---:|---|---|---|
| 1 | `external_key` | String, non-null | Unique issue row key. Joins to `gl-issues.external_key`. |
| 2 | `source_system` | String | Expected value: `MCSC/SPEAR`. |
| 3 | `source_ticket_id` | String | MCSC/SPEAR ticket ID. |
| 4 | `gitlab_project_id` | Integer | GitLab project ID. |
| 5 | `gitlab_issue_id` | Long | Global GitLab issue ID. |
| 6 | `gitlab_iid` | Integer | Project-local issue IID. |
| 7 | `gitlab_web_url` | String | Browser URL to the issue. |
| 8 | `gitlab_title` | String | Current GitLab title. |
| 9 | `gitlab_state` | String | GitLab native state: `opened` or `closed`. |
| 10 | `gitlab_board_column` | String | Observed board column, such as To Do, In Progress, Review, Blocked, or Done. |
| 11 | `gitlab_labels_json` | String | JSON array of current GitLab labels. Empty value is `[]`. |
| 12 | `gitlab_assignees_json` | String | JSON array of current GitLab assignees. Empty value is `[]`. |
| 13 | `gitlab_created_time` | String | GitLab created timestamp. |
| 14 | `gitlab_updated_time` | String | GitLab updated timestamp. |
| 15 | `gitlab_closed_time` | String | GitLab closed timestamp. Null/empty while open. |
| 16 | `gitlab_comment_count` | Long | Count of GitLab notes/comments on the issue. |
| 17 | `heather_managed` | Boolean | True for issues Heather is tracking in this table. |
| 18 | `external_key_found` | Boolean | Whether the hidden Heather marker was found in the live GitLab issue description. |
| 19 | `last_seen_time` | String | Time Heather last observed this issue in GitLab. |
| 20 | `last_synced_time` | String | Time Heather last wrote/refreshed this row in Vantage. |
| 21 | `sync_status` | String | `ok`, `warning`, or `error`. |
| 22 | `sync_error` | String | Error details when applicable. |

### 5.2 Keying Notes

- `external_key` is required for every row.
- Rows without `external_key` are not written to this table.
- `external_key_found` is a diagnostic field. It does not allow orphan rows.
- If a previously tracked issue loses the hidden marker, Heather can still write the row from its known mapping, set `external_key_found=false`, and set `sync_status=warning`.
- `heather_managed` should normally be true for rows in this table because the table is scoped to Heather-tracked issues.

---

## 6. `heather-gitlab-comments` — GitLab User Comments Write-Back

**Written by:** Heather  
**Direction:** GitLab -> Vantage  
**Grain:** One row per GitLab user note/comment on a Heather-tracked issue  
**Write pattern:** Current-state snapshot. Edited comments update in place; deleted comments drop out on the next snapshot.  
**Scope:** GitLab-native user comments only. MCSC/SPEAR source comments remain in `gl-issues.comments_json` and are maintained in GitLab as Heather's marked source-comment transcript note. That Heather-managed note is excluded from this output dataset.

### 6.1 Schema

| # | Column | Type | Notes |
|---:|---|---|---|
| 1 | `note_key` | String, non-null | Unique row key. Format: `gitlab-note-<gitlab_project_id>-<gitlab_note_id>`. |
| 2 | `external_key` | String, non-null | Parent issue key. Joins to `gl-issues` and `heather-gitlab-state`. |
| 3 | `source_ticket_id` | String | Parent MCSC/SPEAR ticket ID. |
| 4 | `gitlab_project_id` | Integer | GitLab project ID. |
| 5 | `gitlab_iid` | Integer | Parent issue IID. |
| 6 | `gitlab_issue_id` | Long | Global parent issue ID. |
| 7 | `gitlab_note_id` | Long | GitLab note/comment ID. |
| 8 | `gitlab_note_url` | String | Deep link to the note when available. |
| 9 | `author_username` | String | GitLab username of note author. |
| 10 | `author_name` | String | GitLab display name of note author. |
| 11 | `body` | String | GitLab user comment body. |
| 12 | `is_system` | Boolean | True for system notes. Stored rows are normally false. |
| 13 | `is_edited` | Boolean | True when `updated_time` differs from `created_time`. |
| 14 | `created_time` | String | GitLab note created timestamp. |
| 15 | `updated_time` | String | GitLab note updated timestamp. |
| 16 | `comment_hash` | String | SHA-256 hash for detecting edited comments. |
| 17 | `last_seen_time` | String | Time Heather last observed the note. |
| 18 | `last_synced_time` | String | Time Heather last wrote/refreshed the row. |
| 19 | `sync_status` | String | `ok`, `warning`, or `error`. |
| 20 | `sync_error` | String | Error details when applicable. |

### 6.2 Comment Stream Separation

These are separate comment streams and must not be conflated:

| Comment source | Dataset/field | Direction | Purpose |
|---|---|---|---|
| MCSC/SPEAR source comments | `gl-issues.comments_json` | Vantage -> GitLab | Written into one Heather-managed authoritative GitLab note. Optional AI summary may appear in the description. |
| GitLab user comments | `heather-gitlab-comments` | GitLab -> Vantage | Captured back from GitLab for DMC visibility and downstream automation. |

`comment_hash` values are only meaningful within their own comment stream. They should not be compared across source comments and GitLab user comments.

---

## 7. Heather Operating Behavior

### 7.1 Direction 1 — Create or Reconcile GitLab Issues

For each row in `gl-issues`, Heather:

1. Reads `external_key`.
2. Checks whether a GitLab issue already exists for that key.
3. Uses the hidden marker as a durable lookup/validation handle.
4. Creates a new GitLab issue only when no matching issue exists.
5. Applies only the existing `Heather` GitLab project label to newly created issues.
6. Refreshes only the Heather-managed description block when source content changes.
7. Creates or updates Heather's marked source-comment transcript note from `comments_json`.
8. Allows newly created issues to enter the default GitLab board location, expected to be To Do.
9. Records current state later through `heather-gitlab-state`.

Heather does not:

```text
Move GitLab issues between board columns.
Set GitLab workflow status.
Close GitLab issues.
Reopen GitLab issues.
Assign GitLab users.
Create or apply source labels from `labels_json`.
```

Humans own GitLab board movement and workflow decisions.

### 7.2 Direction 2 — Capture GitLab State and User Comments

After issue creation/reconciliation, Heather reads tracked GitLab issues and writes:

```text
heather-gitlab-state      -> one current-state row per tracked GitLab issue
heather-gitlab-comments   -> one current-state row per GitLab user comment on tracked issues
```

Both output datasets are refreshed as snapshots. They are not historical append logs.

### 7.3 Heather-Managed Description Block

Heather renders structured `gl-issues` source fields into a managed section of the GitLab issue description:

```markdown
<!-- heather:managed:start -->
Heather-generated source content.
<!-- heather:managed:end -->
```

Heather updates this managed section when the source-content hash changes. Human-written content outside the managed block is not overwritten by Heather.

The top rendered sections are `Ticket Information` and, when `contacts_json` contains stakeholder records, `Stakeholders`. `Ticket Information` includes Customer, Alt. POC, Organization, Stage, and `ADOC Assigned` from the MCSC/SPEAR assignee field.

Heather does not render a visible `Ticket ID` row because the ticket number is already represented in the GitLab issue title. `gl-issues.description` must be clean purpose/source narrative text and cannot contain Heather-generated output. When AI helpers are enabled, Heather Transcription QA and Heather Comment Digest should appear immediately after `Meeting Notes`.

### 7.4 Heather-Managed Source Comment Note

Heather writes authoritative MCSC/SPEAR source comments from `comments_json` into one GitLab note marked with:

```markdown
<!-- heather:source_comments -->
```

This note is Heather-managed and may be updated when `comments_json` changes. It is not treated as a GitLab-native user comment for `heather-gitlab-comments`.

### 7.5 Assignee Handling

`gl-issues.assignee` is the MCSC/SPEAR source assignee display name. Heather treats it as source metadata only.

Heather does not map this value to a GitLab username and does not assign GitLab users from it.

---

## 8. Idempotency Rules

Heather must be safe to run repeatedly.

### 8.1 Issue Identity

Primary identity:

```text
external_key = mcsc-spear-<source_ticket_id>
```

Backup/validation marker in the issue description:

```markdown
<!-- heather:external_key=mcsc-spear-1256795 -->
```

### 8.2 Creation Rules

```text
Create a GitLab issue only when no matching issue exists.
Never create more than one GitLab issue for the same external_key.
Skip creation when a matching issue already exists.
Use external_key first and the hidden marker as backup/validation.
```

### 8.3 Change Detection

`gl-issues.content_hash` is the Vantage source-content change signal. Heather combines it with Heather's render format version to know whether the GitLab-rendered issue content changed.

### 8.4 Human Content Safety

```text
Do not overwrite human-managed GitLab content.
Only touch Heather-managed description sections.
Maintain the Heather-managed source comment note without duplicating notes.
Do not move board columns.
Do not close or reopen issues.
Do not assign users.
```

### 8.5 Write-Back Idempotency

```text
heather-gitlab-state uses external_key as the issue snapshot key.
heather-gitlab-comments uses note_key as the comment snapshot key.
Each run refreshes the current snapshot.
The same issue or note must not produce duplicate rows in one snapshot.
GitLab items no longer present naturally drop out of the next snapshot.
```

---

## 9. Pipeline Position

```text
Scarab
    -> Vantage source datasets
Vantage Transform
    -> gl-issues
Heather Direction 1
    -> create missing GitLab issues and reconcile Heather-managed content
Humans
    -> work the GitLab issue board
Heather Direction 2
    -> heather-gitlab-state
    -> heather-gitlab-comments
Gandalf
    -> lessons learned, AARs, recommendations, EXSUMs
```

Heather keeps GitLab populated from Vantage in one direction and keeps Vantage aware of live GitLab state in the other direction. GitLab remains the operational working record, while Vantage retains current-state visibility for DMC and downstream automation.

# ADOC Project Context: DMC Automation Pipeline

**Project:** Army Data Operations Center (ADOC)  
**Cell:** Data Management Cell (DMC)  
**Status:** Working project reference
**Scope:** ADOC cell structure, DMC mission, documentation expectations, Scarab/Vantage/Heather/Gandalf workflow, Vantage dataset reference, operational notes, and open items.

---

## 1. Purpose of This Document

This document captures the current working understanding of how ADOC (Comprised of three cells (WEC,FINISH,DMC)),  Scarab, Vantage, Heather, and Gandalf fit together.

The core idea:

```text
WEC and Finish does the operational work.
DMC captures the work.
Scarab collects source ticket data.
Vantage organizes and transforms the data.
Heather keeps GitLab aligned with the transformed ticket state.
Gandalf turns high-quality GitLab issue records into reusable knowledge products.
```

The most important principle:

```text
The automation pipeline is only as good as the data captured in GitLab.
```

---

## 2. ADOC Organizational Context

ADOC has three primary cells:

| Cell | Meaning | Primary Role |
|---|---|---|
| **WEC** | Intake / requirements cell | Performs initial intake and identifies requirements. |
| **Finish Cell** | Execution / completion cell | Performs most of the technical work and helps the client reach the finish line. |
| **DMC** | Data Management Cell | Captures data, maintains documentation discipline, supports the automated pipeline, and enables lessons learned / reporting. |

DMC is the cell responsible for making sure operational work is captured in a way that can support automation, reporting, and institutional knowledge management.

---

## 3. DMC Lines of Effort

| LOE | Title | Description |
|---|---|---|
| **LOE 1** | Refine the Operational Framework | Define ADOC's structure, authorities, core processes, and repeatable operating model. |
| **LOE 2** | Build the Core Capability | Assemble personnel, technical resources, workflows, and automated agents. |
| **LOE 3** | Deliver Immediate Value | Attack pre-identified problems through pilot tickets and stakeholder engagements while capturing lessons learned. |

---

## 4. DMC Data Capture Mission

DMC's role is not only to move data between systems. DMC is responsible for making sure the work is captured with enough detail, structure, and chronology to support downstream automation.

The GitLab issue is intended to become the operational single source of truth for automated outputs.

High-fidelity capture is required because Gandalf depends on the contents of GitLab issues and synced Teams conversations to generate:

```text
Lessons Learned
Recommendations
Executive Summaries / EXSUMs
White papers
Leadership reporting products
```

Poor data capture directly degrades AI-generated analysis and reporting.

---

## 5. Full Pipeline Overview

### 5.1 Execution Order

The scheduled pipeline runs in this order:

```text
Scarab → Vantage Transform → Heather → Gandalf
```

Each job depends on the job before it because each application produces the data or state required by the next application.

### 5.2 Dependency Chain

| Order | Job | Depends On | Produces |
|---:|---|---|---|
| 1 | **Scarab** | MCSC/SPEAR source availability and credentials/cookies | Fresh Vantage ticket datasets |
| 2 | **Vantage Transform** | Scarab-updated Vantage datasets | `gl-issues` GitLab-ready table |
| 3 | **Heather** | Refreshed `gl-issues` table | Created, updated, or skipped GitLab issues |
| 4 | **Gandalf** | Updated ADOC GitLab issue board | Lessons Learned, Recommendations, EXSUM / white paper |

---

## 6. Scarab Role

Scarab is responsible for collecting the latest ADOC ticket data from MCSC/SPEAR sources and uploading the resulting datasets into Vantage.
Scarab creates or refreshes the source data that the rest of the automation chain depends on.

### 6.1 Current Scarab/Vantage Outputs

```text
ticket-data.csv
tag-data.csv
contact-data.csv
wec-data.csv
activity-data.csv
tech-eval-data.csv
tech-eval-status-update-data.csv
implementation-data.csv
implementation-status-update-data.csv
```

### 6.3 Scarab Source-of-Truth Mapping

The current source-of-truth schema and dataset mapping document is:

```text
scarab_vantage_schema_mapping.md
```

---

## 7. Vantage Transform Role

After Scarab finishes successfully, an internal Vantage Python transform runs.

The transform takes the current Vantage ticket tables and creates or refreshes a GitLab-ready table called:

```text
gl-issues
```

The `gl-issues` table is the handoff point between the Vantage data layer and Heather.

---

## 8. Heather Role

Heather runs after the Vantage transform creates or refreshes `gl-issues`.

Heather reaches into Vantage and reads:

```text
gl-issues
```

Heather does not read the raw Scarab tables directly.

Heather reads the transformed GitLab-ready Vantage table:

```text
gl-issues
```

Heather's primary job is to create missing GitLab issues from `gl-issues`.

Heather compares each row in `gl-issues` against the current ADOC GitLab issue board using a durable sync identity such as:

```text
source_system = "MCSC/SPEAR"
source_ticket_id = "1256795"
external_key = "mcsc-spear-1256795"
```

Heather-created GitLab issues should include a hidden marker in the GitLab issue description:

```markdown
<!-- heather:external_key=mcsc-spear-1256795 -->
```

This marker gives Heather a stable way to identify whether a GitLab issue already exists for a source MCSC/SPEAR ticket.

Heather has three possible outcomes per `gl-issues` row:

| Outcome | Action |
|---|---|
| A | Create a new GitLab issue when no matching issue exists. |
| B | Record that a matching GitLab issue already exists. |
| C | No-op when no creation action is needed. |

Heather is not a workflow/status-control bot.

Heather does **not**:

```text
Move GitLab issues between board columns.
Set GitLab workflow status.
Close GitLab issues.
Reopen GitLab issues.
Assign GitLab users based on MCSC/SPEAR assignee values.
```

When Heather first creates a GitLab issue, the issue should enter the default GitLab board location, expected to be the `To Do` column.

Humans are responsible for moving GitLab issues through workflow columns such as:

```text
To Do
In Progress
Review
Blocked
Done
```

The MCSC/SPEAR assignee value is source metadata only. It should be included in the GitLab issue description, but it should not be treated as a GitLab username or GitLab user assignment.

Heather should preserve MCSC/SPEAR source comments as one Heather-managed GitLab note. The issue description should contain Heather-rendered content from structured `gl-issues` fields and, when enabled, Heather's non-authoritative summary of the source comments. The authoritative source comments should not be embedded in the description.

Heather should be designed around idempotent issue creation behavior:

```text
Create missing GitLab issues.
Do not create duplicate GitLab issues.
Use external_key and the hidden Heather marker for lookup.
Skip creation when a matching GitLab issue already exists.
Do not overwrite human-managed GitLab content.
Only update Heather-managed description sections and Heather-managed source-comment notes.
```

Heather also has a second responsibility: write GitLab state back into Vantage.

After checking or creating GitLab issues, Heather should read the current GitLab issue board state and write that state back to a Heather-created Vantage output table.

This future write-back table should capture current GitLab state such as:

```text
External key
Source ticket ID
GitLab project ID
GitLab issue IID
GitLab issue URL
GitLab title
GitLab state
GitLab board column
GitLab labels
GitLab assignees
GitLab created time
GitLab updated time
GitLab closed time
GitLab comment count
Last seen time
Last synced time
Sync status
Sync error
```

Heather should also write GitLab user comments back into a separate Heather-created Vantage comments table.

This future comments table should capture comments written by users directly in GitLab issues. These are different from MCSC/SPEAR source comments and should exclude Heather's managed source-comment transcript note.

Conceptually, Heather works in two directions:

```text
Direction 1:
Vantage gl-issues → GitLab

Purpose:
Create missing GitLab issues only.

Direction 2:
GitLab → Vantage

Purpose:
Capture current GitLab issue state, board position, labels, assignees, and GitLab user comments for DMC visibility and downstream automation.
```

Heather supports the DMC mission by making sure GitLab becomes the operational working record while Vantage retains visibility into the current state of GitLab-managed work.

Heather's updated role in the full pipeline is:

```text
Scarab captures MCSC/SPEAR data.
Vantage transforms source tables into gl-issues.
Heather creates missing GitLab issues from gl-issues.
Humans work the GitLab issue board.
Heather captures GitLab state and GitLab user comments back into Vantage.
Gandalf uses high-quality GitLab records for lessons learned, AARs, recommendations, and EXSUMs.
```

---

## 9. Gandalf Role

Gandalf runs after Heather.

Gandalf uses the ADOC GitLab issue board as its input. At this point in the workflow, GitLab should contain the latest issues and updates created or synchronized by Heather.

Gandalf looks for GitLab issues with the correct human-managed labels and metadata, then starts the knowledge pipeline.

Current working trigger condition:

```text
GitLab issue has Closed status + correct human-managed labels.
```

Current working label reference:

```text
LOE 1
```

The exact final label set that triggers Gandalf still needs to be documented.

### 9.1 Gandalf Agents

| Agent | Role |
|---|---|
| **Observer** | Reads GitLab issues and drafts Lesson Learned markdown. |
| **Analyst** | Reviews approved lessons and creates Recommendation markdown. |
| **Reporter** | Uses approved lessons and recommendations to create an EXSUM / white paper. |

### 9.2 Gandalf Sequence

```text
1. Observer reads the GitLab issue.
2. Observer includes synced Teams chat history when available.
3. Observer drafts a Lesson Learned markdown file.
4. Observer submits the Lesson Learned file through a merge request.
5. A human reviews and approves the merge request.
6. Analyst reviews the approved Lesson Learned file.
7. Analyst generates a Recommendation markdown file.
8. Analyst submits the Recommendation file through a second merge request.
9. A human reviews and approves the Recommendation merge request.
10. Reporter compiles approved lessons and recommendations into a final EXSUM / white paper.
```

Human review gates are required to preserve accuracy, security, quality, and accountability.

### 9.3 AAR Auto-Population Note

Gandalf makes AAR as well. 

---

## 10. GitLab Issue as the Operational Single Source of Truth

The GitLab issue is the authoritative record for all automated outputs. This is non-negotiable for the automation model.

Once Heather syncs Vantage-derived ticket data into GitLab, the GitLab issue should contain or link to:

```text
Ticket metadata
Status
Labels
Relevant stakeholders
Technical history
Teams chat history when synced
Meeting notes
Compliance references
Implementation notes
Validation evidence
AAR-relevant comments
```

---

## 11. AAR and Knowledge Management Flow

Once a GitLab issue is closed and has the relevant human-managed labels, Gandalf starts the automated knowledge-management pipeline.

AAR flow:

```text
Closed GitLab issue with correct human-managed labels
        ↓
Observer creates Lesson Learned markdown
        ↓
Human MR review
        ↓
Analyst creates Recommendation markdown
        ↓
Human MR review
        ↓
Reporter creates EXSUM / white paper
        ↓
Leadership-ready output
```

---

## 12. Infrastructure Reference

| Component | Value |
|---|---|
| SPEAR base URL | `https://mcsc.army.mil` |
| SPEAR dashboard endpoint | `https://mcsc.army.mil/fsc/tools/adoc/dashboard/` |
| SPEAR ticket endpoint | `https://mcsc.army.mil/fsc/tools/adoc/tickets/view.php` |
| SPEAR activity endpoint | `https://mcsc.army.mil/fsc/tickets/view/modules/activity.data.php` |
| Cookie env var | `SPEAR_COOKIES_REQUEST_HEADER` |
| GitLab host | `code.cdso.army.mil` |
| Cloud | Azure Government |
| Vantage platform | Palantir Foundry |
| Scarab auth method | CAC browser cookies pasted as manual CI pipeline variable |

---

## 13. Current Working Summary

The current ADOC automation workflow should be understood as a data-to-knowledge pipeline:

```text
MCSC/SPEAR
    ↓
Scarab
    ↓
Vantage datasets
    ↓
Vantage transform
    ↓
gl-issues
    ↓
Heather
    ↓
ADOC GitLab issue board
    ↓
Gandalf Observer
    ↓
Lessons Learned markdown
    ↓
Human review
    ↓
Gandalf Analyst
    ↓
Recommendations markdown
    ↓
Human review
    ↓
Gandalf Reporter
    ↓
EXSUM / white paper
```

DMC's mission is to make sure the captured data is complete, chronological, and useful enough for the automation pipeline to produce reliable knowledge products.

Final operating principle:

```text
High-quality ticket capture creates high-quality automated knowledge products.
Low-quality ticket capture creates low-quality automated knowledge products.
```

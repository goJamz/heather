# Heather Architecture

This document explains how the Heather app is organized after the sync and
description modules were split into smaller files. It is intended for future
developers and maintainers who need to find the right place to make a change
without rediscovering the whole flow.

Heather is run from the `app/` directory:

```bash
uv run python heather/main.py
```

Because of that runtime shape, `app/heather/` is effectively the import root.
Imports inside the app intentionally use the flat style:

```python
from sync.run import run_heather
from tools.description import build_issue_description
```

Do not change these to `from heather.sync...` imports unless the runtime entry
point and packaging model change too.

## Runtime Flow

```text
heather/main.py
    -> sync.run.run_heather()
        -> tools.client.get_gitlab_client()
        -> tools.vantage.get_vantage_client()
        -> read Vantage gl-issues rows
        -> for each source row:
            -> sync.issues.find_gitlab_issue_by_external_key()
            -> if missing:
                -> sync.issues.create_gitlab_issue()
                    -> sync.labels.build_gitlab_issue_labels()
            -> if existing:
                -> refresh managed description block when needed
                -> sync.labels.reconcile_gitlab_issue_labels()
            -> sync.notes.sync_source_comment_note()
            -> sync.rows.build_state_row()
            -> sync.rows.build_comment_rows()
        -> write state and comment snapshots through tools.vantage
```

The synchronization code is deterministic by default. Optional AI helpers can
add non-authoritative sections, but Heather does not use AI to decide labels,
assignees, issue state, closure, or workflow movement.

## Directory Map

```text
heather/
|-- main.py
|-- constants.py
|-- models/
|   `-- azure.py
|-- sync/
|   |-- run.py
|   |-- issues.py
|   |-- labels.py
|   |-- titles.py
|   |-- notes.py
|   `-- rows.py
`-- tools/
    |-- client.py
    |-- vantage.py
    |-- ai.py
    `-- description/
        |-- __init__.py
        |-- markers.py
        |-- hashing.py
        |-- sections.py
        |-- managed_block.py
        `-- source_comments.py
```

## Top-Level Files

### `heather/main.py`

CLI entry point. It parses command-line flags and calls `run_heather()` from
`sync.run`.

This file should stay thin. Add workflow behavior in `sync/`, not in the CLI.

### `heather/constants.py`

Shared constants for:

- Vantage dataset RIDs
- local snapshot file names
- Heather GitLab description markers
- required GitLab labels
- stage label mapping
- known board column labels
- Vantage output schemas

Use this file for stable values that are shared across modules. Environment
variable reading belongs near the behavior that uses it.

### `heather/__init__.py`

Package marker and optional module docstring. It does not define app behavior.

## Sync Modules

The `sync/` package owns the GitLab synchronization workflow. It should contain
business flow code, not low-level clients or markdown rendering details.

### `sync/run.py`

Main orchestrator for one Heather run.

Responsibilities:

- build GitLab and Vantage clients
- read source rows from the `gl-issues` dataset
- skip empty or duplicate `external_key` rows
- create missing GitLab issues
- refresh existing Heather-managed description blocks when source content changes
- reconcile Heather-managed labels
- sync the authoritative source comment note
- build state and comment snapshot rows
- write snapshots to Vantage or local CSV
- print run counts

If you need to change the order of the sync workflow, start here.

### `sync/issues.py`

GitLab issue creation and issue-description update operations.

Responsibilities:

- find existing issues by Heather external-key marker
- build and create new GitLab issues
- read optional `GITLAB_EPIC_ID`
- replace only the Heather-managed description block on existing issues

This module delegates title construction to `sync.titles`, label construction
to `sync.labels`, and description rendering to `tools.description`.

### `sync/labels.py`

Heather-managed GitLab label behavior.

Responsibilities:

- build the required label list for one source row
- preserve non-stage labels already on an issue
- replace Heather-managed `Stage::...` labels based on source stage
- require that configured GitLab labels already exist
- dedupe labels while preserving order

Heather does not create labels. Missing required labels raise an error so the
GitLab project or group configuration can be fixed explicitly.

### `sync/titles.py`

GitLab issue title normalization.

Responsibilities:

- choose the source ticket id
- normalize whitespace
- remove redundant generated customer/person title segments
- fall back to `ADOC Ticket #<id>` when the source title is blank

Keep title-only string rules here so issue creation stays readable.

### `sync/notes.py`

GitLab note handling.

Responsibilities:

- create or update Heather's authoritative source comment note
- find Heather's source comment note
- return user notes while excluding GitLab system notes and Heather's managed
  source-comment note

This module does not render source comments itself. Rendering lives in
`tools.description.source_comments`.

### `sync/rows.py`

Output snapshot row builders.

Responsibilities:

- build `heather-gitlab-state` rows
- build `heather-gitlab-comments` rows
- build error rows when one source row fails
- infer the visible board column from labels and issue state
- build GitLab note deep links
- hash user comment bodies for edit detection
- provide the run timestamp

This module shapes Heather's write-back datasets. If a Vantage output schema
changes, update `constants.py` and the corresponding row builder together.

### `sync/__init__.py`

Package marker and module docstring for sync modules. It does not re-export the
workflow API. Import `run_heather` from `sync.run`.

## Description Modules

The `tools/description/` package owns GitLab markdown rendering, Heather marker
handling, and content hashes. Sync modules use its public exports through
`tools.description`.

### `tools/description/__init__.py`

Public import surface for description helpers used by sync code.

It re-exports:

- `should_refresh_managed_block`
- `build_issue_description`
- `replace_heather_managed_block`
- `get_external_key_marker`
- `is_heather_source_comment_note`
- `build_source_comment_note_body`

If sync code needs a description helper, prefer exporting it here instead of
importing deeply from a submodule.

### `tools/description/markers.py`

Heather's hidden GitLab marker helpers.

Responsibilities:

- build the external-key marker
- build content hash markers
- extract an existing content hash from an issue description
- identify Heather's source-comment note marker

These markers are how Heather safely recognizes what it owns in GitLab.

### `tools/description/hashing.py`

Source-content hash logic.

Responsibilities:

- define fields that do not trigger description refreshes
- define `SOURCE_RENDER_FORMAT_VERSION`
- normalize source values before hashing
- build the managed-description source content hash
- build the source-comment note hash
- decide whether an existing managed block needs refresh

When description rendering semantics change, bump
`SOURCE_RENDER_FORMAT_VERSION` so existing GitLab issues refresh cleanly on the
next sync.

### `tools/description/sections.py`

Visible source-field markdown rendering.

Responsibilities:

- parse JSON array fields from Vantage
- render the main source description
- render the ticket information table
- render the stakeholders table
- format contact summaries and contact details
- escape markdown table cells
- render source text sections
- reject source descriptions that already contain Heather-generated output

This is the main place to change how source-owned fields appear inside the
GitLab issue description.

### `tools/description/managed_block.py`

Heather-managed issue description block assembly and replacement.

Responsibilities:

- build a full issue description for new Heather-created issues
- build only the Heather-managed block
- insert optional generated helper sections after Meeting Notes
- replace an existing Heather-managed block while preserving human text outside
  the block
- add markers when an existing description does not yet contain them

This module defines the boundary between source-owned content that Heather may
refresh and human-authored issue description text that Heather must preserve.

### `tools/description/source_comments.py`

Authoritative source comment note rendering.

Responsibilities:

- parse `comments_json`
- format each MCSC/SPEAR source comment as markdown
- include the source-comment note marker and hash marker
- return an empty string when there are no usable source comments

Source comments live in one Heather-managed GitLab note, not in the issue
description.

## Tool Modules

The `tools/` package contains integration helpers and optional support code.

### `tools/client.py`

Builds the GitLab API client from environment variables.

Uses:

- `GITLAB_API_ENDPOINT`
- `GITLAB_API_TOKEN`
- optional `CURL_CA_BUNDLE`

Keep raw GitLab client setup here. GitLab synchronization behavior belongs in
`sync/`.

### `tools/vantage.py`

Vantage and local CSV I/O.

Responsibilities:

- read source `gl-issues` rows from Vantage or a local CSV
- write Heather output rows to local CSV when configured
- upload typed Parquet snapshots to Vantage
- coerce output dataframe columns to the expected nullable types

The main workflow should call `read_table()`, `upload_rows()`, or
`write_local_rows()` and avoid reaching into private helper methods.

### `tools/ai.py`

Optional Azure/OpenAI helper.

Responsibilities:

- decide whether the optional AI comment digest is enabled by CLI flag or environment
- build the source comment digest prompt
- call the Azure OpenAI model
- format optional markdown sections returned by the model
- degrade gracefully by printing a warning and returning an empty string on AI
  errors

AI output is supplemental. It should not change source-owned fields or workflow
decisions.

### `tools/__init__.py`

Package marker and optional module docstring. It does not define app behavior.

## Model Modules

### `models/azure.py`

Azure/OpenAI model factory used by `tools.ai`.

Responsibilities:

- read Azure environment variables
- acquire an Azure credential token
- construct the `AzureChatOpenAI` client

This module is only needed when optional AI hooks are enabled.

### `models/__init__.py`

Package marker and optional module docstring. It does not define app behavior.

## Data Ownership Boundaries

Heather owns:

- hidden Heather markers in issue descriptions
- content inside `<!-- heather:managed:start -->` and
  `<!-- heather:managed:end -->`
- the single Heather-managed source-comment note
- Heather-managed labels: `Type::ADOC Ticket` and mapped `Stage::...` labels
- Vantage snapshot outputs

Humans own:

- description text outside the Heather-managed block
- ordinary GitLab comments
- issue state, assignees, board movement, closure, and workflow decisions

Maintainers should preserve those boundaries when adding behavior.

## Common Change Guide

| Change | Start Here |
|---|---|
| Add or reorder rendered source fields | `tools/description/sections.py` |
| Change managed block replacement behavior | `tools/description/managed_block.py` |
| Change refresh detection | `tools/description/hashing.py` |
| Change GitLab issue creation payload | `sync/issues.py` |
| Change label mapping or reconciliation | `sync/labels.py` and `constants.py` |
| Change title cleanup | `sync/titles.py` |
| Change source comment note formatting | `tools/description/source_comments.py` |
| Change output snapshot columns | `constants.py` and `sync/rows.py` |
| Change Vantage read/write mechanics | `tools/vantage.py` |
| Change optional AI prompts | `tools/ai.py` |
| Change CLI flags | `main.py`, then pass values into `sync.run` |

## Verification Commands

For a syntax check:

```bash
python3 -m py_compile \
  heather/main.py \
  heather/sync/__init__.py \
  heather/sync/run.py \
  heather/sync/issues.py \
  heather/sync/labels.py \
  heather/sync/titles.py \
  heather/sync/notes.py \
  heather/sync/rows.py \
  heather/tools/description/__init__.py \
  heather/tools/description/markers.py \
  heather/tools/description/hashing.py \
  heather/tools/description/sections.py \
  heather/tools/description/managed_block.py \
  heather/tools/description/source_comments.py
```

For an import-chain check from `app/heather`:

```bash
python3 -c "from sync.run import run_heather; print(run_heather.__name__)"
```

For the documented app entry point from `app/`:

```bash
uv run python heather/main.py --dry-run
```

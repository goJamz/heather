# Scarab to Vantage Schema Mapping

**Project:** ADOC / Scarab  
**Document purpose:** Source-to-target mapping for Scarab SPEAR scraper outputs and the Vantage datasets they populate.  
**Last updated:** 2026-07-01  
**Scope:** Current Scarab scraper outputs, current Vantage datasets, current Vantage schemas, and known field-coverage observations.

---

## 1. High-Level Workflow

Scarab currently has two working code areas:

```text
~/05_adoc/scarab/app
~/05_adoc/scarab/automation
```

The `app` folder contains the reusable Scarab Python package. The `automation` folder contains the operational script and GitLab CI job that install the package and run the scrape/upload workflow.

Current workflow:

```text
1. Code changes are made in ~/05_adoc/scarab/app.
2. Approved changes on main publish the Scarab package to the package registry.
3. The automation pipeline is run manually.
4. The automation pipeline installs Scarab from the package registry.
5. automation/main.py creates a SpearClient and VantageClient.
6. SpearClient extracts datasets from MCSC SPEAR.
7. VantageClient uploads each dataframe as a CSV into its matching Vantage dataset.
```

Operational delivery gap:

```text
Changes made in ~/05_adoc/scarab/app do not affect automation runs until the Scarab package is rebuilt and republished to the package registry. The automation pipeline installs the published package, not the local app working tree.
```

Current Scarab/Vantage dataset outputs:

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
aar-data.csv
```

---

## 2. Current Project Structure

### Scarab app package

```text
~/05_adoc/scarab/app
.
├── README.md
├── demo.py
├── pyproject.toml
└── scarab
    ├── __init__.py
    ├── spear
    │   ├── client.py
    │   └── constants.py
    └── vantage
        ├── client.py
        └── constants.py
```

### Scarab automation folder

```text
~/05_adoc/scarab/automation
.
├── .gitignore
├── .gitlab-ci.yml
├── README.md
├── main.py
├── requirements.txt
└── field_coverage.py
```

`field_coverage.py` is informational only. It reports fields, labels, and tables visible on SPEAR pages that are not currently captured by Scarab. It does not upload data and should not block the pipeline.

---

## 3. Source Systems and Authentication

### SPEAR source

The current scraper reads from the MCSC SPEAR web application, using copied browser cookies after CAC authentication.

Important constants:

```python
SPEAR_BASE_URL = "https://mcsc.army.mil"
SPEAR_ACTIVITY_ENDPOINT = f"{SPEAR_BASE_URL}/fsc/tickets/view/modules/activity.data.php"
SPEAR_DASHBOARD_ENDPOINT = f"{SPEAR_BASE_URL}/fsc/tools/adoc/dashboard/"
SPEAR_TICKET_ENDPOINT = f"{SPEAR_BASE_URL}/fsc/tools/adoc/tickets/view.php"
```

The scraper expects this environment variable:

```text
SPEAR_COOKIES_REQUEST_HEADER
```

The GitLab automation pipeline passes that value from the manual pipeline input named `cookies`.

### Vantage target

The current automation uploads Pandas dataframes as CSV files into existing Vantage datasets. Dataset RIDs are imported from:

```python
scarab.vantage.constants
```

Current target dataset constants expected by the automation flow:

```python
TICKET_DATA_RID
TAG_DATA_RID
CONTACT_DATA_RID
WEC_DATA_RID
ACTIVITY_DATA_RID
TECH_EVAL_DATA_RID
TECH_EVAL_STATUS_UPDATE_DATA_RID
IMPLEMENTATION_DATA_RID
IMPLEMENTATION_STATUS_UPDATE_DATA_RID

# Required only if Scarab automation owns the aar-data upload.
AAR_DATA_RID
```

---

## 4. Current Vantage Datasets

The current Vantage datasets and RIDs from the Vantage schema export are:

| Vantage dataset | RID |
|---|---|
| `ticket-data` | `ri.foundry.main.dataset.e2c6e35f-ee6a-421b-98fd-09118ea28a7a` |
| `tag-data` | `ri.foundry.main.dataset.a13f1900-12e2-4134-a444-79b8229f5cd2` |
| `contact-data` | `ri.foundry.main.dataset.e9a5ada6-79f8-421d-a76d-d185cc471ee6` |
| `wec-data` | `ri.foundry.main.dataset.ff4265c7-2926-46fe-b4b3-7d7a89cb90e6` |
| `activity-data` | `ri.foundry.main.dataset.9f374a13-6f3e-4c39-98f1-2872ac1cc5b2` |
| `tech-eval-data` | `ri.foundry.main.dataset.b75c311b-8dbd-49ca-9f7b-e29f7cf617f0` |
| `tech-eval-status-update-data` | `ri.foundry.main.dataset.d4643d15-6617-4d2a-b8c1-471703d113b8` |
| `implementation-data` | `ri.foundry.main.dataset.eb747c3f-2055-4a87-9a4d-26ef73d1e6e6` |
| `implementation-status-update-data` | `ri.foundry.main.dataset.cc4b771a-8979-4ae3-939b-80111d6d1553` |
| `aar-data` | `ri.foundry.main.dataset.d09f72a0-b360-4a49-9638-daf48df769bb` |

Recommended table intent:

| Vantage dataset | Intended grain | Purpose |
|---|---|---|
| `ticket-data` | One row per ticket | Master ticket identity, status, ticket-level metadata, and attachment references. |
| `tag-data` | One row per ticket in current implementation | Comma-separated tag/system values from `systems-table`. |
| `contact-data` | Many rows per ticket | Alternate POC and stakeholder contact records. |
| `wec-data` | One row per ticket when WEC fields exist | Intake/WEC evaluation fields. |
| `activity-data` | Many rows per ticket | Activity/comments from the SPEAR activity endpoint. |
| `tech-eval-data` | One row per ticket when tech evaluation fields exist | Technical evaluation / Finish Cell summary fields. |
| `tech-eval-status-update-data` | Many rows per ticket | Status update history for technical evaluation. |
| `implementation-data` | One row per ticket when implementation fields exist | Implementation summary, solution, obstacles, lessons learned, and applicability fields. |
| `implementation-status-update-data` | Many rows per ticket | Status update history for implementation. |
| `aar-data` | One row per ticket when AAR fields exist | After Action Report schedule, policy/process, skills, roles, AI/ML potential, strategic alignment, and notes fields. |

---

## 5. Current Automation Main Flow

The current automation should extract the master `ticket-data` first, then use `ticket_data["Ticket ID"]` as the parent ticket list for child/detail datasets.

Recommended current upload order:

| Order | Extraction method | Output filename | Vantage target RID constant | Vantage dataset |
|---:|---|---|---|---|
| 1 | `spear.get_ticket_data()` | `ticket-data.csv` | `TICKET_DATA_RID` | `ticket-data` |
| 2 | `spear.get_tag_data(ticket_ids=ticket_data["Ticket ID"])` | `tag-data.csv` | `TAG_DATA_RID` | `tag-data` |
| 3 | `spear.get_contact_data(ticket_ids=ticket_data["Ticket ID"])` | `contact-data.csv` | `CONTACT_DATA_RID` | `contact-data` |
| 4 | `spear.get_wec_data(ticket_ids=ticket_data["Ticket ID"])` | `wec-data.csv` | `WEC_DATA_RID` | `wec-data` |
| 5 | `spear.get_activity_data(ticket_ids=ticket_data["Ticket ID"])` | `activity-data.csv` | `ACTIVITY_DATA_RID` | `activity-data` |
| 6 | `spear.get_tech_eval_data(ticket_ids=ticket_data["Ticket ID"])` | `tech-eval-data.csv` | `TECH_EVAL_DATA_RID` | `tech-eval-data` |
| 7 | `spear.get_tech_eval_status_update_data(ticket_ids=ticket_data["Ticket ID"])` | `tech-eval-status-update-data.csv` | `TECH_EVAL_STATUS_UPDATE_DATA_RID` | `tech-eval-status-update-data` |
| 8 | `spear.get_implementation_data(ticket_ids=ticket_data["Ticket ID"])` | `implementation-data.csv` | `IMPLEMENTATION_DATA_RID` | `implementation-data` |
| 9 | `spear.get_implementation_status_update_data(ticket_ids=ticket_data["Ticket ID"])` | `implementation-status-update-data.csv` | `IMPLEMENTATION_STATUS_UPDATE_DATA_RID` | `implementation-status-update-data` |
| 10 | AAR source workflow / `spear.get_aar_data(...)` if implemented | `aar-data.csv` | `AAR_DATA_RID` if Scarab-owned | `aar-data` |

Conceptually:

```text
SPEAR dashboard + ticket detail pages + activity/status/AAR endpoints or tables
        ↓
SpearClient extraction methods
        ↓
Pandas DataFrames
        ↓
CSV upload through VantageClient
        ↓
Vantage datasets
```

### 5.1 Current `gl-issues` Transform Consumption Notes

The downstream Vantage transform currently consumes ten source datasets and creates the GitLab-ready `gl-issues` table.

Recent transform updates added:

| Output column | Source dataset | Purpose |
|---|---|---|
| `tech_eval_updates_json` | `tech-eval-status-update-data` | Preserves full technical evaluation status update history as a JSON array. |
| `implementation_updates_json` | `implementation-status-update-data` | Preserves full implementation status update history as a JSON array. |
| `aar_scheduled_date` and six additional `aar_*` columns | `aar-data` | Carries structured AAR data into `gl-issues`. |

The two status update JSON arrays are sorted deterministically with `sort_array(asc=True)` over `struct(date, status, notes)`. This guarantees ascending date-level order. Same-day records are sorted deterministically by status and notes, but that is not true source chronology because the source schemas do not yet include a sequence, timestamp, or source row order field.

The new status-history and AAR columns are excluded from `content_hash` in the current transform state. This avoids unnecessary Heather/GitLab update churn until Heather is updated to render these fields.

---

## 6. `ticket-data` Mapping

### 6.1 Purpose

`ticket-data` is the master ticket table. It should remain focused on one-row-per-ticket fields and should not be used for child tables such as comments, stakeholders, status updates, interviews, implementation team rows, or AAR note rows.

### 6.2 Current source behavior

`get_ticket_data()` performs two extraction steps:

1. Reads the dashboard page.
2. Finds the JavaScript data blob using the pattern `let\s+data\s*=\s*(.+?};)`.
3. The regex is non-greedy and stops at the first `};`, which is a known fragility if the dashboard JavaScript structure changes.
4. Reads `Tables["tickets"]` into a dataframe.
5. Opens each ticket detail page.
6. Adds detail-page fields only when their label exists in `TICKET_DATA_COLUMN_NAMES`.
7. Adds attachment filename and URL fields.

### 6.3 Dashboard fields currently seen

The latest dashboard ticket columns seen are:

```text
Ticket ID
Customer
Category
Status
Submitted
Updated
Resolved
```

### 6.4 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Customer', T.StringType(), False),
    T.StructField('Category', T.StringType(), False),
    T.StructField('Status', T.StringType(), False),
    T.StructField('Submitted', T.TimestampType(), False),
    T.StructField('Updated', T.TimestampType(), False),
    T.StructField('Resolved', T.StringType(), False),
    T.StructField('Data_Type_Description', T.StringType(), False),
    T.StructField('Requested_Completion_Date', T.DateType(), False),
    T.StructField('Created_By', T.StringType(), False),
    T.StructField('Customer1', T.StringType(), False),
    T.StructField('Unit__Organization', T.StringType(), False),
    T.StructField('Location', T.StringType(), False),
    T.StructField('Stage', T.StringType(), False),
    T.StructField('Mission_Priority', T.StringType(), False),
    T.StructField('System__Topic', T.StringType(), False),
    T.StructField('Category1', T.StringType(), False),
    T.StructField('Connection_Type', T.StringType(), False),
    T.StructField('Data_Classification', T.StringType(), False),
    T.StructField('Connection_Direction', T.StringType(), False),
    T.StructField('Purpose_for_Connection', T.StringType(), False),
    T.StructField('Intake_Meeting_Availability', T.StringType(), False),
    T.StructField('Attachments', T.StringType(), False),
    T.StructField('Attachment_URLs', T.StringType(), False),
    T.StructField('Resolution', T.StringType(), False)
])
```

### 6.5 Current source-to-target mapping

| SPEAR/source label | Dataframe column before Vantage normalization | Vantage column | Source area | Notes |
|---|---|---|---|---|
| `Ticket ID` | `Ticket ID` | `Ticket_ID` | Dashboard | Primary ticket identifier. |
| `Customer` | `Customer` | `Customer` | Dashboard | Dashboard customer value. |
| `Category` | `Category` | `Category` | Dashboard | Dashboard category value. |
| `Status` | `Status` | `Status` | Dashboard | Current ticket status. |
| `Submitted` | `Submitted` | `Submitted` | Dashboard | Timestamp in Vantage. |
| `Updated` | `Updated` | `Updated` | Dashboard | Timestamp in Vantage. |
| `Resolved` | `Resolved` | `Resolved` | Dashboard | String in current schema. |
| `Data Type Description` | `Data Type Description` | `Data_Type_Description` | Ticket detail page | Captured when label matches constants. |
| `Requested Completion Date` | `Requested Completion Date` | `Requested_Completion_Date` | Ticket detail page | Date in Vantage. |
| `Created By` | `Created By` | `Created_By` | Ticket detail page | Captured from detail page. |
| `Customer` | `Customer` | `Customer1` | Ticket detail page | Duplicate dashboard/detail name causes normalized duplicate column. |
| `Unit / Organization` | `Unit / Organization` | `Unit__Organization` | Ticket detail page | Slash normalized to double underscore in Vantage. |
| `Location` | `Location` | `Location` | Ticket detail page | Captured from detail page. |
| `Stage` | `Stage` | `Stage` | Ticket detail page | Captured from detail page. |
| `Mission Priority` | `Mission Priority` | `Mission_Priority` | Ticket detail page | Captured from detail page. |
| `System / Topic` | `System / Topic` | `System__Topic` | Ticket detail page | Slash normalized to double underscore in Vantage. |
| `Category` | `Category` | `Category1` | Ticket detail page | Duplicate dashboard/detail name causes normalized duplicate column. |
| `Connection Type` | `Connection Type` | `Connection_Type` | Ticket detail page | Captured from detail page. |
| `Data Classification` | `Data Classification` | `Data_Classification` | Ticket detail page | Captured from detail page. |
| `Connection Direction` | `Connection Direction` | `Connection_Direction` | Ticket detail page | Now included in the active Vantage schema. |
| `Purpose for Connection` | `Purpose for Connection` | `Purpose_for_Connection` | Ticket detail page | Scraper removes bullets, quad-hyphens, and extra whitespace. |
| `Intake Meeting Availability` | `Intake Meeting Availability` | `Intake_Meeting_Availability` | Ticket detail page | Scraper extracts date/time patterns and joins them into one string. |
| File links under `div.fileList.mb-4` | `Attachments` | `Attachments` | Ticket detail page | Comma-separated filenames. |
| File links under `div.fileList.mb-4` | `Attachment URLs` | `Attachment_URLs` | Ticket detail page | Comma-separated URLs. |
| `RESOLUTION` | `Resolution` | `Resolution` | Ticket detail page | Scraper renames `RESOLUTION` to `Resolution`. |

### 6.6 Known duplicate columns

The current schema includes:

```text
Customer
Customer1
Category
Category1
```

This likely happens because `Customer` and `Category` are present in both the dashboard table and the ticket detail page. After concatenation, Vantage/PySpark normalization creates duplicate-safe names.

This document does not recommend changing those duplicates yet. They should be reviewed separately to avoid breaking downstream consumers.

---

## 7. `tag-data` Mapping

### 7.1 Purpose

`tag-data` stores tag/system values associated with each ticket.

### 7.2 Current source behavior

`get_tag_data(ticket_ids)`:

1. Receives the `Ticket ID` series from `ticket-data`.
2. Opens each ticket detail page.
3. Looks for `table id="systems-table"`.
4. Reads the first cell from each row.
5. Joins all values into a comma-separated string.

### 7.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Tags', T.StringType(), False)
])
```

### 7.4 Current source-to-target mapping

| Source | Dataframe column | Vantage column | Notes |
|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Parent ticket identifier. |
| First `<td>` of each row in `systems-table` | `Tags` | `Tags` | Values are comma-separated in one row per ticket. |

### 7.5 Naming note

`constants.py` previously had:

```python
TAG_DATA_COLUMN_NAMES = ["Ticket ID", "Tag"]
```

The current implementation and Vantage schema use:

```text
Tags
```

Recommended future cleanup:

```text
Decide whether this dataset should remain one row per ticket with `Tags`,
or become one row per ticket/tag pair with `Tag`.
```

No change is recommended in this document because the current Vantage table expects `Tags`.

---

## 8. `contact-data` Mapping

### 8.1 Purpose

`contact-data` stores contacts related to a ticket. It is separate from `ticket-data` because one ticket can have multiple contacts/stakeholders.

### 8.2 Current source behavior

`get_contact_data(ticket_ids)` extracts two contact types:

1. `Alternate Point of Contact`
2. `Additional Stakeholders`

For `Alternate Point of Contact`, the scraper finds the matching label and reads following sibling divs until labels stop.

For `Additional Stakeholders`, the scraper finds the stakeholder table and maps recognized table headers using `CONTACT_DATA_COLUMN_NAMES`.

### 8.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Type', T.StringType(), False),
    T.StructField('Name', T.StringType(), False),
    T.StructField('Title', T.StringType(), False),
    T.StructField('Organization', T.StringType(), False),
    T.StructField('Email', T.StringType(), False),
    T.StructField('Phone', T.StringType(), False)
])
```

### 8.4 Current source-to-target mapping

| SPEAR/source label or table header | Dataframe column | Vantage column | Notes |
|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Parent ticket identifier. Current schema uses `IntegerType`. |
| Scraper-generated contact type | `Type` | `Type` | Either `Alternate Point of Contact` or `Stakeholder`. |
| `Stakeholder Name` or `Name` | `Name` | `Name` | Header mapping collapses both to `Name`. |
| `Title/Rank` or `Title` | `Title` | `Title` | `Title/Rank` is cleaned to remove `/Rank`. |
| `Organization` | `Organization` | `Organization` | Contact organization. |
| `Email` | `Email` | `Email` | Contact email. |
| `Phone` | `Phone` | `Phone` | Phone punctuation and spaces are stripped. |

### 8.5 Coverage status

The latest field coverage report found contact table headers:

```text
Email
Organization
Stakeholder Name
Title
```

The report found no currently unrecognized contact table headers for the `Additional Stakeholders` table.

Known coverage gap: the field coverage report also showed uppercase `NAME`, `EMAIL`, and `PHONE` labels. Those likely belong to the `Alternate Point of Contact` block and do not currently map directly in `CONTACT_DATA_COLUMN_NAMES`. This is unverified and should stay on the todo list until the Alternate POC extraction is confirmed against live tickets.

---

## 9. `wec-data` Mapping

### 9.1 Purpose

`wec-data` stores WEC/intake evaluation fields. It should remain separate from `ticket-data` because these fields represent a specific workflow section.

### 9.2 Current source behavior

`get_wec_data(ticket_ids)`:

1. Receives the `Ticket ID` series from `ticket-data`.
2. Opens each ticket detail page.
3. Loops over `div[class*='col-']` values.
4. Reads the label.
5. Normalizes labels that start with `Date Contacted to Schedule Intake` to `Date Contacted to Schedule Intake Evaluation`.
6. Keeps only labels in `WEC_DATA_COLUMN_NAMES`.
7. Replaces `---` and `N/A` with an empty string.
8. Returns a dataframe using `WEC_DATA_COLUMN_NAMES`.

### 9.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Date_Contacted_to_Schedule_Intake_Evaluation', T.DateType(), False),
    T.StructField('Meeting_Notes', T.StringType(), False),
    T.StructField('Related_to_NGC2', T.StringType(), False),
    T.StructField('Success_Definition', T.StringType(), False),
    T.StructField('Attempted_Solutions', T.StringType(), False),
    T.StructField('Roadblocks', T.StringType(), False)
])
```

### 9.4 Current source-to-target mapping

| SPEAR/source label | Dataframe column | Vantage column | Notes |
|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Parent ticket identifier. |
| `Date Contacted to Schedule Intake Evaluation` | `Date Contacted to Schedule Intake Evaluation` | `Date_Contacted_to_Schedule_Intake_Evaluation` | Prefix-normalized by scraper. |
| `Meeting Notes` | `Meeting Notes` | `Meeting_Notes` | WEC note field. |
| `Related to NGC2?` | `Related to NGC2?` | `Related_to_NGC2` | Question mark removed in Vantage schema. |
| `Success Definition` | `Success Definition` | `Success_Definition` | WEC field. |
| `Attempted Solutions` | `Attempted Solutions` | `Attempted_Solutions` | WEC field. |
| `Roadblocks` | `Roadblocks` | `Roadblocks` | WEC field. |

---

## 10. `activity-data` Mapping

### 10.1 Purpose

`activity-data` stores ticket activity/comments. It is separate from `ticket-data` because a ticket can have many activity/comment records.

### 10.2 Current source behavior

`get_activity_data(ticket_ids)`:

1. Receives the `Ticket ID` series from `ticket-data`.
2. Posts each ticket ID to `SPEAR_ACTIVITY_ENDPOINT`.
3. Parses returned HTML cards matching `div.card.mb-2`.
4. Reads author/date from the card header.
5. Reads comment type and comment text from the card body.
6. Returns columns reindexed to `ACTIVITY_DATA_COLUMN_NAMES`.

Operational note: the method name in the published Scarab package must match the method name used by automation. If the app package is changed but not republished, the automation pipeline may still run an older client implementation.

### 10.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Comment_ID', T.IntegerType(), False),
    T.StructField('Date', T.StringType(), False),
    T.StructField('Comment_Type', T.StringType(), False),
    T.StructField('Author', T.StringType(), False),
    T.StructField('Comment', T.StringType(), False)
])
```

### 10.4 Current source-to-target mapping

| Source value | Dataframe column | Vantage column | Notes |
|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Parent ticket identifier. |
| Enumerated local counter | `Comment ID` | `Comment_ID` | Generated by scraper using `enumerate`. |
| Card header second string | `Date` | `Date` | Stored as string in current schema. |
| First `<strong>` value in card body | `Comment Type` | `Comment_Type` | Comment/activity type. |
| Card header first string | `Author` | `Author` | Activity author. |
| Card body text/trailer | `Comment` | `Comment` | Main comment content. |

---

## 11. `tech-eval-data` Mapping

### 11.1 Purpose

`tech-eval-data` stores the one-row-per-ticket technical evaluation / Finish Cell summary fields. It should remain separate from `ticket-data` because these fields belong to a specific evaluation workflow area and may not exist for every ticket.

### 11.2 Current source behavior

Expected current behavior:

1. Receives the `Ticket ID` series from `ticket-data`.
2. Opens each ticket detail page.
3. Extracts technical evaluation / Finish Cell fields from the ticket detail page.
4. Keeps only the fields that belong to the technical evaluation schema.
5. Returns a dataframe using the tech evaluation column names.

### 11.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Lead_Point_of_Contact_for_Finish_Cell', T.StringType(), False),
    T.StructField('Technical_Requirements', T.StringType(), False),
    T.StructField('Policies_Involved', T.StringType(), False),
    T.StructField('Decision', T.StringType(), False)
])
```

### 11.4 Current source-to-target mapping

| SPEAR/source label | Dataframe column | Vantage column | Notes |
|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Parent ticket identifier. |
| `Lead Point of Contact for Finish Cell` | `Lead Point of Contact for Finish Cell` | `Lead_Point_of_Contact_for_Finish_Cell` | Tech evaluation / Finish Cell POC. |
| `Technical Requirements` | `Technical Requirements` | `Technical_Requirements` | Technical requirements captured during evaluation. |
| `Policies Involved` | `Policies Involved` | `Policies_Involved` | Policy references or constraints involved in the technical evaluation. |
| `Decision` | `Decision` | `Decision` | Evaluation decision. |

---

## 12. `tech-eval-status-update-data` Mapping

### 12.1 Purpose

`tech-eval-status-update-data` stores status update history for the technical evaluation workflow. It is separate from `tech-eval-data` because one ticket can have multiple technical evaluation status updates.

### 12.2 Current source behavior

Expected current behavior:

1. Receives the `Ticket ID` series from `ticket-data`.
2. Opens each ticket detail page.
3. Reads the technical evaluation status updates table.
4. Extracts `Date`, `Status`, and `Notes`.
5. Skips UI-only `Actions` columns.
6. Returns one row per status update.

Likely source table from field coverage:

```text
status-updates-table
```

### 12.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Date', T.DateType(), False),
    T.StructField('Status', T.StringType(), False),
    T.StructField('Notes', T.StringType(), False)
])
```

### 12.4 Current source-to-target mapping

| SPEAR/source value | Dataframe column | Vantage column | Notes |
|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Parent ticket identifier. |
| `Date` | `Date` | `Date` | Status update date. Vantage expects `DateType`. |
| `Status` | `Status` | `Status` | Status value at that update point. |
| `Notes` | `Notes` | `Notes` | Status update notes. |
| `Actions` | Not uploaded | Not uploaded | UI-only column; should be skipped. |

---

## 13. `implementation-data` Mapping

### 13.1 Purpose

`implementation-data` stores one-row-per-ticket implementation summary fields. It should remain separate from `ticket-data` because these fields describe the solution/implementation workflow, not the original ticket request.

### 13.2 Current source behavior

Expected current behavior:

1. Receives the `Ticket ID` series from `ticket-data`.
2. Opens each ticket detail page.
3. Extracts implementation fields from the ticket detail page.
4. Keeps only the fields that belong to the implementation schema.
5. Returns a dataframe using the implementation column names.

### 13.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Lead_Point_of_Contact_for_Finish_Cell', T.StringType(), False),
    T.StructField('Solution_Implemented', T.StringType(), False),
    T.StructField('Additional_Solution_Documentation', T.StringType(), False),
    T.StructField('Obstacles', T.StringType(), False),
    T.StructField('Lessons_Learned', T.StringType(), False),
    T.StructField('Applicability_of_Solution', T.StringType(), False)
])
```

### 13.4 Current source-to-target mapping

| SPEAR/source label | Dataframe column | Vantage column | Notes |
|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Parent ticket identifier. |
| `Lead Point of Contact for Finish Cell` | `Lead Point of Contact for Finish Cell` | `Lead_Point_of_Contact_for_Finish_Cell` | Implementation / Finish Cell POC. |
| `Solution Implemented` | `Solution Implemented` | `Solution_Implemented` | Summary of the implemented solution. |
| `Additional Solution Documentation` | `Additional Solution Documentation` | `Additional_Solution_Documentation` | Additional links, references, or notes. |
| `Obstacles` | `Obstacles` | `Obstacles` | Obstacles encountered during implementation. |
| `Lessons Learned` | `Lessons Learned` | `Lessons_Learned` | Lessons learned from implementation. |
| `Applicability of Solution` | `Applicability of Solution` | `Applicability_of_Solution` | Where/how the solution applies. |

---

## 14. `implementation-status-update-data` Mapping

### 14.1 Purpose

`implementation-status-update-data` stores status update history for the implementation workflow. It is separate from `implementation-data` because one ticket can have multiple implementation status updates.

### 14.2 Current source behavior

Expected current behavior:

1. Receives the `Ticket ID` series from `ticket-data`.
2. Opens each ticket detail page.
3. Reads the implementation status updates table.
4. Extracts `Date`, `Status`, and `Notes`.
5. Skips UI-only `Actions` columns.
6. Returns one row per implementation status update.

Likely source table from field coverage:

```text
implementation-status-updates-table
```

### 14.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Date', T.DateType(), False),
    T.StructField('Status', T.StringType(), False),
    T.StructField('Notes', T.StringType(), False)
])
```

### 14.4 Current source-to-target mapping

| SPEAR/source value | Dataframe column | Vantage column | Notes |
|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Parent ticket identifier. |
| `Date` | `Date` | `Date` | Status update date. Vantage expects `DateType`. |
| `Status` | `Status` | `Status` | Status value at that update point. |
| `Notes` | `Notes` | `Notes` | Implementation status update notes. |
| `Actions` | Not uploaded | Not uploaded | UI-only column; should be skipped. |

---

## 15. `aar-data` Mapping

### 15.1 Purpose

`aar-data` stores After Action Report fields associated with a ticket. It is a one-row-per-ticket source table used by the `gl-issues` transform to append structured AAR columns to the GitLab-ready output.

### 15.2 Current source behavior

The current Vantage transform validates `aar-data` as one row per `Ticket_ID` before joining it into `gl-issues`. The join is a left join so tickets without AAR data remain in the output with empty AAR strings.

### 15.3 Current Vantage schema

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Date_After_Action_Report_AAR_Scheduled', T.DateType(), False),
    T.StructField('Policy_and_Process_Improvements', T.StringType(), False),
    T.StructField('Skills_Needed', T.StringType(), False),
    T.StructField('Roles_Needed', T.StringType(), False),
    T.StructField('AIML_Potential', T.StringType(), False),
    T.StructField('Strategic_Alignment', T.StringType(), False),
    T.StructField('Notes', T.StringType(), False)
])
```

### 15.4 Current source-to-target mapping

| SPEAR/source label | Dataframe column | Vantage column | `gl-issues` output column | Notes |
|---|---|---|---|---|
| Ticket ID passed from `ticket-data` | `Ticket ID` | `Ticket_ID` | Join key only | Parent ticket identifier. |
| `Date After Action Report AAR Scheduled` | `Date After Action Report AAR Scheduled` | `Date_After_Action_Report_AAR_Scheduled` | `aar_scheduled_date` | Transform formats as `yyyy-MM-dd`; empty string when absent. |
| `Policy and Process Improvements` | `Policy and Process Improvements` | `Policy_and_Process_Improvements` | `aar_policy_process_improvements` | Empty string when absent. |
| `Skills Needed` | `Skills Needed` | `Skills_Needed` | `aar_skills_needed` | Empty string when absent. |
| `Roles Needed` | `Roles Needed` | `Roles_Needed` | `aar_roles_needed` | Empty string when absent. |
| `AIML Potential` | `AIML Potential` | `AIML_Potential` | `aar_aiml_potential` | Empty string when absent. |
| `Strategic Alignment` | `Strategic Alignment` | `Strategic_Alignment` | `aar_strategic_alignment` | Empty string when absent. |
| `Notes` | `Notes` | `Notes` | `aar_notes` | Empty string when absent. |

### 15.5 Transform notes

The `gl-issues` transform appends the seven AAR output columns as columns 40-46. The original 39 columns remain unchanged in name, type, and order.

`INCLUDE_AAR_IN_CONTENT_HASH` currently defaults to `False`, so AAR fields are not part of `content_hash`. This is the safe rollout state because Heather has not yet been updated to render AAR fields in GitLab. When Heather rendering is ready, the transform switch can be changed to `True` as part of a coordinated deployment.

---

## 16. Active Schema Summary

This section is the quick reference for all active Vantage schemas.

### 16.1 `wec-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Date_Contacted_to_Schedule_Intake_Evaluation', T.DateType(), False),
    T.StructField('Meeting_Notes', T.StringType(), False),
    T.StructField('Related_to_NGC2', T.StringType(), False),
    T.StructField('Success_Definition', T.StringType(), False),
    T.StructField('Attempted_Solutions', T.StringType(), False),
    T.StructField('Roadblocks', T.StringType(), False)
])
```

### 16.2 `ticket-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Customer', T.StringType(), False),
    T.StructField('Category', T.StringType(), False),
    T.StructField('Status', T.StringType(), False),
    T.StructField('Submitted', T.TimestampType(), False),
    T.StructField('Updated', T.TimestampType(), False),
    T.StructField('Resolved', T.StringType(), False),
    T.StructField('Data_Type_Description', T.StringType(), False),
    T.StructField('Requested_Completion_Date', T.DateType(), False),
    T.StructField('Created_By', T.StringType(), False),
    T.StructField('Customer1', T.StringType(), False),
    T.StructField('Unit__Organization', T.StringType(), False),
    T.StructField('Location', T.StringType(), False),
    T.StructField('Stage', T.StringType(), False),
    T.StructField('Mission_Priority', T.StringType(), False),
    T.StructField('System__Topic', T.StringType(), False),
    T.StructField('Category1', T.StringType(), False),
    T.StructField('Connection_Type', T.StringType(), False),
    T.StructField('Data_Classification', T.StringType(), False),
    T.StructField('Connection_Direction', T.StringType(), False),
    T.StructField('Purpose_for_Connection', T.StringType(), False),
    T.StructField('Intake_Meeting_Availability', T.StringType(), False),
    T.StructField('Attachments', T.StringType(), False),
    T.StructField('Attachment_URLs', T.StringType(), False),
    T.StructField('Resolution', T.StringType(), False)
])
```

### 16.3 `tech-eval-status-update-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Date', T.DateType(), False),
    T.StructField('Status', T.StringType(), False),
    T.StructField('Notes', T.StringType(), False)
])
```

### 16.4 `tech-eval-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Lead_Point_of_Contact_for_Finish_Cell', T.StringType(), False),
    T.StructField('Technical_Requirements', T.StringType(), False),
    T.StructField('Policies_Involved', T.StringType(), False),
    T.StructField('Decision', T.StringType(), False)
])
```

### 16.5 `tag-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Tags', T.StringType(), False)
])
```

### 16.6 `implementation-status-update-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Date', T.DateType(), False),
    T.StructField('Status', T.StringType(), False),
    T.StructField('Notes', T.StringType(), False)
])
```

### 16.7 `implementation-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Lead_Point_of_Contact_for_Finish_Cell', T.StringType(), False),
    T.StructField('Solution_Implemented', T.StringType(), False),
    T.StructField('Additional_Solution_Documentation', T.StringType(), False),
    T.StructField('Obstacles', T.StringType(), False),
    T.StructField('Lessons_Learned', T.StringType(), False),
    T.StructField('Applicability_of_Solution', T.StringType(), False)
])
```

### 16.8 `contact-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Type', T.StringType(), False),
    T.StructField('Name', T.StringType(), False),
    T.StructField('Title', T.StringType(), False),
    T.StructField('Organization', T.StringType(), False),
    T.StructField('Email', T.StringType(), False),
    T.StructField('Phone', T.StringType(), False)
])
```

### 16.9 `activity-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Comment_ID', T.IntegerType(), False),
    T.StructField('Date', T.StringType(), False),
    T.StructField('Comment_Type', T.StringType(), False),
    T.StructField('Author', T.StringType(), False),
    T.StructField('Comment', T.StringType(), False)
])
```

### 16.10 `aar-data`

```python
T.StructType([
    T.StructField('Ticket_ID', T.IntegerType(), False),
    T.StructField('Date_After_Action_Report_AAR_Scheduled', T.DateType(), False),
    T.StructField('Policy_and_Process_Improvements', T.StringType(), False),
    T.StructField('Skills_Needed', T.StringType(), False),
    T.StructField('Roles_Needed', T.StringType(), False),
    T.StructField('AIML_Potential', T.StringType(), False),
    T.StructField('Strategic_Alignment', T.StringType(), False),
    T.StructField('Notes', T.StringType(), False)
])
```

---

## 17. Tables Visible But Not Clearly Captured By Current Active Schemas

The field coverage report found the following recurring ticket-page tables.

Notes for future scraping:

```text
currentPrioritiesTable appears to be a shared dashboard-style widget repeated on each ticket page, not unique per-ticket detail data.
Actions columns are UI button/action columns and should be skipped if these tables are scraped later.
```

| Table id | Headers | Current status |
|---|---|---|
| `currentPrioritiesTable` | `Ranking`, `Ticket ID`, `Mission Priority`, `Title`, `Organization`, `Phase`, `Stage`, `Time in Stage` | Not currently mapped to an active Vantage detail table. Appears to be a shared dashboard-style widget repeated on each ticket page, not unique per-ticket data. |
| `ticket-associations-table` | `Ticket ID`, `Mission Priority`, `Title`, `Phase`, `Stage`, `Actions` | Not currently mapped to an active Vantage table. |
| `intake-interviews-table` | `Interview Type`, `Date`, `Time`, `Time Zone` | Not present in the current active Vantage schema export. |
| `tech-interviews-table` | `Meeting Type`, `Date`, `Time`, `Time Zone`, `Actions` | Not present in the current active Vantage schema export. |
| `status-updates-table` | `Date`, `Status`, `Notes`, `Actions` | Covered by `tech-eval-status-update-data` when used for technical evaluation status updates. `Actions` should be skipped. |
| `implementation-team-table` | `Team Member Name`, `Organization`, `LCAT`, `Actions` | Not present in the current active Vantage schema export. |
| `implementation-status-updates-table` | `Date`, `Status`, `Notes`, `Actions` | Covered by `implementation-status-update-data`. `Actions` should be skipped. |
| `aar-notes-table` | `Date`, `Notes`, `Actions` | Related AAR coverage now exists through active `aar-data`; confirm whether this UI table is the same source before changing scraper logic. `Actions` should be skipped. |

---

## 18. Current Notable Schema Changes From Previous Version

The important updates from the previous mapping document are:

1. `ticket-data` includes `Connection_Direction` as an active schema field, placed between `Data_Classification` and `Purpose_for_Connection`.
2. `contact-data.Ticket_ID` is documented as `IntegerType`, matching the current Vantage schema.
3. `tech-eval-data` is an active Vantage dataset.
4. `tech-eval-status-update-data` is an active Vantage dataset and is now preserved in `gl-issues.tech_eval_updates_json`.
5. `implementation-data` is an active Vantage dataset.
6. `implementation-status-update-data` is an active Vantage dataset and is now preserved in `gl-issues.implementation_updates_json`.
7. `aar-data` is now an active Vantage source dataset and is appended to `gl-issues` as seven AAR columns.
8. `gl-issues` now has 46 columns total: 37 original columns, 2 status-history JSON columns, and 7 AAR columns.
9. The status-history JSON arrays are deterministically sorted by date, with same-day tiebreaks by status and notes because no source sequence/timestamp exists yet.
10. Intake interviews, tech interviews, and implementation team rows are still not present in the current active Vantage schema export.


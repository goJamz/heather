# Heather automation

This project is the GitLab CI wrapper for Heather.

The manual pipeline installs Heather from the `adoc/heather/app` package
registry, waits until `gl-issues` is newer than the 10 upstream Scarab datasets,
then runs the Heather GitLab sync.

## Manual pipeline

Run the pipeline manually from GitLab. The job only runs when
`CI_PIPELINE_SOURCE` is `web`.

The job runs:

```sh
python -u main.py
```

## Required variables

Set these in the `adoc/heather/automation` GitLab project:

- `GITLAB_API_ENDPOINT`
- `GITLAB_API_TOKEN`
- `GITLAB_PROJECT_ID`
- `FOUNDRY_HOSTNAME` or `VANTAGE_HOSTNAME`
- `FOUNDRY_TOKEN` or `VANTAGE_TOKEN`

## Optional variables

- `GITLAB_EPIC_ID`
- `FOUNDRY_BRANCH_ID`
- `FOUNDRY_VERIFY`
- `HEATHER_ENABLE_AI_COMMENT_DIGEST`
- `HEATHER_FRESHNESS_POLL_SECONDS`
- `HEATHER_FRESHNESS_TIMEOUT_SECONDS`

`CURL_CA_BUNDLE` is set by the CI job.

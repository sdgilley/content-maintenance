# Azure AI Docs Content Maintenance - Automation

This directory contains the automation infrastructure for monitoring Azure code samples and their impact on documentation.

## Overview

The automation system provides four main workflows:

1. **Daily PR Monitor** - Automatically reviews and approves safe PRs in code repositories
2. **Daily Merge Docs** - Creates documentation update PRs when code changes affect docs
3. **Weekly Snippet Scanner** - Scans documentation for code references and updates CODEOWNERS files
4. **Monthly Report** - Generates statistics and health reports

## Directory Structure

```
automation/
├── core/                      # Core infrastructure modules
│   ├── config.py             # Configuration management
│   ├── github_client.py      # GitHub API wrapper with retry logic
│   ├── git_operations.py     # Git operations for multi-repo management
│   └── reporter.py           # Report generation and file saving
├── workflows/                 # Workflow orchestrators
│   ├── daily_pr_monitor.py   # Daily PR review automation
│   ├── merge_docs.py         # Daily merge documentation updates
│   ├── weekly_scanner.py     # Weekly snippet scanning
│   └── monthly_report.py     # Monthly statistics
├── templates/                 # Report templates (HTML)
│   ├── daily_report.html
│   ├── weekly_report.html
│   └── monthly_report.html
└── reports/                   # Generated Markdown reports (gitignored)
    ├── daily-report-YYYY-MM-DD.md
    ├── weekly-report-YYYY-MM-DD.md
    └── monthly-report-YYYY-MM-DD.md
```

## Setup

### Prerequisites

1. **GitHub Personal Access Token** with the following permissions:
   - `repo` (full repository access)
   - `workflow` (for triggering workflows)

2. **SMTP Email Account** (OPTIONAL) - Only required if you want email notifications
   - Gmail, Office 365, or other SMTP provider
   - Reports are always saved to files, email is optional

### Environment Variables

The following environment variables must be configured in GitHub Actions Secrets:

```bash
# GitHub Authentication (REQUIRED)
GH_ACCESS_TOKEN=ghp_your_token_here

# Email Configuration (OPTIONAL - set EMAIL_ENABLED=true to enable)
EMAIL_ENABLED=false              # Set to true to enable email notifications
SMTP_SERVER=smtp.gmail.com       # Only needed if EMAIL_ENABLED=true
SMTP_PORT=587                    # Only needed if EMAIL_ENABLED=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_EMAIL=your-email@gmail.com
NOTIFICATION_EMAIL=recipient@example.com

# Reports Configuration (OPTIONAL)
REPORTS_DIRECTORY=automation/reports  # Default location for saved reports

# Other Configuration
DRY_RUN=false                    # Set to true for testing
AUTO_APPROVE_ENABLED=true        # Enable/disable PR auto-approval
```

### GitHub Secrets Setup

1. Go to your repository Settings → Secrets and variables → Actions
2. Add the following **required** secrets:
   - `GH_ACCESS_TOKEN`

3. Add the following **optional** secrets (only if you want email notifications):
   - `EMAIL_ENABLED` (set to `true`)
   - `SMTP_SERVER`
   - `SMTP_PORT`
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`
   - `SMTP_EMAIL`
   - `NOTIFICATION_EMAIL`

## Workflows

### Daily PR Monitor

**Schedule:** Monday-Friday at 7:00 AM EST (12:00 UTC)

**What it does:**
1. Monitors PRs across **3 code repositories**:
   - **Azure/azureml-examples** - Azure Machine Learning examples
   - **microsoft-foundry/foundry-samples** - Azure AI Foundry samples
   - **Azure-Samples/azureai-samples** - Azure AI samples
2. Finds PRs requesting review from the AI Platform Docs team
3. Analyzes each PR for documentation impact
4. Auto-approves PRs that meet safety criteria:
   - No deleted files referenced in documentation
   - No renamed files referenced in documentation
   - No deleted cells/snippets in modified files that are referenced in docs
5. Flags unsafe PRs for manual review
6. Saves report to `automation/reports/` (email optional)

**Manual trigger:**
```bash
# Via GitHub Actions UI
Actions → Daily PR Monitor → Run workflow
# Select dry_run: true for testing
```

**Safety Criteria:**
PRs are only auto-approved if ALL of the following are true:
- No deleted files are referenced in documentation
- No renamed files are referenced in documentation
- No deleted notebook cells/code snippets in modified files
- PR is mergeable (no conflicts)

### Daily Merge Documentation

**Schedule:** Daily at 9:00 AM EST (14:00 UTC)

**What it does:**
1. Analyzes recently merged PRs in code repositories (last 2 days)
2. Identifies documentation files that reference changed code
3. Creates PRs to update `update-code` metadata in affected docs
4. Tracks processed PRs to avoid duplicate updates
5. Commits tracking data back to the repository

**Manual trigger:**
```bash
# Via GitHub Actions UI
Actions → Daily Merge Documentation → Run workflow
# Options: dry_run, days (lookback period), ignore_tracking
```

**Tracking:**
- Processed PRs are recorded in `outputs/merge-tracking.json`
- Uses 2-day lookback to ensure overlap between runs
- Already-processed PRs are automatically skipped
- Use `--ignore-tracking` to reprocess all PRs

**Local usage:**
```bash
# Default: 2 days lookback, create PR
python -m automation.workflows.merge_docs

# Preview without creating PR
python -m automation.workflows.merge_docs --dry-run

# Custom lookback period
python -m automation.workflows.merge_docs --days 3

# Ignore tracking (reprocess all)
python -m automation.workflows.merge_docs --ignore-tracking
```

### Weekly Snippet Scanner

**Schedule:** Every Monday at 6:00 AM EST (11:00 UTC)

**What it does:**
1. Scans azure-ai-docs repository for code snippets
2. Generates CODEOWNERS files for each code repository
3. Creates PRs to update CODEOWNERS in code repositories
4. Commits output files to maintenance repository
5. Sends email report with results

**Manual trigger:**
```bash
# Via GitHub Actions UI
Actions → Weekly Snippet Scanner → Run workflow
# Select dry_run: true for testing
```

**Output files:**
- `outputs/refs-found.csv` - All code references found in documentation
- `outputs/CODEOWNERS-*.txt` - CODEOWNERS content for each repository
- `outputs/code-counts-*.csv` - Statistics on code blocks

### Monthly Maintenance Report

**Schedule:** 1st of each month at 5:00 AM EST (10:00 UTC)

**What it does:**
1. Collects statistics from the past month
2. Checks GitHub API rate limits
3. Warns about expiring tokens
4. Sends monthly summary email

**Manual trigger:**
```bash
# Via GitHub Actions UI
Actions → Monthly Maintenance Report → Run workflow
```

## Testing with Dry-Run Mode

All workflows support dry-run mode for safe testing:

```bash
# Set DRY_RUN environment variable
export DRY_RUN=true

# Or use manual trigger with dry_run checkbox
```

**In dry-run mode:**
- ✅ All analysis and validation runs normally
- ✅ Reports are generated showing what *would* happen
- ✅ All actions are logged
- ❌ No PR approvals are made
- ❌ No commits are pushed
- ❌ No PRs are created

## Local Development

### Running Workflows Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export GH_ACCESS_TOKEN=your_token

# Optional: Set email configuration (only if you want email notifications)
export EMAIL_ENABLED=true
export SMTP_USERNAME=your_email
export SMTP_PASSWORD=your_password
export NOTIFICATION_EMAIL=recipient@example.com

# Run daily workflow (reports saved to automation/reports/)
python -m automation.workflows.daily_pr_monitor --dry-run

# Run merge docs workflow
python -m automation.workflows.merge_docs --dry-run

# Run weekly workflow
python -m automation.workflows.weekly_scanner --dry-run

# Run monthly workflow
python -m automation.workflows.monthly_report --dry-run

# View generated reports
ls automation/reports/
cat automation/reports/daily-report-*.md
```

### Testing Configuration

```python
# Test configuration loading
from automation.core.config import get_automation_config

config = get_automation_config()
print(config.get_repositories())
```

### Testing GitHub Client

```python
# Test GitHub client
from automation.core.github_client import GitHubClient

client = GitHubClient()
repo = client.get_repo("Azure/azureml-examples")
print(f"Rate limit: {client.get_rate_limit_status()}")
```

## Accessing Reports

### File-Based Reports (Recommended)

All workflows save reports as Markdown files in `automation/reports/`:

- `daily-report-YYYY-MM-DD.md` - Daily PR monitoring results
- `weekly-report-YYYY-MM-DD.md` - Weekly snippet scan results
- `monthly-report-YYYY-MM-DD.md` - Monthly maintenance statistics

**Accessing reports:**

1. **From GitHub Actions Artifacts:**
   - Go to the workflow run in GitHub Actions
   - Download the `*-reports-*` artifact
   - Extract and view the `.md` files

2. **Locally (if running workflows locally):**
   ```bash
   ls automation/reports/
   # View a report
   cat automation/reports/daily-report-2026-01-13.md
   ```

3. **In GitHub Actions Job Summary:**
   - Each workflow run shows a summary in the Actions UI
   - Navigate to Actions → [Workflow Name] → [Run] → Summary

### Email Reports (Optional)

If `EMAIL_ENABLED=true` is configured, reports are also sent via email to `NOTIFICATION_EMAIL`:

- **Daily:** List of auto-approved PRs and PRs requiring manual review
- **Weekly:** CODEOWNERS updates and documentation PRs created
- **Monthly:** Statistics and warnings

**To enable email notifications:**
1. Set `EMAIL_ENABLED=true` in GitHub Secrets
2. Configure all SMTP settings (see Environment Variables section)

**Note:** Reports are always saved to files, even if email is disabled.

## Monitoring

### GitHub Actions

View workflow runs at: `https://github.com/YOUR_ORG/content-maintenance/actions`

Each workflow run includes:
- Console logs with detailed execution information
- Job summary with key metrics in Markdown format
- Downloadable artifacts containing reports

### Artifacts

Workflow artifacts are retained for 30-90 days and include:

- **Reports artifacts:** Markdown reports from `automation/reports/`
  - `daily-reports-*` - Daily PR monitoring reports
  - `weekly-reports-*` - Weekly snippet scan reports
  - `monthly-reports-*` - Monthly statistics reports
  
- **Output artifacts:** CSV and text files from `outputs/`
  - `refs-found.csv` - Code references found in docs
  - `CODEOWNERS-*.txt` - Generated CODEOWNERS files
  - `code-counts-*.csv` - Statistics on code blocks
  - `merge-tracking.json` - Tracking data for processed merge PRs

## Troubleshooting

### Workflow Fails with Authentication Error

**Problem:** `Error: GitHub token is required`

**Solution:**
1. Verify `GH_ACCESS_TOKEN` secret is set correctly
2. Check token has required permissions (repo, workflow)
3. Ensure token hasn't expired

### Email Not Delivered (Optional Feature)

**Problem:** Email reports not received (only relevant if `EMAIL_ENABLED=true`)

**Solution:**
1. Verify `EMAIL_ENABLED` secret is set to `true`
2. Check spam/junk folder
3. Verify all SMTP credentials are set in secrets
4. For Gmail: Use an [App Password](https://support.google.com/accounts/answer/185833)
5. Check workflow logs for SMTP errors

**Note:** Reports are always saved to `automation/reports/` and available as GitHub Actions artifacts, regardless of email configuration. Email is optional.

### Cannot Find Reports

**Problem:** Unable to locate generated reports

**Solution:**
1. Check GitHub Actions artifacts:
   - Go to Actions → [Workflow Run] → Artifacts section at bottom
   - Download the `*-reports-*` artifact
2. If running locally, check `automation/reports/` directory
3. Check GitHub Actions job summary for inline report preview
4. Verify workflow completed successfully (check for errors in logs)

### PR Not Auto-Approved

**Problem:** Safe PR not auto-approved

**Solution:**
1. Check workflow logs for validation details
2. Verify `AUTO_APPROVE_ENABLED=true`
3. Ensure `DRY_RUN=false`
4. Check PR meets all safety criteria

### Rate Limit Exceeded

**Problem:** `GitHub API rate limit exceeded`

**Solution:**
1. Wait for rate limit to reset (shown in error message)
2. Consider reducing workflow frequency
3. Check for other processes using the same token

## Architecture

### Safety Mechanisms

1. **Dry-Run Mode** - Test without making changes
2. **Safety Criteria** - Multiple validation checks before auto-approval
3. **Manual Review Flags** - Unsafe PRs are commented and flagged
4. **Audit Trail** - All actions logged in workflow runs

### Error Handling

- Exponential backoff for API rate limits
- Retry logic for transient failures
- Detailed error logging
- Graceful degradation (continues processing on individual failures)

## Contributing

When modifying automation code:

1. Test locally with dry-run mode
2. Test via manual workflow trigger with dry_run=true
3. Review workflow logs carefully
4. Monitor first few automated runs

## Support

For issues or questions:
1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Check troubleshooting section
4. Create an issue in the repository

---

**Version:** 1.1.0  
**Last Updated:** 2026-01-29

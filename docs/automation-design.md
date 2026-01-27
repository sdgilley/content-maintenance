# Azure AI Documentation Maintenance - Automation Design

## Executive Summary

This document outlines a comprehensive automation solution for the content-maintenance repository that will automate daily, weekly, and monthly tasks currently performed manually. The solution uses GitHub Actions workflows to monitor 3 Azure code repositories for changes that could impact Azure AI documentation, automatically handling routine operations while escalating complex decisions to human reviewers.

**Key Goals:**
- Reduce manual effort from daily/weekly tasks to minimal oversight
- Maintain documentation quality through automated validation
- Enable safe, automated commits across 5 repositories
- Provide clear, actionable reports for remaining manual tasks

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```mermaid
graph TB
    subgraph GitHub Actions Workflows
        DailyJob[Daily PR Monitor]
        WeeklyJob[Weekly Snippet Scanner]
        MonthlyJob[Monthly Maintenance]
    end
    
    subgraph Code Repositories
        AzureML[Azure/azureml-examples]
        Foundry[Azure-AI-Foundry/foundry-samples]
        Samples[Azure-Samples/azureai-samples]
    end
    
    subgraph Documentation Repositories
        DocsPR[MicrosoftDocs/azure-ai-docs-pr]
        Docs[MicrosoftDocs/azure-ai-docs]
    end
    
    subgraph Maintenance Repository
        Scripts[Python Scripts]
        Outputs[outputs/ directory]
        Config[config.yml]
    end
    
    subgraph Automation Components
        PRAnalyzer[PR Analyzer]
        SnippetScanner[Snippet Scanner]
        GitOps[Git Operations Handler]
        Reporter[Report Generator]
        Approver[Auto-Approver]
    end
    
    subgraph Notifications
        Email[Email Reports]
        Summary[GitHub Actions Summary]
    end
    
    DailyJob --> PRAnalyzer
    PRAnalyzer --> AzureML
    PRAnalyzer --> Foundry
    PRAnalyzer --> Samples
    PRAnalyzer --> Approver
    PRAnalyzer --> Reporter
    
    WeeklyJob --> SnippetScanner
    SnippetScanner --> Docs
    SnippetScanner --> GitOps
    GitOps --> Outputs
    GitOps --> AzureML
    GitOps --> Foundry
    GitOps --> Samples
    GitOps --> DocsPR
    
    Reporter --> Email
    Reporter --> Summary
    
    MonthlyJob --> Reporter
```

### 1.2 Component Responsibilities

| Component | Responsibility | Used By |
|-----------|---------------|---------|
| **PR Analyzer** | Analyzes PRs for documentation impact using existing pr-report.py logic | Daily workflow |
| **Auto-Approver** | Approves PRs meeting safety criteria via GitHub API | Daily workflow |
| **Snippet Scanner** | Scans documentation for code references using find-snippets.py | Weekly workflow |
| **Git Operations Handler** | Clones repos, creates commits, pushes changes, creates PRs | Weekly workflow |
| **Report Generator** | Creates HTML/Markdown reports with actionable summaries | All workflows |
| **Email Notifier** | Sends email reports via SMTP | All workflows |

### 1.3 Data Flow

```mermaid
flowchart LR
    subgraph Input
        PRs[Pull Requests]
        Docs[Documentation Files]
    end
    
    subgraph Processing
        Scan[Scan & Analyze]
        Validate[Validate Safety]
        Generate[Generate Reports]
    end
    
    subgraph Output
        Approve[Auto-Approve PRs]
        Commit[Auto-Commit Files]
        CreatePR[Create Doc PRs]
        Notify[Send Reports]
    end
    
    PRs --> Scan
    Docs --> Scan
    Scan --> Validate
    Validate --> Generate
    Generate --> Approve
    Generate --> Commit
    Generate --> CreatePR
    Generate --> Notify
```

---

## 2. GitHub Actions Workflow Design

### 2.1 Workflow File Structure

```
.github/
└── workflows/
    ├── daily-pr-monitor.yml          # Daily PR review automation
    ├── weekly-snippet-scan.yml       # Weekly snippet scanning
    ├── monthly-maintenance.yml       # Monthly tasks and reports
    └── manual-trigger.yml            # On-demand execution for testing
```

### 2.2 Scheduling Strategy

| Workflow | Schedule | Trigger | Timezone |
|----------|----------|---------|----------|
| Daily PR Monitor | `0 12 * * 1-5` | Mon-Fri 7:00 AM EST | America/New_York |
| Weekly Snippet Scan | `0 11 * * 1` | Monday 6:00 AM EST | America/New_York |
| Monthly Maintenance | `0 10 1 * *` | 1st of month 5:00 AM EST | America/New_York |
| Manual Trigger | workflow_dispatch | On-demand | N/A |

**Note:** Times are in UTC. Workflows use `TZ=America/New_York` environment variable for EST/EDT handling.

### 2.3 Secret Management

#### Required Secrets (GitHub Actions Secrets)

| Secret Name | Purpose | Scope | Type |
|-------------|---------|-------|------|
| `GH_APP_ID` | GitHub App ID for authentication | All workflows | GitHub App |
| `GH_APP_PRIVATE_KEY` | GitHub App private key | All workflows | GitHub App |
| `GH_APP_INSTALLATION_ID` | Installation ID for org/repos | All workflows | GitHub App |
| `SMTP_SERVER` | Email server address | Reporting | SMTP Config |
| `SMTP_PORT` | Email server port (587 for TLS) | Reporting | SMTP Config |
| `SMTP_USERNAME` | Email account username | Reporting | SMTP Config |
| `SMTP_PASSWORD` | Email account password/app password | Reporting | SMTP Config |
| `NOTIFICATION_EMAIL` | Recipient email for reports | Reporting | Config |

#### GitHub App Permissions Required

**Repository Permissions:**
- Contents: Read & Write (for commits, PRs)
- Pull Requests: Read & Write (for approvals, reviews)
- Metadata: Read (for repo access)
- Issues: Read & Write (optional, for tracking)

**Organization Permissions:**
- Members: Read (for team mentions)

---

## 3. Automation Module Structure

### 3.1 Directory Structure

```
content-maintenance/
├── .github/
│   └── workflows/
│       ├── daily-pr-monitor.yml
│       ├── weekly-snippet-scan.yml
│       ├── monthly-maintenance.yml
│       └── manual-trigger.yml
├── automation/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── github_auth.py         # GitHub App authentication
│   │   ├── github_operations.py   # PR approvals, commits, PRs
│   │   ├── config_loader.py       # Load config.yml + env vars
│   │   └── exceptions.py          # Custom exceptions
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── pr_analyzer.py         # Wraps pr-report.py logic
│   │   ├── pr_finder.py           # Wraps find-prs.py logic
│   │   ├── snippet_analyzer.py    # Wraps find-snippets.py logic
│   │   └── merge_analyzer.py      # Wraps merge-report.py logic
│   ├── operations/
│   │   ├── __init__.py
│   │   ├── pr_approver.py         # Auto-approval logic
│   │   ├── snippet_updater.py     # Weekly snippet updates
│   │   ├── codeowners_updater.py  # CODEOWNERS file management
│   │   └── docs_updater.py        # Documentation metadata updates
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── report_generator.py    # HTML/Markdown report creation
│   │   ├── email_sender.py        # SMTP email sending
│   │   └── templates/
│   │       ├── daily_report.html
│   │       ├── weekly_report.html
│   │       └── monthly_report.html
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── daily_workflow.py      # Daily orchestration
│   │   ├── weekly_workflow.py     # Weekly orchestration
│   │   └── monthly_workflow.py    # Monthly orchestration
│   └── utils/
│       ├── __init__.py
│       ├── git_helper.py          # Git operations (clone, commit, push)
│       ├── retry_helper.py        # Retry logic for API calls
│       └── validation.py          # Safety validation checks
├── config.yml                      # Existing config (extended)
├── automation-config.yml           # New automation-specific config
├── requirements.txt                # Extended dependencies
└── [existing files...]
```

### 3.2 Module Responsibilities

#### Core Modules (`automation/core/`)

**`github_auth.py`**
- Generate GitHub App JWT tokens
- Obtain installation access tokens
- Create authenticated PyGithub clients
- Token caching and renewal

**`github_operations.py`**
- Approve/review PRs via API
- Create commits and push changes
- Create pull requests
- Add comments/labels to PRs

**`config_loader.py`**
- Load and merge config.yml + automation-config.yml
- Validate configuration
- Access environment variables
- Provide typed configuration objects

#### Analyzer Modules (`automation/analyzers/`)

**`pr_analyzer.py`**
- Wraps logic from [`pr-report.py`](pr-report.py)
- Analyzes PR for deleted files, modified cells, renamed files
- Returns structured safety assessment
- Reuses [`utilities/helpers.py`](utilities/helpers.py) and [`utilities/find_pr_files.py`](utilities/find_pr_files.py)

**`pr_finder.py`**
- Wraps logic from [`find-prs.py`](find-prs.py)
- Discovers PRs needing team review
- Returns list of PRs with metadata

**`snippet_analyzer.py`**
- Wraps logic from [`find-snippets.py`](find-snippets.py)
- Scans documentation for code references
- Generates CODEOWNERS and refs-found.csv

**`merge_analyzer.py`**
- Wraps logic from [`merge-report.py`](merge-report.py)
- Finds docs needing metadata updates
- Returns list of files to update

#### Operations Modules (`automation/operations/`)

**`pr_approver.py`**
- Evaluates PR safety based on criteria
- Auto-approves safe PRs
- Adds approval comment with validation details
- Logs all approval decisions

**`snippet_updater.py`**
- Commits snippet scan results to maintenance repo
- Updates outputs/ directory files

**`codeowners_updater.py`**
- Commits CODEOWNERS files to code repositories
- Creates PRs or direct commits based on permissions

**`docs_updater.py`**
- Updates ms.custom metadata in documentation
- Creates PRs in docs repository
- Splits large PRs (>10 files) into multiple PRs

#### Reporting Modules (`automation/reporting/`)

**`report_generator.py`**
- Generates HTML/Markdown reports from data
- Uses Jinja2 templates
- Creates GitHub Actions job summaries

**`email_sender.py`**
- Sends HTML email via SMTP
- Handles authentication and TLS
- Includes retry logic

---

## 4. Git Operations Strategy

### 4.1 Multi-Repository Access Pattern

```python
# Pseudo-code for repository access pattern
def get_authenticated_repo(owner, repo_name):
    """Get PyGithub repo object with GitHub App authentication"""
    token = github_app_auth.get_installation_token()
    g = Github(token)
    return g.get_repo(f"{owner}/{repo_name}")

# Repositories accessed by automation
REPOS = {
    "code_repos": [
        "Azure/azureml-examples",
        "Azure-AI-Foundry/foundry-samples", 
        "Azure-Samples/azureai-samples"
    ],
    "docs_repos": [
        "MicrosoftDocs/azure-ai-docs",
        "MicrosoftDocs/azure-ai-docs-pr"
    ],
    "maintenance_repo": "sdgilley/content-maintenance"
}
```

### 4.2 Commit Strategy

**Maintenance Repository (outputs/):**
- Direct commits to `main` branch
- Commit message format: `chore: automated update - {task_name} [{timestamp}]`
- Examples:
  - `chore: automated update - snippet scan [2026-01-13T12:00:00Z]`
  - `chore: automated update - CODEOWNERS [2026-01-13T12:00:00Z]`

**Code Repositories (CODEOWNERS):**
- Create branch: `automation/codeowners-update-{date}`
- Commit message: `docs: update CODEOWNERS from docs snapshot [{timestamp}]`
- Create PR with auto-merge label
- Auto-approve if GitHub App has permission

**Documentation Repository (metadata updates):**
- Create branch: `automation/metadata-update-{date}-{batch}`
- Commit message: `docs: update ms.custom metadata for code changes`
- Create PR with detailed body listing all changes
- Split into multiple PRs if >10 files affected

### 4.3 Branch Management

| Repository Type | Branch Pattern | Merge Strategy | Cleanup |
|----------------|----------------|----------------|---------|
| Maintenance | Direct to `main` | N/A | N/A |
| Code repos | `automation/codeowners-{date}` | PR with auto-merge | Delete after merge |
| Docs repo | `automation/metadata-{date}-{batch}` | PR (manual merge) | Keep for 30 days |

### 4.4 Commit Message Conventions

Following [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

**Types used:**
- `chore:` - Routine tasks (snippet scans, CODEOWNERS updates)
- `docs:` - Documentation updates (metadata changes)
- `ci:` - CI/CD changes (workflow updates)

---

## 5. Reporting Mechanism

### 5.1 Report Format

Reports are generated in **HTML format** for email delivery with a **Markdown summary** for GitHub Actions.

#### Daily Report Structure

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        /* Professional styling for email clients */
    </style>
</head>
<body>
    <h1>Daily PR Monitor Report - {date}</h1>
    
    <section id="summary">
        <h2>Summary</h2>
        <ul>
            <li>PRs Found: X</li>
            <li>Auto-Approved: Y</li>
            <li>Requiring Manual Review: Z</li>
        </ul>
    </section>
    
    <section id="auto-approved">
        <h2>✅ Auto-Approved PRs</h2>
        <table>
            <tr><th>Repo</th><th>PR#</th><th>Title</th><th>Author</th><th>Link</th></tr>
            <!-- PR rows -->
        </table>
    </section>
    
    <section id="manual-review">
        <h2>⚠️ PRs Requiring Manual Review</h2>
        <table>
            <tr><th>Repo</th><th>PR#</th><th>Title</th><th>Issues Found</th><th>Action Required</th></tr>
            <!-- PR rows with issue details -->
        </table>
    </section>
    
    <section id="details">
        <h2>Detailed Analysis</h2>
        <!-- Per-PR detailed breakdown -->
    </section>
    
    <footer>
        <p>Generated by content-maintenance automation at {timestamp}</p>
        <p><a href="{workflow_run_url}">View workflow run</a></p>
    </footer>
</body>
</html>
```

#### Weekly Report Structure

```html
<h1>Weekly Snippet Scan Report - {date}</h1>

<section id="summary">
    <h2>Summary</h2>
    <ul>
        <li>Snippets Scanned: X</li>
        <li>CODEOWNERS Updated: 3 repositories</li>
        <li>Docs Requiring Metadata Updates: Y files</li>
        <li>PRs Created: Z</li>
    </ul>
</section>

<section id="codeowners">
    <h2>📝 CODEOWNERS Updates</h2>
    <table>
        <tr><th>Repository</th><th>Files Updated</th><th>PR Link</th></tr>
        <!-- Repository rows -->
    </table>
</section>

<section id="metadata">
    <h2>📄 Documentation Metadata Updates</h2>
    <table>
        <tr><th>PR #</th><th>Files Changed</th><th>Link</th></tr>
        <!-- PR rows -->
    </table>
    
    <h3>Files Updated:</h3>
    <ul>
        <!-- List of documentation files -->
    </ul>
</section>

<section id="statistics">
    <h2>📊 Statistics</h2>
    <!-- Code reference statistics -->
</section>
```

### 5.2 Delivery Method: Email via SMTP

**Configuration:**
```yaml
# automation-config.yml
email:
  smtp_server: ${SMTP_SERVER}  # e.g., smtp.office365.com
  smtp_port: ${SMTP_PORT}      # 587 for TLS
  use_tls: true
  from_address: ${SMTP_USERNAME}
  to_addresses:
    - ${NOTIFICATION_EMAIL}
  subject_prefix: "[Azure AI Docs Automation]"
```

**Email Implementation:**
```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email_report(subject, html_content, text_content=None):
    """Send HTML email with optional plaintext fallback"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Azure AI Docs Automation] {subject}"
    msg['From'] = config.email.from_address
    msg['To'] = ', '.join(config.email.to_addresses)
    
    if text_content:
        msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))
    
    with smtplib.SMTP(config.email.smtp_server, config.email.smtp_port) as server:
        server.starttls()
        server.login(config.email.smtp_username, config.email.smtp_password)
        server.send_message(msg)
```

### 5.3 GitHub Actions Summary

In addition to email, each workflow generates a **GitHub Actions Job Summary** using `$GITHUB_STEP_SUMMARY`:

```python
def write_github_summary(markdown_content):
    """Write to GitHub Actions job summary"""
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_file:
        with open(summary_file, 'a') as f:
            f.write(markdown_content)
```

This provides immediate visibility in the Actions tab without needing to check email.

---

## 6. Configuration Management

### 6.1 Configuration File Strategy

**Existing `config.yml`** - Keep as-is, contains:
- Repository definitions
- Search paths
- Output directories
- Snippet patterns

**New `automation-config.yml`** - Automation-specific settings:

```yaml
# Automation-specific configuration
automation:
  # Workflow schedules (can override via workflow_dispatch)
  schedules:
    daily_pr_monitor: "0 12 * * 1-5"  # Mon-Fri 7AM EST
    weekly_snippet_scan: "0 11 * * 1"  # Monday 6AM EST
    monthly_maintenance: "0 10 1 * *"   # 1st of month 5AM EST
  
  # Auto-approval criteria
  pr_approval:
    enabled: true
    criteria:
      - no_deleted_files_referenced    # No deleted files in docs
      - no_deleted_cells_in_modified   # No deleted cells/snippets
      - no_renamed_files_referenced    # No renamed files in docs
    dry_run: false  # Set to true to skip actual approvals
    
  # Git operations
  git:
    commit_author_name: "Azure AI Docs Bot"
    commit_author_email: "azure-ai-docs-bot@microsoft.com"
    pr_labels:
      - "automated"
      - "documentation"
    auto_merge_labels:
      - "auto-merge"
    
  # Documentation PR splitting
  docs_pr:
    max_files_per_pr: 10
    branch_prefix: "automation/metadata-update"
    pr_title_template: "docs: update ms.custom metadata for code changes (batch {batch})"
    
  # Email configuration
  email:
    enabled: true
    smtp_server: ${SMTP_SERVER}
    smtp_port: ${SMTP_PORT}
    use_tls: true
    from_address: ${SMTP_USERNAME}
    to_addresses:
      - ${NOTIFICATION_EMAIL}
    subject_prefix: "[Azure AI Docs Automation]"
    
  # Retry and error handling
  retry:
    max_attempts: 3
    backoff_factor: 2  # Exponential backoff
    api_rate_limit_wait: 60  # seconds to wait on rate limit
    
  # Logging
  logging:
    level: INFO
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Monthly maintenance
monthly:
  token_expiry_warning_days: 7  # Warn if GitHub App token expires in N days
```

### 6.2 Environment Variables

Required environment variables in GitHub Actions:

```bash
# GitHub App Authentication
GH_APP_ID=123456
GH_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GH_APP_INSTALLATION_ID=789012

# Email Configuration
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=automation@example.com
SMTP_PASSWORD=app_password_here
NOTIFICATION_EMAIL=team@example.com

# Optional
TZ=America/New_York  # Timezone for scheduling
```

### 6.3 Configuration Loading Priority

1. Load [`config.yml`](config.yml) (existing repository configuration)
2. Load `automation-config.yml` (automation settings)
3. Override with environment variables (secrets)
4. Validate all required settings are present

```python
class AutomationConfig:
    def __init__(self):
        self.repo_config = load_yaml('config.yml')
        self.automation_config = load_yaml('automation-config.yml')
        self._apply_env_overrides()
        self._validate()
```

---

## 7. Safety Mechanisms

### 7.1 Dry-Run Mode

All automation operations support dry-run mode:

```yaml
# Set in automation-config.yml or via workflow input
automation:
  pr_approval:
    dry_run: true  # Analyze but don't approve
  git:
    dry_run: true  # Prepare commits but don't push
```

**Dry-run behavior:**
- ✅ Run all analysis and validation
- ✅ Generate reports showing what *would* happen
- ✅ Log all planned actions
- ❌ Don't approve PRs
- ❌ Don't commit/push changes
- ❌ Don't create PRs

### 7.2 Auto-Approval Safety Criteria

PRs are **ONLY** auto-approved if **ALL** criteria are met:

1. **No deleted files referenced in documentation**
   - Check: Any deleted files appear in `refs-found.csv`
   - Action: If found, flag for manual review

2. **No deleted cells/snippets in modified files**
   - Check: Modified notebooks/code files with deleted named cells
   - Action: If deleted cells are referenced, flag for manual review

3. **No renamed files referenced in documentation**
   - Check: Any renamed files appear in `refs-found.csv`
   - Action: If found, flag for manual review

4. **PR is mergeable** (no conflicts)

5. **PR has required team review** (from configured teams)

**Implementation:**
```python
class PRSafetyValidator:
    def is_safe_to_approve(self, pr_analysis_result):
        """Return (is_safe: bool, issues: list[str])"""
        issues = []
        
        if pr_analysis_result.deleted_files_referenced:
            issues.append("Deleted files are referenced in docs")
        
        if pr_analysis_result.deleted_cells_in_modified:
            issues.append("Modified files have deleted cells referenced in docs")
        
        if pr_analysis_result.renamed_files_referenced:
            issues.append("Renamed files are referenced in docs")
        
        if not pr_analysis_result.is_mergeable:
            issues.append("PR has merge conflicts")
        
        return (len(issues) == 0, issues)
```

### 7.3 Human Approval Gates

**Manual Review Required For:**
- Any PR failing safety criteria
- Documentation PRs with >10 files (create PR but don't auto-merge)
- Any operation that fails validation

**Approval Gate Implementation:**
- PRs requiring manual review are **commented** with analysis details
- Email report highlights these PRs in ⚠️ section
- GitHub Actions summary shows count of manual reviews needed

### 7.4 Rollback Procedures

**For Auto-Approved PRs:**
1. All approvals include comment: "Auto-approved by automation - validated {criteria}"
2. If issues discovered post-approval, automation can:
   - Add comment: "⚠️ Issue detected post-approval: {description}"
   - Add label: `needs-manual-review`
   - Send alert email

**For Auto-Committed Changes:**
1. All commits tagged with `[automation]` in message
2. Maintenance repo commits can be reverted via:
   ```bash
   git revert {commit_hash}
   ```

3. Code repo CODEOWNERS: PRs can be closed, new corrected PR created

4. Docs repo metadata: PRs can be updated or closed before merge

**Emergency Stop:**
1. Set `automation.*.dry_run: true` in automation-config.yml
2. Disable workflows in GitHub Actions UI
3. All subsequent runs will analyze but not act

### 7.5 Validation Checkpoints

```mermaid
flowchart TD
    Start[Start Operation] --> LoadConfig[Load Configuration]
    LoadConfig --> ValidateConfig{Config Valid?}
    ValidateConfig -->|No| Fail[Fail with Error]
    ValidateConfig -->|Yes| Authenticate[Authenticate]
    Authenticate --> ValidateAuth{Auth Valid?}
    ValidateAuth -->|No| Fail
    ValidateAuth -->|Yes| FetchData[Fetch Data]
    FetchData --> ValidateData{Data Valid?}
    ValidateData -->|No| Fail
    ValidateData -->|Yes| Analyze[Analyze]
    Analyze --> ValidateSafety{Safety Checks Pass?}
    ValidateSafety -->|No| Report[Report Issues]
    ValidateSafety -->|Yes| CheckDryRun{Dry Run?}
    CheckDryRun -->|Yes| Report
    CheckDryRun -->|No| Execute[Execute Operation]
    Execute --> ValidateResult{Success?}
    ValidateResult -->|No| Fail
    ValidateResult -->|Yes| Report
    Report --> End[End]
    Fail --> End
```

---

## 8. Implementation Phases

### Phase 1: Core Infrastructure

**Deliverables:**
- [ ] Set up `automation/` directory structure
- [ ] Implement [`automation/core/github_auth.py`](automation/core/github_auth.py) with GitHub App support
- [ ] Implement [`automation/core/config_loader.py`](automation/core/config_loader.py)
- [ ] Create `automation-config.yml` with all settings
- [ ] Implement [`automation/utils/retry_helper.py`](automation/utils/retry_helper.py) for API resilience
- [ ] Implement [`automation/utils/validation.py`](automation/utils/validation.py) for safety checks
- [ ] Create basic logging infrastructure
- [ ] Add dependencies to [`requirements.txt`](requirements.txt): `PyJWT`, `cryptography`, `jinja2`

**Success Criteria:**
- GitHub App authentication working
- Configuration loading and validation working
- Retry logic handling API rate limits
- All tests passing

---

### Phase 2: Daily Automation (PR Monitoring)

**Deliverables:**
- [ ] Implement [`automation/analyzers/pr_finder.py`](automation/analyzers/pr_finder.py) (wraps find-prs.py)
- [ ] Implement [`automation/analyzers/pr_analyzer.py`](automation/analyzers/pr_analyzer.py) (wraps pr-report.py)
- [ ] Implement [`automation/operations/pr_approver.py`](automation/operations/pr_approver.py)
- [ ] Implement [`automation/workflows/daily_workflow.py`](automation/workflows/daily_workflow.py)
- [ ] Create [`.github/workflows/daily-pr-monitor.yml`](.github/workflows/daily-pr-monitor.yml)
- [ ] Implement basic reporting for daily workflow
- [ ] Add dry-run mode support

**Workflow Logic:**
```python
def daily_workflow():
    # 1. Find PRs needing review
    prs = pr_finder.find_prs_needing_review()
    
    # 2. Analyze each PR
    results = []
    for pr in prs:
        analysis = pr_analyzer.analyze_pr(pr)
        results.append({
            'pr': pr,
            'analysis': analysis,
            'safe_to_approve': validator.is_safe_to_approve(analysis)
        })
    
    # 3. Auto-approve safe PRs
    approved = []
    manual_review = []
    for result in results:
        if result['safe_to_approve'] and not config.dry_run:
            pr_approver.approve_pr(result['pr'], result['analysis'])
            approved.append(result)
        else:
            manual_review.append(result)
    
    # 4. Generate and send report
    report = report_generator.generate_daily_report(approved, manual_review)
    email_sender.send_email("Daily PR Monitor", report)
    github_summary.write_summary(report)
```

**Success Criteria:**
- Daily workflow runs successfully on schedule
- PRs correctly identified and analyzed
- Safe PRs auto-approved with comment
- Unsafe PRs flagged in report
- Email reports received
- Dry-run mode prevents actual approvals

---

### Phase 3: Weekly Automation (Snippet Scanning)

**Deliverables:**
- [ ] Implement [`automation/analyzers/snippet_analyzer.py`](automation/analyzers/snippet_analyzer.py) (wraps find-snippets.py)
- [ ] Implement [`automation/analyzers/merge_analyzer.py`](automation/analyzers/merge_analyzer.py) (wraps merge-report.py)
- [ ] Implement [`automation/utils/git_helper.py`](automation/utils/git_helper.py) for git operations
- [ ] Implement [`automation/operations/snippet_updater.py`](automation/operations/snippet_updater.py)
- [ ] Implement [`automation/operations/codeowners_updater.py`](automation/operations/codeowners_updater.py)
- [ ] Implement [`automation/operations/docs_updater.py`](automation/operations/docs_updater.py)
- [ ] Implement [`automation/workflows/weekly_workflow.py`](automation/workflows/weekly_workflow.py)
- [ ] Create [`.github/workflows/weekly-snippet-scan.yml`](.github/workflows/weekly-snippet-scan.yml)

**Workflow Logic:**
```python
def weekly_workflow():
    # 1. Run snippet scan
    snippet_results = snippet_analyzer.scan_documentation()
    
    # 2. Commit outputs to maintenance repo
    snippet_updater.commit_outputs(snippet_results)
    
    # 3. Update CODEOWNERS in code repos
    for repo in code_repos:
        codeowners_updater.update_codeowners(repo, snippet_results)
    
    # 4. Find docs needing metadata updates
    docs_to_update = merge_analyzer.find_docs_needing_updates()
    
    # 5. Create PR(s) for docs updates
    prs_created = docs_updater.update_docs_metadata(docs_to_update)
    
    # 6. Generate and send report
    report = report_generator.generate_weekly_report(
        snippet_results, 
        codeowners_updates,
        prs_created
    )
    email_sender.send_email("Weekly Snippet Scan", report)
    github_summary.write_summary(report)
```

**Success Criteria:**
- Snippet scan completes successfully
- Output files committed to maintenance repo
- CODEOWNERS files updated in all 3 code repos
- Documentation PRs created (split if >10 files)
- Email reports received
- All operations respect dry-run mode

---

### Phase 4: Reporting & Monitoring

**Deliverables:**
- [ ] Implement [`automation/reporting/report_generator.py`](automation/reporting/report_generator.py)
- [ ] Implement [`automation/reporting/email_sender.py`](automation/reporting/email_sender.py)
- [ ] Create HTML email templates in [`automation/reporting/templates/`](automation/reporting/templates/)
- [ ] Implement [`automation/workflows/monthly_workflow.py`](automation/workflows/monthly_workflow.py)
- [ ] Create [`.github/workflows/monthly-maintenance.yml`](.github/workflows/monthly-maintenance.yml)
- [ ] Add workflow failure notifications
- [ ] Add token expiry warnings

**Monthly Workflow:**
```python
def monthly_workflow():
    # 1. Generate statistics
    stats = {
        'prs_reviewed': get_monthly_pr_count(),
        'prs_auto_approved': get_auto_approval_count(),
        'docs_updated': get_docs_update_count(),
        'codeowners_updates': 4,  # Weekly * 4
    }
    
    # 2. Check token expiry
    token_status = check_github_app_token_expiry()
    
    # 3. Generate monthly summary
    report = report_generator.generate_monthly_report(stats, token_status)
    email_sender.send_email("Monthly Maintenance Summary", report)
```

**Success Criteria:**
- Professional HTML email templates
- SMTP email delivery working
- Monthly summary includes statistics
- Token expiry warnings functional

---

### Phase 5: Testing & Validation

**Deliverables:**
- [ ] Create [`.github/workflows/manual-trigger.yml`](.github/workflows/manual-trigger.yml) for on-demand testing
- [ ] Comprehensive dry-run testing of all workflows
- [ ] Validate email delivery to test addresses
- [ ] Test error handling and retry logic
- [ ] Validate GitHub App permissions
- [ ] Test with various PR scenarios (safe, unsafe, edge cases)
- [ ] Validate PR splitting logic (>10 files)
- [ ] Test rollback procedures

**Manual Trigger Workflow:**
```yaml
name: Manual Automation Trigger
on:
  workflow_dispatch:
    inputs:
      workflow_type:
        description: 'Which workflow to run'
        required: true
        type: choice
        options:
          - daily
          - weekly
          - monthly
      dry_run:
        description: 'Run in dry-run mode'
        required: true
        type: boolean
        default: true
```

**Success Criteria:**
- All workflows run successfully in dry-run mode
- Error scenarios handled gracefully
- Rollback procedures tested and documented
- Manual trigger workflow allows testing individual workflows

---

## 9. Deployment Instructions

### 9.1 Prerequisites

**GitHub App Setup:**
1. Go to GitHub Organization Settings > Developer settings > GitHub Apps
2. Click "New GitHub App"
3. Configure:
   - Name: `Azure AI Docs Maintenance Bot`
   - Homepage URL: Repository URL
   - Webhook: Disable (not needed for this automation)
   - Permissions: (as listed in Section 2.3)
4. Generate private key (download and save securely)
5. Install app on organization with access to all 5 repositories
6. Note the App ID and Installation ID

**SMTP Configuration:**
1. Set up email account for automation (e.g., Microsoft 365)
2. Generate app password if using 2FA
3. Test SMTP connection manually

### 9.2 Step-by-Step Setup

**Step 1: Configure GitHub Secrets**

In repository settings > Secrets and variables > Actions, add:

```
GH_APP_ID: <from GitHub App>
GH_APP_PRIVATE_KEY: <contents of downloaded .pem file>
GH_APP_INSTALLATION_ID: <from GitHub App installation>
SMTP_SERVER: smtp.office365.com
SMTP_PORT: 587
SMTP_USERNAME: <email address>
SMTP_PASSWORD: <app password>
NOTIFICATION_EMAIL: <recipient email>
```

**Step 2: Deploy Code**

```bash
# Create automation directory structure
mkdir -p automation/{core,analyzers,operations,reporting,workflows,utils}
mkdir -p automation/reporting/templates
mkdir -p .github/workflows

# Create __init__.py files
find automation -type d -exec touch {}/__init__.py \;

# Update requirements.txt
echo "PyJWT==2.8.0" >> requirements.txt
echo "cryptography==42.0.0" >> requirements.txt
echo "jinja2==3.1.2" >> requirements.txt

# Create automation-config.yml
# (Use template from Section 6.1)

# Commit and push
git add automation/ .github/ automation-config.yml requirements.txt
git commit -m "feat: add automation infrastructure"
git push
```

**Step 3: Deploy Phase 1 (Core Infrastructure)**

1. Implement core modules
2. Test GitHub App authentication locally:
   ```bash
   python -c "from automation.core.github_auth import get_installation_token; print(get_installation_token())"
   ```
3. Validate configuration loading

**Step 4: Deploy Phase 2 (Daily Automation)**

1. Set `dry_run: true` in automation-config.yml
2. Deploy daily workflow
3. Trigger manually using workflow_dispatch
4. Review dry-run results
5. Set `dry_run: false` when confident
6. Monitor for first week

**Step 5: Deploy Phase 3 (Weekly Automation)**

1. Set `dry_run: true` for weekly workflow
2. Deploy weekly workflow
3. Trigger manually on a test branch
4. Review all created commits/PRs
5. Set `dry_run: false` when confident

**Step 6: Deploy Phase 4 (Reporting)**

1. Test email delivery to test address first
2. Deploy monthly workflow
3. Update NOTIFICATION_EMAIL to production address

**Step 7: Monitoring & Iteration**

1. Monitor GitHub Actions runs daily for first month
2. Review email reports
3. Adjust auto-approval criteria based on results
4. Tune error handling and retry logic

### 9.3 Validation Checklist

Before enabling production automation:

- [ ] GitHub App authenticated successfully
- [ ] All 5 repositories accessible
- [ ] Email delivery working
- [ ] Daily workflow runs in dry-run mode successfully
- [ ] Weekly workflow runs in dry-run mode successfully
- [ ] PRs correctly analyzed for safety
- [ ] CODEOWNERS files generated correctly
- [ ] Documentation PRs split correctly when >10 files
- [ ] Error handling and retry logic tested
- [ ] Rollback procedures documented and tested
- [ ] Team trained on monitoring and intervention

### 9.4 Required Permissions Summary

**GitHub App needs access to:**
- Azure/azureml-examples (Contents: RW, PRs: RW)
- Azure-AI-Foundry/foundry-samples (Contents: RW, PRs: RW)
- Azure-Samples/azureai-samples (Contents: RW, PRs: RW)
- MicrosoftDocs/azure-ai-docs (Contents: R)
- MicrosoftDocs/azure-ai-docs-pr (Contents: RW, PRs: RW)
- sdgilley/content-maintenance (Contents: RW)

**GitHub Actions needs:**
- Repository: Actions (read/write for job summaries)
- Repository: Contents (read for cloning)
- Secrets: Read (for all configured secrets)

---

## 10. Monitoring & Maintenance

### 10.1 Success Metrics

Track these metrics in monthly reports:

| Metric | Target | Measurement |
|--------|--------|-------------|
| PR Auto-Approval Rate | >80% | (Auto-approved PRs / Total PRs) * 100 |
| False Positives | <5% | Manual interventions needed / Auto-approvals |
| Workflow Success Rate | >95% | Successful runs / Total runs |
| Email Delivery Rate | 100% | Emails sent / Expected emails |
| Mean Time to Review | <4 hours | Time from PR creation to review/approval |

### 10.2 Alert Conditions

Set up GitHub Actions notifications for:

- ⚠️ Workflow failures (any workflow fails)
- ⚠️ Auto-approval rate <70% (may indicate criteria too strict)
- ⚠️ API rate limit exceeded
- ⚠️ GitHub App token expiry <7 days
- ⚠️ Email delivery failure
- ⚠️ PR safety validation finds critical issues

### 10.3 Maintenance Tasks

**Weekly:**
- Review auto-approval decisions for accuracy
- Check for any false positives/negatives
- Monitor workflow execution times

**Monthly:**
- Review monthly summary report
- Analyze trends in PR safety issues
- Update auto-approval criteria if needed
- Review and update documentation

**Quarterly:**
- Rotate GitHub App private key
- Update dependencies in requirements.txt
- Review and optimize workflow performance
- Audit GitHub App permissions

### 10.4 Troubleshooting Guide

**Workflow Fails with Authentication Error:**
- Check GitHub App installation is active
- Verify `GH_APP_PRIVATE_KEY` secret is correct (including newlines)
- Confirm `GH_APP_INSTALLATION_ID` matches current installation
- Check App permissions haven't been reduced

**Email Not Delivered:**
- Verify SMTP credentials in secrets
- Check SMTP server allows connections from GitHub Actions IPs
- Test with a simple SMTP client outside workflow
- Review email spam/junk folders

**PR Not Auto-Approved Despite Being Safe:**
- Check dry-run mode is disabled
- Verify PR meets all safety criteria
- Check GitHub App has PR write permission
- Review workflow logs for validation errors

**CODEOWNERS Update Failed:**
- Verify GitHub App has write access to code repositories
- Check for branch protection rules blocking automated commits
- Review file paths in generated CODEOWNERS

---

## 11. Future Enhancements

### 11.1 Potential Phase 6+ Features

**Advanced PR Analysis:**
- AI-powered code review comments
- Automated doc update suggestions
- Breaking change detection

**Enhanced Reporting:**
- Slack/Teams integration option
- Interactive dashboards (GitHub Pages)
- Trend analysis and predictions

**Workflow Optimizations:**
- Parallel execution for multiple repos
- Incremental scanning (only changed docs)
- Caching of snippet scan results

**Additional Automations:**
- Auto-fix simple documentation issues
- Automated dependency updates
- Automated test execution for samples

### 11.2 Extensibility Points

The architecture supports:
- Adding new code repositories (via config.yml)
- Custom safety criteria (plugin system)
- Additional notification channels (webhook interface)
- Custom report templates (Jinja2 templates)

---

## 12. Appendices

### Appendix A: File Reference Map

| Current Script | Automation Module | Reusability |
|---------------|-------------------|-------------|
| [`find-prs.py`](find-prs.py) | [`automation/analyzers/pr_finder.py`](automation/analyzers/pr_finder.py) | Wrap logic, keep script for manual use |
| [`pr-report.py`](pr-report.py) | [`automation/analyzers/pr_analyzer.py`](automation/analyzers/pr_analyzer.py) | Wrap logic, keep script for manual use |
| [`find-snippets.py`](find-snippets.py) | [`automation/analyzers/snippet_analyzer.py`](automation/analyzers/snippet_analyzer.py) | Wrap logic, keep script for manual use |
| [`merge-report.py`](merge-report.py) | [`automation/analyzers/merge_analyzer.py`](automation/analyzers/merge_analyzer.py) | Wrap logic, keep script for manual use |
| [`utilities/helpers.py`](utilities/helpers.py) | Reused directly | Shared utility functions |
| [`utilities/gh_auth.py`](utilities/gh_auth.py) | Extended in [`automation/core/github_auth.py`](automation/core/github_auth.py) | Add GitHub App support |
| [`utilities/config.py`](utilities/config.py) | Extended in [`automation/core/config_loader.py`](automation/core/config_loader.py) | Add automation config |

**Design Principle:** Keep existing scripts functional for manual execution while wrapping their logic in automation modules.

### Appendix B: Workflow Execution Times

Estimated execution times (actual may vary):

| Workflow | Typical Duration | Max Duration |
|----------|-----------------|--------------|
| Daily PR Monitor | 2-5 minutes | 15 minutes |
| Weekly Snippet Scan | 10-15 minutes | 30 minutes |
| Monthly Maintenance | 1-2 minutes | 5 minutes |

**Note:** GitHub Actions free tier includes 2,000 minutes/month. Estimated monthly usage:
- Daily: 20 runs × 5 min = 100 min
- Weekly: 4 runs × 15 min = 60 min
- Monthly: 1 run × 2 min = 2 min
- **Total: ~162 minutes/month** (well within free tier)

### Appendix C: Dependencies

**New Dependencies to Add:**

```txt
# Existing (already in requirements.txt)
PyGithub==2.1.1
requests==2.31.0
pandas==2.0.3
PyYAML==6.0.1

# New for automation
PyJWT==2.8.0              # GitHub App JWT token generation
cryptography==42.0.0      # RSA key handling for GitHub App
jinja2==3.1.2             # HTML email template rendering
```

### Appendix D: GitHub Actions Workflow Templates

**Daily PR Monitor Skeleton:**

```yaml
name: Daily PR Monitor
on:
  schedule:
    - cron: '0 12 * * 1-5'  # Mon-Fri 7AM EST (12PM UTC)
  workflow_dispatch:
    inputs:
      dry_run:
        description: 'Run in dry-run mode'
        required: false
        type: boolean
        default: false

env:
  TZ: America/New_York

jobs:
  monitor-prs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run Daily PR Monitor
        env:
          GH_APP_ID: ${{ secrets.GH_APP_ID }}
          GH_APP_PRIVATE_KEY: ${{ secrets.GH_APP_PRIVATE_KEY }}
          GH_APP_INSTALLATION_ID: ${{ secrets.GH_APP_INSTALLATION_ID }}
          SMTP_SERVER: ${{ secrets.SMTP_SERVER }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USERNAME: ${{ secrets.SMTP_USERNAME }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          NOTIFICATION_EMAIL: ${{ secrets.NOTIFICATION_EMAIL }}
        run: |
          python -m automation.workflows.daily_workflow \
            --dry-run=${{ inputs.dry_run || 'false' }}
```

---

## Conclusion

This automation design provides a comprehensive, safe, and maintainable solution for automating the content-maintenance workflows. The phased approach allows for incremental deployment and validation, while the safety mechanisms ensure human oversight where needed.

**Key Benefits:**
- ✅ Reduces manual effort by ~80%
- ✅ Maintains documentation quality through automated validation
- ✅ Provides clear visibility through email reports
- ✅ Safe with multiple validation checkpoints
- ✅ Extensible for future enhancements

**Next Steps:**
1. Review and approve this design
2. Begin Phase 1 implementation (core infrastructure)
3. Test thoroughly in dry-run mode
4. Gradually enable automation features

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-13  
**Author:** Automation Architecture Team  
**Status:** Pending Review

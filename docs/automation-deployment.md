# Automation Deployment Guide

This guide provides step-by-step instructions for deploying and configuring the GitHub Actions automation workflows for Azure AI documentation maintenance.

## Table of Contents

- [Prerequisites Checklist](#prerequisites-checklist)
- [Step-by-Step Setup](#step-by-step-setup)
  - [A. GitHub Personal Access Token Setup](#a-github-personal-access-token-setup)
  - [B. Email Configuration](#b-email-configuration)
  - [C. GitHub Secrets Configuration](#c-github-secrets-configuration)
  - [D. Testing with Dry-Run Mode](#d-testing-with-dry-run-mode)
  - [E. Enabling Scheduled Workflows](#e-enabling-scheduled-workflows)
- [Validation Checklist](#validation-checklist)
- [Post-Deployment Monitoring](#post-deployment-monitoring)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Rollback Procedures](#rollback-procedures)
- [Advanced Configuration](#advanced-configuration)
- [Security Best Practices](#security-best-practices)

---

## Prerequisites Checklist

Before starting deployment, ensure you have:

- [ ] **GitHub Repository Access** - Admin or maintainer permissions on the `content-maintenance` repository
- [ ] **Organization Permissions** - Access to configure SSO for Personal Access Tokens
- [ ] **Email Account** (OPTIONAL) - Gmail, Office 365, or other SMTP-compatible email account (only needed for email notifications)
- [ ] **Email App Password** (OPTIONAL) - Generated app-specific password (only needed if using email)
- [ ] **Basic Knowledge** - Familiarity with GitHub Actions and repository settings

**Note:** Reports are always saved to files and available as GitHub Actions artifacts. Email is completely optional.

---

## Step-by-Step Setup

### A. GitHub Personal Access Token Setup

The automation requires a GitHub Personal Access Token (PAT) with specific permissions to interact with repositories and workflows.

#### 1. Create a Personal Access Token

**Navigate to Token Settings:**

1. Go to **GitHub.com** → Click your profile picture (top-right)
2. Select **Settings** → Scroll down to **Developer settings** (bottom-left)
3. Click **Personal access tokens** → **Tokens (classic)**
4. Click **Generate new token** → **Generate new token (classic)**

> 💡 **TIP**: Use classic tokens for now as they're more widely supported. Fine-grained tokens may work but require additional configuration.

#### 2. Configure Token Permissions

**Set the following details:**

- **Note**: `Content Maintenance Automation` (or any descriptive name)
- **Expiration**: `90 days` (recommended - set calendar reminder to renew)

**Select these scopes:**

- ✅ `repo` - Full control of private repositories
  - Includes: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`
- ✅ `workflow` - Update GitHub Action workflows
- ✅ `read:org` - Read org and team membership, read org projects
- ✅ `read:user` - Read user profile data
- ✅ `user:email` - Access user email addresses (read-only)

> ⚠️ **WARNING**: Do NOT grant `admin:org`, `delete_repo`, or other admin permissions. Follow the principle of least privilege.

#### 3. Generate and Save Token

1. Scroll to bottom and click **Generate token**
2. **IMMEDIATELY COPY THE TOKEN** - You won't be able to see it again
3. Store it securely (password manager recommended)
4. Format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### 4. Configure SSO Authorization

If your organization uses SSO (like MicrosoftDocs):

1. Next to the newly created token, click **Configure SSO**
2. Find **MicrosoftDocs** organization
3. Click **Authorize** next to it
4. Complete any additional authentication steps
5. Verify: Token should show "Authorized" for MicrosoftDocs

> ⚠️ **CRITICAL**: Without SSO authorization, the token won't work with organization repositories!

#### 5. Test Token Works

**Using curl (recommended):**

```bash
curl -H "Authorization: token ghp_YOUR_TOKEN_HERE" \
  https://api.github.com/user
```

**Expected response:** Your user information in JSON format

**If you see errors:**
- `401 Unauthorized` - Token is invalid or expired
- `403 Forbidden` - SSO not configured or insufficient scopes
- `404 Not Found` - Check the URL

---

### B. Email Configuration (OPTIONAL)

**Email notifications are completely optional.** Reports are always saved as Markdown files in `automation/reports/` and uploaded as GitHub Actions artifacts, which you can download and review.

If you want to receive email notifications in addition to file-based reports, follow the steps below. Otherwise, skip to [Section C: GitHub Secrets Configuration](#c-github-secrets-configuration).

#### Why You Might Skip Email Setup

- ✅ **File-based reports** are always generated and available in GitHub Actions artifacts
- ✅ **GitHub Actions job summaries** show report highlights inline
- ✅ **No email setup required** - one less thing to configure
- ✅ **No credentials to manage** - more secure
- ✅ **Access reports on-demand** - download when you need them

#### Setting Up Email (Optional)

Email notifications require SMTP credentials. Choose the option that matches your email provider.

#### Option 1: Gmail with App Password

Gmail requires an app-specific password when 2FA is enabled (which it should be).

**Step 1: Enable 2-Factor Authentication**

1. Go to **myaccount.google.com/security**
2. Under "Signing in to Google", click **2-Step Verification**
3. Follow prompts to enable 2FA if not already enabled

**Step 2: Generate App Password**

1. Go to **myaccount.google.com/apppasswords**
2. Select app: **Mail**
3. Select device: **Other (Custom name)**
4. Enter name: `GitHub Actions Automation`
5. Click **Generate**
6. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)

**Step 3: Note Your Settings**

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  (the app password)
SMTP_EMAIL=your.email@gmail.com
```

> 💡 **TIP**: Remove spaces from the app password when entering it as a secret.

#### Option 2: Office 365 / Outlook

**Step 1: Enable SMTP Authentication**

1. Sign in to **Microsoft 365 admin center**
2. Go to **Users** → **Active users**
3. Select your user → **Mail** tab
4. Click **Manage email apps**
5. Ensure **Authenticated SMTP** is checked
6. Save changes

**Step 2: Note Your Settings**

```
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your.email@yourdomain.com
SMTP_PASSWORD=your_account_password
SMTP_EMAIL=your.email@yourdomain.com
```

> ⚠️ **WARNING**: If your organization enforces MFA, you may need an app password. Contact your IT admin.

#### Option 3: Other SMTP Servers

For other providers, you'll need:

- **SMTP Server Address** (e.g., `smtp.example.com`)
- **SMTP Port** (usually `587` for TLS or `465` for SSL)
- **Authentication credentials** (username and password)

Common providers:

| Provider | SMTP Server | Port |
|----------|-------------|------|
| Yahoo | smtp.mail.yahoo.com | 587 |
| Outlook.com | smtp-mail.outlook.com | 587 |
| SendGrid | smtp.sendgrid.net | 587 |
| AWS SES | email-smtp.region.amazonaws.com | 587 |

#### Testing SMTP Connection

**Using Python (recommended):**

```python
import smtplib
from email.mime.text import MIMEText

# Your credentials
smtp_server = "smtp.gmail.com"
smtp_port = 587
username = "your.email@gmail.com"
password = "your_app_password"

try:
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(username, password)
    
    # Send test email
    msg = MIMEText("Test from automation setup")
    msg['Subject'] = 'SMTP Test'
    msg['From'] = username
    msg['To'] = username
    
    server.send_message(msg)
    server.quit()
    print("✅ SMTP connection successful!")
    
except Exception as e:
    print(f"❌ SMTP connection failed: {e}")
```

**Common Email Issues:**

- **530 Authentication failed** - Wrong username/password
- **535 Authentication credentials invalid** - Need app password
- **Connection timeout** - Wrong server or port, or firewall blocking
- **TLS error** - Try port 465 instead of 587

---

### C. GitHub Secrets Configuration

Secrets are encrypted environment variables used by GitHub Actions workflows.

#### Navigate to Secrets Settings

1. Go to your repository on GitHub.com
2. Click **Settings** (top menu bar)
3. In left sidebar: **Secrets and variables** → **Actions**
4. You should see "Actions secrets and variables" page

```
Repository Settings
├── General
├── Collaborators
├── ...
└── Secrets and variables
    └── Actions  ← Click here
        ├── Secrets (tab)  ← You are here
        └── Variables (tab)
```

#### Add Required Secrets

Click **New repository secret** for the following **REQUIRED** secret:

##### 1. GH_ACCESS_TOKEN (REQUIRED)

- **Name**: `GH_ACCESS_TOKEN`
- **Secret**: Paste your GitHub Personal Access Token from Step A
- **Example**: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### Add Optional Email Secrets

**Only add these if you completed Section B and want email notifications:**

##### 2. EMAIL_ENABLED (Optional)

- **Name**: `EMAIL_ENABLED`
- **Secret**: `true`
- **Purpose**: Enables email notifications (defaults to `false` if not set)

##### 3. SMTP_SERVER (Optional)

- **Name**: `SMTP_SERVER`
- **Secret**: Your SMTP server address
- **Example**: `smtp.gmail.com` or `smtp.office365.com`

##### 4. SMTP_PORT (Optional)

- **Name**: `SMTP_PORT`
- **Secret**: Your SMTP port number
- **Example**: `587` (most common) or `465`

##### 5. SMTP_USERNAME (Optional)

- **Name**: `SMTP_USERNAME`
- **Secret**: Your email username (usually your full email address)
- **Example**: `your.email@gmail.com`

##### 6. SMTP_PASSWORD (Optional)

- **Name**: `SMTP_PASSWORD`
- **Secret**: Your email password or app password
- **Example**: `xxxxxxxxxxxxxxxx` (app password without spaces)

##### 7. SMTP_EMAIL (Optional)

- **Name**: `SMTP_EMAIL`
- **Secret**: The "From" email address for notifications
- **Example**: `your.email@gmail.com`
- **Note**: Usually same as SMTP_USERNAME

##### 8. NOTIFICATION_EMAIL (Optional)

- **Name**: `NOTIFICATION_EMAIL`
- **Secret**: Recipient email address(es) for reports
- **Example**: `recipient@example.com`
- **Multiple recipients**: `email1@example.com,email2@example.com`

#### Verify Secrets Are Added

**Minimum configuration (no email):**

```
Repository secrets
└── GH_ACCESS_TOKEN         Updated X seconds ago
```

**Full configuration (with email):**

```
Repository secrets
├── GH_ACCESS_TOKEN         Updated X seconds ago
├── EMAIL_ENABLED           Updated X seconds ago
├── SMTP_SERVER             Updated X seconds ago
├── SMTP_PORT               Updated X seconds ago
├── SMTP_USERNAME           Updated X seconds ago
├── SMTP_PASSWORD           Updated X seconds ago
├── SMTP_EMAIL              Updated X seconds ago
└── NOTIFICATION_EMAIL      Updated X seconds ago
```

> 💡 **TIP**: Secret values are hidden and can't be viewed after creation. If you make a mistake, simply create a new secret with the same name to overwrite it.

> ℹ️ **NOTE**: Reports are always saved to files regardless of email configuration. You can add email later if needed.

---

### D. Testing with Dry-Run Mode

Before enabling automated workflows, test everything manually with dry-run mode enabled.

#### Understanding Dry-Run Mode

When `dry_run` is enabled:

- ✅ All repository scanning and analysis runs normally
- ✅ All validation checks are performed
- ✅ Reports are generated showing what *would* happen
- ✅ Email reports are sent (showing proposed actions)
- ❌ No PR approvals are actually made
- ❌ No commits are pushed to repositories
- ❌ No pull requests are created

This lets you verify everything works without making any changes.

#### Step 1: Navigate to GitHub Actions

1. Go to your repository on GitHub.com
2. Click **Actions** tab (top menu)
3. You should see a list of workflows in the left sidebar

#### Step 2: Run Manual Test Workflow

1. In left sidebar, click **Manual Automation Trigger**
2. Click **Run workflow** button (top-right)
3. A dialog appears with options:

```
Run workflow
├── Use workflow from: Branch: main
├── Which workflow to run: [dropdown]
│   ├── daily
│   ├── weekly  
│   └── monthly
└── Run in dry-run mode: ✅ (checked)
```

4. Select **daily** from the dropdown
5. Ensure **dry-run mode is CHECKED** ✅
6. Click green **Run workflow** button

#### Step 3: Monitor Workflow Execution

1. Workflow appears in the runs list (may take 5-10 seconds)
2. Click on the workflow run to see details
3. Watch the job progress in real-time:

```
monitor-prs (or scan-snippets, monthly-report)
├── Set up job          ✅ Complete
├── Checkout repository ✅ Complete
├── Set up Python       ✅ Complete
├── Install dependencies ✅ Complete
├── Run workflow        🔵 In progress...
└── Upload artifacts    ⏳ Pending
```

#### Step 4: Review Workflow Logs

1. Click on **Run [Workflow Type]** step to expand logs
2. Look for key indicators of success:

**For Daily PR Monitor:**
```
✅ Found X PRs requesting review
✅ Analyzing PR #XXX: Title of PR
✅ Safety check passed: no_deleted_referenced_files
✅ [DRY RUN] Would approve PR #XXX
✅ Email report sent successfully
```

**For Weekly Scanner:**
```
✅ Scanning azure-ai-docs repository
✅ Found X code references across Y files
✅ Generated CODEOWNERS for azureml-examples
✅ [DRY RUN] Would create PR to update CODEOWNERS
✅ Email report sent successfully
```

**For Monthly Report:**
```
✅ Collecting monthly statistics
✅ GitHub API rate limit: X/5000 remaining
✅ Email report sent successfully
```

#### Step 5: Check for Errors

**Look for these common issues:**

❌ **Authentication errors:**
```
Error: GitHub token is required
Error: Bad credentials
```
→ Check that `GH_ACCESS_TOKEN` is set correctly and has SSO authorization

❌ **Email errors:**
```
SMTPAuthenticationError: Username and Password not accepted
Connection timeout
```
→ Verify SMTP credentials and test connection again

❌ **Permission errors:**
```
Resource not accessible by integration
403 Forbidden
```
→ Check token scopes and repository permissions

#### Step 6: Download and Review Report Artifacts

1. Scroll to bottom of workflow run page
2. Under **Artifacts** section, download the report
3. Extract the ZIP file
4. Review the HTML and Markdown reports:
   - Open `*_report.html` in a browser
   - Check that all data looks correct
   - Verify the report format is readable

#### Step 7: Verify Email Received

1. Check your inbox at the `NOTIFICATION_EMAIL` address
2. Look for email with subject like:
   - `Daily PR Monitor Report - [Date]`
   - `Weekly Snippet Scanner Report - [Date]`
   - `Monthly Maintenance Report - [Date]`
3. Verify email formatting and content
4. Check that dry-run indicators are present

> 💡 **TIP**: If email doesn't arrive within 5 minutes, check spam/junk folder, then review workflow logs for SMTP errors.

#### Step 8: Test All Three Workflows

Repeat steps 2-7 for each workflow type:

1. ✅ Daily PR Monitor - Test with `dry_run: true`
2. ✅ Weekly Snippet Scanner - Test with `dry_run: true`
3. ✅ Monthly Report - Test with `dry_run: false` (safe, doesn't make changes)

---

### E. Enabling Scheduled Workflows

After successful testing, enable the automated schedules.

#### Understanding Workflow Schedules

The automation runs on these schedules (all times in EST/UTC):

| Workflow | Schedule | Time (EST) | Time (UTC) | Runs On |
|----------|----------|------------|------------|---------|
| Daily PR Monitor | Weekdays | 7:00 AM | 12:00 PM | Mon-Fri |
| Weekly Scanner | Weekly | 6:00 AM | 11:00 AM | Monday |
| Monthly Report | Monthly | 5:00 AM | 10:00 AM | 1st of month |

> 💡 **TIP**: Schedules use UTC time. The workflows set `TZ: America/New_York` to display times correctly in logs.

#### Verify Workflows Are Enabled

GitHub may automatically disable workflows in forked repositories or after periods of inactivity.

**Check workflow status:**

1. Go to **Actions** tab
2. In left sidebar, check each workflow
3. Look for yellow banner: *"This workflow was disabled because..."*

**If disabled, enable them:**

1. Click the workflow name
2. Click **Enable workflow** button
3. Repeat for all three scheduled workflows:
   - [`Daily PR Monitor`](.github/workflows/daily-pr-monitor.yml)
   - [`Weekly Snippet Scanner`](.github/workflows/weekly-scanner.yml)
   - [`Monthly Maintenance Report`](.github/workflows/monthly-report.yml)

#### Temporarily Disable a Workflow

If you need to pause automation:

1. Go to **Actions** → Select workflow
2. Click **⋯** (three dots menu, top-right)
3. Select **Disable workflow**
4. Workflow won't run on schedule until re-enabled

#### Monitor First Scheduled Run

1. Wait for the next scheduled time (or wait until the next day)
2. Check **Actions** tab for new runs
3. Verify workflows start automatically
4. Review logs to ensure they complete successfully

> ⚠️ **WARNING**: On the first scheduled run, workflows run with `DRY_RUN=false` by default. They WILL make actual changes (approve PRs, create commits, etc.). Make sure testing was successful first!

---

## Validation Checklist

Use this checklist to verify your deployment is complete and working:

### Initial Setup
- [ ] GitHub PAT created with scopes: `repo`, `workflow`, `read:org`, `read:user`, `user:email`
- [ ] PAT configured for SSO with MicrosoftDocs organization
- [ ] PAT tested successfully with curl or API call
- [ ] `GH_ACCESS_TOKEN` secret configured in repository settings
- [ ] (Optional) Email SMTP credentials tested and working
- [ ] (Optional) Email secrets configured if email is desired

### Testing
- [ ] Manual dry-run test of Daily PR Monitor completed successfully
- [ ] Manual dry-run test of Weekly Scanner completed successfully
- [ ] Manual dry-run test of Monthly Report completed successfully
- [ ] Report artifacts downloaded and verified
- [ ] (Optional) Email reports received for all three workflow types if email enabled
- [ ] Workflow logs show no authentication errors
- [ ] Workflow logs show no email errors (or email correctly skipped if disabled)

### Production Readiness
- [ ] All scheduled workflows enabled (not disabled)
- [ ] First scheduled workflow run completed successfully
- [ ] Email notifications received on schedule
- [ ] Workflow status shows green checkmarks in Actions tab

### Post-Deployment
- [ ] Calendar reminder set for PAT renewal (before expiration)
- [ ] Team members notified about automation
- [ ] Documentation bookmarked for future reference
- [ ] Monitoring plan established (who checks what, how often)

---

## Post-Deployment Monitoring

### First Week: Close Monitoring

During the first week after deployment, monitor closely to catch any issues early.

#### Daily Checks (First 5 Business Days)

**After Daily PR Monitor runs:**

1. Check **Actions** tab for workflow status
2. Review email report:
   - How many PRs were processed?
   - How many were auto-approved?
   - Any PRs flagged for manual review?
3. Verify auto-approved PRs look safe:
   - Check the PRs that were approved
   - Confirm they meet safety criteria
   - Look for false positives
4. Review workflow logs for warnings or errors

**Expected behavior:**
- ✅ Workflow completes in 2-5 minutes
- ✅ Email arrives within 5 minutes of completion
- ✅ 0-10 PRs processed per day (depends on repository activity)
- ✅ Most PRs auto-approved (if they're truly safe)

#### Weekly Checks (First Month)

**After Weekly Scanner runs (Monday mornings):**

1. Check for new PRs created in code repositories
2. Review CODEOWNERS update PRs:
   - Do the changes look correct?
   - Are the right people being added as owners?
3. Check commit history in content-maintenance repo:
   - Verify outputs files were updated
   - Review `refs-found.csv` for accuracy
4. Look for any failed workflow runs

**Expected behavior:**
- ✅ 1-3 CODEOWNERS update PRs created
- ✅ PRs have clear descriptions
- ✅ CSV files updated in outputs/ directory

#### Monthly Checks

**After Monthly Report (1st of each month):**

1. Review monthly statistics email
2. Check for warnings:
   - Token expiration warnings (renew if < 30 days)
   - Rate limit warnings (should have plenty remaining)
   - Any unusual patterns
3. Archive the monthly report for records

### Ongoing: Routine Monitoring

After the first week, establish a regular monitoring routine.

#### Weekly Quick Check (5 minutes)

1. Go to **Actions** tab
2. Scan recent workflow runs for red ❌ or yellow ⚠️ icons
3. If all green ✅, you're good
4. If failures, investigate logs

#### Reading GitHub Actions Logs

**Understanding log structure:**

```
Run Daily PR Monitor
  └── Job: monitor-prs
      ├── Step: Checkout repository
      ├── Step: Set up Python
      ├── Step: Install dependencies
      ├── Step: Run Daily PR Monitor ← Main logic here
      └── Step: Upload report artifact
```

**What to look for:**

✅ **Success indicators:**
```
✅ Configuration loaded successfully
✅ GitHub client initialized
✅ Found X PRs requesting review
✅ Email sent successfully
```

⚠️ **Warnings (usually OK, but watch):**
```
⚠️ No PRs found requesting review (slow day)
⚠️ Rate limit at 40% (still plenty of capacity)
⚠️ PR #XXX flagged for manual review (expected for unsafe changes)
```

❌ **Errors (need attention):**
```
❌ Error: Bad credentials (token expired or wrong)
❌ SMTPAuthenticationError (email credentials wrong)
❌ Rate limit exceeded (too many API calls)
❌ Error: Resource not accessible (permission issue)
```

#### Understanding Email Reports

**Daily PR Monitor Report Structure:**

```
Subject: Daily PR Monitor Report - 2026-01-13

Summary:
- Total PRs Processed: 5
- Auto-Approved: 3
- Flagged for Review: 2

Auto-Approved PRs:
✅ PR #123 - Update documentation [Safe]
   Reason: No breaking changes detected

Flagged PRs (Manual Review Needed):
⚠️ PR #456 - Delete old sample
   Reason: Deleted file 'example.py' is referenced in docs
   Action Required: Review docs impact before merging
```

### When Workflows Might Fail

**Common failure scenarios:**

1. **Token Expiration**
   - Frequency: Every 60-90 days (based on PAT expiration)
   - Warning: Monthly report will warn 30 days before
   - Fix: Generate new PAT and update `GH_ACCESS_TOKEN` secret

2. **Rate Limit Exceeded**
   - Frequency: Rare, only if processing many PRs
   - Warning: Workflow logs will show retry attempts
   - Fix: Workflow has automatic retry logic; usually resolves itself

3. **SMTP Password Changed**
   - Frequency: When you change email password
   - Fix: Generate new app password and update secrets

4. **Repository Renamed/Moved**
   - Frequency: Rare
   - Fix: Update [`config.yml`](config.yml) with new repository names

5. **Protected Branch Policies Changed**
   - Frequency: When repository settings are modified
   - Fix: Ensure bot has bypass permissions or adjust workflow

### Adjusting Scheduling

If workflows are running too frequently or at inconvenient times, you can adjust schedules:

**Edit workflow files:**
1. Open [`.github/workflows/daily-pr-monitor.yml`](.github/workflows/daily-pr-monitor.yml)
2. Find the `cron` schedule line:
   ```yaml
   schedule:
     - cron: '0 12 * * 1-5'  # 12:00 UTC = 7:00 AM EST
   ```
3. Modify using [cron syntax](https://crontab.guru):
   - `0 13 * * 1-5` = 8:00 AM EST (1 hour later)
   - `0 12 * * 1-3` = Mon-Wed only
   - `0 12 1-31/2 * 1-5` = Every other day

> ⚠️ **WARNING**: Use UTC time, not EST. Add/subtract 5 hours for EST conversion.

---

## Troubleshooting Guide

### Authentication Errors

#### Error: "Bad credentials" or "401 Unauthorized"

**Symptoms:**
```
Error: Bad credentials
Status code: 401
```

**Possible causes:**
1. GitHub PAT is incorrect or expired
2. PAT was regenerated but secret not updated
3. Token doesn't have required scopes

**Solutions:**

✅ **Verify token in secrets:**
1. Go to Settings → Secrets → Actions
2. Update `GH_ACCESS_TOKEN` with correct token
3. Re-run workflow to test

✅ **Check token expiration:**
1. Go to github.com → Settings → Developer settings → Personal access tokens
2. Check "Expires" column
3. If expired, generate new token and update secret

✅ **Verify token scopes:**
1. Click on token in GitHub settings
2. Verify these scopes are checked: `repo`, `workflow`, `read:org`, `read:user`, `user:email`
3. If missing scopes, create new token with correct scopes

#### Error: "Resource not accessible by integration" or "403 Forbidden"

**Symptoms:**
```
Error: Resource not accessible by integration
Status code: 403
```

**Possible causes:**
1. SSO not authorized for organization
2. Repository permissions changed
3. Token doesn't have specific scope needed

**Solutions:**

✅ **Configure SSO authorization:**
1. GitHub → Settings → Developer settings → Personal access tokens
2. Click "Configure SSO" next to your token
3. Authorize for MicrosoftDocs organization
4. Re-run workflow

✅ **Check repository permissions:**
1. Verify you have write access to repositories
2. Check that workflows are allowed to create PRs and approve
3. Repository Settings → Actions → General → Workflow permissions
4. Select "Read and write permissions"
5. Check "Allow GitHub Actions to create and approve pull requests"

### Email Not Sending

#### Error: "SMTPAuthenticationError: Username and Password not accepted"

**Symptoms:**
```
SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted')
```

**Possible causes:**
1. Wrong SMTP username or password
2. Need to use app password instead of account password
3. 2FA enabled but app password not created

**Solutions:**

✅ **For Gmail:**
1. Verify 2FA is enabled at myaccount.google.com/security
2. Generate new app password at myaccount.google.com/apppasswords
3. Update `SMTP_PASSWORD` secret with app password (no spaces)
4. Ensure `SMTP_USERNAME` is your full Gmail address

✅ **For Office 365:**
1. Verify SMTP authentication is enabled (contact IT admin)
2. Try using account password first
3. If MFA is required, get app password from IT admin
4. Update `SMTP_PASSWORD` secret

#### Error: Connection timeout

**Symptoms:**
```
TimeoutError: [Errno 110] Connection timed out
```

**Possible causes:**
1. Wrong SMTP server address
2. Wrong port number
3. Firewall blocking outbound SMTP
4. GitHub Actions runner network issue

**Solutions:**

✅ **Verify SMTP settings:**
1. Double-check `SMTP_SERVER` secret:
   - Gmail: `smtp.gmail.com`
   - O365: `smtp.office365.com`
2. Verify `SMTP_PORT` secret:
   - Try `587` (TLS - most common)
   - Try `465` (SSL - if 587 fails)

✅ **Test locally:**
1. Run the Python SMTP test script from section B
2. If it works locally but not in Actions, might be network issue
3. Consider using alternative SMTP provider (SendGrid, AWS SES)

#### Emails Going to Spam

**Symptoms:**
- Workflow succeeds but email not in inbox
- Email found in spam/junk folder

**Solutions:**

✅ **Add sender to contacts:**
1. Add `SMTP_EMAIL` address to your email contacts
2. Mark one email as "Not Spam"
3. Future emails should arrive in inbox

✅ **Check SPF/DKIM:**
1. For Gmail: Ensure "Less secure app access" is NOT needed
2. Use app password instead of account password
3. Consider using dedicated transactional email service

### Rate Limit Errors

#### Error: "API rate limit exceeded"

**Symptoms:**
```
Error: API rate limit exceeded for user
Rate limit: 0/5000
```

**Possible causes:**
1. Too many API requests in short time
2. Another process using same token
3. Workflow processing hundreds of PRs

**Solutions:**

✅ **Check rate limit status:**
1. View monthly report email for rate limit stats
2. GitHub gives 5000 requests/hour for authenticated users
3. Workflow has automatic retry with exponential backoff

✅ **Wait for reset:**
1. Rate limit resets every hour
2. Error message shows reset time
3. Workflow will automatically retry

✅ **Reduce API calls:**
1. If processing many PRs, consider running less frequently
2. Adjust cron schedule to run less often
3. Limit number of repositories in [`config.yml`](config.yml)

### Git Operations Fail

#### Error: "Push rejected" or "Protected branch"

**Symptoms:**
```
! [remote rejected] main -> main (protected branch hook declined)
error: failed to push some refs
```

**Possible causes:**
1. Branch protection rules prevent bot from pushing
2. PAT doesn't have bypass permissions
3. Required status checks not passing

**Solutions:**

✅ **Configure branch protection bypass:**
1. Repository Settings → Branches → Branch protection rules
2. Edit protection rule for main/master
3. Under "Allow specified actors to bypass", add bot user
4. Or: Uncheck "Include administrators" if using admin token

✅ **Use pull request workflow:**
1. Weekly scanner creates PRs instead of direct commits
2. This is the default behavior - PRs can be reviewed and merged
3. No special permissions needed

### Python Errors

#### Error: "ModuleNotFoundError"

**Symptoms:**
```
ModuleNotFoundError: No module named 'github'
```

**Possible causes:**
1. Dependencies not installed
2. Requirements file missing or incomplete
3. Cache corruption

**Solutions:**

✅ **Verify requirements.txt:**
1. Check [`requirements.txt`](requirements.txt) exists
2. Contains all needed packages: `PyGithub`, `PyYAML`, `pandas`, `jinja2`, `GitPython`
3. Re-run workflow (will reinstall dependencies)

✅ **Clear workflow cache:**
1. Actions → Caches → Delete all caches
2. Re-run workflow to rebuild cache

#### Error: Import errors in automation modules

**Symptoms:**
```
ImportError: cannot import name 'GitHubClient' from 'automation.core.github_client'
```

**Possible causes:**
1. Code files missing or corrupted
2. Wrong Python path
3. Syntax errors in code

**Solutions:**

✅ **Verify automation directory structure:**
1. Check that [`automation/`](automation/) directory exists
2. Verify [`automation/core/github_client.py`](automation/core/github_client.py) exists
3. Check for `__init__.py` files in automation directories

---

## Rollback Procedures

If automation is causing issues, you can quickly disable or rollback.

### Emergency: Disable All Automation

**Fastest method (5 seconds):**

1. Go to **Actions** tab
2. Click each workflow in sidebar:
   - Daily PR Monitor
   - Weekly Snippet Scanner
   - Monthly Maintenance Report
3. Click **⋯** menu → **Disable workflow**

All scheduled runs will stop immediately. Manual triggers still work if you need to run something.

### Temporary: Enable Dry-Run for All Workflows

If you want automation to keep running but not make changes:

**Edit workflow environment variables:**

1. Open `.github/workflows/daily-pr-monitor.yml`
2. Find the `env` section at line 49:
   ```yaml
   DRY_RUN: ${{ inputs.dry_run || 'false' }}
   ```
3. Change to:
   ```yaml
   DRY_RUN: 'true'  # Force dry-run mode
   ```
4. Repeat for [`weekly-scanner.yml`](.github/workflows/weekly-scanner.yml) and [`monthly-report.yml`](.github/workflows/monthly-report.yml)
5. Commit changes

Now all workflows run in dry-run mode - they'll analyze and report but not make changes.

### Manual Task Execution

If automation fails, you can perform tasks manually:

**Manual PR Review:**
1. Go to each code repository
2. Filter PRs by: `is:pr is:open review-requested:@me`
3. Review and approve safe PRs manually

**Manual CODEOWNERS Update:**
1. Run scanner locally: `python -m automation.workflows.weekly_scanner --dry-run`
2. Review generated files in `outputs/`
3. Manually create PRs with CODEOWNERS updates

**Manual Report Generation:**
1. Run report locally: `python -m automation.workflows.monthly_report --dry-run`
2. Review HTML report
3. Email report manually

### Restore Previous Version

If a code change broke automation:

1. Go to **Actions** tab → Click failed workflow
2. Note the commit hash where it started failing
3. Go to **Code** tab → Click "X commits"
4. Find the last working commit (before failures)
5. Click **<>** (Browse files at this point in history)
6. Click **⋯** → **Create branch from this commit**
7. Name it `rollback-working-automation`
8. Create PR to merge rollback branch into main
9. Merge PR to restore working version

---

## Advanced Configuration

### Customization Options

#### Changing Schedule Times

**Adjust when workflows run:**

Edit cron schedules in workflow files. Times are in UTC.

```yaml
# .github/workflows/daily-pr-monitor.yml
schedule:
  - cron: '0 13 * * 1-5'  # 8:00 AM EST instead of 7:00 AM
```

**Helpful cron patterns:**
- `0 12 * * 1-5` - Weekdays at 7 AM EST
- `0 12 * * 1,3,5` - Mon/Wed/Fri only
- `0 12,18 * * 1-5` - Twice daily (7 AM and 1 PM EST)
- `0 12 1,15 * *` - Twice monthly (1st and 15th)

Use [crontab.guru](https://crontab.guru) to test cron expressions.

#### Adjusting Auto-Approval Criteria

**Make approval more or less strict:**

Edit [`automation/workflows/daily_pr_monitor.py`](automation/workflows/daily_pr_monitor.py):

```python
# Current safety checks (around line 50)
safety_checks = [
    'no_deleted_referenced_files',
    'no_renamed_referenced_files', 
    'no_deleted_cells_in_modified_files'
]

# Add additional checks:
safety_checks.append('max_files_changed')  # Limit to PRs changing < X files
safety_checks.append('approved_authors')   # Only auto-approve known authors
```

> ⚠️ **WARNING**: Modifying approval criteria requires code changes. Test thoroughly with dry-run first.

#### Modifying Email Recipients

**Add multiple recipients:**

Update `NOTIFICATION_EMAIL` secret to comma-separated list:

```
recipient1@example.com,recipient2@example.com,recipient3@example.com
```

**Send different reports to different people:**

Edit [`automation/core/reporter.py`](automation/core/reporter.py) to customize recipient logic per workflow type.

#### Adding Additional Safety Checks

**Example: Require specific file patterns:**

In [`automation/workflows/daily_pr_monitor.py`](automation/workflows/daily_pr_monitor.py):

```python
def is_safe_to_approve(pr_analysis):
    # Existing checks...
    
    # New check: Only auto-approve if changes are in /samples directory
    all_files_in_samples = all(
        file.startswith('samples/') 
        for file in pr_analysis['changed_files']
    )
    
    if not all_files_in_samples:
        pr_analysis['safety_issues'].append(
            "Changes outside /samples directory"
        )
        return False
    
    return True
```

#### Customizing Report Templates

**Modify email appearance:**

Edit HTML templates in [`automation/templates/`](automation/templates/):
- [`daily_report.html`](automation/templates/daily_report.html)
- [`weekly_report.html`](automation/templates/weekly_report.html)
- [`monthly_report.html`](automation/templates/monthly_report.html)

Templates use Jinja2 syntax. Example:

```html
<h1>Custom Report Header</h1>
<p>Total PRs: {{ total_prs }}</p>

{% for pr in approved_prs %}
  <div class="pr-item">
    <a href="{{ pr.url }}">{{ pr.title }}</a>
  </div>
{% endfor %}
```

### Performance Tuning

#### Adjusting API Rate Limit Handling

**Modify retry behavior:**

Edit [`automation/core/github_client.py`](automation/core/github_client.py):

```python
# Current: Exponential backoff with 3 retries
max_retries = 3
backoff_factor = 2  # Wait 1s, 2s, 4s between retries

# More aggressive: 5 retries, faster
max_retries = 5
backoff_factor = 1.5  # Wait 1s, 1.5s, 2.25s...
```

#### Parallel Processing Options

**Process repositories concurrently:**

Edit [`automation/workflows/weekly_scanner.py`](automation/workflows/weekly_scanner.py):

```python
from concurrent.futures import ThreadPoolExecutor

# Sequential (current)
for repo in repositories:
    process_repository(repo)

# Parallel (faster, but uses more API quota)
with ThreadPoolExecutor(max_workers=3) as executor:
    executor.map(process_repository, repositories)
```

> ⚠️ **WARNING**: Parallel processing increases API rate limit usage significantly.

#### Caching Strategies

**Cache frequently accessed data:**

GitHub Actions automatically caches pip dependencies. To add more caching:

```yaml
# In workflow file
- name: Cache analysis results
  uses: actions/cache@v4
  with:
    path: |
      outputs/
      .cache/
    key: analysis-${{ github.run_id }}
    restore-keys: analysis-
```

---

## Security Best Practices

### Token Rotation Schedule

**Recommended schedule:**

1. **Initial Setup**: Create PAT with 90-day expiration
2. **30 Days Before Expiry**: Monthly report will send warning
3. **7 Days Before Expiry**: Generate new PAT
4. **Update Secret**: Replace `GH_ACCESS_TOKEN` with new token
5. **Revoke Old**: After confirming new token works, revoke old one

**Set calendar reminders:**
- 30 days before expiration: Review and prepare
- 7 days before expiration: Generate and test new token
- Day before expiration: Update secret and verify

### Principle of Least Privilege

**Token permissions:**

✅ **DO grant:**
- `repo` - Required for reading/writing repository content
- `workflow` - Required for triggering workflows
- `read:org` - Required for organization access
- `read:user` - Required for user information

❌ **DO NOT grant:**
- `admin:org` - Not needed, gives too much power
- `delete_repo` - Never needed for automation
- `admin:repo_hook` - Not needed for this automation
- `admin:public_key` - Not needed

**Email permissions:**

✅ **DO:**
- Use app-specific password, not account password
- Restrict to single mailbox if possible
- Use dedicated "bot" email account

❌ **DO NOT:**
- Use admin email credentials
- Share credentials across multiple systems
- Grant full OAuth scopes

### Securing SMTP Credentials

**Best practices:**

1. **Use App Passwords**: Never use your main account password
2. **Dedicated Email**: Consider creating `docs-automation@example.com` for bot emails
3. **Read-Only Mailbox**: If provider supports it, limit to send-only permissions
4. **Monitor Usage**: Watch sent items for unauthorized emails
5. **Rotate Regularly**: Change app passwords every 6 months

### Audit Log Review

**Monthly security check:**

1. Go to repository **Settings** → **Security** → **Audit log**
2. Filter by: `action:workflow` or `action:secret`
3. Review for unexpected changes:
   - Secrets accessed or modified
   - Workflows triggered by unknown users
   - Failed authentication attempts
4. Investigate any suspicious activity

**What to look for:**

✅ **Normal activity:**
```
Workflow run by github-actions
Secret GH_ACCESS_TOKEN read
Workflow completed successfully
```

⚠️ **Investigate these:**
```
Secret GH_ACCESS_TOKEN updated by unknown-user
Workflow triggered from suspicious branch
Multiple failed authentication attempts
```

### Revoking Access When Team Members Change

**When someone leaves the team:**

1. **Review their access:**
   - Did they have access to repository secrets?
   - Did they create the PAT used for automation?
   - Did they have admin access?

2. **Rotate credentials they had access to:**
   - Generate new GitHub PAT
   - Update `GH_ACCESS_TOKEN` secret
   - Change SMTP password if they knew it
   - Update all related secrets

3. **Review recent activity:**
   - Check audit logs for their actions
   - Review workflow runs they triggered
   - Verify no backdoors or scheduled jobs they created

**When someone joins the team:**

1. **Share documentation**, not credentials
2. **Grant minimal access** needed for their role
3. **Enable notifications** for their email if they need reports
4. **Don't share secrets** - they should create their own for local testing

---

## Quick Reference

### Required Secrets

| Secret | Required? | Example | Description |
|--------|-----------|---------|-------------|
| `GH_ACCESS_TOKEN` | **Yes** | `ghp_xxxx...` | GitHub Personal Access Token |
| `EMAIL_ENABLED` | No | `true` | Enable email notifications (default: false) |
| `SMTP_SERVER` | No* | `smtp.gmail.com` | Email server address |
| `SMTP_PORT` | No* | `587` | Email server port |
| `SMTP_USERNAME` | No* | `user@gmail.com` | Email username |
| `SMTP_PASSWORD` | No* | `xxxx xxxx xxxx` | Email password/app password |
| `SMTP_EMAIL` | No* | `user@gmail.com` | From address |
| `NOTIFICATION_EMAIL` | No* | `recipient@example.com` | To address(es) |

\* Only required if `EMAIL_ENABLED=true`

**Note:** Reports are always saved to `automation/reports/` and available as GitHub Actions artifacts, regardless of email configuration.

### Workflow Files

| File | Purpose | Schedule |
|------|---------|----------|
| [`daily-pr-monitor.yml`](.github/workflows/daily-pr-monitor.yml) | Auto-approve safe PRs | Mon-Fri 7 AM EST |
| [`weekly-scanner.yml`](.github/workflows/weekly-scanner.yml) | Update CODEOWNERS | Monday 6 AM EST |
| [`monthly-report.yml`](.github/workflows/monthly-report.yml) | Monthly statistics | 1st of month 5 AM EST |
| [`manual-trigger.yml`](.github/workflows/manual-trigger.yml) | Manual testing | On-demand |

### Key Commands

```bash
# Test SMTP connection
python -c "import smtplib; s=smtplib.SMTP('smtp.gmail.com',587); s.starttls(); s.login('user@gmail.com','password'); print('✅ Success')"

# Test GitHub token
curl -H "Authorization: token ghp_TOKEN" https://api.github.com/user

# Run workflow locally (dry-run)
export GH_ACCESS_TOKEN=ghp_xxx
export SMTP_USERNAME=user@gmail.com
export SMTP_PASSWORD=xxx
export NOTIFICATION_EMAIL=recipient@example.com
python -m automation.workflows.daily_pr_monitor --dry-run
```

### Support Resources

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Cron Schedule Tester**: https://crontab.guru
- **Gmail App Passwords**: https://myaccount.google.com/apppasswords
- **GitHub PAT Settings**: https://github.com/settings/tokens
- **Repository Actions**: https://github.com/YOUR_ORG/content-maintenance/actions

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-01-13  
**Maintained by**: Azure AI Documentation Team

---

## Need Help?

1. ✅ Check workflow logs in GitHub Actions
2. ✅ Review [Troubleshooting Guide](#troubleshooting-guide) section
3. ✅ Test with dry-run mode to isolate issues
4. ✅ Verify all secrets are configured correctly
5. ✅ Create an issue in the repository with logs attached

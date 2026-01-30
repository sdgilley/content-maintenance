# <img src="./media/maintenance.svg" width="46" height="46" style="vertical-align: text-bottom"> Code maintenance for Azure docs

> **📖 Getting Started:** Open [Daily and weekly tasks](docs/code-snippets.md) to start work on maintenance tasks.

## Overview

This repository contains scripts that help monitor code repos for changes that could break documentation builds and help identify when documentation updates are needed.

## How it Works

When sample code from a code repo is referenced in documentation, certain changes in the code repos can break the documentation build:

- **File deletion** - Referenced files are removed
- **File renaming** - Referenced file paths change  
- **Content changes** - Named sections or code blocks are modified or removed

Also, when a code file is updated, the document won't reflect the changes until a rebuild of the markdown file is triggered.

The scripts in this repository help prevent problems and identify necessary document updates.

## 🤖 Automation

**NEW!** This repository now includes automation for daily, weekly, and monthly maintenance tasks:

- **Daily PR Monitor** - Automatically monitors PRs across **3 code repositories** (Azure/azureml-examples, Azure-AI-Foundry/foundry-samples, Azure-Samples/azureai-samples), analyzes them for documentation impact, and auto-approves safe PRs (Mon-Fri 7 AM EST)
- **Weekly Snippet Scanner** - Scans docs and updates CODEOWNERS files (Mon 6 AM EST)
- **Monthly Reports** - Generates statistics and health reports (1st of month)

👉 **See [automation/README.md](automation/README.md) for setup and usage**

The automation reduces manual effort by ~80% while maintaining documentation quality through automated validation and safety checks.

## Documentation

* [Setup and overview](docs/setup.md)
* [Create token for authentication](docs/create-update-auth.md)
* [Daily and weekly tasks](docs/code-snippets.md)
* [Fix the problem](docs/fix-the-problem.md)
* **[Automation Guide](automation/README.md)** ⭐ **NEW**

## Run the scripts in this repository

### Configuration

All code repo configurations are centralized in `config.yml`. This file contains:

- Repository details (owner, repo name, team assignments)
- Search paths for each repository
- File naming patterns and output directories  
- Default settings for various scripts

To add or modify repositories, edit the `config.yml` file.

**Note:** The docs repo is currently hardcoded as `MicrosoftDocs/azure-ai-docs` in the scripts.  

### Installation

Scripts in this repository can be run locally or in a GitHub Codespace.

#### Local Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd content-maintenance
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up GitHub authentication:**
   ```bash
   export GH_ACCESS_TOKEN=your_github_token_here
   ```

See instructions in [Daily and weekly tasks](docs/code-snippets.md) for details.


## Scripts

<details>
<summary> Click to view script details </summary>

### Main Scripts

**[find-prs.py](find-prs.py)** - Find PRs requiring team review
- Identifies pull requests across multiple repositories that need review from documentation team members
- Generates a markdown report (`pr-review-report-DATE.md`) with clickable links
- **Usage:** `python find-prs.py`

**[find-snippets.py](find-snippets.py)** - Scan documentation for code references
- Creates `refs-found.csv` file used by other scripts
- Generates CODEOWNERS files for each repository
- **Usage:** `python find-snippets.py`

**[pr-report.py](pr-report.py)** - Analyze specific PR impact on documentation
- Evaluates whether a specific PR will cause documentation build issues
- Supports repository-specific arguments for targeting different code repos
- **Usage:**
  - `python pr-report.py 91` (for azureml-examples)
  - `python pr-report.py 169 ai` (for foundry-samples)
  - `python pr-report.py 267 ai2` (for azureai-samples)

**[merge-report.py](merge-report.py)** - Review recent merged PRs
- Shows PRs merged in the last N days (default: 8) that may require documentation updates
- **Usage:** `python merge-report.py` or `python merge-report.py 14`

### Utility Modules

These files provide functions used by the main scripts:

- **[config.py](utilities/config.py)** - Reads repository configurations from `config.yml`
- **[helpers.py](utilities/helpers.py)** - Common functions for snippet processing and file operations
- **[gh_auth.py](utilities/gh_auth.py)** - GitHub authentication and API interaction functions  
- **[find_pr_files.py](utilities/find_pr_files.py)** - Functions for analyzing PR file changes and documentation impact

</details>

## Workflow

1. **Initial Setup:** Run `find-snippets.py` to scan documentation and create the reference database
2. **Regular Monitoring:** Use `find-prs.py` to identify PRs requiring review
3. **PR Analysis:** Use `pr-report.py` to evaluate specific PRs before approval
4. **Post-Merge Review:** Use `merge-report.py` to identify documentation that may need updates after PRs are merged

## Repository Configuration

The monitored repositories are defined in `config.yml`:

- **foundry-samples** (microsoft-foundry/foundry-samples)
- **azureai-samples** (Azure-Samples/azureai-samples)  
- **azureml-examples** (Azure/azureml-examples)

Each repository configuration includes team assignments, search paths, and service categorizations for automated processing.

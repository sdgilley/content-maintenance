# Code maintenance for Azure docs

When using this process, you'll create PRs in each of the following repositories:

- **<img src="./media/code.svg" width="20" height="20" style="vertical-align: text-top"> Code Repo** - GitHub repositories where sample code is stored (Currently for ML and Foundry: azureml-examples, foundry-samples, and azureai-samples)
- **<img src="./media/docs.svg" width="18" height="18" style="vertical-align: text-top">  Docs Repo** - The MicrosoftDocs repository where documentation articles are stored - currently hardcoded to MicrosoftDocs/azure-ai-docs
- **<img src="./media/maintenance.svg" width="18" height="18" style="vertical-align: text-top">  Maintenance Repo** - The content maintenance repository you're viewing now, containing monitoring and reporting scripts

## Overview

This repository contains scripts that help monitor code repositories for changes that could break documentation builds and help identify when documentation updates are needed.

### How it Works

When sample code from a code repository is referenced in documentation, certain changes in the code repository can break the documentation build:

- **File deletion** - Referenced files are removed
- **File renaming** - Referenced file paths change  
- **Content changes** - Named sections or code blocks are modified or removed

Also, when a code file is updated, the document won't reflect the changes until a rebuild of the markdown file is triggered.

The scripts in this repository help prevent problems and identify necessary document updates:

- Scanning documentation for code references
- Monitoring pull requests in code repositories
- Providing review guidance for documentation team members
- Generating reports when referenced code is modified

## Documentation

* [Setup and overview](docs/setup.md) 
* [Create token for authentication](docs/create-update-auth.md)
* [Daily and weekly tasks](docs/code-snippets.md)
* [Fix the problem](docs/fix-the-problem.md)

## Run the scripts in this repository

### Configuration

All code repository configurations are centralized in `config.yml`. This file contains:

- Repository details (owner, repo name, team assignments)
- Search paths for each repository
- File naming patterns and output directories  
- Default settings for various scripts

To add or modify repositories, edit the `config.yml` file.

**Note:** The docs repository is currently hardcoded as `MicrosoftDocs/azure-ai-docs` in the scripts.  

### Installation

Scripts in this repository can be run locally or in a GitHub Codespace.

First create a GitHub personal access token and store it as a code secret.  See [Create/update a GitHub access token](docs/create-update-auth.md). 

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/sdgilley/content-maintenance?quickstart=1)

### Local Setup

<details>
<summary> Click to view local setup </summary>

For local execution, you'll need:

- Python 3.8 or later (check with `py -3 --version`)
- Git installed and configured
- A GitHub personal access token (see [authentication setup](docs/create-update-auth.md))

**Setup steps:**

1. Clone this repository
2. Create a virtual environment and install dependencies:

   ```bash
   py -3 -m venv .venv
   .venv\scripts\activate
   pip install -r requirements.txt
   ```

3. Store your GitHub access token as an environment variable:
   - Create a personal access token following steps in [Create/update a GitHub access token](docs/create-update-auth.md) 
   - Set the `GH_ACCESS_TOKEN` environment variable with your token

> ⚠️ **Important:** You must set the `GH_ACCESS_TOKEN` environment variable before running any scripts. 

</details>

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

- **foundry-samples** (Azure-AI-Foundry/foundry-samples)
- **azureai-samples** (Azure-Samples/azureai-samples)  
- **azureml-examples** (Azure/azureml-examples)

Each repository configuration includes team assignments, search paths, and service categorizations for automated processing.

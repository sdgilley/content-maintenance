# Code maintenance for Azure docs

- **Code Repositories** - GitHub repositories where sample code is stored (currently: azureml-examples, foundry-samples, and azureai-samples)
- **Docs Repository** - The MicrosoftDocs/azure-ai-docs repository where documentation articles are stored
- **This Repository** - The content maintenance repository you're viewing now, containing monitoring and reporting scripts

## Overview

This repository contains automated scripts that help maintain consistency between Azure documentation and sample code repositories. The scripts monitor code repositories for changes that could break documentation builds and help identify when documentation updates are needed.

### How it Works

When sample code from a code repository is referenced in documentation, certain changes can break the documentation build:

1. **File deletion** - Referenced files are removed
2. **File renaming** - Referenced file paths change  
3. **Content changes** - Named sections or code blocks are modified or removed

The scripts in this repository help identify these issues by:
- Scanning documentation for code references
- Monitoring pull requests in code repositories
- Generating reports when referenced code is modified
- Providing review guidance for documentation team members

## Documentation

* [Setup and overview](docs/setup.md) 
* [Create token for authentication](docs/create-update-auth.md)
* [Daily and weekly tasks](docs/code-snippets.md)
* [Fix the problem](docs/fix-the-problem.md)

## Configuration

All code repository configurations are centralized in `config.yml`. This file contains:

- Repository details (owner, repo name, team assignments)
- Search paths for each repository
- File naming patterns and output directories  
- Default settings for various scripts

To add or modify repositories, edit the `config.yml` file instead of hardcoding values in individual scripts.

**Note:** The docs repository is currently hardcoded as `MicrosoftDocs/azure-ai-docs` in the scripts.  

## Installation

Scripts in this repository can be run locally or in a GitHub Codespace.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/sdgilley/content-maintenance?quickstart=1)

### Local Setup

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

3. Set up your GitHub access token as an environment variable:
   - Create a personal access token following steps in [Create/update a GitHub access token](docs/create-update-auth.md) 
   - Set the `GH_ACCESS_TOKEN` environment variable with your token

> ⚠️ **Important:** You must set the `GH_ACCESS_TOKEN` environment variable before running any scripts. 

## Scripts

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

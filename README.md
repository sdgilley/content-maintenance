# Code maintenance for Azure docs

- **Code Repo** refers to the GitHub repository where code is stored. You can have multiple code repos (we currently have three).  
- **Docs Repo** refers the MicrosoftDocs repo where articles are stored.  At this time, the docs repo is hard coded as **MicrosoftDocs/azure-ai-docs** in the scripts, but this could be easily modified.
- **This Repo** refers to the content maintenance repository you're looking at right now.

The set of scripts here help us monitor the code repos for code changes that could break our docs build.  

Once code from a code repo is referenced in a doc, the following activities in the code repo can break the build:

1. The referenced file is deleted
1. The referenced file is renamed
1. A named section in the file is deleted or renamed

After a code repository has been configured, PRs that touch referenced files require a review from a member of the docs team.  A script will let you know if any problems are found in the PR to make review easy.

## Documentation

* [Setup and overview](docs/setup.md) 
* [Create token for authentication](docs/create-update-auth.md)
* [Daily and weekly tasks](docs/code-snippets.md)
* [Fix the problem](docs/fix-the-problem.md)

## Configuration of scripts in this repo

All code repository configurations are centralized in `config.yml`. This file contains:

- Repository details (owner, repo name, team assignments)
- Search paths for each repository  
- File naming patterns and output directories
- Default settings for various scripts

To add or modify repositories, edit the `config.yml` file.

At the moment, the docs repo is hard-coded as **MicrosoftDocs/azure-ai-docs** in the scripts.  

## Install instructions for this repo

Scripts in this repo are used to help us maintain our code references.  You can run them locally or in a Codespace.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/sdgilley/content-maintenance?quickstart=1) 

* Local execution.  If running locally, you'll need:

    * Python 3.8 or later installed on your machine.  You can check this by running `py -3 --version` in a command prompt.
    * Azure CLI installed and authenticated with `az login`
    * Create a python virtual environment and install requirements:

        ```bash
        py -3 -m venv .venv
        .venv\scripts\activate
        pip install -r requirements.txt
        ```
  
 > ⚠️ IMPORTANT.   Set a GH_ACCESS_TOKEN environment variable before running the scripts. See instructions at [Create/update a GitHub access token](docs/create-update-auth.md).  Then add the token to an environment variable called **GH_ACCESS_TOKEN**.


##  Script details

* [find-prs.py](find-prs.py) - Find PRs that need approval from your team. Use this to identify pull requests requiring review from team members across multiple repositories. The output will appear in pr-review-report-DATE.md.  You can delete the report when you're done with it.
    * Examples:
        * `python find-prs.py

* [find-snippets.py](find-snippets.py) 
    * creates the file refs-found.csv.  This file is used for both the pr-report and merge-report scripts.
    * create a CODEOWNERS file for each repo.  Use the content in this file to update the corresponding CODEOWNERS file in that repo.
    * Examples:
        * `python find-snippets.py` 

* [pr-report.py](pr-report.py) - 
    * Add argument `ai` for **foundry-samples**.
    * Add argument `ai2` for **azureai-samples**.  
    * No argument needed for **azureml-examples**.
Use this to evaluate whether a PR in the repo will cause problems in our docs build.  If you're using it for the first time in a while, first run [find-sippets.py](find-snippets.py) to get the most recent version of code snippets referenced by azure-ai-docs.
    * Examples:
        * `python pr-report.py 91` to check PR 91 in  **azureml-examples** repo.
        * `python pr-report.py 169 ai` to check PR 169 in **foundry-samples** repo. 
        * `python pr-report.py 267 ai2` to check PR 267 in **azureai-samples** repo.

* [merge-report.py](merge-report.py) -  Use to see what PRs in your repos have merged in the last N days that might require a docs update (default is 8 days). If you're using it for the first time in a while, first run [find-sippets.py](find-snippets.py) to get the most recent version of code snippets referenced by azure-ai-docs.
    * Examples:
        * `python merge-report.py` to check all repos.

### Utilities

These files provide functions used in the above scripts:

* [helpers.py](utilities/helpers.py) - functions used by find-snippets, pr-report, and merge-report
* [h_auth.py](utilities/gh_auth.py) - function used by pr-report and merge-report to authenticate to github.
* [find_pr_files.py](utilities/find_pr_files.py) - function used from merge_report, finds PRs merged in the last N days that have doc references. 
* [config.py](utilities/config.py) - reads the config.yml file to get information about the repositories to monitor
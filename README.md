# Code maintenance for Azure docs

## Documentation

* [Setup and overview](docs/setup.md) 
* [Create token for authentication](docs/create-update-auth.md)
* [Daily and weekly tasks](docs/code-snippets.md)
* [Fix the problem](docs/fix-the-problem.md)


## Scripts

Scripts in this repo are used to help us maintain our code references.  You can run them locally or in a Codespace.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/sdgilley/content-maintenance?quickstart=1) 

* Local execution.  If running locally, you'll need:

    * Python 3.8 or later installed on your machine.  You can check this by running `py -3 --version` in a command prompt.
    * Azure CLI installed and authenticated with `az login`
    * Create a python virtual environment and install requirements:

        ```
        py -3 -m venv .venv
        .venv\scripts\activate
        pip install pyGithub pandas
        ```
  
 > ⚠️ IMPORTANT.   Set a GH_ACCESS_TOKEN environment variable before running the scripts. See https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens to create a token.  Then add the token to an environment variable called **GH_ACCESS_TOKEN**.


##  Scripts in this repository

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

* [merge-report.py](merge-report.py) -  Use this to see what PRs in azureml-examples, foundry-samples, and azureai-samples have merged in the last N days that might require a docs update (default is 8 days). If you're using it for the first time in a while, first run [find-sippets.py](find-snippets.py) to get the most recent version of code snippets referenced by azure-ai-docs.
    * Examples:
        * `python merge-report.py` to check all repos.

The following files provide functions used in the above scripts:

* [utilities.py](utilities.py) - functions used by find-snippets, pr-report, and merge-report
* [auth_request.py](auth.py) - function used by pr-report and merge-report to authenticate to github.
    
    You'll need to set a GH_ACCESS_TOKEN environment variable before using auth_request.py. See https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens to create a token.  Then add the token to an environment variable called GH_ACCESS_TOKEN.

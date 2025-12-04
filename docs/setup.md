# Setup and overview

## Set up your environment to run the scripts

To run the scripts, create a GitHub access token.  Then run the scripts either in CODESPACES or locally.

<details>
<summary> Create a GitHub personal access token</summary>

First create a GitHub personal access token following instructions in [Create/update a GitHub access token](create-update-auth.md). 

> ⚠️ **Important:**  Don't forget to configure SSO for MicrosoftDocs.

</details>

<details>
<summary> Run scripts in GitHub CODESPACES</summary>

Once your secret is stored, perform all maintenance tasks using the button below to open this repo in GitHub Codespaces. No additional setup needed. Use the Codespace terminal to run the scripts.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/sdgilley/content-maintenance?quickstart=1)

</details>

<details>
<summary> Run scripts locally </summary>

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

## Add a new code repo (done once per code repo)

The process of monitoring a code repoository involves some initial setup:

1. (Docs) Create GitHub team in appropriate organization.  The team must be in the same organization as the code repository.
    * In order to create a team, you must be a member of the org.  In order to add someone to a team, they must be members of the org.
    * Join an org at `https://repos.opensurce.microsoft.com/orgs/{ORG-NAME}`. (For example, https://repos.opensource.microsoft.com/orgs/azure)
    * Create a team at `https://github.com/orgs/{ORG-NAME}/teams/`. (For example, https://github.com/orgs/azure/teams/)
    * Add members to the team once they've joined the org.
1. (Docs) Add information about the repo to [config.yml](../config.yml) in the maintenance repo
1. (Code repository admin) To configure a code repository:

    * Add the above GH team with write permissions into the repository.
    * Create a CODEOWNERS file in the repository.  
    * Require approval from a code owner before the author can merge a pull request. Require a reapproval if subsequent pushes made.

## Process overview

Once the repo is configured, a team member is responsible for the maintenance task.  (We rotate on a monthly basis for AI Platform Docs.)

1. (Daily) Monitor and approve PRs.  
    * Use `find-prs.py` to find them.  
    * Use `pr-report.py` to check for problems.  
    * Fix any problems as needed before approval.  (See [Fix the problem](fix-the-problem.md)).
1. (Weekly) Keep CODEOWNERS file(s) up to date with `find-snippets.py`.
1. (Weekly) Update docs for recent code changes with `merge-report.py`

See [Maintain code snippets in Azure docs](code-snippets.md) **Daily** and **Weekly** tasks for more details.

## ML and Foundry details

Code samples we monitor are currently in one of these three repos:

| Docset | Code Repo | Docs Team |
| -- | -- | -- |
| Foundry | https://github.com/azure-ai-foundry/foundry-samples | [@azure-ai-foundry/ai-platform-docs](https://github.com/orgs/azure-ai-foundry/teams/ai-platform-docs/) |
| Foundry | https://github.com/Azure-Samples/azureai-samples | [@azure-samples/ai-platform-docs](https://github.com/orgs/azure-samples/teams/ai-platform-docs/) |
| ML | https://github.com/Azure/azureml-examples | [@azure/ai-platform-docs](https://github.com/orgs/azure/teams/ai-platform-docs/) |

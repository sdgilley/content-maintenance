# Maintain code snippets in Azure docs

Run these scripts either locally or in GitHub Codespaces

First create a GitHub personal access token and store it as a code secret (if using Codespaces) or environment variable (for running locally).  
See [Create/update a GitHub access token](docs/create-update-auth.md) for complete instructions. 

> ⚠️ **Important:**  Don't forget to configure SSO for MicrosoftDocs.

### GitHub Codespaces

<details>
<summary> Click to view GitHub codespaces info</summary>

Once your secret is stored, perform all maintenance tasks using the button below to open this repo in GitHub Codespaces. No additional setup needed. Use the Codespace terminal to run the scripts.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/sdgilley/content-maintenance?quickstart=1)

</details>

### Local Setup

<details>
<summary> Click to view local setup info</summary>

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


## Daily tasks - monitor the Code Repos


### Check PRs

1. Check for PRs that need review:

    ```
    python find-prs.py
    ```

1. Review the output in pr-review-report-DATE.md.  Set to Preview (Ctrl=Shift-V) to make it easier to read.
1. For each PR, use the python command shown in the Report column.
1. Approve if no issues reported.
1. If issues are present, see [Fix the Problem](fix-the-problem.md).

### Check messages

1. Check for message at the [AI Platform Docs teams channel](https://teams.microsoft.com/l/channel/19%3AHhf4F_YfPn3kYGdmWvePNwlbF5-RR8wciQEUwwrcggw1%40thread.tacv2/General?groupId=fdaf4412-8993-4ea6-a7d4-aeaded7fc854&tenantId=72f988bf-86f1-41af-91ab-2d7cd011db47).

1. If you're asked to review a PR, in the terminal, run:

    * for azureml-examples repo:

        ```bash
        python pr-report.py <PR number> 
        ```

    * for foundry-samples repo:

        ```bash
        python pr-report.py <PR number> ai
        ```

    * for azureai-samples repo:

        ```bash
        python pr-report.py <PR number> ai2
        ```

## Weekly tasks - update files

### Search code for updates

Keep the appropriate files up to date with the find-snippets script.

1. Run this script (takes approximately 10-12 minutes for the current three code repos):

    ```bash
    python find-snippets.py
    ```

### Update codeowners files - <img src="../media/maintenance.svg" width="32" height="32" style="vertical-align: text-top"> Maintenance Repo

1. If changes to any `*.txt` files appear, commit them to sdgilley/content-maintenance. 

### Update codeowners files - <img src="../media/code.svg" width="32" height="32" style="vertical-align: text-top"> Code Repos

1. If changes to CODEOWNERS-azureml-examples.txt appear, copy the content and commit to [azureml-examples CODEOWNERS](https://github.com/Azure/azureml-examples/blob/main/.github/CODEOWNERS) file.
1. If changes to CODEOWNERS-foundry-samples.txt appear, copy the content and commit to [foundry-samples CODEOWNERS](https://github.com/Azure-AI-Foundry/foundry-samples/blob/main/.github/CODEOWNERS) file.
1. If changes to CODEOWNERS-azureai-samples.txt appear, copy the content and commit to [azureai-samples CODEOWNERS](https://github.com/Azure-Samples/azureai-samples/blob/main/.github/CODEOWNERS) file.

### Update docs - <img src="../media/docs.svg" width="32" height="32" style="vertical-align: text-top"> Docs Repo

When code changes in a code repository, the corresponding document won't update until the next time it's built.  Find related documents by using the merge report.  A change in metadata in these articles will force a build, allowing it to update to the latest code content.

1. Run the merge report.  If last run 7 days ago, simply run:

    ```bash
    python merge-report.py 
    ```

    The report will show PRs merged in the last 8 days.  (The extra day insures that you don't miss a merge that happened after your report 7 days ago.)  
1. If longer than 7 days since last run, add a days parameter to the command.:

    ```bash
    python merge-report.py <days>
    ```

1. Modify the files in azure-ai-docs-pr as listed in the report.  If there are more than 10 files, break it into multiple PRs to be eligible for auto-merge. (You'll see three separate sections, make sure you look at results from all three.)

1. You might want to copy the report output to your work item.  This will let you see when it was last run, so that you can adjust days accordingly for your next report.

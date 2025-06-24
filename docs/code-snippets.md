# Maintain code snippets in Azure docs

This repository contains scripts to help maintain code snippets in Azure documentation. 

The scripts are designed to be run in a GitHub Codespace.
https://github.com/pulls?q=is%3Apr+is%3Aopen+user-review-requested%3A%40me
If you're evaluating a file for Machine Learning FRESHNESS, see the [Freshness Dashboard](https://sdgilley.github.io/learn-tools/).

## Setup for Codespaces

Follow the steps to [create/update a GitHub access token](create-update-auth.md) for use with the scripts in this repo.

Once your secret is stored, perform all maintenance tasks using the button below to open this repo in GitHub Codespaces. No additional setup needed. Use the Codespace terminal to run the scripts.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/sdgilley/code-maintenance?quickstart=1)

## Daily tasks


### Check PRs

1. Check for PRs that need review:

    ```
    python find-prs.py
    ```

1. Review the output in pr-review-report-DATE.md.  Set to Preview to make it easier to read.
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

## Weekly tasks

### Update snippet references and codeowners files

1. Run this script (takes approximately 12 minutes ):

    ```bash
    python find-snippets.py
    ```

1. If changes to CODEOWNERS-xx.txt and refs-found-xx.csv files appear, commit them to sdgilley/content-maintenance. You can do this from a Codespace, but if you're on main, you'll first need to switch to a new branch. Create a PR and let me know so I can merge it. (If you're the one maintaining the snippets for the month, no hurry on the PR - just make sure you commit changes before the end of the month so the next person has the right versions of these files.)
1. You can ignore any other txt or csv files that are changed.
1. If changes to CODEOWNERS-azureml-examples.txt appear, copy the content and commit to [azureml-examples CODEOWNERS](https://github.com/Azure/azureml-examples/blob/main/.github/CODEOWNERS) file.
1. If changes to CODEOWNERS-foundry-samples.txt appear, copy the content and commit to [azureml-examples CODEOWNERS](https://github.com/Azure-AI-Foundry/foundry-samples/blob/main/.github/CODEOWNERS) file.
1. For now, you can ignore changes to CODEOWNERS-azureai-samples.txt.  
1. If temp-fix is not listed as one of the active branches, [update the temp-fix branch](#temp-fix) to keep it current.

### Update docs

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

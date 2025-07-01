# Setup and overview

The process of monitoring a code repoository involves some initial setup:

1. (Docs) Create GitHub team in appropriate organization.  The team must be in the same organization as the code repository.
    * In order to create or add someone to a team, you must first be members of the org. Each member can join the org at https://repos.opensurce.microsoft.com/orgs/{ORG-NAME}. (For example, https://repos.opensource.microsoft.com/orgs/azure)
    * Create a team at https://github.com/orgs/{ORN-NAME}/teams/. (For example, https://github.com/orgs/azure/teams/)
    * Add members to the team once they've joined the org.

1. (Code repository admin) To configure a code repository:

    * Add the above GH team with write permissions into the repository.
    * Create a CODEOWNERS file in the repository.  
    * Require approval from a code owner before the author can merge a pull request. Require a reapproval if subsequent pushes made.

Once the repo is configured, a team member is responsible for the maintenance task.  (We rotate on a monthly basis for AI Platform Docs.)

1. Monitor and approve PRs.  
    * Use `find-prs.py` to find them.  
    * Use `pr-report.py` to check for problems.  
    * Fix any problems as needed before approval.  (See [Fix the problem](fix-the-problem.md)).
1. Keep CODEOWNERS file(s) up to date with the weekly script, `find-snippets.py`.

See [Maintain code snippets in Azure docs](code-snippets.md) **Daily** and **Weekly** tasks for more details.

## ML and Foundry details

Code samples we monitor are currently in one of these three repos:

| Docset | Code Repo | Docs Team |
| -- | -- | -- |
| Foundry | https://github.com/azure-ai-foundry/foundry-samples | [@azure-ai-foundry/ai-platform-docs](https://github.com/orgs/azure-ai-foundry/teams/ai-platform-docs/) |
| Foundry | https://github.com/Azure-Samples/azureai-samples | [@azure-samples/ai-platform-docs](https://github.com/orgs/azure-samples/teams/ai-platform-docs/) |
| ML | https://github.com/Azure/azureml-examples | [@azure/ai-platform-docs](https://github.com/orgs/azure/teams/ai-platform-docs/) |

# Fix the problem 

We currently have three code repos:

| Docs reference | Code repo |
| ---------------|-----------|
| ~/azureml-examples-main | https://github.com/Azure/azureml-examples |
| ~/foundry-samples-main | https://github.com/microsoft-foundry/foundry-samples |
| ~/azureai-samples-main | https://github.com/azure-samples/azureai-samples |

When the pr-report shows a problem in a PR in any of these repos, you need to fix the problem before you can approve the PR.

The problems that will break our build are:

* A file that we reference is being deleted or renamed.
* An id or notebook cell name is being deleted.

Before the PR can be approved, we need to make sure that the docs that reference these files or ids/names are updated.  

There are various ways to fix the problem, depending on the situation.  These are outlined in the sections below.

> ⚠️ IMPORTANT! During a docs freeze (before Build or Ignite), try not to approve any PRs that have problems - it's harder to fix on our end during this time.  If they deleted a file, have them put it back.  If they deleted an ID or cell name, have them put it back, even if there are no contents in the section or cell.
> If the HAVE to make the change, the doc fix first has to merge into **all** the release branches before we can approve the PR.
> 

## Push back - why is the change needed?

The first question I'd ask in a PR is why the change is necessary.  Remember, these aren't code changes, they are deletions.  It may be that the author didn't think the comments or cell name mattered and just deleted them.  If that's the case, ask them to put the comments back.  

## No fix necessary

In some cases, the name of the notebook cell or id that was deleted is not actually used in the referencing file.  In that case, you can approve the PR without making any changes. This does sometimes happen.  

### Example

You'll see the following output from `python pr-report.py 2779`:

```
MMODIFIED FILES: 4
Potential problems found in 2 files.
Fix these references in azure-ai-docs-pr before approving this PR:

Modified File: sdk/python/endpoints/batch/deploy-pipelines/hello-batch/sdk-deploy-and-test.ipynb
  Referenced in:
   https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/machine-learning/how-to-use-batch-pipeline-deployments.md
   Notebook cells deleted: 1
   * previews
*azureml-examples temp-fix branch has the same version of this file as main

Modified File: sdk/python/endpoints/batch/deploy-pipelines/training-with-components/sdk-deploy-and-test.ipynb
  Referenced in:
   https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/machine-learning/how-to-use-batch-training-pipeline.md
   Notebook cells deleted: 1
   * python38-azureml
*azureml-examples temp-fix branch has the same version of this file as main
```

But when you open https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/machine-learning/how-to-use-batch-pipeline-deployments.md, you won't find the cell name "previews" referenced anywhere in the document. So there's nothing to fix here.

Likewise, when you open https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/machine-learning/how-to-use-batch-training-pipeline.md, you won't find a reference to a cell named "python38-azureml".  So again, there is nothing to fix here.

## Quick fix in azure-ai-docs-pr

If you can quickly fix the reference in azure-ai-docs-pr, do so.  For example, if the reference is no longer necessary, remove it.  Or perhaps if it is a single line of code, replace the reference with the hard-coded line.  (Don't do this for anything longer than one or two lines, though.)

1. Create a PR in azure-ai-docs-pr to apply this fix.  
2. After your azure-ai-docs-pr PR with the fix is merged, you can approve the azureml-examples PR.

> ⚠️ NOTE FOR RELEASE BRANCHES: During Build or Ignite, when there are release branches, this process is more complex. All those release branches also need your update.  Coordinate with the Build/Ignite roadshow owner before you approve the code repo's PR.  They'll need to sync main into all release branches before you can approve the original code repo PR.

## Move to a temporary branch

If you can't do a quick fix, follow this process:

1. If temp-fix has the same version of the file, skip 2 and proceed to #3.
1. If temp-fix does not have the same version of the file, use the steps below to first [update the temp-fix branch](#temp-fix) in the code repo.
1. <a name="three"></a> Create a PR in azure-ai-docs-pr to use the temp-fix branch, i.e., **~/azureml-examples-temp-fix** instead of **~/azureml-examples-main** for the reference(s) to the problem file/id(s).
1. Once your PR in azure-ai-docs-pr is merged to main, you can approve the code repo PR.
   > ⚠️ NOTE FOR RELEASE BRANCHES: During Build or Ignite, when there are release branches, this process is more complex. All those release branches also need your update.  Coordinate with the Build/Ignite roadshow owner before you approve the azureml-examples PR.  They'll need to sync main into the release branches before you can approve the original code repo PR.
1. Create a work item to update these articles to again use ~/azureml-examples-main or ~/foundry-samples-main after the azureml-examples PR has merged.  We want to minimize the time that an article references a file on the temp-fix branch.

### Example

You'll see the following output from `python pr-report.py 2888`:

```
Potential problems found in 1 files.

Modified File: cli/setup.sh
  Referenced in:
   https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/machine-learning/how-to-deploy-automl-endpoint.md
   https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/machine-learning/how-to-configure-cli.md
   Code cells deleted: 2
   * # <az_configure_defaults>
   * # </az_configure_defaults>
*azureml-examples temp-fix branch has the same version of this file as main
```

There are two docs that reference the file cli/setup.sh.  The ID `az_configure_defaults` is being deleted in the PR.

My first question would to be ask the PR author why they are deleting this comment or the section.  Is it no longer necessary?  If so, delete the references to it in the docs as well, (https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/machine-learning/how-to-deploy-automl-endpoint.md & 
   https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/machine-learning/how-to-configure-cli.md)

If it was a mistake (they didn't think the comments mattered and just deleted them), ask them to put the comments back.

If the deletion was for some good reason, the temp-fix branch contains the same version of the file as main.  So you can switch the references in the docs to point to the temp-fix branch (instead of main) for this particular id.  That is, change:

:::code language="azurecli" source="~/azureml-examples-**main**/cli/setup.sh" id="az_configure_defaults":::

to:

:::code language="azurecli" source="~/azureml-examples-**temp-fix**/cli/setup.sh" id="az_configure_defaults":::

Once your azure-ai-docs-pr change has merged to main, you can approve the PR in azureml-examples.  

Once the azureml-examples change has merged, you can go back to the docs and update the references to point back to main.  We want to minimize the time that the docs reference the temp-fix branch.

## <a name="temp-fix"></a> Update the temp-fix branch

Before you make any changes to the temp-fix branch in azureml-examples, see if it currently being used for any docs in azure-ai-docs-pr.

Run `python find-snippet.py ml` to see if the temp-fix is one of the active branches. As of now, we don't have temp-fix branches in the other repos.  Create one if necessary.  To use it in our documentation, add to the .openpublishing.publish.config.json file.

### temp-fix is NOT an active branch
    
when the temp-fix branch is not in use, you can simply update the files in the temp-fix branch to the latest versions from the main branch.

1. In [azureml-examples](https://github.com/Azure/azureml-examples) - checkout the branch temp-fix.
1. Pull from origin/main.  
1. Commit changes in the branch.  For the commit message, use "Update from main".
1. Push your changes to origin/temp-fix.

### temp-fix IS an active branch

When temp-fix is being used, you don't want to mess with other referenced files that haven't been fixed yet. So you can't just pull all of main into temp-fix. Instead, add just the main branch version of the file(s) that are causing the problem to the temp-fix branch:
    
1. Checkout the **main** branch in azureml-examples.
1. COPY the file(s) from the main branch that are causing you to reject the PR. Stash them somewhere on your computer outside the azureml-examples repo.
1. Checkout the **temp-fix** branch in azureml-examples.
1. Paste those files from main back to the repo folder.  
1. At this point, the only changes in the temp-fix branch should be the files you just pasted in. Commit these changes to the temp-fix branch. For the commit message, reference the PR number that you are fixing.
1. Push your changes to origin/temp-fix. This will update the files you want to reference in the temp-fix branch to their latest versions prior to the new PR.
1. Now proceed to [step 3 above](#three).


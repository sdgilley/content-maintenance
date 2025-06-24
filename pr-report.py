"""
This script shows the files deleted or modified in a PR in azureml-examples
If any of these files are referenced azure-ai-docs-pr, 
the corresponding file (labeled referenced_from_file) is also shown.

To run this script, first run find_snippets.py to create the snippets.csv file.
Then run from command line:

    python pr-report.py <PR number> 


To decide if the PR is safe to merge:
* If any deleted cell in a MODIFIED file is referenced in azure-ai-docs-pr, PR is not ready to merge
* If any DELETED file is referenced, PR is not ready to merge.

"""

import pandas as pd
import sys
from utilities import gh_auth as a
from utilities import helpers as h
import os

# read arguments from command line - pr and optionally, whether to authenticate
import argparse
debug = False
parser = argparse.ArgumentParser(
    description="Process a PR number."
)  # Create the parser
# Add the arguments
parser.add_argument("pr", type=int, help="The PR number you are interested in.")
parser.add_argument("repo", type=str, nargs='?', default="ml", choices=["ai", "ai2", "ml"], help="Which repo: 'ai', 'ai2', or 'ml'")
args = parser.parse_args()  # Parse the arguments
pr = args.pr
repo_arg = args.repo.lower()
# fix truncation?
pd.set_option("display.max_colwidth", 500)

# form the URL for the GitHub API
if repo_arg == "ml":
    repo_name = "azureml-examples"
    owner_name = "Azure"
elif repo_arg == "ai":
    repo_name = "foundry-samples"
    owner_name = "Azure-AI-Foundry"
elif repo_arg == "ai2":
    repo_name = "azureai-samples"
    owner_name = "Azure-Samples"

url = f"https://api.github.com/repos/{owner_name}/{repo_name}/pulls/{pr}/files?per_page=100"

print(f"\n================ {repo_name} PR summary: {pr} ===================")

print(f"https://github.com/{owner_name}/{repo_name}/pull/{pr}/files\n")

prfiles = a.get_auth_response(url)
repo = a.connect_repo(f"{owner_name}/{repo_name}")

if "message" in prfiles:
    print("Error occurred.  Check the PR number and try again.")
    print(prfiles)
    sys.exit()
else:
    deleted_files = [
        file["filename"] for file in prfiles if file["status"] == "removed"
    ]
    modified_files = [
        (file["filename"], file["blob_url"])
        for file in prfiles
        if file["status"] == "modified"
    ]
    added_files = [file["filename"] for file in prfiles if file["status"] == "added"]
    renamed_files = [file["previous_filename"] for file in prfiles if file["status"] == "renamed"]

snippet_fn = os.path.join(os.path.dirname(os.path.realpath(__file__)),'outputs', f"refs-found.csv")
snippets = h.read_snippets(snippet_fn)  # read the snippets file

# Process the files:

modified = len(modified_files)
deleted = len(deleted_files)
renamed = len(renamed_files)

print(f"PR {pr} changes {len(prfiles)} files.")
if len(added_files) > 0:
    print(f"ADDED {len(added_files)} files. (Added files won't cause a problem.)") 
if modified > 0:
    print(f"MODIFIED {modified} files.")
if deleted > 0:
    print(f"DELETED {deleted} files.")
if renamed > 0:
    print(f"RENAMED {renamed} files.\n")

# print("\nChanges that may affect azure-ai-docs-pr:\n")
data = []  # create an empty list to hold data for modified files that are referenced
nb_mods = []  # create an empty list to hold data for modified notebooks

### MODIFIED FILES
if modified > 0:
    if debug:
        print(f"Modified files: {modified_files}")
        print(f"Checking {modified} modified files for deleted cells or comments:")
    for file, blob_url in modified_files:
        if debug:
            print(f"Checking {file} for deleted cells or comments:")
        if (snippets["ref_file"] == file).any():
            if debug:
                print(f"  {file} is referenced in azure-ai-docs-pr.")
            # Get matching rows for this file and create full path references
            matching_rows = snippets.loc[snippets["ref_file"] == file]
            snippet_matches = matching_rows.apply(lambda row: f"{row['from_file_dir']}/{row['from_file']}", axis=1)
            snippet_match_str = snippet_matches.to_string(index=False)
            # Check if there are deleted nb named cells or code comments
            nb, adds, deletes, blob_url = h.find_changes(file, prfiles, blob_url)
            if debug:
                print(f"  {file} - nb: {nb}, adds: {adds}, deletes: {deletes}")
            # print (nb, adds, deletes)
            if nb:
                nb_mods.append(blob_url)
                # print("added to nb_mods: ", file)
            deleted_cells = [value for value in deletes if value not in adds]
            if deleted_cells:
                cell_type = "Notebook" if nb else "Code"
                for cell in deleted_cells:
                    # Append the data to the list
                    data.append(
                        {
                            "Modified File": file,
                            "Referenced In": snippet_match_str,
                            "Cell Type": cell_type,
                            "Cell": cell,
                        }
                    )
                # print(f"*** {cell}")
    if data == []:
        print(
            "✅ No problems with any of the modified files.\n"
        )
    else:
        # Group the data by 'Modified File' and 'Referenced In'
        grouped_data = {}
        for item in data:
            key = (item["Modified File"], item["Referenced In"])
            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(item["Cell"])
        print(f"Potential problems found in {len(grouped_data)} files. \n")        # Print the grouped data
        for (modified_file, referenced_in), cells in grouped_data.items():
            print(f"Modified File: {modified_file} \n  Referenced in:")
            refs = referenced_in.split("\n")
            for ref in refs:
                print(
                    f"   https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/{ref.strip()}"
                )
            print(f"   {cell_type} cells deleted: {len(cells)}")
            for cell in cells:
                print(f"   * {cell}")
            # compare the sha to this same file in branch "temp-fix"

            h.compare_branches(repo, file, "main", "temp-fix")
        # also print all the modified notebooks
        print("⚠️ Fix all references to modified files before approving this PR.\n")

    if nb_mods:
        print(
            "MODIFIED NOTEBOOKS\nFollow each link to ensure notebooks are valid before approving the PR:"
        )
        nb_mods = list(set(nb_mods))  # remove duplicates
        for file in nb_mods:
            print(f"* {file}\n")
        print("⚠️ Fix all references to modified files before approving this PR.\n")

### DELETED FILES
if deleted > 0:
    found = 0
    for file in deleted_files:
        if (snippets["ref_file"] == file).any():
            # Get matching rows for this file and create full path references
            matching_rows = snippets.loc[snippets["ref_file"] == file]
            snippet_matches = matching_rows.apply(lambda row: f"{row['from_file_dir']}/{row['from_file']}", axis=1)

            print(f"DELETED FILE: {file} \n  Referenced in:")
            refs = snippet_matches.to_string(index=False).split("\n")
            for ref in refs:
                print(
                    f"* https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/{ref.strip()}"
                )
            # print(snippet_match.to_string(index=False))
            h.compare_branches(repo, file, "main", "temp-fix")
            found = +1
    if found == 0:
        print(
            "✅ No problems with any of the deleted files.\n"
        )
    else:
        print("⚠️ Fix all references to deleted files before approving this PR.\n")
 
### RENAMED FILES
if renamed > 0:
    found = 0
    for file in renamed_files:
        if (snippets["ref_file"] == file).any():
            # Get matching rows for this file and create full path references
            matching_rows = snippets.loc[snippets["ref_file"] == file]
            snippet_matches = matching_rows.apply(lambda row: f"{row['from_file_dir']}/{row['from_file']}", axis=1)

            print(f"RENAMED FILE: {file} \n  Referenced in:")
            refs = snippet_matches.to_string(index=False).split("\n")
            for ref in refs:
                print(
                    f"* https://github.com/MicrosoftDocs/azure-ai-docs-pr/edit/main/articles/{ref.strip()}"
                )
            # print(snippet_match.to_string(index=False))
            h.compare_branches(repo, file, "main", "temp-fix")
            found = +1
    if found == 0:
        print(
            "✅ No problems with any of the renamed files.\n"
        )
    else:
        print("⚠️ Fix all references to renamed files before approving this PR.\n")

print(f"\n================ {repo_name} PR summary: {pr} ===================")

## test PRs:
# 3081 - no problems
# 2890 - deletes files
# 2888 - deletes ids in a file
# 3113 - deletes a cell in a notebook
# 3210 - renames files we use
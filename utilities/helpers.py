# some functions to use for find-snippets, pr-report, and merge-report


# function to read the CODEOWNERS file from the azureml-examples repo
# and return only the lines that are docs files.
def read_codeowners():
    # read the codeowners file from azureml-examples
    import requests

    url = "https://raw.githubusercontent.com/Azure/azureml-examples/main/.github/CODEOWNERS"
    response = requests.get(url)
    contents = response.text.splitlines()

    # get the lines that are docs files
    start_index = end_index = 0
    for i, line in enumerate(contents):
        if line.startswith("#### files"):
            start_index = i
        if line.startswith("# End of docs"):
            end_index = i
            break

    contents = contents[start_index + 1 : end_index]
    return contents


# function to get the changes for a specific file in a PR.
# Then searches for notebook cells or code snippets the were added/deleted.
# Returns a tuple with a boolean for whether the file is a notebook,
# a list of added cells, and a list of deleted cells.
def find_changes(thisfile, prfiles, blob_url):
    # pass blob_url back so we can preview the file in the report.
    import re

    patch = [file["patch"] for file in prfiles if file["filename"] == thisfile]
    nb_cell = (
        r'(\\n[\+-])\s*"name":\s*"([^"]*)"'  # finds added or deleted cells with a name
    )
    code_cell = (
        r"(\\n[\+-])\s*(#\s*<[^>]*>)"  # finds lines that start with # <> or # </>
    )
    # only works for files that use # as comment.
    adds = []
    deletes = []
    nb = False

    if thisfile.endswith(".ipynb"):
        nb = True
        matches = re.findall(nb_cell, str(patch))
    else:
        matches = re.findall(code_cell, str(patch))

    for match in matches:
        if match[0] == "\\n+":
            adds.append(match[1])
        elif match[0] == "\\n-":
            deletes.append(match[1])
        else:
            print(
                "ERROR in utilities.py find_changes. The match was not an add or delete."
            )

    return (nb, adds, deletes, blob_url)


# function to clean up the matches
# syntax of a match is different if it is from a notebook vs. code files.
# returns info about the match:
#       path to the file in azureml-examples
#       file name of the file being referenced
#       branch used to find the file(i.e., azureml-examples-main)
#       match - the full match
#       name - the name of the notebook cell
def cleanup_matches(match):
    import os

    # If match starts and ends with parentheses, remove them
    if match.startswith("(") and match.endswith(")"):
        match = match[1:-1]

    # match= match.replace('(', '').replace(')', '').replace('"', '').replace(',', '').replace('source=', '')
    match = match.replace('"', "").replace(",", "").replace("source=", "")

    # print(f"** match is {match}")
    # split up the match into parts here.
    path = os.path.dirname(match)
    ref_file = os.path.basename(match)
    # the first part of the path, after ~/, is the "path-to-root"  which includes the branch name
    # path-to-root is configured in azure-ai-docs-pr/.openpublishing.publish.config.json
    branch = path.split("/")[1]
    # remove the branch info to get the path to the file in azureml-examples
    path = path.replace("~/", "")
    if path == branch:
        path = ""
    else:
        path = path.replace(f"{branch}/", "")
    if "?" in ref_file:  # split out the id name from the ref_file if it exists
        ref_file, name = ref_file.split("?", 1)
    else:
        name = ""
    if path != "":  # if the path is empty, we don't want a beginning slash.
        ref_file = f"{path}/{ref_file}"  # add the path to the ref_file
    ref_file = ref_file.replace("///", "/").replace(
        "//", "/"
    )  # get rid of triple or double slashes
    return (
        path,
        ref_file,
        branch,
        match,
        name,
    )  # right now, not using match and name.  But might in the future


# function to read local file - try utf-8 first, then latin-1
def read_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as target_file:
            lines = target_file.readlines()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as target_file:
                lines = target_file.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            lines = []
    return lines


def read_snippets(snippet_fn):
    import os
    import sys
    import pandas as pd

    # read the snippets file
    
    
    # Check if snippets file exists
    if os.path.exists(snippet_fn):
        snippets = pd.read_csv(snippet_fn)
    else:
        print(f"{snippet_fn} does not exist.")
        print("Run 'find-snippets.py' to create the file.")
        sys.exit()
    return snippets


# function to compare file on two branches in a
def compare_branches(repo, file, branch1, branch2):
    try:
        file_b1 = repo.get_contents(file, ref=branch1)
    except Exception:
        print(f"Can't compare branches; {file} no longer found in {branch1}")
        return
    try:
        file_b2 = repo.get_contents(file, ref=branch2)
    except Exception:
        print(f"Can't compare branches; {file} no longer found in {branch2}")
        return    
    
    if file_b1.sha == file_b2.sha:
        print(
            f"*{repo.name} {branch2} branch has the same version of this file as {branch1}\n"
        )
    else:
        print(
            f"*{repo.name} {branch2} branch has a DIFFERENT version of this file from {branch1}\n"
        )


# call  for each line in the file, send in current info and get back updated values
def count_code_lines(line, blocks, inside_code_block, count, code_type, line_num=None, start_line=None):
    line = line.lstrip()
    if line.startswith("```"):
        if inside_code_block:  # done - this is the end of the block
            blocks.append((code_type, count, start_line))  # Add type, count, and start line to the list
            start_line = None
        else:  # starting - get the type and reset the count
            code_type = line[3:].strip()  # Get the rest of the line after ```
            count = 0
            start_line = line_num  # Record where the code block starts
        inside_code_block = not inside_code_block
    else:
        count += 1
    return blocks, inside_code_block, count, code_type, start_line


def find_snippets(line, branches, az_ml_branch, file):
    match_snippet = re.findall(
        r'\(~\/azureml-examples[^)]*\)|source="~\/azureml-examples[^"]*"', line
    )
    if match_snippet:
        for match in match_snippet:
            path, ref_file, branch, match, name = cleanup_matches(match)
            branches.append(branch)
            if (
                branch == az_ml_branch
            ):  # PRs are merged into main, so only these files are relevant
                row_dict = {"ref_file": ref_file, "from_file": file}
                dict_list.append(row_dict)


# get all contents from the path and all sub-directories
def get_all_contents(repo, path, repo_branch, exclude_dirs=None):
    """
    Get all contents from the path and all sub-directories.
    
    Args:
        repo: GitHub repository object
        path: Starting path to search
        repo_branch: Branch to search
        exclude_dirs: List of directory names to exclude (default: ['media'])
    
    Returns:
        List of content objects
    """
    if exclude_dirs is None:
        exclude_dirs = ['media']  # Default exclusion for backward compatibility
    
    contents = []
    stack = [path]

    while stack:
        current_path = stack.pop()
        try:
            current_contents = repo.get_contents(current_path, ref=repo_branch)
        except Exception as e:
            print(f"Warning: Could not access {current_path}: {e}")
            continue

        for content in current_contents:
            if content.type == 'dir':
                # Check if directory should be excluded
                should_exclude = False
                
                for exclude_pattern in exclude_dirs:
                    exclude_pattern = exclude_pattern.lower().strip('/')
                    content_path_lower = content.path.lower()
                    content_name_lower = content.name.lower()
                    
                    # Check if the exclude pattern matches:
                    # 1. The directory name exactly
                    # 2. The directory path contains the pattern
                    # 3. The directory path ends with the pattern
                    if (exclude_pattern == content_name_lower or 
                        exclude_pattern in content_path_lower or
                        content_path_lower.endswith(exclude_pattern)):
                        should_exclude = True
                        break
                
                if not should_exclude:
                    stack.append(content.path)
            else:
                contents.append(content)

    return contents

if __name__ == "__main__":
    problem = "~/azureml-examples-main/sdk/python/featurestore_sample/notebooks/sdk_only/7. Develop a feature set using Domain Specific Language (DSL).ipynb?name=setup-root-dir"
    path, ref_file, branch, match, name = cleanup_matches(problem)
    print(f"path: {path}, ref_file: {ref_file}")

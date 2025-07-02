"""
This script reads through the files in azure-ai-docs (main) and finds code snippets from 
azureml-examples, foundry-samples, and azureai-samples.
It creates the following files in the outputs directory
* code-counts-XX.csv - counts of code blocks in each repo
* code-counts-machine-learning.csv - counts of code blocks in machine-learning articles     
* CODEOWNERS-XX.txt - use the contents to populate the CODEOWNERS file in each repo
* refs-found.csv - needed for the merge-report and pr-report scripts

Run this script periodically to stay up to date with the latest references.

Configuration:
- Repository configurations and search paths are defined in config.yml
- Exclude directories can be configured in config.yml under defaults.exclude_directories
"""

def find_snippets():
    import os
    import re
    import sys
    from utilities import helpers as h
    from utilities import gh_auth as a
    from utilities import config
    import pandas as pd
    from datetime import datetime

    ###################### INPUT HERE ############################
    # Name the path to your repo. If trying to use a private repo, you'll need a token that has access to it.
    repo_name = "MicrosoftDocs/azure-ai-docs"
    repo_branch = "main"
    
    # Get repository configurations from config file
    repos_config = config.get_repositories()
    repo_configs = {}
    for repo_key, repo_config in repos_config.items():
        repo_configs[repo_key] = {
            "repo_token": repo_config["repo"],
            "owners": repo_config["team"]
        }
    
    # Get search paths from config (use all unique paths from all repos)
    all_search_paths = set()
    for repo_config in repos_config.values():
        for path in repo_config.get("search_paths", []):
            all_search_paths.add(path)
    
    search_paths = [
        {"path": path, "include_subdirs": True if "ai-foundry" in path else False}
        for path in sorted(all_search_paths)
    ]
    
    # Get exclude directories from config
    exclude_dirs = config.get_exclude_directories()

    ############################ DONE ############################
    
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "outputs")
    
    # Initialize data storage
    all_dict_lists = {key: [] for key in repo_configs.keys()}  # Per-repo references
    all_branches = {key: [] for key in repo_configs.keys()}    # Per-repo branches
    all_code_counts = []                                        # Code block counts
    combined_refs_list = []                                     # Combined references
      # Get the repo
    repo = a.connect_repo(repo_name)
    
    start_time = datetime.now()
    print(f"Starting search at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("☕This will take awhile, go grab a coffee and come back later...")
    
    # Search through all defined paths
    for search_config in search_paths:
        path_in_repo = search_config["path"]
        include_subdirs = search_config["include_subdirs"]
        
        # print(f"Searching {path_in_repo} (include_subdirs: {include_subdirs})")
        
        try:
            if include_subdirs:
                contents = h.get_all_contents(repo, path_in_repo, repo_branch, exclude_dirs)
            else:
                contents = repo.get_contents(path_in_repo, ref=repo_branch)
                # Convert to list if not already (when getting single directory)
                if not isinstance(contents, list):
                    contents = [contents]
        except Exception as e:
            print(f"Error accessing {path_in_repo}: {e}")
            continue
            
        # Process each file
        for content_file in contents:
            if content_file.type != "file" or not content_file.name.endswith(".md"):
                continue
                
            file = os.path.basename(content_file.path)
            file_content = content_file.decoded_content
            lines = file_content.decode().splitlines()

            blocks = []
            count = 0
            code_type = None
            inside_code_block = False
            
            for line in lines:
                # count hard-coded code blocks
                blocks, inside_code_block, count, code_type = h.count_code_lines(
                    line, blocks, inside_code_block, count, code_type
                )                # Search for all three snippet patterns in each line
                for repo_key, config in repo_configs.items():
                    repo_token = config["repo_token"]
                    az_branch = f"{repo_token}-main"
                    
                    match_snippet = re.findall(
                        rf'\(~/{repo_token}[^)]*\)|source="~/{repo_token}[^"]*"', line
                    )
                    
                    if match_snippet:
                        for match in match_snippet:
                            path, ref_file, branch, m, name = h.cleanup_matches(match)
                            
                            if "(" in ref_file:  # this might be a mistake
                                print(f"{file}: Warning: Found a snippet with a ( in it: {match}")
                                print(f" cleaned up match is {m}")
                                print(f"  The snippet was split into {path}\n {ref_file}\n {branch}")
                            
                            all_branches[repo_key].append(branch)
                            
                            if branch == az_branch:  # PRs are merged into main, so only these files are relevant
                                # Extract the complete directory path from content_file.path
                                # content_file.path looks like: "articles/ai-foundry/includes/create-project-fdp.md"
                                # We want to extract everything after "articles/" and before the filename
                                full_path = content_file.path
                                if "articles/" in full_path:
                                    # Remove "articles/" prefix and the filename to get the directory structure
                                    dir_part = full_path.replace("articles/", "").replace(f"/{file}", "")
                                    from_file_dir = dir_part
                                else:
                                    # Fallback to the original logic if path structure is unexpected
                                    from_file_dir = "ai-foundry" if "ai-foundry" in content_file.path else "machine-learning"
                                
                                row_dict = {"ref_file": ref_file, "from_file": file}
                                all_dict_lists[repo_key].append(row_dict)
                                
                                # Add to combined list with repo_name and from_file_dir
                                combined_row_dict = {
                                    "ref_file": ref_file, 
                                    "from_file": file, 
                                    "repo_name": repo_token,
                                    "from_file_dir": from_file_dir
                                }
                                combined_refs_list.append(combined_row_dict)

            if inside_code_block:
                print(f"⚠️ Warning! {content_file}: A code block started but did not end.")
                print(f"  The last code block type was {code_type} and had {count} lines.")
                
            if blocks:
                # this file has code blocks. add info to the dictionary
                path_name = "ai-foundry" if "ai-foundry" in content_file.path else "machine-learning"
                for block in blocks:
                    all_code_counts.append({"file": file, "type": block[0], "lines": block[1], "path": path_name})

    # Write combined refs file with all references
    if combined_refs_list:
        combined_found = pd.DataFrame(combined_refs_list)
        combined_found = combined_found.drop_duplicates()
        combined_found = combined_found.sort_values(by=["repo_name", "ref_file"])
        
        combined_result_fn = os.path.join(output_dir, "refs-found.csv")
        combined_found.to_csv(combined_result_fn, index=False)
        print(f"Writing {combined_result_fn} file with {len(combined_found)} total references")
    else:
        print("No references found across all repositories")    # Process results for each repository (for individual CODEOWNERS files)
    for repo_key, config in repo_configs.items():
        repo_token = config["repo_token"]
        owners = config["owners"]
        
        # Create output filenames (only for CODEOWNERS, not refs-found)
        path_name = "ai-foundry" if repo_key in ["ai", "ai2"] else "machine-learning"
        codeowners_fn = os.path.join(output_dir, f"CODEOWNERS-{repo_token}.txt")
        
        # Process found snippets
        found = pd.DataFrame.from_dict(all_dict_lists[repo_key])
        branches = pd.DataFrame(all_branches[repo_key])
        
        # get rid of duplicates
        found = found.drop_duplicates()
        branches = branches.drop_duplicates()
        
        # sort the file
        if not found.empty:
            found = found.sort_values(by=["ref_file"])
            
            # create codeowners file
            refs = found["ref_file"].drop_duplicates().replace(" ", r"\ ", regex=True)
            with open(codeowners_fn, "w+") as f:
                print(f"Creating {codeowners_fn} file")
                print(f"  with the following owners: {owners}")
                for ref in refs:
                    f.write(f"/{ref} {owners}\n")
        else:
            print(f"No references found for {repo_token}")

    # Write code counts file
    if all_code_counts:
        code_counts = pd.DataFrame(all_code_counts)
        for path_name in ["machine-learning", "ai-foundry"]:
            path_counts = code_counts[code_counts["path"] == path_name]
            if not path_counts.empty:
                code_counts_fn = os.path.join(output_dir, f"code-counts-{path_name}.csv")
                path_counts.to_csv(code_counts_fn, index=False)
                print(f"Writing {code_counts_fn} file")

    end_time = datetime.now()
    print(f"Search completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {end_time - start_time}")
    return


if __name__ == "__main__":
    find_snippets()

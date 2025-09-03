"""
This script finds PRs that were merged in the last X days (defaults to 8)
and reports on doc files that need updating because of those merges.

Use "ai", ai2, "ml", or  as the argument to specify which repo to check. Default is "ml".
Example:
    python merge-report.py 8 ai

    # these are all equivalent:
    python merge-report.py 8 ml
    python merge-report.py 8
    python merge-report.py
"""


def merge_report(days, service):

    from utilities import helpers as h
    from utilities import find_pr_files as f
    from utilities import config
    import os

    # Get repository configurations from config file
    repos_config = config.get_repositories()
    
    if service == "ai":
        # Get AI-related repositories
        ai_repos = config.get_repositories_by_service("ai")
        repo_names = [repo_config["repo"] for repo_config in ai_repos.values()]
        owner_names = [repo_config["owner"] for repo_config in ai_repos.values()]
    elif service == "ml":
        # Get ML-related repositories  
        ml_repos = config.get_repositories_by_service("ml")
        repo_names = [repo_config["repo"] for repo_config in ml_repos.values()]
        owner_names = [repo_config["owner"] for repo_config in ml_repos.values()]
    else:
        print(f"Unknown service: {service}")
        return
        
    output_dir = config.get_output_directory()
    
    # get the refs-found file for this service
    file_paths = config.get_file_paths()
    fn = os.path.join(output_dir, file_paths["refs_found_csv"])
    # print(f"Reading {fn} for all snippets")
    snippets = h.read_snippets(fn)  # read the snippets file
    
    # Aggregate results from all repos
    all_results = []
    for owner_name, repo_name in zip(owner_names, repo_names):
        repo_results = f.find_pr_files(owner_name, repo_name, snippets, days)
        if isinstance(repo_results, dict) and "error" in repo_results:
            print(f"Error for repo {repo_name}: {repo_results['error']}")
        elif repo_results:
            all_results.extend(repo_results)

    # Print a single combined report
    if not all_results:
        print("\n ✅ Nothing to do here :-)  There are no PRs that impacted references.\n")
        return

    import pandas as pd
    df = pd.DataFrame(all_results)
    print("\nThese PRs impacted references across all repos:\n")
    prs = df[["owner", "repo", "PR"]].drop_duplicates()
    for _, row in prs.iterrows():
        pr_url = f"https://github.com/{row['owner']}/{row['repo']}/pull/{row['PR']}"
        print(f"* [PR {row['PR']} ({row['repo']})]({pr_url})")

    print("\n✏️ **Add 'update-code' to ms.custom metadata (or modify if already present) to the following files:**")
    # Collect all referenced files
    refs = []
    for ref_list in df["Referenced In"]:
        refs.extend(ref_list)
    refs = sorted(set(refs))
    for i, ref in enumerate(refs, 1):
        print(f"{i}  {ref}")
    return

if __name__ == "__main__":
    import concurrent.futures
    from utilities import helpers as h
    from utilities import find_pr_files as f
    from utilities import config
    import os
    import sys

    # Parse optional days argument
    days = 8
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"Invalid days argument: {sys.argv[1]}. Using default 8 days.")

    # Always use all repos from config.yml
    repos_config = config.get_repositories()
    repo_args = [(repo_config["owner"], repo_config["repo"]) for repo_config in repos_config.values()]

    output_dir = config.get_output_directory()
    file_paths = config.get_file_paths()
    fn = os.path.join(output_dir, file_paths["refs_found_csv"])
    snippets = h.read_snippets(fn)

    all_results = []
    def process_repo(args):
        owner_name, repo_name = args
        repo_results = f.find_pr_files(owner_name, repo_name, snippets, days)
        if isinstance(repo_results, dict) and "error" in repo_results:
            print(f"Error for repo {repo_name}: {repo_results['error']}")
        elif repo_results:
            return repo_results
        return []

    # Use ThreadPoolExecutor to process repos in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_repo, args) for args in repo_args]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                all_results.extend(result)

    # Print a single combined report
    if not all_results:
        print("\n ✅ Nothing to do here :-)  There are no PRs that impacted references.\n")
    else:
        import pandas as pd
        df = pd.DataFrame(all_results)
        print("\nThese PRs impacted references across all repos:\n")
        prs = df[["owner", "repo", "PR"]].drop_duplicates()
        for _, row in prs.iterrows():
            pr_url = f"https://github.com/{row['owner']}/{row['repo']}/pull/{row['PR']}"
            print(f"* PR {row['PR']} ({row['repo']}) - {pr_url}")

        print("\n✏️ Modify ms.custom metadata  (add or modify 'update-code') in these files:")
        refs = []
        for ref_list in df["Referenced In"]:
            refs.extend(ref_list)
        refs = sorted(set(refs))
        for i, ref in enumerate(refs, 1):
            print(f"{i}  {ref}")

        print("\n")
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
    
    # loop through all the repos that contain snippets for this service
    for owner_name, repo_name in zip(owner_names, repo_names):
        f.find_pr_files(owner_name, repo_name, snippets, days)
    return

if __name__ == "__main__":
    
    import argparse
    # Create the parser
    parser = argparse.ArgumentParser(description="Find number of days and which service.")
    parser.add_argument(
        "input", type=str, nargs="*", help="For how many days and/or which service: 'ai', 'ml', or 'all'"
    )

    args = parser.parse_args()  # Parse the arguments

    service = "all"  # Default service
    days = 8

    for arg in args.input:
        if arg.isdigit():
            days = int(arg)
        elif arg.lower() in ["ai", "ml", "all"]:
            service = arg.lower()

    if service == "all":
        merge_report(days, "ai")
        merge_report(days, "ml")

    else:
        merge_report(days, service)
# function to find PRs merged in the last N days that have doc references
# used from merge_report
def find_pr_files(owner_name, repo_name, snippets, days):
    import requests
    import os
    import pandas as pd
    from utilities import gh_auth as a
    from datetime import datetime, timedelta

    # Calculate the date to filter by
    if days < 100:
        days_ago = (datetime.now() - timedelta(days)).isoformat()
    else:
        # Return error info to caller
        return {"error": "The maximum number of days is 100."}

    # Define the URL for the GitHub API
    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/pulls?state=closed&sort=updated&direction=desc"
    
    # Use authenticated request to avoid rate limiting
    headers = {}
    token = os.environ.get("GH_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    response = requests.get(url, headers=headers)
    pr_data = response.json()
    
    # Check if we got an error response (usually a dict with 'message' key)
    if isinstance(pr_data, dict) and "message" in pr_data:
        return {"error": f"GitHub API error for {repo_name}: {pr_data['message']}"}

    # Filter the PRs that were merged in the last N days
    merged_prs = [
        pr["number"] for pr in pr_data if pr.get("merged_at") and pr["merged_at"] > days_ago
    ]
    import concurrent.futures

    def process_pr_files(repo_name, owner_name, pr):
        url = f"https://api.github.com/repos/{owner_name}/{repo_name}/pulls/{pr}/files?per_page=100"
        prfiles = a.get_auth_response(url)
        modified_files = [
            file["filename"] for file in prfiles if file["status"] == "modified"
        ]
        results = []
        for file in modified_files:
            if (snippets["ref_file"] == file).any():
                matching_rows = snippets.loc[snippets["ref_file"] == file]
                snippet_matches = matching_rows.apply(lambda row: f"{row['from_file_dir']}/{row['from_file']}", axis=1)
                snippet_matches_list = snippet_matches.tolist()
                results.append({
                    "repo": repo_name,
                    "owner": owner_name,
                    "PR": pr,
                    "Modified File": file,
                    "Referenced In": snippet_matches_list
                })
        return results

    merged_prs = [
        pr["number"] for pr in pr_data if pr.get("merged_at") and pr["merged_at"] > days_ago
    ]

    results = []  # create an empty list to hold data for modified files that are referenced
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_pr = {executor.submit(process_pr_files, repo_name, owner_name, pr): pr for pr in merged_prs}
        for future in concurrent.futures.as_completed(future_to_pr):
            results.extend(future.result())

    # Return the results list (empty if nothing found)
    return results


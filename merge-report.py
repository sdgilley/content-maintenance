"""
This script finds PRs that were merged in the last X days (defaults to 8)
and reports on doc files that need updating because of those merges.

Usage examples:
    python merge-report.py              # Last 8 days
    python merge-report.py 14           # Last 14 days
    python merge-report.py 8 --create-pr       # Create metadata update PR (auto-detects your fork)
    python merge-report.py 8 --create-pr --dry-run  # Preview changes without creating PR
    python merge-report.py 8 --create-pr --fork-repo username/fork-name  # Use different fork

The --create-pr option creates a PR in the main repo from your fork that automatically:
- Identifies documentation files impacted by recent code repository PRs
- Adds or increments the 'update-code' metadata field for each file
- Uses GitHub API (no large clone needed) - only updates files that actually change
- Generates a detailed PR with related code repository references

Fork detection:
  - By default, uses your GitHub username from the GH_ACCESS_TOKEN
  - Can override with --fork-repo username/fork-name if needed

Requirements:
    GH_ACCESS_TOKEN environment variable must be set for PR creation
    PyGithub must be installed (pip install -r requirements.txt)
"""


import os
import re
import sys
import logging
from typing import List, Dict, Any

# Configure logging to show messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def update_yaml_metadata(content: str) -> tuple[str, bool]:
    """
    Update YAML frontmatter to add or increment update-code metadata.
    
    Args:
        content: File content with YAML frontmatter
        
    Returns:
        Tuple of (updated_content, was_changed)
        
    The metadata value is stored as a single string:
    - "update-code" -> "update-code1"
    - "update-code4" -> "update-code5"
    """
    # Match YAML frontmatter (content between --- markers at start)
    yaml_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    
    if not yaml_match:
        logger.warning("No YAML frontmatter found")
        return content, False
    
    yaml_content = yaml_match.group(1)
    yaml_end_pos = yaml_match.end()
    rest_of_content = content[yaml_end_pos:]
    
    # Check if "update-code" exists in the metadata
    if 'update-code' in yaml_content:
        # Extract the version number if present
        update_code_match = re.search(r'update-code(\d+)?', yaml_content)
        
        if update_code_match:
            current_version_str = update_code_match.group(1)
            if current_version_str:
                # Has a number, increment it
                current_version = int(current_version_str)
                new_version = current_version + 1
                old_value = f'update-code{current_version}'
                new_value = f'update-code{new_version}'
            else:
                # Just "update-code" without number, add "1"
                old_value = 'update-code'
                new_value = 'update-code1'
            
            yaml_content = yaml_content.replace(old_value, new_value)
            updated_content = f'---\n{yaml_content}\n---\n{rest_of_content}'
            return updated_content, True
    else:
        # "update-code" not found, add it
        # Add to ms.custom section or create it
        custom_match = re.search(r'^(\s*)ms\.custom:\s*(.*)$', yaml_content, re.MULTILINE)
        
        if custom_match:
            # ms.custom exists - append to it
            indent = custom_match.group(1)
            current_value = custom_match.group(2).strip()
            
            if current_value:
                # Has a value, append update-code1
                new_value = f'{current_value}, update-code1'
            else:
                # Empty ms.custom, just add update-code1
                new_value = 'update-code1'
            
            yaml_content = re.sub(
                r'^(\s*)ms\.custom:\s*(.*)$',
                f'\\1ms.custom: {new_value}',
                yaml_content,
                flags=re.MULTILINE
            )
        else:
            # No ms.custom section, add one
            yaml_content = yaml_content.rstrip() + '\nms.custom: update-code1'
        
        updated_content = f'---\n{yaml_content}\n---\n{rest_of_content}'
        return updated_content, True
    
    return content, False


def create_metadata_update_pr(
    doc_files: List[str], 
    pr_info: Dict[str, Any],
    dry_run: bool = False,
    fork_repo: str = None
) -> str:
    """
    Create a PR in a fork to update metadata for files.
    
    Args:
        doc_files: List of documentation file paths to update
        pr_info: Dictionary with PRs that triggered updates
        dry_run: If True, don't actually create PR
        fork_repo: Your fork repository (owner/repo). If None, reads from config or env var.
        
    Returns:
        PR URL string if successful, None if failed or no changes needed
        
    Fork repo resolution order:
        1. fork_repo parameter (CLI argument)
        2. Auto-detect from authenticated user's GitHub username
    """
    from utilities import gh_auth, config as cfg
    from datetime import datetime
    from github import Github, Auth
    
    try:
        # Resolve fork_repo - use CLI arg or auto-detect from token
        if fork_repo is None:
            # Auto-detect from authenticated user
            logger.info("Auto-detecting fork from authenticated user...")
            token = os.environ.get('GH_ACCESS_TOKEN')
            if not token:
                raise ValueError("GH_ACCESS_TOKEN environment variable not set")
            auth = Auth.Token(token)
            gh = Github(auth=auth)
            user = gh.get_user()
            username = user.login
            fork_repo = f"{username}/azure-ai-docs-pr"
            logger.info(f"Detected fork: {fork_repo}")
        
        # Connect to the fork repo for updates
        fork_github_repo = gh_auth.connect_repo(fork_repo)
        
        # Also connect to the main repo for PR creation
        main_repo = gh_auth.connect_repo("MicrosoftDocs/azure-ai-docs-pr")
        
        logger.info(f"Using fork: {fork_repo}")
        logger.info(f"PR will be created in: MicrosoftDocs/azure-ai-docs-pr")
        
        # Create feature branch in fork
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        branch_name = f"chore/update-code-metadata-{timestamp}"
        
        # Get the main branch reference from UPSTREAM (to stay in sync)
        logger.info(f"Fetching latest from upstream main branch...")
        main_ref = main_repo.get_git_ref("heads/main")
        main_sha = main_ref.object.sha
        logger.info(f"Using upstream main at SHA: {main_sha[:7]}")
        
        if not dry_run:
            # Create the feature branch in fork
            fork_github_repo.create_git_ref(f"refs/heads/{branch_name}", main_sha)
            logger.info(f"Created branch in fork: {branch_name}")
        else:
            logger.info(f"[DRY RUN] Would create branch: {branch_name}")
        
        # Track which files were actually changed
        updated_files = []
        failed_files = []
        
        # Update metadata for each file using GitHub API
        for doc_file in doc_files:
            # Prepend 'articles/' if not already present
            if not doc_file.startswith('articles/'):
                repo_path = f'articles/{doc_file}'
            else:
                repo_path = doc_file
            try:
                # Get the file from the exact SHA we're basing the branch on (upstream main)
                try:
                    file_content = main_repo.get_contents(repo_path, ref=main_sha)
                except Exception as e:
                    logger.warning(f"File not found: {repo_path} - {e}")
                    failed_files.append(doc_file)
                    continue
                
                # Decode content
                content = file_content.decoded_content.decode('utf-8')
                
                # Update metadata
                updated_content, was_changed = update_yaml_metadata(content)
                
                if was_changed:
                    if not dry_run:
                        # Update the file in the feature branch in fork
                        fork_github_repo.update_file(
                            path=repo_path,
                            message=f"chore: update update-code metadata for {doc_file}",
                            content=updated_content,
                            sha=file_content.sha,
                            branch=branch_name
                        )
                    updated_files.append(doc_file)
                    logger.info(f"Updated metadata: {doc_file}")
                else:
                    logger.info(f"No changes needed: {doc_file}")
                    
            except Exception as e:
                logger.error(f"Error updating {doc_file}: {e}")
                failed_files.append(doc_file)
        
        if not updated_files:
            logger.info("No files needed metadata updates")
            return None
        
        if dry_run:
            logger.info(f"[DRY RUN] Would update {len(updated_files)} files:")
            for file in updated_files:
                logger.info(f"  - {file}")
            if failed_files:
                logger.warning(f"Would skip {len(failed_files)} files (not found)")
            return "dry-run-success"  # Return truthy value to indicate success in dry-run
        
        # Build PR information
        pr_summary = []
        for repo_name, prs in pr_info.items():
            pr_links = ", ".join([f"#{pr}" for pr in prs])
            pr_summary.append(f"{repo_name}: {pr_links}")
        
        pr_summary_text = "\n".join(pr_summary)
        
        # Create PR
        pr_title = f"chore: update code reference metadata ({datetime.now().strftime('%Y-%m-%d')})"
        pr_body = f"""## Updates

Updated `update-code` metadata for documentation files impacted by recent code repository changes.

### Files Modified
{chr(10).join(['- `' + f + '`' for f in updated_files[:20]])}
{"..." if len(updated_files) > 20 else ""}

### Related Code Changes
{pr_summary_text}

### Details
- Added or incremented `update-code` field in ms.custom metadata
- Total files updated: {len(updated_files)}
- Created by: automated merge-report workflow
"""
        # Create PR in main repo with head pointing to fork branch
        fork_owner = fork_repo.split('/')[0]
        
        pr = main_repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=f"{fork_owner}:{branch_name}",
            base="main"
        )
        
        logger.info(f"Created PR: {pr.html_url}")
        if failed_files:
            logger.warning(f"Note: {len(failed_files)} files were not found in the repo")
        
        return pr.html_url
            
    except Exception as e:
        logger.error(f"Failed to create metadata update PR: {e}", exc_info=True)
        return None



    from utilities import helpers as h
    from utilities import find_pr_files as f
    from utilities import config

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
    import sys
    import argparse

    # Setup argument parsing
    parser = argparse.ArgumentParser(description="Find PRs that impact documentation and optionally create metadata update PR")
    parser.add_argument('days', nargs='?', type=int, default=8, help='Days to look back (default: 8)')
    parser.add_argument('--create-pr', action='store_true', help='Create PR in your fork with metadata updates')
    parser.add_argument('--fork-repo', type=str, default=None, help='Fork repository (owner/repo). Defaults to GH_FORK_REPO env var or config.yml')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without creating PR')
    
    args = parser.parse_args()
    days = args.days
    create_pr = args.create_pr
    fork_repo = args.fork_repo
    dry_run = args.dry_run

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
        
        # If --create-pr flag is set, create a PR with metadata updates
        if create_pr:
            print("=" * 60)
            if dry_run:
                print("[DRY RUN MODE] Would create metadata update PR")
            else:
                print("Creating metadata update PR...")
            
            # Build PR info dictionary
            pr_info = {}
            for _, row in df[["owner", "repo", "PR"]].drop_duplicates().iterrows():
                repo = row['repo']
                pr_num = row['PR']
                if repo not in pr_info:
                    pr_info[repo] = []
                pr_info[repo].append(pr_num)
            
            # Create the PR (fork_repo can be None to use config/env)
            pr_url = create_metadata_update_pr(refs, pr_info, dry_run=dry_run, fork_repo=fork_repo)
            
            if pr_url:
                print("✅ Metadata update PR created successfully!")
                print(f"   {pr_url}")
            else:
                print("❌ Failed to create metadata update PR")
                sys.exit(1)

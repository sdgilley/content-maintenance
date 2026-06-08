"""
This script finds PRs that were merged in the last X days (defaults to 8)
and reports on doc files that need updating because of those merges.

Usage examples:
    python merge-report.py              # Last 8 days
    python merge-report.py 14           # Last 14 days
    python merge-report.py 8 --create-pr       # Create metadata update PR (auto-detects your fork)
    python merge-report.py 8 --create-pr --dry-run  # Preview changes without creating PR
    python merge-report.py 8 --create-pr --fork-repo username/fork-name  # Use different fork
    python merge-report.py 8 --ignore-tracking  # Process all PRs, ignoring tracking data

The --create-pr option creates a PR in the main repo from your fork that automatically:
- Identifies documentation files impacted by recent code repository PRs
- Adds or increments the 'update-code' metadata field for each file
- Uses GitHub API (no large clone needed) - only updates files that actually change
- Generates a detailed PR with related code repository references
- Records processed PRs in outputs/merge-tracking.json to avoid duplicates

Tracking:
  - Processed PRs are recorded in outputs/merge-tracking.json
  - On subsequent runs, already-processed PRs are automatically skipped
  - Use --ignore-tracking to process all PRs regardless of tracking data

Fork detection:
  - By default, uses your GitHub username from the authenticated `gh` CLI session
  - Can override with --fork-repo username/fork-name if needed

Requirements:
    GitHub CLI authentication (`gh auth login`) is preferred for PR creation
    PyGithub must be installed (pip install -r requirements.txt)
"""


import os
import re
import sys
import json
import logging
from typing import List, Dict, Any, Set
from datetime import datetime

# Configure logging to show messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def load_tracking_data() -> Dict[str, Any]:
    """
    Load the merge tracking data from the JSON file.
    
    Returns:
        Dictionary with tracking data including:
        - processed_prs: Dict mapping "owner/repo" to list of processed PR numbers
        - update_prs: List of documentation update PRs that were created
    """
    from utilities import config
    
    tracking_file = config.get_tracking_file_path()
    
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded tracking data from {tracking_file}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading tracking file: {e}. Starting fresh.")
    
    # Return empty structure if file doesn't exist or is invalid
    return {
        "processed_prs": {},  # "owner/repo" -> [pr_numbers]
        "update_prs": []      # List of update PR records
    }


def save_tracking_data(data: Dict[str, Any]) -> None:
    """
    Save the merge tracking data to the JSON file.
    
    Args:
        data: Tracking data dictionary to save
    """
    from utilities import config
    
    tracking_file = config.get_tracking_file_path()
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
    
    with open(tracking_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Saved tracking data to {tracking_file}")


def get_processed_prs(tracking_data: Dict[str, Any], owner: str, repo: str) -> Set[int]:
    """
    Get the set of already-processed PR numbers for a repository.
    
    Args:
        tracking_data: The tracking data dictionary
        owner: Repository owner
        repo: Repository name
        
    Returns:
        Set of PR numbers that have already been processed
    """
    repo_key = f"{owner}/{repo}"
    pr_list = tracking_data.get("processed_prs", {}).get(repo_key, [])
    return set(pr_list)


def record_processed_prs(
    tracking_data: Dict[str, Any],
    pr_info: Dict[str, Any],
    doc_pr_url: str,
    updated_files: List[str]
) -> None:
    """
    Record that PRs have been processed and a documentation update PR was created.
    
    Args:
        tracking_data: The tracking data dictionary (will be modified in place)
        pr_info: Dictionary mapping repo names to lists of PR numbers
        doc_pr_url: URL of the documentation update PR that was created
        updated_files: List of documentation files that were updated
    """
    # Add PR numbers to the processed list
    if "processed_prs" not in tracking_data:
        tracking_data["processed_prs"] = {}
    
    for repo_name, pr_numbers in pr_info.items():
        # pr_info keys might be just repo name, not owner/repo
        # We need to find the full key
        repo_key = repo_name
        if "/" not in repo_key:
            # Try to find the matching repository from config
            from utilities import config
            repos_config = config.get_repositories()
            for key, repo_config in repos_config.items():
                if repo_config["repo"] == repo_name:
                    repo_key = f"{repo_config['owner']}/{repo_name}"
                    break
        
        if repo_key not in tracking_data["processed_prs"]:
            tracking_data["processed_prs"][repo_key] = []
        
        # Add new PR numbers (avoid duplicates)
        existing = set(tracking_data["processed_prs"][repo_key])
        for pr_num in pr_numbers:
            if pr_num not in existing:
                tracking_data["processed_prs"][repo_key].append(pr_num)
    
    # Record the update PR
    if "update_prs" not in tracking_data:
        tracking_data["update_prs"] = []
    
    update_record = {
        "created_at": datetime.now().isoformat(),
        "pr_url": doc_pr_url,
        "source_prs": pr_info,
        "files_updated": updated_files
    }
    tracking_data["update_prs"].append(update_record)


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

    This implementation uses an SSH-backed git flow for the fork branch push and
    the GitHub CLI for PR creation. It avoids relying on GH_ACCESS_TOKEN for
    the write path when the runner already has SSH access to the fork.
    """
    import os
    import shutil
    import subprocess
    import tempfile

    from datetime import datetime

    try:
        if fork_repo is None:
            try:
                result = subprocess.run(
                    ["gh", "api", "user", "--jq", ".login"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                username = result.stdout.strip()
                fork_repo = f"{username}/azure-ai-docs-pr"
                logger.info(f"Detected fork from gh CLI: {fork_repo}")
            except Exception as exc:
                raise ValueError("Could not determine your fork. Pass --fork-repo or authenticate with gh CLI first.") from exc

        logger.info(f"Using fork: {fork_repo}")
        logger.info("PR will be created in: MicrosoftDocs/azure-ai-docs-pr")

        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        branch_name = f"chore/update-code-metadata-{timestamp}"
        updated_files = []
        failed_files = []

        if dry_run:
            logger.info(f"[DRY RUN] Would create branch: {branch_name}")
            logger.info("[DRY RUN] SSH/gh-based write path is enabled when a fork repo is provided")
            return "dry-run-success", updated_files

        temp_root = tempfile.mkdtemp(prefix="merge-report-")
        main_clone = os.path.join(temp_root, "main")
        fork_clone = os.path.join(temp_root, "fork")

        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", "main", "https://github.com/MicrosoftDocs/azure-ai-docs-pr.git", main_clone],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["gh", "repo", "clone", fork_repo, fork_clone],
                check=True,
                capture_output=True,
                text=True,
            )

            subprocess.run(["git", "-C", fork_clone, "config", "user.name", "Content Maintenance Bot"], check=True)
            subprocess.run(["git", "-C", fork_clone, "config", "user.email", "bot@example.com"], check=True)
            subprocess.run(["git", "-C", fork_clone, "checkout", "-b", branch_name], check=True)

            for doc_file in doc_files:
                repo_path = f"articles/{doc_file}" if not doc_file.startswith('articles/') else doc_file
                main_path = os.path.join(main_clone, repo_path)
                fork_path = os.path.join(fork_clone, repo_path)

                if not os.path.exists(main_path):
                    logger.warning(f"File not found: {repo_path}")
                    failed_files.append(doc_file)
                    continue

                with open(main_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                updated_content, was_changed = update_yaml_metadata(content)
                if was_changed:
                    os.makedirs(os.path.dirname(fork_path), exist_ok=True)
                    with open(fork_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    updated_files.append(doc_file)
                    logger.info(f"Updated metadata: {doc_file}")
                else:
                    logger.info(f"No changes needed: {doc_file}")

            if not updated_files:
                logger.info("No files needed metadata updates")
                return None, []

            subprocess.run(["git", "-C", fork_clone, "add", "."], check=True)
            subprocess.run(["git", "-C", fork_clone, "commit", "-m", f"chore: update update-code metadata for {len(updated_files)} files"], check=True)
            subprocess.run(["git", "-C", fork_clone, "push", "--set-upstream", "origin", branch_name], check=True)

            pr_summary = []
            for repo_name, prs in pr_info.items():
                pr_links = ", ".join([f"#{pr}" for pr in prs])
                pr_summary.append(f"{repo_name}: {pr_links}")
            pr_summary_text = "\n".join(pr_summary)

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

            body_file = os.path.join(temp_root, "pr_body.md")
            with open(body_file, 'w', encoding='utf-8') as f:
                f.write(pr_body)

            gh_cmd = [
                "gh", "pr", "create",
                "--repo", "MicrosoftDocs/azure-ai-docs-pr",
                "--head", f"{fork_repo.split('/')[0]}:{branch_name}",
                "--base", "main",
                "--title", pr_title,
                "--body-file", body_file,
            ]
            pr_result = subprocess.run(gh_cmd, check=True, capture_output=True, text=True)
            pr_url = pr_result.stdout.strip().splitlines()[-1]
            logger.info(f"Created PR: {pr_url}")

            if failed_files:
                logger.warning(f"Note: {len(failed_files)} files were not found in the repo")

            return pr_url, updated_files
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    except Exception as e:
        logger.error(f"Failed to create metadata update PR: {e}", exc_info=True)
        return None, []



def generate_report_for_service(service: str, days: int) -> None:
    """Generate a combined report for AI or ML repository references."""
    from utilities import helpers as h
    from utilities import find_pr_files as f
    from utilities import config

    repos_config = config.get_repositories()

    if service == "ai":
        ai_repos = config.get_repositories_by_service("ai")
        repo_names = [repo_config["repo"] for repo_config in ai_repos.values()]
        owner_names = [repo_config["owner"] for repo_config in ai_repos.values()]
    elif service == "ml":
        ml_repos = config.get_repositories_by_service("ml")
        repo_names = [repo_config["repo"] for repo_config in ml_repos.values()]
        owner_names = [repo_config["owner"] for repo_config in ml_repos.values()]
    else:
        print(f"Unknown service: {service}")
        return

    output_dir = config.get_output_directory()
    file_paths = config.get_file_paths()
    fn = os.path.join(output_dir, file_paths["refs_found_csv"])
    snippets = h.read_snippets(fn)

    all_results = []
    for owner_name, repo_name in zip(owner_names, repo_names):
        delay = 0
        for rc in repos_config.values():
            if rc["owner"] == owner_name and rc["repo"] == repo_name:
                delay = rc.get("sync_delay_hours", 0)
                break
        repo_results = f.find_pr_files(owner_name, repo_name, snippets, days, sync_delay_hours=delay)
        if isinstance(repo_results, dict) and "error" in repo_results:
            print(f"Error for repo {repo_name}: {repo_results['error']}")
        elif repo_results:
            all_results.extend(repo_results)

    if not all_results:
        print("\n[OK] Nothing to do here :-)  There are no PRs that impacted references.\n")
        return

    import pandas as pd

    df = pd.DataFrame(all_results)
    print("\nThese PRs impacted references across all repos:\n")
    prs = df[["owner", "repo", "PR"]].drop_duplicates()
    for _, row in prs.iterrows():
        pr_url = f"https://github.com/{row['owner']}/{row['repo']}/pull/{row['PR']}"
        print(f"* [PR {row['PR']} ({row['repo']})]({pr_url})")

    print("\n[ACTION] **Add 'update-code' to ms.custom metadata (or modify if already present) to the following files:**")
    refs = []
    for ref_list in df["Referenced In"]:
        refs.extend(ref_list)
    refs = sorted(set(refs))
    for i, ref in enumerate(refs, 1):
        print(f"{i}  {ref}")

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
    parser.add_argument('--ignore-tracking', action='store_true', help='Ignore tracking data and process all PRs')
    
    args = parser.parse_args()
    days = args.days
    create_pr = args.create_pr
    fork_repo = args.fork_repo
    dry_run = args.dry_run
    ignore_tracking = args.ignore_tracking

    # Load tracking data to filter out already-processed PRs
    tracking_data = load_tracking_data()
    
    # Always use all repos from config.yml
    repos_config = config.get_repositories()
    repo_args = [(repo_config["owner"], repo_config["repo"], repo_config.get("sync_delay_hours", 0)) for repo_config in repos_config.values()]

    output_dir = config.get_output_directory()
    file_paths = config.get_file_paths()
    fn = os.path.join(output_dir, file_paths["refs_found_csv"])
    snippets = h.read_snippets(fn)

    all_results = []
    skipped_prs = []  # Track PRs we skip because they were already processed
    
    def process_repo(args):
        owner_name, repo_name, delay = args
        repo_results = f.find_pr_files(owner_name, repo_name, snippets, days, sync_delay_hours=delay)
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

    # Filter out already-processed PRs (unless --ignore-tracking is set)
    if not ignore_tracking and all_results:
        filtered_results = []
        for result in all_results:
            owner = result.get('owner', '')
            repo = result.get('repo', '')
            pr_num = result.get('PR', 0)
            
            processed_prs = get_processed_prs(tracking_data, owner, repo)
            if pr_num in processed_prs:
                skipped_prs.append(f"{owner}/{repo}#{pr_num}")
            else:
                filtered_results.append(result)
        
        if skipped_prs:
            print(f"\n[INFO] Skipped {len(skipped_prs)} already-processed PR(s): {', '.join(skipped_prs)}")
            print("   (Use --ignore-tracking to process them again)\n")
        
        all_results = filtered_results

    # Print a single combined report
    if not all_results:
        print("\n[OK] Nothing to do here :-)  There are no PRs that impacted references.\n")
    else:
        import pandas as pd
        df = pd.DataFrame(all_results)
        print("\nThese PRs impacted references across all repos:\n")
        prs = df[["owner", "repo", "PR"]].drop_duplicates()
        for _, row in prs.iterrows():
            pr_url = f"https://github.com/{row['owner']}/{row['repo']}/pull/{row['PR']}"
            print(f"* PR {row['PR']} ({row['repo']}) - {pr_url}")

        print("\n[ACTION] Modify ms.custom metadata  (add or modify 'update-code') in these files:")
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
            
            # Build PR info dictionary with full owner/repo for tracking
            pr_info = {}
            pr_info_full = {}  # For tracking with owner/repo keys
            for _, row in df[["owner", "repo", "PR"]].drop_duplicates().iterrows():
                repo = row['repo']
                owner = row['owner']
                pr_num = row['PR']
                
                # Short key for PR body
                if repo not in pr_info:
                    pr_info[repo] = []
                pr_info[repo].append(pr_num)
                
                # Full key for tracking
                full_key = f"{owner}/{repo}"
                if full_key not in pr_info_full:
                    pr_info_full[full_key] = []
                pr_info_full[full_key].append(pr_num)
            
            # Create the PR (fork_repo can be None to use config/env)
            pr_url, updated_files = create_metadata_update_pr(refs, pr_info, dry_run=dry_run, fork_repo=fork_repo)
            
            if pr_url:
                print("[OK] Metadata update PR created successfully!")
                print(f"   {pr_url}")
                
                # Record the processed PRs in tracking data
                if not dry_run:
                    record_processed_prs(tracking_data, pr_info_full, pr_url, updated_files)
                    save_tracking_data(tracking_data)
                    print(f"[INFO] Recorded {sum(len(prs) for prs in pr_info_full.values())} processed PR(s) in tracking file")
            elif pr_url is None and not dry_run:
                print("[ERROR] Failed to create metadata update PR")
                sys.exit(1)

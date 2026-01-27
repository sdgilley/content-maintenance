#!/usr/bin/env python3
"""
Find PRs that need approval from our team

This script helps identify pull requests in the AI platform docs team repositories
that require review. It automatically checks all repos in the config.yml file.


The script can filter by various criteria like:
- PRs awaiting review
- PRs with specific labels
- PRs updated within a certain timeframe

Usage:
    python find-prs.py                              # Auto-generates markdown report
    python find-prs.py --requested-reviewers        # Only PRs with requested reviewers
    python find-prs.py --labels documentation,needs-review
    python find-prs.py --days 14 --verbose
    python find-prs.py --markdown my-report.md      # Custom markdown filename
    python find-prs.py --output data.csv            # Also save as CSV

Requirements:
    - Set GH_ACCESS_TOKEN environment variable
    - Install required packages: pip install PyGithub requests pandas
"""

import argparse
from datetime import datetime, timedelta, timezone
import pandas as pd
import subprocess
import sys

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import sys
from utilities import gh_auth as auth
from utilities import config


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Find PRs that need approval from AI platform docs teams"
    )
    
    # Filter options (removed repo and team options as they are now hardcoded)
    parser.add_argument(
        "--requested-reviewers", 
        action="store_true",
        help="Only show PRs with requested reviewers"
    )
    
    # Filter options
    parser.add_argument(
        "--labels", 
        type=str, 
        help="Comma-separated list of labels to filter by"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=14,
        help="Look at PRs updated in the last N days (default: 14)"
    )
    parser.add_argument(
        "--state", 
        type=str, 
        choices=["open", "closed", "all"], 
        default="open",        help="PR state to filter by (default: open)"
    )
    parser.add_argument(
        "--draft", 
        action="store_true",
        help="Include draft PRs"
    )
    
    # Output options
    parser.add_argument(
        "--output", 
        type=str, 
        help="Output file path (CSV format)"
    )
    parser.add_argument(
        "--markdown", 
        type=str, 
        help="Output file path for Markdown format with clickable links"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show detailed information"
    )
    
    return parser.parse_args()


def get_team_repos():
    """Get the hardcoded list of repositories and their teams"""
    repos_config = config.get_repositories()
    team_repos = []
    
    for repo_key, repo_config in repos_config.items():
        team_repos.append({
            "owner": repo_config["owner"],
            "repo": repo_config["repo"], 
            "team": repo_config["team"],
            "short_name": repo_config["short_name"],
            "pr_report_arg": repo_config["pr_report_arg"]
        })
    
    return team_repos


def get_prs_for_repo(owner, repo_name, args):
    """Get PRs for a specific repository based on criteria"""
    try:
        repo = auth.connect_repo(f"{owner}/{repo_name}")
        
        # Get the team info for this repository
        team_info = None
        for repo_config in get_team_repos():
            if repo_config["owner"] == owner and repo_config["repo"] == repo_name:
                team_info = repo_config
                break
        
        # Calculate date filter if specified
        since_date = None
        if args.days:
            since_date = datetime.now(timezone.utc) - timedelta(days=args.days)
        
        # Get PRs
        prs = repo.get_pulls(
            state=args.state,
            sort="updated",
            direction="desc"
        )
        
        pr_data = []
        
        for pr in prs:
            # Skip if too old
            if since_date and pr.updated_at < since_date:
                if args.verbose and pr.number == 3662:
                    print(f"PR #{pr.number} skipped due to age. Updated: {pr.updated_at}, Cutoff: {since_date}")
                continue
                
            # Skip drafts unless requested
            if pr.draft and not args.draft:
                if args.verbose and pr.number == 3662:
                    print(f"PR #{pr.number} skipped because it's a draft")
                continue
            
            # Check labels filter
            if args.labels:
                required_labels = [label.strip() for label in args.labels.split(",")]
                pr_labels = [label.name for label in pr.labels]
                if not any(label in pr_labels for label in required_labels):
                    if args.verbose and pr.number == 3662:
                        print(f"PR #{pr.number} skipped due to labels filter")
                    continue
            
            # Check if PR needs review from team
            needs_team_review = check_if_needs_team_review(pr, args, team_info)
            
            if args.verbose and pr.number == 3662:
                print(f"PR #{pr.number} needs_team_review: {needs_team_review}")
                if hasattr(pr, 'requested_teams'):
                    print(f"Requested teams: {[team.slug for team in pr.requested_teams]}")

            if needs_team_review:
                pr_info = {
                    "repository": f"{owner}/{repo_name}",
                    "pr_number": pr.number,
                    "title": pr.title,
                    "author": pr.user.login,
                    "state": pr.state,
                    "draft": pr.draft,
                    "created_at": pr.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": pr.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "url": pr.html_url,
                    "labels": ", ".join([label.name for label in pr.labels]),
                    "requested_reviewers": ", ".join([reviewer.login for reviewer in pr.requested_reviewers]),
                    "requested_teams": ", ".join([team.slug for team in pr.requested_teams]) if hasattr(pr, 'requested_teams') else "",
                    "assignees": ", ".join([assignee.login for assignee in pr.assignees]),
                    "mergeable": pr.mergeable
                }
                pr_data.append(pr_info)
                
        return pr_data
        
    except Exception as e:
        print(f"Error accessing repository {owner}/{repo_name}: {e}")
        return []


def check_if_needs_team_review(pr, args, team_info):
    """Check if a PR needs review from the specific team"""
    if not team_info:
        return False
    
    # Get the team name without the @ symbol for comparison
    team_name = team_info["team"].replace("@", "")
    
    # Check if the team is in requested reviewers (teams)
    requested_teams = [team.slug.lower() for team in pr.requested_teams] if hasattr(pr, 'requested_teams') else []
    
    # The team slug format might be different, so check various formats
    team_variations = [
        team_name.lower(),
        team_name.lower().replace("/", "-"),
        team_name.lower().split("/")[-1] if "/" in team_name else team_name.lower(),
        "ai-platform-docs"  # Add the known GitHub team slug
    ]
    
    # Check if any variation of our team name is in the requested teams
    for variation in team_variations:
        if variation in requested_teams:
            return True
    
    # Also check requested_reviewers for individual users if requested_reviewers flag is set
    if args.requested_reviewers:
        return len(pr.requested_reviewers) > 0
    
    # If no team match found, don't include this PR
    return False


def run_pr_report(pr_number, repo_key):
    """Run pr-report.py for a specific PR and return the report status"""
    try:
        result = subprocess.run(
            [sys.executable, "pr-report.py", str(pr_number), repo_key],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        
        # Check for approval indicators in output
        # [OK] indicates no problems found
        # [WARN] indicates issues that need fixing
        has_issues = "[WARN]" in output
        has_approval = "[OK]" in output
        
        return {
            "approved": has_approval and not has_issues,
            "output": output,
            "needs_check": has_issues
        }
    except subprocess.TimeoutExpired:
        return {
            "approved": False,
            "output": "Report execution timed out",
            "needs_check": True
        }
    except Exception as e:
        return {
            "approved": False,
            "output": f"Error running report: {e}",
            "needs_check": True
        }


def write_markdown_report(all_pr_data, filename):
    """Write results to a Markdown file with categorized PRs"""
    approved_prs = all_pr_data.get("approved", [])
    check_prs = all_pr_data.get("needs_check", [])
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Pull Requests Review Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        total_prs = len(approved_prs) + len(check_prs)
        f.write(f"**Total PRs Analyzed: {total_prs}**\n\n")
        
        if total_prs == 0:
            f.write("Nothing to do here, no PRs found.\n")
            return
        
        # Section 1: PRs OK to Approve
        f.write("## [OK] PRs OK to Approve\n\n")
        f.write(f"**Count: {len(approved_prs)}**\n\n")
        
        if approved_prs:
            f.write("| Repo | PR | Title | Author |\n")
            f.write("|----|----|----|----|  \n")
            
            for pr in approved_prs:
                pr_link = f"[#{pr['pr_number']}]({pr['url']})"
                title = pr['title'].replace('|', '\\|')
                author = pr['author']
                shortname = pr.get('short_name', pr['repository'].split('/')[-1])
                
                f.write(f"| {shortname} | {pr_link} | {title} | {author} |\n")
        else:
            f.write("No PRs ready for approval at this time.\n")
        
        f.write("\n")
        
        # Section 2: PRs Requiring Further Review
        f.write("## [WARN] PRs Requiring Further Review\n\n")
        f.write(f"**Count: {len(check_prs)}**\n\n")
        
        if check_prs:
            f.write("| Repo | PR | Title | Author | Issues Found |\n")
            f.write("|----|----|----|----|----| \n")
            
            for pr in check_prs:
                pr_link = f"[#{pr['pr_number']}]({pr['url']})"
                title = pr['title'].replace('|', '\\|')
                author = pr['author']
                shortname = pr.get('short_name', pr['repository'].split('/')[-1])
                issues = pr.get('issue_summary', 'Issues found - review details')
                
                f.write(f"| {shortname} | {pr_link} | {title} | {author} | {issues} |\n")
            
            # Add detailed findings section
            f.write("\n### Detailed Findings\n\n")
            
            for pr in check_prs:
                f.write(f"#### PR #{pr['pr_number']}: {pr['title']}\n\n")
                f.write(f"**Repository:** {pr['repository']}\n\n")
                f.write(f"**Author:** {pr['author']}\n\n")
                
                if pr.get('report_output'):
                    f.write("**Report Output:**\n\n")
                    f.write("```\n")
                    f.write(pr['report_output'][:1000])  # Limit output to first 1000 chars
                    if len(pr.get('report_output', '')) > 1000:
                        f.write("\n... (output truncated) ...\n")
                    f.write("```\n\n")
                
                f.write("---\n\n")
        else:
            f.write("No PRs requiring further review.\n")
        
        f.write("\n---\n")
        f.write("*Report generated by find-prs.py with pr-report.py analysis*\n")




def display_results(all_pr_data, args):
    """Display the results in a formatted way"""
    approved_prs = all_pr_data.get("approved", [])
    check_prs = all_pr_data.get("needs_check", [])
    
    total_prs = len(approved_prs) + len(check_prs)
    
    if total_prs == 0:
        print("✅ You're all caught up.")
        return
    
    print(f"\n{'='*80}")
    print(f"PR ANALYSIS COMPLETE")
    print(f"{'='*80}\n")
    
    print(f"[OK] PRs OK to Approve: {len(approved_prs)}")
    if approved_prs:
        for pr in approved_prs:
            print(f"  - [{pr['short_name']}] #{pr['pr_number']}: {pr['title'][:60]}")
            print(f"    {pr['url']}")
    
    print(f"\n[WARN]  PRs Requiring Further Review: {len(check_prs)}")
    if check_prs:
        for pr in check_prs:
            print(f"  - [{pr['short_name']}] #{pr['pr_number']}: {pr['title'][:60]}")
            print(f"    {pr['url']}")
            if pr.get('issue_summary'):
                print(f"    Issue: {pr['issue_summary']}")
    
    print(f"\n{'='*80}\n")
    
    # Save to Markdown
    if args.markdown:
        write_markdown_report(all_pr_data, args.markdown)
        print(f"Markdown report saved to: {args.markdown}")
    else:
        # Auto-generate markdown report with default name if no specific output requested
        default_md_file = f"pr-review-report-{datetime.now().strftime('%Y-%m-%d')}.md"
        write_markdown_report(all_pr_data, default_md_file)
        print(f"Markdown report saved to: {default_md_file}")
    
    # Save to CSV if requested
    if args.output:
        # Flatten the data for CSV output
        csv_data = []
        for pr in approved_prs:
            pr['status'] = 'OK_TO_APPROVE'
            csv_data.append(pr)
        for pr in check_prs:
            pr['status'] = 'NEEDS_CHECK'
            csv_data.append(pr)
        
        if csv_data:
            df = pd.DataFrame(csv_data)
            df.to_csv(args.output, index=False)
            print(f"CSV report saved to: {args.output}")



def main():
    """Main function"""
    args = parse_arguments()
    
    approved_prs = []
    check_prs = []
    
    # Process hardcoded repositories
    team_repos = get_team_repos()
    
    for repo_config in team_repos:
        owner = repo_config["owner"]
        repo_name = repo_config["repo"]
        team = repo_config["team"]
        repo_key = repo_config["pr_report_arg"]
        short_name = repo_config["short_name"]
        
        print(f"Checking repository: {owner}/{repo_name} (Team: {team})")
        pr_data = get_prs_for_repo(owner, repo_name, args)
        
        # Run pr-report.py for each PR and categorize
        for pr in pr_data:
            print(f"  Analyzing PR #{pr['pr_number']}: {pr['title'][:50]}...", end=" ")
            report = run_pr_report(pr['pr_number'], repo_key)
            
            pr['short_name'] = short_name
            pr['report_output'] = report['output']
            
            if report['approved']:
                approved_prs.append(pr)
                print("[OK]")
            else:
                # Extract issue summary from output
                if "Modified File" in report['output']:
                    pr['issue_summary'] = "Modified files with references found"
                elif "DELETED FILE" in report['output']:
                    pr['issue_summary'] = "Deleted files with references found"
                elif "RENAMED FILE" in report['output']:
                    pr['issue_summary'] = "Renamed files with references found"
                elif "No problems" in report['output']:
                    pr['issue_summary'] = "Review passed"
                    approved_prs.append(pr)
                    print("[OK]")
                    continue
                else:
                    pr['issue_summary'] = "Review required"
                
                check_prs.append(pr)
                print("[WARN]")
    
    # Prepare data for output
    all_pr_data = {
        "approved": approved_prs,
        "needs_check": check_prs
    }
    
    # Display and save results
    print(f"\nTotal PRs found across all repositories: {len(approved_prs) + len(check_prs)}")
    display_results(all_pr_data, args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Find PRs that need approval from our team

This script helps identify pull requests in the AI platform docs team repositories
that require review. It automatically checks both:
- Azure-AI-Foundry/foundry-samples (Team: @azure-ai-foundry/ai-platform-docs)
- Azure-Samples/azureai-samples (Team: @azure/ai-platform-docs)

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
from utilities import gh_auth as auth


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
        help="Look at PRs updated in the last N days (default: 7)"
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
    return [
        {
            "owner": "Azure-AI-Foundry",
            "repo": "foundry-samples", 
            "team": "@azure-ai-foundry/ai-platform-docs"
        },
        {
            "owner": "Azure",
            "repo": "azureml-examples",
            "team": "@azure/ai-platform-docs"
        }
    ]


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
                continue
                
            # Skip drafts unless requested
            if pr.draft and not args.draft:
                continue
            
            # Check labels filter
            if args.labels:
                required_labels = [label.strip() for label in args.labels.split(",")]
                pr_labels = [label.name for label in pr.labels]
                if not any(label in pr_labels for label in required_labels):
                    continue
            
            # Check if PR needs review from team
            needs_team_review = check_if_needs_team_review(pr, args, team_info)
            
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
                    "mergeable": pr.mergeable,
                    "review_status": get_review_status(pr)
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
    requested_teams = [team.slug for team in pr.requested_teams] if hasattr(pr, 'requested_teams') else []
    
    # The team slug format might be different, so check various formats
    team_variations = [
        team_name,
        team_name.replace("/", "-"),
        team_name.split("/")[-1] if "/" in team_name else team_name
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


def get_review_status(pr):
    """Get the review status of a PR"""
    try:
        reviews = pr.get_reviews()
        review_states = [review.state for review in reviews]
        
        if "APPROVED" in review_states:
            return "APPROVED"
        elif "CHANGES_REQUESTED" in review_states:
            return "CHANGES_REQUESTED"
        elif "COMMENTED" in review_states:
            return "COMMENTED"
        else:
            return "NO_REVIEWS"
    except:
        return "UNKNOWN"


def write_markdown_report(all_pr_data, filename):
    """Write results to a Markdown file with clickable links"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Pull Requests Requiring Review\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total PRs found: **{len(all_pr_data)}**\n\n")
        
        if not all_pr_data:
            f.write("No PRs found matching the criteria.\n")
            return
        
        # Group by repository
        repos = {}
        for pr in all_pr_data:
            repo_name = pr['repository']
            if repo_name not in repos:
                repos[repo_name] = []
            repos[repo_name].append(pr)
        
        # Write each repository section
        for repo_name, prs in repos.items():
            f.write(f"## {repo_name}\n\n")
            f.write(f"Found **{len(prs)}** PRs in this repository\n\n")
            
            # Write table header
            f.write("| PR | Title | Author |  Report |\n")
            f.write("|----|----|----|----| \n")
            
            # Write each PR as a table row
            for pr in prs:
                pr_link = f"[#{pr['pr_number']}]({pr['url']})"
                title = pr['title'].replace('|', '\\|')  # Escape pipes in title
                author = pr['author']
                status = pr['review_status']
                if pr['draft']:
                    status += " (DRAFT)"
                updated = pr['updated_at'].split(' ')[0]  # Just the date
                # reviewers = pr['requested_reviewers'] if pr['requested_reviewers'] else "None"
                # teams = pr['requested_teams'] if pr['requested_teams'] else "None"
                # labels = pr['labels'] if pr['labels'] else "None"
                
                # Generate the appropriate pr-report.py command based on repository
                repo_arg = ""
                if "Azure-AI-Foundry/foundry-samples" in repo_name:
                    repo_arg = "ai"
                elif "Azure-Samples/azureai-samples" in repo_name:
                    repo_arg = "ai2"
                elif "Azure/azureml-examples" in repo_name:
                    repo_arg = "ml"
                
                report_command = f"`python pr-report.py {pr['pr_number']} {repo_arg}`"
                
                f.write(f"| {pr_link} | {title} | {author} | {report_command} |\n")
            
            f.write("\n")
        
        f.write("\n---\n")
        f.write("*Click on PR numbers to view the pull request on GitHub*\n")
def display_results(all_pr_data, args):
    """Display the results in a formatted way"""
    if not all_pr_data:
        print("No PRs found matching the criteria.")
        return
    
    df = pd.DataFrame(all_pr_data)
      # Set display options for better formatting
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_colwidth", 50)
    pd.set_option("display.width", None)
    
    print(f"\n{'='*80}")
    print(f"FOUND {len(all_pr_data)} PRs REQUIRING REVIEW")
    print(f"{'='*80}\n")
    
    if args.verbose:
        # Show detailed information
        for _, pr in df.iterrows():
            print(f"Repository: {pr['repository']}")
            print(f"PR #{pr['pr_number']}: {pr['title']}")
            print(f"Author: {pr['author']}")
            print(f"State: {pr['state']} {'(DRAFT)' if pr['draft'] else ''}")
            print(f"Review Status: {pr['review_status']}")
            print(f"Updated: {pr['updated_at']}")
            print(f"URL: {pr['url']}")
            if pr['labels']:
                print(f"Labels: {pr['labels']}")
            if pr['requested_reviewers']:
                print(f"Requested Reviewers: {pr['requested_reviewers']}")
            if pr['requested_teams']:
                print(f"Requested Teams: {pr['requested_teams']}")
            if pr['assignees']:
                print(f"Assignees: {pr['assignees']}")
            print("-" * 60)
    else:
        # Show summary table
        summary_df = df[['repository', 'pr_number', 'title', 'author', 'review_status', 'updated_at', 'url']]
        print(summary_df.to_string(index=False))
    
    # Save to CSV if requested
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nResults saved to: {args.output}")
    
    # Save to Markdown if requested
    if args.markdown:
        write_markdown_report(all_pr_data, args.markdown)
        print(f"\nMarkdown report saved to: {args.markdown}")
    
    # Auto-generate markdown report with default name if no specific output requested
    if not args.output and not args.markdown:
        default_md_file = f"pr-review-report-{datetime.now().strftime('%Y-%m-%d')}.md"
        write_markdown_report(all_pr_data, default_md_file)
        print(f"\nMarkdown report automatically saved to: {default_md_file}")


def main():
    """Main function"""
    args = parse_arguments()
    
    all_pr_data = []
    
    # Process hardcoded repositories
    team_repos = get_team_repos()
    
    for repo_config in team_repos:
        owner = repo_config["owner"]
        repo_name = repo_config["repo"]
        team = repo_config["team"]
        
        print(f"Checking repository: {owner}/{repo_name} (Team: {team})")
        pr_data = get_prs_for_repo(owner, repo_name, args)
        all_pr_data.extend(pr_data)
    
    # Display results
    display_results(all_pr_data, args)


if __name__ == "__main__":
    main()

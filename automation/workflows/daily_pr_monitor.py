"""
Daily PR monitoring workflow

Finds PRs needing review, analyzes them for safety, and auto-approves
safe PRs while flagging others for manual review.
"""

import os
import sys
import logging
import argparse
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from automation.core.config import (
    get_automation_config,
    get_email_config,
    get_pr_approval_config
)
from automation.core.github_client import GitHubClient
from automation.core.reporter import ReportGenerator, EmailSender

# Import existing utilities
from utilities import gh_auth
from utilities import helpers as h
import pandas as pd

logger = logging.getLogger(__name__)


class PRAnalyzer:
    """Analyzes PRs using existing pr-report.py logic"""
    
    def __init__(self, config):
        self.config = config
    
    def analyze_pr(self, repo_full_name: str, pr_number: int) -> Dict[str, Any]:
        """
        Analyze a PR for documentation impact
        
        Args:
            repo_full_name: Full repository name (owner/repo)
            pr_number: PR number
            
        Returns:
            Analysis results dictionary
        """
        try:
            owner, repo = repo_full_name.split('/')
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files?per_page=100"
            
            prfiles = gh_auth.get_auth_response(url)
            
            if "message" in prfiles:
                return {
                    'error': f"Failed to fetch PR files: {prfiles.get('message')}",
                    'safe_to_approve': False
                }
            
            # Extract file changes
            deleted_files = [f["filename"] for f in prfiles if f["status"] == "removed"]
            modified_files = [(f["filename"], f["blob_url"]) for f in prfiles if f["status"] == "modified"]
            renamed_files = [f["previous_filename"] for f in prfiles if f["status"] == "renamed"]
            
            # Load snippet references
            snippet_fn = self.config.get_refs_found_csv_path()
            if not os.path.exists(snippet_fn):
                logger.warning(f"Snippet file not found: {snippet_fn}")
                snippets = pd.DataFrame(columns=['ref_file', 'from_file', 'repo_name'])
            else:
                snippets = h.read_snippets(snippet_fn)
            
            # Check for issues
            issues = []
            deleted_cells_found = []
            
            # Check deleted files
            deleted_referenced = []
            for file in deleted_files:
                if (snippets["ref_file"] == file).any():
                    deleted_referenced.append(file)
                    issues.append(f"Deleted file is referenced: {file}")
            
            # Check renamed files
            renamed_referenced = []
            for file in renamed_files:
                if (snippets["ref_file"] == file).any():
                    renamed_referenced.append(file)
                    issues.append(f"Renamed file is referenced: {file}")
            
            # Check modified files for deleted cells
            repo_obj = gh_auth.connect_repo(repo_full_name)
            for file, blob_url in modified_files:
                if (snippets["ref_file"] == file).any():
                    nb, adds, deletes, _ = h.find_changes(file, prfiles, blob_url)
                    deleted_cells = [value for value in deletes if value not in adds]
                    if deleted_cells:
                        deleted_cells_found.append({
                            'file': file,
                            'cells': deleted_cells
                        })
                        issues.append(f"Modified file has deleted cells: {file}")
            
            return {
                'pr_number': pr_number,
                'repo': repo_full_name,
                'deleted_files': deleted_files,
                'modified_files': [f[0] for f in modified_files],
                'renamed_files': renamed_files,
                'deleted_referenced': deleted_referenced,
                'renamed_referenced': renamed_referenced,
                'deleted_cells': deleted_cells_found,
                'issues': issues,
                'safe_to_approve': len(issues) == 0
            }
        except Exception as e:
            logger.error(f"Error analyzing PR {pr_number}: {e}")
            return {
                'error': str(e),
                'safe_to_approve': False
            }


class PRFinder:
    """Finds PRs needing review using existing find-prs.py logic"""
    
    def __init__(self, config, github_client):
        self.config = config
        self.github_client = github_client
    
    def find_prs_needing_review(self, days: int = 14) -> List[Dict[str, Any]]:
        """
        Find PRs needing team review
        
        Args:
            days: Look at PRs updated in last N days
            
        Returns:
            List of PR dictionaries
        """
        all_prs = []
        
        repos = self.config.get_repositories()
        for repo_key, repo_config in repos.items():
            owner = repo_config['owner']
            repo_name = repo_config['repo']
            team = repo_config['team']
            
            try:
                logger.info(f"Checking {owner}/{repo_name} for PRs needing review")
                
                repo = self.github_client.get_repo(f"{owner}/{repo_name}")
                prs = repo.get_pulls(state='open', sort='updated', direction='desc')
                
                for pr in prs:
                    # Check if team is requested
                    team_slug = team.replace('@', '').split('/')[-1].lower()
                    requested_teams = [t.slug.lower() for t in pr.requested_teams] if hasattr(pr, 'requested_teams') else []
                    
                    # Also check for common team slug variations
                    if any(slug in requested_teams for slug in [team_slug, 'ai-platform-docs']):
                        all_prs.append({
                            'repo': f"{owner}/{repo_name}",
                            'number': pr.number,
                            'title': pr.title,
                            'author': pr.user.login,
                            'url': pr.html_url,
                            'draft': pr.draft,
                            'mergeable': pr.mergeable,
                            'pr_object': pr
                        })
            except Exception as e:
                logger.error(f"Error finding PRs in {owner}/{repo_name}: {e}")
        
        logger.info(f"Found {len(all_prs)} PRs needing review")
        return all_prs


def run_daily_workflow(dry_run: bool = False):
    """
    Main daily workflow function
    
    Args:
        dry_run: If True, only analyze without taking actions
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=" * 60)
    logger.info("Starting Daily PR Monitoring Workflow")
    logger.info(f"Dry run mode: {dry_run}")
    logger.info("=" * 60)
    
    # Initialize variables for report generation (ensures report is always created)
    auto_approved = []
    manual_review = []
    errors = []
    prs = []
    config = None
    report_gen = None
    
    try:
        # Load configurations
        config = get_automation_config()
        email_config = get_email_config()
        pr_config = get_pr_approval_config()
        
        # Override dry_run from config if set
        if pr_config.dry_run:
            dry_run = True
            logger.info("Dry run mode enabled via configuration")
        
        # Initialize components
        github_client = GitHubClient()
        pr_finder = PRFinder(config, github_client)
        pr_analyzer = PRAnalyzer(config)
        report_gen = ReportGenerator()
        
        # Find PRs needing review
        prs = pr_finder.find_prs_needing_review(days=14)
        
        if not prs:
            logger.info("No PRs found needing review")
            # Continue to report generation below (don't return early)
        
        # Analyze each PR
        auto_approved = []
        manual_review = []
        errors = []
        
        for pr_info in prs:
            logger.info(f"Analyzing PR #{pr_info['number']} in {pr_info['repo']}")
            
            analysis = pr_analyzer.analyze_pr(pr_info['repo'], pr_info['number'])
            
            if 'error' in analysis:
                errors.append(f"PR #{pr_info['number']}: {analysis['error']}")
                manual_review.append({
                    'number': pr_info['number'],
                    'repo': pr_info['repo'],
                    'title': pr_info['title'],
                    'url': pr_info['url'],
                    'issues': [analysis['error']]
                })
                continue
            
            pr_data = {
                'number': pr_info['number'],
                'repo': pr_info['repo'],
                'title': pr_info['title'],
                'url': pr_info['url'],
                'author': pr_info['author']
            }
            
            if analysis['safe_to_approve'] and pr_config.auto_approve_enabled:
                # Auto-approve PR
                comment = (
                    "✅ **Auto-approved by content maintenance automation**\n\n"
                    "This PR has been automatically validated and approved because:\n"
                    "- No deleted files are referenced in documentation\n"
                    "- No renamed files are referenced in documentation\n"
                    "- No deleted cells/snippets in modified files that are referenced in docs\n\n"
                    "If you notice any issues, please add a comment and we'll review."
                )
                
                success = github_client.approve_pr(pr_info['pr_object'], comment, dry_run)
                
                if success:
                    logger.info(f"✅ Auto-approved PR #{pr_info['number']}")
                    auto_approved.append(pr_data)
                else:
                    logger.error(f"Failed to approve PR #{pr_info['number']}")
                    errors.append(f"Failed to approve PR #{pr_info['number']}")
                    manual_review.append({**pr_data, 'issues': ['Failed to auto-approve']})
            else:
                # Requires manual review
                logger.info(f"⚠️ PR #{pr_info['number']} requires manual review")
                manual_review.append({
                    **pr_data,
                    'issues': analysis['issues']
                })
                
                # Add comment explaining issues
                if analysis['issues'] and not dry_run:
                    comment = (
                        "⚠️ **Manual review required**\n\n"
                        "This PR requires manual review due to the following issues:\n"
                        + "\n".join([f"- {issue}" for issue in analysis['issues']])
                        + "\n\nPlease review and address these issues before merging."
                    )
                    github_client.add_comment(pr_info['pr_object'], comment, dry_run)
        
        # Generate and send report
        logger.info("Generating daily report")
        html, text = report_gen.generate_daily_report(auto_approved, manual_review, errors)
        
        # Save report to file
        reports_dir = config.get_reports_directory()
        saved_path = report_gen.save_to_file(html, reports_dir, 'daily')
        if saved_path:
            logger.info(f"Report saved to: {saved_path}")
        else:
            logger.warning("Failed to save report to file")
        
        # Write GitHub Actions summary
        summary_md = f"""# Daily PR Monitor Report - {datetime.now().strftime('%Y-%m-%d')}

## Summary
- **Total PRs Found**: {len(prs)}
- **Auto-Approved**: {len(auto_approved)}
- **Requiring Manual Review**: {len(manual_review)}
- **Errors**: {len(errors)}

## Auto-Approved PRs
"""
        for pr in auto_approved:
            summary_md += f"- [#{pr['number']}]({pr['url']}) - {pr['title']}\n"
        
        if manual_review:
            summary_md += "\n## PRs Requiring Manual Review\n"
            for pr in manual_review:
                summary_md += f"- [#{pr['number']}]({pr['url']}) - {pr['title']}\n"
                summary_md += f"  - Issues: {', '.join(pr['issues'])}\n"
        
        report_gen.write_github_summary(summary_md)
        
        # Send email (if configured)
        if email_config.is_configured():
            logger.info("Email is configured, sending email report")
            email_sender = EmailSender(
                email_config.smtp_server,
                email_config.smtp_port,
                email_config.smtp_username,
                email_config.smtp_password,
                email_config.from_address
            )
            
            subject = f"[Azure AI Docs] Daily PR Monitor - {datetime.now().strftime('%Y-%m-%d')}"
            if dry_run:
                subject = "[DRY RUN] " + subject
            
            email_sender.send_email(
                email_config.to_addresses,
                subject,
                html,
                text,
                dry_run
            )
            logger.info("Email report sent")
        else:
            logger.info("Email not configured, skipping email notification")
        
        logger.info("=" * 60)
        logger.info("Daily workflow completed successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Daily workflow failed: {e}", exc_info=True)
        errors.append(f"Workflow error: {str(e)}")
        
        # Still try to generate a report even on failure
        try:
            if report_gen is None:
                report_gen = ReportGenerator()
            if config is None:
                config = get_automation_config()
            
            html, text = report_gen.generate_daily_report(auto_approved, manual_review, errors)
            
            reports_dir = config.get_reports_directory()
            saved_path = report_gen.save_to_file(html, reports_dir, 'daily')
            if saved_path:
                logger.info(f"Error report saved to: {saved_path}")
            
            # Write error summary to GitHub Actions
            summary_md = f"""# Daily PR Monitor Report - {datetime.now().strftime('%Y-%m-%d')}

## ⚠️ Workflow Error

The workflow encountered an error: `{str(e)}`

## Partial Results
- **PRs Analyzed Before Error**: {len(auto_approved) + len(manual_review)}
- **Auto-Approved**: {len(auto_approved)}
- **Requiring Manual Review**: {len(manual_review)}
- **Errors**: {len(errors)}

Please check the workflow logs for more details.
"""
            report_gen.write_github_summary(summary_md)
        except Exception as report_error:
            logger.error(f"Failed to generate error report: {report_error}")
        
        raise


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Daily PR monitoring workflow")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no actual approvals)'
    )
    args = parser.parse_args()
    
    run_daily_workflow(dry_run=args.dry_run)


if __name__ == '__main__':
    main()

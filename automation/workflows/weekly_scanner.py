"""
Weekly snippet scanning workflow

Scans documentation for code references, updates CODEOWNERS files,
and creates PRs for documentation metadata updates.
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
    get_git_config
)
from automation.core.github_client import GitHubClient
from automation.core.git_operations import GitOperations, commit_to_maintenance_repo
from automation.core.reporter import ReportGenerator, EmailSender

# Import existing utilities
from find_snippets import find_snippets
from merge_report import main as run_merge_report

logger = logging.getLogger(__name__)


def run_weekly_workflow(dry_run: bool = False):
    """
    Main weekly workflow function
    
    Args:
        dry_run: If True, only analyze without taking actions
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=" * 60)
    logger.info("Starting Weekly Snippet Scanning Workflow")
    logger.info(f"Dry run mode: {dry_run}")
    logger.info("=" * 60)
    
    # Initialize variables for report generation (ensures report is always created)
    config = None
    report_gen = None
    results = {
        'snippet_scan_completed': False,
        'codeowners_updates': [],
        'docs_updates': [],
        'errors': []
    }
    
    try:
        # Load configurations
        config = get_automation_config()
        email_config = get_email_config()
        git_config = get_git_config()
        
        # Override dry_run from config if set
        if git_config.dry_run:
            dry_run = True
            logger.info("Dry run mode enabled via configuration")
        
        # Initialize components
        github_client = GitHubClient()
        git_ops = GitOperations(github_client, git_config.commit_author_name, git_config.commit_author_email)
        report_gen = ReportGenerator()
        
        # Step 1: Run snippet scanner
        logger.info("Step 1: Running snippet scanner")
        try:
            find_snippets()
            results['snippet_scan_completed'] = True
            logger.info("✅ Snippet scan completed")
        except Exception as e:
            logger.error(f"Snippet scan failed: {e}")
            results['errors'].append(f"Snippet scan failed: {str(e)}")
        
        # Step 2: Commit output files to maintenance repo
        if results['snippet_scan_completed']:
            logger.info("Step 2: Committing output files to maintenance repo")
            try:
                output_dir = config.get_output_directory()
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Check which files changed
                import git
                repo = git.Repo('.')
                changed_files = [item.a_path for item in repo.index.diff(None)]
                changed_files.extend([item.a_path for item in repo.index.diff('HEAD')])
                
                output_files_changed = [f for f in changed_files if f.startswith('outputs/')]
                
                if output_files_changed:
                    commit_message = f"chore: automated update - snippet scan [{timestamp}]"
                    
                    if not dry_run:
                        repo.index.add(output_files_changed)
                        repo.index.commit(commit_message)
                        repo.git.push('origin', 'main')
                        logger.info(f"✅ Committed {len(output_files_changed)} output files")
                    else:
                        logger.info(f"[DRY RUN] Would commit {len(output_files_changed)} files")
                else:
                    logger.info("No changes to output files")
            except Exception as e:
                logger.error(f"Failed to commit output files: {e}")
                results['errors'].append(f"Output commit failed: {str(e)}")
        
        # Step 3: Update CODEOWNERS in code repos
        logger.info("Step 3: Updating CODEOWNERS in code repositories")
        repos = config.get_repositories()
        
        for repo_key, repo_config in repos.items():
            try:
                owner = repo_config['owner']
                repo_name = repo_config['repo']
                
                # Read CODEOWNERS file from outputs
                codeowners_file = os.path.join(
                    config.get_output_directory(),
                    f"CODEOWNERS-{repo_name}.txt"
                )
                
                if not os.path.exists(codeowners_file):
                    logger.warning(f"CODEOWNERS file not found: {codeowners_file}")
                    continue
                
                with open(codeowners_file, 'r') as f:
                    codeowners_content = f.read()
                
                # Clone repo, create branch, update file, create PR
                repo_obj = git_ops.clone_repository(f"{owner}/{repo_name}")
                if not repo_obj:
                    results['errors'].append(f"Failed to clone {owner}/{repo_name}")
                    continue
                
                branch_name = f"automation/codeowners-update-{datetime.now().strftime('%Y%m%d')}"
                git_ops.create_branch(repo_obj, branch_name)
                
                # Update CODEOWNERS file
                git_ops.update_file(repo_obj, ".github/CODEOWNERS", codeowners_content)
                
                # Commit and push
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                commit_msg = f"docs: update CODEOWNERS from docs snapshot [{timestamp}]"
                
                git_ops.commit_changes(repo_obj, [".github/CODEOWNERS"], commit_msg, dry_run)
                git_ops.push_changes(repo_obj, branch_name, dry_run)
                
                # Create PR
                github_repo = github_client.get_repo(f"{owner}/{repo_name}")
                pr = github_client.create_pull_request(
                    github_repo,
                    f"Update CODEOWNERS from documentation snapshot",
                    f"Automated update to CODEOWNERS based on current documentation references.\n\nGenerated on {timestamp}",
                    branch_name,
                    "main",
                    dry_run
                )
                
                if pr or dry_run:
                    results['codeowners_updates'].append({
                        'repo': f"{owner}/{repo_name}",
                        'branch': branch_name,
                        'pr_url': pr.html_url if pr else 'N/A (dry run)',
                        'status': 'success'
                    })
                    logger.info(f"✅ Updated CODEOWNERS for {owner}/{repo_name}")
                else:
                    results['errors'].append(f"Failed to create PR for {owner}/{repo_name}")
                
            except Exception as e:
                logger.error(f"Failed to update CODEOWNERS for {repo_key}: {e}")
                results['errors'].append(f"CODEOWNERS update failed for {repo_key}: {str(e)}")
        
        # Step 4: Run merge report to find docs needing updates
        logger.info("Step 4: Running merge report to find docs needing updates")
        try:
            # Note: merge_report.py would need to be modified to return results
            # For now, we'll just log that this step would run
            logger.info("Merge report analysis would run here")
            # run_merge_report() would be called and results processed
        except Exception as e:
            logger.error(f"Merge report failed: {e}")
            results['errors'].append(f"Merge report failed: {str(e)}")
        
        # Step 5: Create PRs for doc updates (placeholder - would need merge report results)
        logger.info("Step 5: Creating documentation update PRs")
        # This would process results from merge_report and create PRs
        
        # Cleanup temporary directories
        git_ops.cleanup()
        
        # Generate and send report
        logger.info("Generating weekly report")
        
        snippet_results = {
            'completed': results['snippet_scan_completed'],
            'files_committed': len([e for e in results['codeowners_updates'] if e['status'] == 'success'])
        }
        
        html, text = report_gen.generate_weekly_report(
            snippet_results,
            results['codeowners_updates'],
            results['docs_updates']
        )
        
        # Save report to file
        reports_dir = config.get_reports_directory()
        saved_path = report_gen.save_to_file(html, reports_dir, 'weekly')
        if saved_path:
            logger.info(f"Report saved to: {saved_path}")
        else:
            logger.warning("Failed to save report to file")
        
        # Write GitHub Actions summary
        summary_md = f"""# Weekly Snippet Scan Report - {datetime.now().strftime('%Y-%m-%d')}

## Summary
- **Snippet Scan**: {'✅ Completed' if results['snippet_scan_completed'] else '❌ Failed'}
- **CODEOWNERS Updates**: {len(results['codeowners_updates'])}
- **Documentation PRs Created**: {len(results['docs_updates'])}
- **Errors**: {len(results['errors'])}

## CODEOWNERS Updates
"""
        for update in results['codeowners_updates']:
            summary_md += f"- {update['repo']}: [{update['status']}]({update['pr_url']})\n"
        
        if results['errors']:
            summary_md += "\n## Errors\n"
            for error in results['errors']:
                summary_md += f"- {error}\n"
        
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
            
            subject = f"[Azure AI Docs] Weekly Snippet Scan - {datetime.now().strftime('%Y-%m-%d')}"
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
        logger.info("Weekly workflow completed successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Weekly workflow failed: {e}", exc_info=True)
        results['errors'].append(f"Workflow error: {str(e)}")
        
        # Still try to generate a report even on failure
        try:
            if report_gen is None:
                report_gen = ReportGenerator()
            if config is None:
                config = get_automation_config()
            
            snippet_results = {
                'completed': results['snippet_scan_completed'],
                'files_committed': len([e for e in results['codeowners_updates'] if e.get('status') == 'success'])
            }
            
            html, text = report_gen.generate_weekly_report(
                snippet_results,
                results['codeowners_updates'],
                results['docs_updates']
            )
            
            reports_dir = config.get_reports_directory()
            saved_path = report_gen.save_to_file(html, reports_dir, 'weekly')
            if saved_path:
                logger.info(f"Error report saved to: {saved_path}")
            
            # Write error summary to GitHub Actions
            summary_md = f"""# Weekly Snippet Scan Report - {datetime.now().strftime('%Y-%m-%d')}

## ⚠️ Workflow Error

The workflow encountered an error: `{str(e)}`

## Partial Results
- **Snippet Scan**: {'✅ Completed' if results['snippet_scan_completed'] else '❌ Failed'}
- **CODEOWNERS Updates**: {len(results['codeowners_updates'])}
- **Errors**: {len(results['errors'])}

Please check the workflow logs for more details.
"""
            report_gen.write_github_summary(summary_md)
        except Exception as report_error:
            logger.error(f"Failed to generate error report: {report_error}")
        
        raise


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Weekly snippet scanning workflow")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no actual commits/PRs)'
    )
    args = parser.parse_args()
    
    run_weekly_workflow(dry_run=args.dry_run)


if __name__ == '__main__':
    main()

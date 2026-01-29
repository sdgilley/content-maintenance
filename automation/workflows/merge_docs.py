"""
Merge documentation workflow

Runs merge-report.py to analyze recently merged PRs and automatically
creates documentation update PRs when code changes affect docs.

This workflow looks at the last 2 days of merges to ensure overlap
between runs and avoid missing any PRs based on execution timing.
"""

import os
import sys
import logging
import argparse
import subprocess
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from automation.core.config import get_automation_config, get_email_config, get_git_config
from automation.core.reporter import ReportGenerator, EmailSender

logger = logging.getLogger(__name__)


def commit_tracking_file(repo_dir: str) -> bool:
    """
    Commit the merge-tracking.json file back to the repository.
    
    This ensures the tracking data persists between automation runs.
    
    Args:
        repo_dir: Path to the repository root
        
    Returns:
        True if committed successfully, False otherwise
    """
    try:
        import git
        repo = git.Repo(repo_dir)
        
        tracking_file = "outputs/merge-tracking.json"
        
        # Check if tracking file has changes
        changed_files = [item.a_path for item in repo.index.diff(None)]
        untracked = repo.untracked_files
        
        if tracking_file in changed_files or tracking_file in untracked:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
            commit_message = f"chore: update merge tracking data [{timestamp}]"
            
            repo.index.add([tracking_file])
            repo.index.commit(commit_message)
            
            # Push to origin
            origin = repo.remote('origin')
            origin.push()
            
            logger.info(f"✅ Committed and pushed {tracking_file}")
            return True
        else:
            logger.info("No changes to tracking file")
            return True
            
    except Exception as e:
        logger.error(f"Failed to commit tracking file: {e}")
        raise


def run_merge_docs(days: int = 2, dry_run: bool = False, ignore_tracking: bool = False):
    """
    Run merge-report.py to create documentation update PRs
    
    Args:
        days: Look at PRs merged in the last N days (default: 2 for overlap between runs)
        dry_run: If True, preview changes without creating PR
        ignore_tracking: If True, process all PRs regardless of tracking data
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=" * 60)
    logger.info("Starting Merge Documentation Workflow")
    logger.info(f"Looking back: {days} days")
    logger.info(f"Dry run mode: {dry_run}")
    logger.info(f"Ignore tracking: {ignore_tracking}")
    logger.info("=" * 60)
    
    results = {
        'merge_report_completed': False,
        'pr_created': False,
        'pr_url': None,
        'files_updated': 0,
        'tracking_committed': False,
        'errors': []
    }
    
    try:
        # Load configurations
        config = get_automation_config()
        email_config = get_email_config()
        git_config = get_git_config()
        
        # Run merge-report.py
        logger.info("Running merge-report.py analysis...")
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        merge_report_script = os.path.join(script_dir, "merge-report.py")
        
        # Build command arguments
        cmd = [sys.executable, merge_report_script, str(days)]
        
        if not dry_run:
            cmd.append("--create-pr")
        else:
            cmd.extend(["--create-pr", "--dry-run"])
        
        if ignore_tracking:
            cmd.append("--ignore-tracking")
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=script_dir
        )
        
        # Log the output
        if result.stdout:
            logger.info(f"merge-report.py output:\n{result.stdout}")
        
        if result.returncode != 0:
            logger.error(f"merge-report.py failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output: {result.stderr}")
            results['errors'].append(f"merge-report.py execution failed: {result.stderr}")
        else:
            results['merge_report_completed'] = True
            logger.info("✅ merge-report.py completed successfully")
            
            # Parse output to extract PR information
            output = result.stdout
            if "Created documentation update PR:" in output:
                results['pr_created'] = True
                # Extract PR URL from output
                for line in output.split('\n'):
                    if "Created documentation update PR:" in line or "https://github.com" in line:
                        if "github.com" in line:
                            # Extract URL
                            import re
                            url_match = re.search(r'https://github\.com/[^\s]+', line)
                            if url_match:
                                results['pr_url'] = url_match.group(0)
                                break
            elif "No documentation files need updating" in output:
                logger.info("No documentation files needed updating")
            elif "All PRs in this time period have already been processed" in output:
                logger.info("All PRs already processed (tracked)")
        
        # Commit tracking file back to repo if changes were made
        if results['merge_report_completed'] and not dry_run:
            logger.info("Committing tracking file to repository...")
            try:
                commit_tracking_file(script_dir)
                results['tracking_committed'] = True
            except Exception as e:
                logger.warning(f"Failed to commit tracking file: {e}")
                results['errors'].append(f"Tracking file commit failed: {str(e)}")
        
        # Generate summary report
        summary_md = generate_summary_report(results, days, dry_run)
        
        # Write to GitHub Actions summary if available
        report_gen = ReportGenerator()
        report_gen.write_github_summary(summary_md)
        
        # Send email if configured
        if email_config.is_configured():
            logger.info("Sending email report...")
            email_sender = EmailSender(
                email_config.smtp_server,
                email_config.smtp_port,
                email_config.smtp_username,
                email_config.smtp_password,
                email_config.from_address
            )
            
            subject = f"[Azure AI Docs] Merge Docs Workflow - {datetime.now().strftime('%Y-%m-%d')}"
            
            if results['pr_created']:
                subject += " - PR Created"
            
            try:
                email_sender.send_email(
                    to_addresses=email_config.to_addresses,
                    subject=subject,
                    body=summary_md,
                    is_html=False
                )
                logger.info("Email report sent successfully")
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
                results['errors'].append(f"Email send failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        results['errors'].append(str(e))
        raise
    
    finally:
        # Always log final results
        logger.info("=" * 60)
        logger.info("Workflow completed")
        logger.info(f"Merge report completed: {results['merge_report_completed']}")
        logger.info(f"PR created: {results['pr_created']}")
        if results['pr_url']:
            logger.info(f"PR URL: {results['pr_url']}")
        if results['errors']:
            logger.warning(f"Errors encountered: {len(results['errors'])}")
        logger.info("=" * 60)
    
    return results


def generate_summary_report(results: dict, days: int, dry_run: bool) -> str:
    """Generate a markdown summary report"""
    summary = f"""# Merge Documentation Report - {datetime.now().strftime('%Y-%m-%d')}

## Configuration
- **Days analyzed**: {days}
- **Dry run mode**: {dry_run}

## Results
- **Merge report completed**: {'✅' if results['merge_report_completed'] else '❌'}
- **Documentation PR created**: {'✅' if results['pr_created'] else '➖ No'}
- **Tracking file committed**: {'✅' if results.get('tracking_committed') else '➖ No'}
"""
    
    if results['pr_url']:
        summary += f"- **PR URL**: {results['pr_url']}\n"
    
    if dry_run:
        summary += "\n⚠️ **DRY RUN MODE** - No PR was actually created\n"
    
    if results['errors']:
        summary += "\n## ❌ Errors\n"
        for error in results['errors']:
            summary += f"- {error}\n"
    
    if not results['pr_created'] and not results['errors']:
        summary += "\n## ℹ️ Notes\n"
        summary += "- No documentation files needed updating, or all PRs were already processed.\n"
        summary += "- This is normal if there were no recent code merges affecting documentation.\n"
    
    return summary


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Merge documentation workflow - analyzes merged PRs and creates doc update PRs"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=2,
        help='Look at PRs merged in the last N days (default: 2 for overlap between runs)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without creating PR'
    )
    parser.add_argument(
        '--ignore-tracking',
        action='store_true',
        help='Process all PRs regardless of tracking data'
    )
    args = parser.parse_args()
    
    run_merge_docs(days=args.days, dry_run=args.dry_run, ignore_tracking=args.ignore_tracking)


if __name__ == '__main__':
    main()

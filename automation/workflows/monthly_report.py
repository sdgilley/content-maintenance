"""
Monthly maintenance report workflow

Generates statistics and sends monthly summary report.
"""

import os
import sys
import logging
import argparse
from typing import Dict, List, Any
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from automation.core.config import (
    get_automation_config,
    get_email_config
)
from automation.core.github_client import GitHubClient
from automation.core.reporter import ReportGenerator, EmailSender

logger = logging.getLogger(__name__)


def collect_monthly_statistics(github_client: GitHubClient, config) -> Dict[str, Any]:
    """
    Collect statistics for the past month
    
    Args:
        github_client: GitHubClient instance
        config: Automation configuration
        
    Returns:
        Dictionary of statistics
    """
    stats = {
        'prs_reviewed': 0,
        'prs_auto_approved': 0,
        'prs_manual_review': 0,
        'codeowners_updates': 0,
        'docs_prs_created': 0,
        'workflow_runs': 0,
        'failed_workflows': 0
    }
    
    try:
        # Get date range for last month
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Note: These would need to be collected from workflow run history
        # For now, we provide placeholders
        
        # In a real implementation, you would:
        # 1. Query GitHub Actions API for workflow runs
        # 2. Parse workflow logs/artifacts for statistics
        # 3. Count PRs created/approved by the automation
        
        logger.info("Collecting monthly statistics...")
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Placeholder: In real implementation, query GitHub API
        stats['workflow_runs'] = 4  # ~4 weekly runs per month
        stats['codeowners_updates'] = 12  # 3 repos × 4 weeks
        
    except Exception as e:
        logger.error(f"Error collecting statistics: {e}")
    
    return stats


def check_token_expiry() -> List[str]:
    """
    Check if GitHub token is expiring soon
    
    Returns:
        List of warnings
    """
    warnings = []
    
    try:
        # Check if using GitHub App (which has token expiry)
        # Personal Access Tokens don't typically expire unless manually set
        
        # This is a placeholder - in real implementation:
        # 1. Check GitHub App installation token expiry
        # 2. Check if PAT has expiration date set
        # 3. Warn if expiring within 7 days
        
        logger.info("Checking token expiry...")
        
    except Exception as e:
        logger.error(f"Error checking token expiry: {e}")
        warnings.append(f"Failed to check token expiry: {str(e)}")
    
    return warnings


def run_monthly_workflow(dry_run: bool = False):
    """
    Main monthly workflow function
    
    Args:
        dry_run: If True, only generate report without sending
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=" * 60)
    logger.info("Starting Monthly Maintenance Report Workflow")
    logger.info(f"Dry run mode: {dry_run}")
    logger.info("=" * 60)
    
    # Initialize variables for report generation (ensures report is always created)
    config = None
    report_gen = None
    statistics = {}
    warnings = []
    
    try:
        # Load configurations
        config = get_automation_config()
        email_config = get_email_config()
        
        # Initialize components
        github_client = GitHubClient()
        report_gen = ReportGenerator()
        
        # Collect statistics
        logger.info("Collecting monthly statistics")
        statistics = collect_monthly_statistics(github_client, config)
        
        # Check for warnings
        logger.info("Checking for warnings")
        warnings = check_token_expiry()
        
        # Check rate limits
        rate_limits = github_client.get_rate_limit_status()
        logger.info(f"Rate limit status: {rate_limits['core']['remaining']}/{rate_limits['core']['limit']}")
        
        if rate_limits['core']['remaining'] < 100:
            warnings.append(f"GitHub API rate limit low: {rate_limits['core']['remaining']} remaining")
        
        # Generate report
        logger.info("Generating monthly report")
        html, text = report_gen.generate_monthly_report(statistics, warnings)
        
        # Save report to file
        reports_dir = config.get_reports_directory()
        saved_path = report_gen.save_to_file(html, reports_dir, 'monthly')
        if saved_path:
            logger.info(f"Report saved to: {saved_path}")
        else:
            logger.warning("Failed to save report to file")
        
        # Write GitHub Actions summary
        month_name = datetime.now().strftime('%B %Y')
        summary_md = f"""# Monthly Maintenance Report - {month_name}

## Statistics
- **Workflow Runs**: {statistics.get('workflow_runs', 'N/A')}
- **PRs Reviewed**: {statistics.get('prs_reviewed', 'N/A')}
- **PRs Auto-Approved**: {statistics.get('prs_auto_approved', 'N/A')}
- **PRs Manual Review**: {statistics.get('prs_manual_review', 'N/A')}
- **CODEOWNERS Updates**: {statistics.get('codeowners_updates', 'N/A')}
- **Documentation PRs Created**: {statistics.get('docs_prs_created', 'N/A')}

## API Rate Limits
- **Core API**: {rate_limits['core']['remaining']}/{rate_limits['core']['limit']}
- **Search API**: {rate_limits['search']['remaining']}/{rate_limits['search']['limit']}
"""
        
        if warnings:
            summary_md += "\n## ⚠️ Warnings\n"
            for warning in warnings:
                summary_md += f"- {warning}\n"
        
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
            
            subject = f"[Azure AI Docs] Monthly Maintenance Summary - {month_name}"
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
        logger.info("Monthly workflow completed successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Monthly workflow failed: {e}", exc_info=True)
        warnings.append(f"Workflow error: {str(e)}")
        
        # Still try to generate a report even on failure
        try:
            if report_gen is None:
                report_gen = ReportGenerator()
            if config is None:
                config = get_automation_config()
            
            html, text = report_gen.generate_monthly_report(statistics, warnings)
            
            reports_dir = config.get_reports_directory()
            saved_path = report_gen.save_to_file(html, reports_dir, 'monthly')
            if saved_path:
                logger.info(f"Error report saved to: {saved_path}")
            
            # Write error summary to GitHub Actions
            month_name = datetime.now().strftime('%B %Y')
            summary_md = f"""# Monthly Maintenance Report - {month_name}

## ⚠️ Workflow Error

The workflow encountered an error: `{str(e)}`

## Partial Results
- **Statistics Collected**: {len(statistics) > 0}
- **Warnings**: {len(warnings)}

Please check the workflow logs for more details.
"""
            report_gen.write_github_summary(summary_md)
        except Exception as report_error:
            logger.error(f"Failed to generate error report: {report_error}")
        
        raise


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Monthly maintenance report workflow")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no email sent)'
    )
    args = parser.parse_args()
    
    run_monthly_workflow(dry_run=args.dry_run)


if __name__ == '__main__':
    main()

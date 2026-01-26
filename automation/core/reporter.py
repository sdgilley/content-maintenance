"""
Report generation and email notification

Generates HTML/text reports and sends them via email.
Also saves reports as Markdown files to disk.
"""

import os
import logging
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Any, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, Template
from pathlib import Path
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class HTMLToMarkdown:
    """Convert HTML to Markdown format"""
    
    @staticmethod
    def convert(html_content: str) -> str:
        """
        Convert HTML content to readable Markdown
        
        Args:
            html_content: HTML string to convert
            
        Returns:
            Markdown formatted string
        """
        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
        
        # Convert headings
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert links
        text = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert bold
        text = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert italic
        text = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert line breaks
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        
        # Convert paragraphs
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert lists
        text = re.sub(r'<ul[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</ul>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<ol[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</ol>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert code blocks
        text = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', r'```\n\1\n```\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert tables (basic)
        text = re.sub(r'<table[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</table>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<tr[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<th[^>]*>(.*?)</th>', r'| \1 ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<td[^>]*>(.*?)</td>', r'| \1 ', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()


class ReportGenerator:
    """Generate reports from templates"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize report generator
        
        Args:
            templates_dir: Path to templates directory
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        
        if self.templates_dir.exists():
            self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
        else:
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            self.env = None
    
    def generate_daily_report(
        self,
        auto_approved: List[Dict[str, Any]],
        manual_review: List[Dict[str, Any]],
        errors: List[str] = None
    ) -> tuple[str, str]:
        """
        Generate daily PR monitoring report
        
        Args:
            auto_approved: List of auto-approved PRs
            manual_review: List of PRs requiring manual review
            errors: List of errors encountered
            
        Returns:
            Tuple of (html_content, text_content)
        """
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'auto_approved': auto_approved,
            'manual_review': manual_review,
            'errors': errors or [],
            'total_prs': len(auto_approved) + len(manual_review),
            'workflow_url': os.getenv('GITHUB_RUN_URL', '')
        }
        
        html = self._render_template('daily_report.html', data)
        text = self._generate_daily_text_report(data)
        
        return html, text
    
    def generate_weekly_report(
        self,
        snippet_results: Dict[str, Any],
        codeowners_updates: List[Dict[str, Any]],
        prs_created: List[Dict[str, Any]]
    ) -> tuple[str, str]:
        """
        Generate weekly snippet scanning report
        
        Args:
            snippet_results: Results from snippet scanning
            codeowners_updates: CODEOWNERS updates made
            prs_created: PRs created for documentation updates
            
        Returns:
            Tuple of (html_content, text_content)
        """
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'snippet_results': snippet_results,
            'codeowners_updates': codeowners_updates,
            'prs_created': prs_created,
            'workflow_url': os.getenv('GITHUB_RUN_URL', '')
        }
        
        html = self._render_template('weekly_report.html', data)
        text = self._generate_weekly_text_report(data)
        
        return html, text
    
    def generate_monthly_report(
        self,
        statistics: Dict[str, Any],
        warnings: List[str] = None
    ) -> tuple[str, str]:
        """
        Generate monthly maintenance report
        
        Args:
            statistics: Monthly statistics
            warnings: List of warnings
            
        Returns:
            Tuple of (html_content, text_content)
        """
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'month': datetime.now().strftime('%B %Y'),
            'statistics': statistics,
            'warnings': warnings or [],
            'workflow_url': os.getenv('GITHUB_RUN_URL', '')
        }
        
        html = self._render_template('monthly_report.html', data)
        text = self._generate_monthly_text_report(data)
        
        return html, text
    
    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render HTML template"""
        if self.env:
            try:
                template = self.env.get_template(template_name)
                return template.render(**data)
            except Exception as e:
                logger.error(f"Failed to render template {template_name}: {e}")
        
        # Fallback to simple HTML
        return self._generate_simple_html(data)
    
    def _generate_simple_html(self, data: Dict[str, Any]) -> str:
        """Generate simple HTML report as fallback"""
        html = f"""
        <html>
        <head><title>Automation Report</title></head>
        <body>
            <h1>Automation Report - {data.get('date', 'N/A')}</h1>
            <pre>{str(data)}</pre>
        </body>
        </html>
        """
        return html
    
    def _generate_daily_text_report(self, data: Dict[str, Any]) -> str:
        """Generate plain text daily report"""
        lines = [
            f"Daily PR Monitor Report - {data['date']}",
            "=" * 60,
            "",
            f"Total PRs Found: {data['total_prs']}",
            f"Auto-Approved: {len(data['auto_approved'])}",
            f"Requiring Manual Review: {len(data['manual_review'])}",
            ""
        ]
        
        if data['auto_approved']:
            lines.append("AUTO-APPROVED PRs:")
            for pr in data['auto_approved']:
                lines.append(f"  - PR #{pr.get('number')} in {pr.get('repo')}: {pr.get('title')}")
                lines.append(f"    {pr.get('url')}")
            lines.append("")
        
        if data['manual_review']:
            lines.append("PRs REQUIRING MANUAL REVIEW:")
            for pr in data['manual_review']:
                lines.append(f"  - PR #{pr.get('number')} in {pr.get('repo')}: {pr.get('title')}")
                lines.append(f"    Issues: {', '.join(pr.get('issues', []))}")
                lines.append(f"    {pr.get('url')}")
            lines.append("")
        
        if data['errors']:
            lines.append("ERRORS:")
            for error in data['errors']:
                lines.append(f"  - {error}")
            lines.append("")
        
        if data['workflow_url']:
            lines.append(f"Workflow Run: {data['workflow_url']}")
        
        return "\n".join(lines)
    
    def _generate_weekly_text_report(self, data: Dict[str, Any]) -> str:
        """Generate plain text weekly report"""
        lines = [
            f"Weekly Snippet Scan Report - {data['date']}",
            "=" * 60,
            "",
            "SUMMARY:",
            f"  - CODEOWNERS updates: {len(data['codeowners_updates'])}",
            f"  - Documentation PRs created: {len(data['prs_created'])}",
            ""
        ]
        
        if data['codeowners_updates']:
            lines.append("CODEOWNERS UPDATES:")
            for update in data['codeowners_updates']:
                lines.append(f"  - {update.get('repo')}: {update.get('status')}")
            lines.append("")
        
        if data['prs_created']:
            lines.append("DOCUMENTATION PRs CREATED:")
            for pr in data['prs_created']:
                lines.append(f"  - PR #{pr.get('number')}: {pr.get('title')}")
                lines.append(f"    Files: {pr.get('file_count')}")
                lines.append(f"    {pr.get('url')}")
            lines.append("")
        
        if data['workflow_url']:
            lines.append(f"Workflow Run: {data['workflow_url']}")
        
        return "\n".join(lines)
    
    def _generate_monthly_text_report(self, data: Dict[str, Any]) -> str:
        """Generate plain text monthly report"""
        lines = [
            f"Monthly Maintenance Report - {data['month']}",
            "=" * 60,
            "",
            "STATISTICS:",
        ]
        
        for key, value in data.get('statistics', {}).items():
            lines.append(f"  - {key}: {value}")
        
        lines.append("")
        
        if data['warnings']:
            lines.append("WARNINGS:")
            for warning in data['warnings']:
                lines.append(f"  - {warning}")
            lines.append("")
        
        if data['workflow_url']:
            lines.append(f"Workflow Run: {data['workflow_url']}")
        
        return "\n".join(lines)
    
    def save_to_file(
        self,
        html_content: str,
        reports_dir: str,
        workflow_type: str,
        date: Optional[str] = None
    ) -> Optional[str]:
        """
        Save report as Markdown file
        
        Args:
            html_content: HTML content to convert and save
            reports_dir: Directory to save reports in
            workflow_type: Type of workflow (daily, weekly, monthly)
            date: Optional date string (defaults to today)
            
        Returns:
            Path to saved file, or None if failed
        """
        try:
            # Create reports directory if it doesn't exist
            reports_path = Path(reports_dir)
            reports_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            filename = f"{workflow_type}-report-{date}.md"
            filepath = reports_path / filename
            
            # If file exists, add timestamp to make it unique
            if filepath.exists():
                timestamp = datetime.now().strftime('%H%M%S')
                filename = f"{workflow_type}-report-{date}-{timestamp}.md"
                filepath = reports_path / filename
                logger.info(f"File exists, using timestamped filename: {filename}")
            
            # Convert HTML to Markdown
            markdown_content = HTMLToMarkdown.convert(html_content)
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Report saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save report to file: {e}")
            return None
    
    def write_github_summary(self, markdown_content: str):
        """
        Write to GitHub Actions job summary
        
        Args:
            markdown_content: Markdown content to write
        """
        summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary_file:
            try:
                with open(summary_file, 'a', encoding='utf-8') as f:
                    f.write(markdown_content)
                logger.info("Wrote GitHub Actions summary")
            except Exception as e:
                logger.error(f"Failed to write GitHub summary: {e}")
        else:
            logger.info("Not running in GitHub Actions, skipping summary")


class EmailSender:
    """Send email reports via SMTP"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_address: str
    ):
        """
        Initialize email sender
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_address: From email address
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
    
    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        dry_run: bool = False
    ) -> bool:
        """
        Send email report
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (fallback)
            dry_run: If True, only log the action without sending
            
        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would send email to: {to_addresses}")
            logger.info(f"[DRY RUN] Subject: {subject}")
            return True
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_address
            msg['To'] = ', '.join(to_addresses)
            
            # Add text content if provided
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # Add HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            logger.info(f"Sending email to {to_addresses}: {subject}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info("Email sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

"""
Configuration management for automation workflows

Loads configuration from config.yml and environment variables,
providing a centralized interface for all automation settings.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class AutomationConfig:
    """Central configuration manager for automation workflows"""
    
    def __init__(self, config_path: str = "config.yml"):
        """
        Initialize configuration from file and environment variables
        
        Args:
            config_path: Path to main configuration file
        """
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_path = self.base_dir / config_path
        self._config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _validate_config(self):
        """Validate required configuration keys exist"""
        required_keys = ['repositories', 'output_directory']
        for key in required_keys:
            if key not in self._config:
                raise ValueError(f"Missing required configuration key: {key}")
    
    def get_repositories(self) -> Dict[str, Dict[str, Any]]:
        """Get all repository configurations"""
        return self._config.get('repositories', {})
    
    def get_repository(self, repo_key: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific repository"""
        return self._config.get('repositories', {}).get(repo_key)
    
    def get_repository_by_name(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository configuration by owner and repo name"""
        repos = self.get_repositories()
        for repo_config in repos.values():
            if repo_config.get('owner') == owner and repo_config.get('repo') == repo:
                return repo_config
        return None
    
    def get_output_directory(self) -> str:
        """Get output directory path"""
        output_dir = self._config.get('output_directory', 'outputs')
        return str(self.base_dir / output_dir)
    
    def get_reports_directory(self) -> str:
        """Get reports directory path"""
        # Allow override via environment variable or config, default to automation/reports
        reports_dir = os.getenv('REPORTS_DIRECTORY') or self._config.get('reports_directory', 'automation/reports')
        return str(self.base_dir / reports_dir)
    
    def get_refs_found_csv_path(self) -> str:
        """Get path to refs-found.csv file"""
        output_dir = self.get_output_directory()
        return os.path.join(output_dir, "refs-found.csv")
    
    def get_exclude_directories(self) -> List[str]:
        """Get directories to exclude from scanning"""
        return self._config.get('defaults', {}).get('exclude_directories', [])
    
    def get_max_days_for_pr_search(self) -> int:
        """Get max days to search for PRs"""
        return self._config.get('defaults', {}).get('max_days_for_pr_search', 100)


class EmailConfig:
    """Email configuration for notifications"""
    
    def __init__(self):
        # Check if email is explicitly enabled (default: False)
        self.email_enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
        
        # Load SMTP settings (optional if email is disabled)
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_address = os.getenv('SMTP_EMAIL', self.smtp_username)
        
        # Parse recipient addresses
        notification_emails = os.getenv('NOTIFICATION_EMAIL', '')
        self.to_addresses = [email.strip() for email in notification_emails.split(',') if email.strip()]
        
        # Email is enabled only if explicitly set AND credentials are provided
        self.enabled = self.email_enabled and bool(self.smtp_username and self.smtp_password and self.to_addresses)
    
    def validate(self):
        """Validate email configuration (only if email is enabled)"""
        if self.email_enabled:
            if not self.smtp_username:
                raise ValueError("SMTP_USERNAME environment variable is required when EMAIL_ENABLED=true")
            if not self.smtp_password:
                raise ValueError("SMTP_PASSWORD environment variable is required when EMAIL_ENABLED=true")
            if not self.to_addresses:
                raise ValueError("NOTIFICATION_EMAIL environment variable is required when EMAIL_ENABLED=true")
    
    def is_configured(self) -> bool:
        """Check if email is fully configured and enabled"""
        return self.enabled


class GitConfig:
    """Git operations configuration"""
    
    def __init__(self):
        self.commit_author_name = os.getenv('GIT_AUTHOR_NAME', 'Content Maintenance Bot')
        self.commit_author_email = os.getenv('GIT_AUTHOR_EMAIL', 'bot@example.com')
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'


class PRApprovalConfig:
    """PR approval configuration"""
    
    def __init__(self):
        self.auto_approve_enabled = os.getenv('AUTO_APPROVE_ENABLED', 'true').lower() == 'true'
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
        
        # Safety checks that must pass for auto-approval
        self.safety_checks = [
            'no_deleted_referenced_files',
            'no_renamed_referenced_files', 
            'no_deleted_cells_in_modified_files'
        ]


def get_automation_config() -> AutomationConfig:
    """Get automation configuration instance"""
    return AutomationConfig()


def get_email_config() -> EmailConfig:
    """Get email configuration instance"""
    return EmailConfig()


def get_git_config() -> GitConfig:
    """Get git configuration instance"""
    return GitConfig()


def get_pr_approval_config() -> PRApprovalConfig:
    """Get PR approval configuration instance"""
    return PRApprovalConfig()

"""
GitHub API client with retry logic and rate limit handling

Provides a wrapper around PyGithub with exponential backoff,
retry logic, and enhanced error handling.
"""

import os
import time
import logging
from typing import Optional, List
from github import Github, GithubException
from github.Repository import Repository
from github.PullRequest import PullRequest
from github.Issue import Issue

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client with retry logic and rate limiting"""
    
    def __init__(self, token: Optional[str] = None, max_retries: int = 3, backoff_factor: int = 2):
        """
        Initialize GitHub client
        
        Args:
            token: GitHub access token (defaults to GH_ACCESS_TOKEN env var)
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
        """
        self.token = token or os.getenv('GH_ACCESS_TOKEN')
        if not self.token:
            raise ValueError("GitHub token is required (GH_ACCESS_TOKEN environment variable)")
        
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._github = Github(self.token)
        
        logger.info("GitHub client initialized")
    
    def _retry_on_rate_limit(self, func, *args, **kwargs):
        """
        Execute function with retry logic for rate limiting
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result of function execution
        """
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except GithubException as e:
                if e.status == 403 and 'rate limit' in str(e).lower():
                    # Rate limit exceeded
                    reset_time = self._github.get_rate_limit().core.reset
                    wait_time = (reset_time - time.time()) + 10  # Add 10 seconds buffer
                    
                    if wait_time > 0 and attempt < self.max_retries - 1:
                        logger.warning(f"Rate limit exceeded. Waiting {wait_time:.0f} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Rate limit exceeded and max retries reached")
                        raise
                elif e.status >= 500 and attempt < self.max_retries - 1:
                    # Server error, retry with exponential backoff
                    wait_time = self.backoff_factor ** attempt
                    logger.warning(f"Server error ({e.status}). Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Other error or max retries reached
                    raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
        
        raise Exception(f"Max retries ({self.max_retries}) exceeded")
    
    def get_repo(self, full_name: str) -> Repository:
        """
        Get repository object
        
        Args:
            full_name: Full repository name (owner/repo)
            
        Returns:
            Repository object
        """
        logger.info(f"Getting repository: {full_name}")
        return self._retry_on_rate_limit(self._github.get_repo, full_name)
    
    def get_pull_request(self, repo: Repository, pr_number: int) -> PullRequest:
        """
        Get pull request object
        
        Args:
            repo: Repository object
            pr_number: Pull request number
            
        Returns:
            PullRequest object
        """
        logger.info(f"Getting PR #{pr_number} from {repo.full_name}")
        return self._retry_on_rate_limit(repo.get_pull, pr_number)
    
    def get_pull_requests(self, repo: Repository, state: str = 'open', **kwargs) -> List[PullRequest]:
        """
        Get pull requests from repository
        
        Args:
            repo: Repository object
            state: PR state ('open', 'closed', 'all')
            **kwargs: Additional filters
            
        Returns:
            List of PullRequest objects
        """
        logger.info(f"Getting {state} PRs from {repo.full_name}")
        prs = self._retry_on_rate_limit(repo.get_pulls, state=state, **kwargs)
        return list(prs)
    
    def approve_pr(self, pr: PullRequest, comment: str = "", dry_run: bool = False) -> bool:
        """
        Approve a pull request
        
        Args:
            pr: PullRequest object
            comment: Approval comment
            dry_run: If True, only log the action without executing
            
        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would approve PR #{pr.number} in {pr.base.repo.full_name}")
            logger.info(f"[DRY RUN] Comment: {comment}")
            return True
        
        try:
            logger.info(f"Approving PR #{pr.number} in {pr.base.repo.full_name}")
            self._retry_on_rate_limit(
                pr.create_review,
                event="APPROVE",
                body=comment
            )
            return True
        except Exception as e:
            logger.error(f"Failed to approve PR #{pr.number}: {e}")
            return False
    
    def add_comment(self, pr: PullRequest, comment: str, dry_run: bool = False) -> bool:
        """
        Add comment to pull request
        
        Args:
            pr: PullRequest object
            comment: Comment text
            dry_run: If True, only log the action without executing
            
        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would add comment to PR #{pr.number}")
            logger.info(f"[DRY RUN] Comment: {comment}")
            return True
        
        try:
            logger.info(f"Adding comment to PR #{pr.number} in {pr.base.repo.full_name}")
            self._retry_on_rate_limit(pr.create_issue_comment, comment)
            return True
        except Exception as e:
            logger.error(f"Failed to add comment to PR #{pr.number}: {e}")
            return False
    
    def create_pull_request(
        self,
        repo: Repository,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        dry_run: bool = False
    ) -> Optional[PullRequest]:
        """
        Create a pull request
        
        Args:
            repo: Repository object
            title: PR title
            body: PR description
            head: Head branch name
            base: Base branch name
            dry_run: If True, only log the action without executing
            
        Returns:
            PullRequest object if successful, None otherwise
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would create PR in {repo.full_name}")
            logger.info(f"[DRY RUN] Title: {title}")
            logger.info(f"[DRY RUN] Head: {head} -> Base: {base}")
            return None
        
        try:
            logger.info(f"Creating PR in {repo.full_name}: {title}")
            pr = self._retry_on_rate_limit(
                repo.create_pull,
                title=title,
                body=body,
                head=head,
                base=base
            )
            logger.info(f"Created PR #{pr.number}: {pr.html_url}")
            return pr
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            return None
    
    def add_labels(self, pr: PullRequest, labels: List[str], dry_run: bool = False) -> bool:
        """
        Add labels to pull request
        
        Args:
            pr: PullRequest object
            labels: List of label names
            dry_run: If True, only log the action without executing
            
        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would add labels to PR #{pr.number}: {labels}")
            return True
        
        try:
            logger.info(f"Adding labels to PR #{pr.number}: {labels}")
            self._retry_on_rate_limit(pr.add_to_labels, *labels)
            return True
        except Exception as e:
            logger.error(f"Failed to add labels to PR #{pr.number}: {e}")
            return False
    
    def get_rate_limit_status(self) -> dict:
        """
        Get current rate limit status
        
        Returns:
            Dictionary with rate limit information
        """
        rate_limit = self._github.get_rate_limit()
        return {
            'core': {
                'remaining': rate_limit.core.remaining,
                'limit': rate_limit.core.limit,
                'reset': rate_limit.core.reset
            },
            'search': {
                'remaining': rate_limit.search.remaining,
                'limit': rate_limit.search.limit,
                'reset': rate_limit.search.reset
            }
        }

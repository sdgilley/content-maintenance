"""
Git operations for multi-repository management

Handles cloning, committing, pushing, and creating pull requests
across multiple repositories.
"""

import os
import tempfile
import shutil
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import git
from git import Repo

logger = logging.getLogger(__name__)


class GitOperations:
    """Git operations handler for multi-repository workflows"""
    
    def __init__(self, github_client, author_name: str, author_email: str):
        """
        Initialize git operations
        
        Args:
            github_client: GitHubClient instance for API operations
            author_name: Git commit author name
            author_email: Git commit author email
        """
        self.github_client = github_client
        self.author_name = author_name
        self.author_email = author_email
        self.temp_dirs: List[str] = []
    
    def clone_repository(self, repo_full_name: str, branch: str = "main") -> Optional[Repo]:
        """
        Clone repository to temporary directory
        
        Args:
            repo_full_name: Full repository name (owner/repo)
            branch: Branch to clone
            
        Returns:
            GitPython Repo object or None if failed
        """
        try:
            temp_dir = tempfile.mkdtemp(prefix=f"git_{repo_full_name.replace('/', '_')}_")
            self.temp_dirs.append(temp_dir)
            
            clone_url = f"https://{self.github_client.token}@github.com/{repo_full_name}.git"
            
            logger.info(f"Cloning {repo_full_name} (branch: {branch}) to {temp_dir}")
            repo = Repo.clone_from(clone_url, temp_dir, branch=branch)
            
            # Configure git user
            with repo.config_writer() as config:
                config.set_value("user", "name", self.author_name)
                config.set_value("user", "email", self.author_email)
            
            return repo
        except Exception as e:
            logger.error(f"Failed to clone {repo_full_name}: {e}")
            return None
    
    def create_branch(self, repo: Repo, branch_name: str) -> bool:
        """
        Create and checkout new branch
        
        Args:
            repo: GitPython Repo object
            branch_name: Name of branch to create
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Creating branch: {branch_name}")
            repo.git.checkout('-b', branch_name)
            return True
        except Exception as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            return False
    
    def commit_changes(
        self,
        repo: Repo,
        files: List[str],
        commit_message: str,
        dry_run: bool = False
    ) -> bool:
        """
        Stage and commit changes
        
        Args:
            repo: GitPython Repo object
            files: List of file paths to commit
            commit_message: Commit message
            dry_run: If True, only log the action without executing
            
        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would commit {len(files)} files")
            logger.info(f"[DRY RUN] Message: {commit_message}")
            logger.info(f"[DRY RUN] Files: {files}")
            return True
        
        try:
            # Stage files
            for file_path in files:
                logger.info(f"Staging file: {file_path}")
                repo.index.add([file_path])
            
            # Commit
            logger.info(f"Committing changes: {commit_message}")
            repo.index.commit(commit_message)
            return True
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            return False
    
    def push_changes(self, repo: Repo, branch: str, dry_run: bool = False) -> bool:
        """
        Push changes to remote
        
        Args:
            repo: GitPython Repo object
            branch: Branch name to push
            dry_run: If True, only log the action without executing
            
        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would push branch: {branch}")
            return True
        
        try:
            logger.info(f"Pushing branch: {branch}")
            repo.git.push('origin', branch)
            return True
        except Exception as e:
            logger.error(f"Failed to push branch {branch}: {e}")
            return False
    
    def update_file(
        self,
        repo: Repo,
        file_path: str,
        content: str
    ) -> bool:
        """
        Update file content in repository
        
        Args:
            repo: GitPython Repo object
            file_path: Relative path to file in repository
            content: New file content
            
        Returns:
            True if successful
        """
        try:
            full_path = Path(repo.working_dir) / file_path
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Updated file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to update file {file_path}: {e}")
            return False
    
    def file_exists(self, repo: Repo, file_path: str) -> bool:
        """
        Check if file exists in repository
        
        Args:
            repo: GitPython Repo object
            file_path: Relative path to file
            
        Returns:
            True if file exists
        """
        full_path = Path(repo.working_dir) / file_path
        return full_path.exists()
    
    def read_file(self, repo: Repo, file_path: str) -> Optional[str]:
        """
        Read file content from repository
        
        Args:
            repo: GitPython Repo object
            file_path: Relative path to file
            
        Returns:
            File content or None if failed
        """
        try:
            full_path = Path(repo.working_dir) / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
    
    def get_changed_files(self, repo: Repo) -> List[str]:
        """
        Get list of changed files in repository
        
        Args:
            repo: GitPython Repo object
            
        Returns:
            List of changed file paths
        """
        try:
            # Get both staged and unstaged changes
            changed_files = [item.a_path for item in repo.index.diff(None)]
            changed_files.extend([item.a_path for item in repo.index.diff('HEAD')])
            return list(set(changed_files))  # Remove duplicates
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return []
    
    def cleanup(self):
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            try:
                logger.info(f"Cleaning up temporary directory: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_dir}: {e}")
        
        self.temp_dirs = []
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()


def commit_to_maintenance_repo(
    file_path: str,
    content: str,
    commit_message: str,
    dry_run: bool = False
) -> bool:
    """
    Commit changes directly to maintenance repository (current repo)
    
    Args:
        file_path: Relative path to file
        content: File content
        commit_message: Commit message
        dry_run: If True, only log the action without executing
        
    Returns:
        True if successful
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would commit to maintenance repo: {file_path}")
        logger.info(f"[DRY RUN] Message: {commit_message}")
        return True
    
    try:
        # Get current repository
        repo = Repo('.')
        
        # Write file
        full_path = Path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Stage and commit
        repo.index.add([str(file_path)])
        repo.index.commit(commit_message)
        
        # Push to origin
        repo.git.push('origin', 'main')
        
        logger.info(f"Committed {file_path} to maintenance repo")
        return True
    except Exception as e:
        logger.error(f"Failed to commit to maintenance repo: {e}")
        return False

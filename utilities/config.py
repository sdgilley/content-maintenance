"""
Configuration utilities for content maintenance scripts.
Provides functions to read and access the central config.yml file.
"""

import yaml
import os


def load_config():
    """Load the configuration from config.yml file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yml")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found at {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing config.yml: {e}")


def get_repositories():
    """Get the list of repositories from config."""
    config = load_config()
    return config.get('repositories', {})


def get_repository_by_key(repo_key):
    """Get a specific repository configuration by its key."""
    repos = get_repositories()
    return repos.get(repo_key)


def get_repository_by_owner_repo(owner, repo_name):
    """Get a repository configuration by owner and repo name."""
    repos = get_repositories()
    for key, repo_config in repos.items():
        if repo_config['owner'] == owner and repo_config['repo'] == repo_name:
            return repo_config
    return None


def get_repositories_by_service(service_type):
    """Get repositories filtered by service type (ai, ml, etc.)."""
    repos = get_repositories()
    return {key: config for key, config in repos.items() 
            if config.get('service_type') == service_type}


def get_output_directory():
    """Get the output directory path."""
    config = load_config()
    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_dir, config.get('output_directory', 'outputs'))


def get_default_settings():
    """Get default settings from config."""
    config = load_config()
    return config.get('defaults', {})


def get_file_paths():
    """Get file path configurations."""
    config = load_config()
    return config.get('files', {})


def get_snippet_patterns():
    """Get the list of snippet patterns to search for."""
    defaults = get_default_settings()
    return defaults.get('snippet_patterns', [])

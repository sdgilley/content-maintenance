#!/usr/bin/env python3
"""Test script to verify the config system works correctly."""

from utilities import config

def test_config():
    print("Testing config system...")
    
    try:
        # Test loading repositories
        repos = config.get_repositories()
        print(f"✅ Loaded {len(repos)} repositories: {list(repos.keys())}")
        
        # Test getting a specific repository
        ml_repo = config.get_repository_by_key("azureml-examples")
        if ml_repo:
            print(f"✅ Found azureml-examples: {ml_repo['owner']}/{ml_repo['repo']}")
        
        # Test getting repositories by service
        ai_repos = config.get_repositories_by_service("ai")
        print(f"✅ Found {len(ai_repos)} AI repositories: {list(ai_repos.keys())}")
        
        # Test file paths
        file_paths = config.get_file_paths()
        print(f"✅ File paths configured: {list(file_paths.keys())}")
        
        # Test output directory
        output_dir = config.get_output_directory()
        print(f"✅ Output directory: {output_dir}")
        
        print("\n🎉 All config tests passed!")
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_config()

#!/usr/bin/env python3
"""Test the exclude directory logic"""

def test_exclude_logic():
    """Test the new exclude directory logic"""
    
    # Simulate the logic from helpers.py
    def should_exclude_path(content_path, content_name, exclude_dirs):
        for exclude_pattern in exclude_dirs:
            exclude_pattern = exclude_pattern.lower().strip('/')
            content_path_lower = content_path.lower()
            content_name_lower = content_name.lower()
            
            if (exclude_pattern == content_name_lower or 
                exclude_pattern in content_path_lower or
                content_path_lower.endswith(exclude_pattern)):
                return True
        return False
    
    # Test cases
    exclude_dirs = ["media", "ai-foundry/openai"]
    
    test_cases = [
        # (path, name, should_be_excluded)
        ("articles/ai-foundry/openai", "openai", True),
        ("articles/ai-foundry/openai/subfolder", "subfolder", True),
        ("articles/ai-foundry/tutorials", "tutorials", False),
        ("articles/machine-learning/media", "media", True),
        ("articles/ai-foundry/includes", "includes", False),
        ("articles/ai-foundry", "ai-foundry", False),
    ]
    
    print("Testing exclude directory logic:")
    print(f"Exclude patterns: {exclude_dirs}")
    print()
    
    for path, name, expected in test_cases:
        result = should_exclude_path(path, name, exclude_dirs)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} Path: {path}, Name: {name} -> Excluded: {result} (Expected: {expected})")
    
if __name__ == "__main__":
    test_exclude_logic()

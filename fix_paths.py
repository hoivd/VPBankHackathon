#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to replace absolute paths with relative paths for EC2 deployment
"""

import os
import re
import glob

def get_project_root():
    """Get the project root directory"""
    return os.path.dirname(os.path.abspath(__file__))

def fix_paths_in_file(file_path):
    """Replace absolute paths with relative paths in a single file"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace D:/VPBankHackathon with relative paths
    content = re.sub(
        r"'",
        "'",
        content
    )
    
    # Replace D:/3rd/VP_Bank_Hack/VPBankHackathon with relative paths
    content = re.sub(
        r"'",
        "'",
        content
    )
    
    # Replace D:/VPBankHackathon (without trailing slash)
    content = re.sub(
        r"'.'",
        "'.'",
        content
    )
    
    # Replace D:/3rd/VP_Bank_Hack/VPBankHackathon (without trailing slash)
    content = re.sub(
        r"'.'",
        "'.'",
        content
    )
    
    # Only write if content changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated: {file_path}")
        return True
    else:
        print(f"⏭️  No changes needed: {file_path}")
        return False

def main():
    """Main function to process all Python files"""
    
    # Get all Python files in the project
    python_files = []
    
    # Common directories to search
    directories = [
        '.',
        'blacklist_builder',
        'blacklist_builder/builder',
        'blacklist_builder/faiss_handler',
        'dynamodb',
        'embedder',
        'faiss_manager',
        'llm_model',
        'matching',
        'mongodb',
        'agents',
        'agents/tools',
        'S3',
        'service'
    ]
    
    for directory in directories:
        if os.path.exists(directory):
            pattern = os.path.join(directory, '**/*.py')
            python_files.extend(glob.glob(pattern, recursive=True))
    
    # Remove duplicates
    python_files = list(set(python_files))
    
    print(f"Found {len(python_files)} Python files to process")
    
    updated_count = 0
    
    for file_path in python_files:
        try:
            if fix_paths_in_file(file_path):
                updated_count += 1
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n🎉 Completed! Updated {updated_count} files out of {len(python_files)} total files.")
    print("\n📝 Summary of changes:")
    print("   - Replaced '' with '' (relative to project root)")
    print("   - Replaced '' with '' (relative to project root)")
    print("   - All paths are now relative and EC2 deployment ready!")

if __name__ == "__main__":
    main() 
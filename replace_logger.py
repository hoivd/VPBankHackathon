#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to replace custom logger setup with Python's built-in logging
"""

import os
import re
import glob

def replace_logger_in_file(file_path):
    """Replace custom logger setup with built-in logging in a single file"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace logger import
    content = re.sub(
        r'from logger import _setup_logger\s*\n',
        '',
        content
    )
    
    # Replace logger setup
    content = re.sub(
        r'logger = _setup_logger\(__name__, config\.LOG_LEVEL\)',
        'logger = logging.getLogger(__name__)',
        content
    )
    
    # Add logging import if not present
    if 'import logging' not in content:
        # Find the first import line and add logging import after it
        import_pattern = r'^import\s+\w+'
        match = re.search(import_pattern, content, re.MULTILINE)
        if match:
            content = content[:match.end()] + '\nimport logging' + content[match.end():]
        else:
            # If no import found, add at the beginning
            content = 'import logging\n' + content
    
    # Remove any existing logging.basicConfig calls
    content = re.sub(
        r'# Configure logging\s*\nlogging\.basicConfig\([^)]*\)\s*\n',
        '',
        content
    )
    
    # Remove any standalone logging.basicConfig calls
    content = re.sub(
        r'logging\.basicConfig\([^)]*\)\s*\n',
        '',
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
            if replace_logger_in_file(file_path):
                updated_count += 1
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n🎉 Completed! Updated {updated_count} files out of {len(python_files)} total files.")

if __name__ == "__main__":
    main() 
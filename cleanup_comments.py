#!/usr/bin/env python3
"""
Script to remove non-core comments from Python files in the agents folder
Preserves docstrings, function/class documentation, and critical inline comments
"""
import os
import re
from pathlib import Path

def is_core_comment(line, next_line=None, prev_line=None):
    """
    Determine if a comment line should be preserved
    """
    stripped = line.strip()
    
    # Always preserve shebang lines
    if stripped.startswith('#!'):
        return True
    
    # Always preserve encoding declarations
    if stripped.startswith('# -*- coding:') or stripped.startswith('# coding:'):
        return True
    
    # Preserve TODO, FIXME, NOTE, WARNING comments
    if any(keyword in stripped.upper() for keyword in ['TODO', 'FIXME', 'NOTE', 'WARNING', 'HACK', 'BUG']):
        return True
    
    # Preserve comments that explain complex logic (longer comments)
    if len(stripped) > 50 and not stripped.startswith('##'):
        return True
    
    # Preserve comments before function/class definitions
    if next_line and (next_line.strip().startswith('def ') or next_line.strip().startswith('class ')):
        return True
    
    # Preserve comments after imports explaining why
    if prev_line and 'import' in prev_line and len(stripped) > 10:
        return True
    
    # Remove simple comments like "# Setup", "# Main logic", etc.
    simple_patterns = [
        r'^#\s*[A-Z][a-z]*\s*$',  # Single word capitalized
        r'^#\s*[A-Z][a-z]*\s+[a-z]+\s*$',  # Two words
        r'^#\s*=+\s*$',  # Just equals signs
        r'^#\s*-+\s*$',  # Just dashes
        r'^#\s*\*+\s*$',  # Just asterisks
        r'^#\s*#+\s*$',  # Just hash signs
    ]
    
    for pattern in simple_patterns:
        if re.match(pattern, stripped):
            return False
    
    # Remove debug/development comments
    debug_patterns = [
        'print', 'debug', 'test', 'temp', 'temporary', 'remove this', 'delete this'
    ]
    if any(keyword in stripped.lower() for keyword in debug_patterns) and len(stripped) < 30:
        return False
    
    # Default: preserve if unsure
    return True

def clean_python_file(file_path):
    """Clean comments from a single Python file"""
    print(f"Processing: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    cleaned_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines or whitespace-only lines
        if not stripped:
            cleaned_lines.append(line)
            i += 1
            continue
        
        # Handle triple-quoted strings (docstrings) - always preserve
        if '"""' in line or "'''" in line:
            cleaned_lines.append(line)
            i += 1
            continue
        
        # Handle comment lines
        if stripped.startswith('#'):
            next_line = lines[i + 1] if i + 1 < len(lines) else None
            prev_line = lines[i - 1] if i > 0 else None
            
            if is_core_comment(line, next_line, prev_line):
                cleaned_lines.append(line)
            else:
                # Skip this comment line
                pass
        else:
            # Not a comment line - preserve
            cleaned_lines.append(line)
        
        i += 1
    
    # Write back the cleaned file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    
    print(f"Cleaned: {file_path}")

def clean_agents_folder():
    """Clean all Python files in the agents folder"""
    agents_path = Path('agents')
    
    if not agents_path.exists():
        print("Agents folder not found!")
        return
    
    # Find all Python files
    python_files = []
    
    for root, dirs, files in os.walk(agents_path):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files to clean:")
    for file in python_files:
        print(f"  - {file}")
    
    # Clean each file
    for file_path in python_files:
        try:
            clean_python_file(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nCompleted cleaning {len(python_files)} files!")

if __name__ == "__main__":
    clean_agents_folder() 
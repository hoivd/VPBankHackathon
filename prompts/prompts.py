#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompts module - Contains all prompt templates as Python variables
All variables are in UPPERCASE for consistency
"""

import os

def load_prompt_file(filename):
    """Load content from a prompt file"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Warning: Could not find prompt file: {filename}")
        return ""

# Load all prompt files
RERANK_PERSONAL = load_prompt_file('rerank_personal.txt')
PROMPT_EXTRACTOR = load_prompt_file('prompt_extractor.txt')
PROMPT_COMPARE_NEW_OLD_ORGANIZATION = load_prompt_file('prompt_compare_new_old_organization.txt')
PROMPT_COMPARE_NEW_OLD_PERSONAL_RISK_INFO = load_prompt_file('prompt_compare_new_old_personal_risk_info.txt')
PROMPT_COMPARE_QUERY_PERSONAL = load_prompt_file('prompt_compare_query_personal.txt')
PROMPT_COMPARE_QUERY_ORG = load_prompt_file('prompt_compare_query_org.txt')
PROMPT_COMPARE_INFO = load_prompt_file('promt_compare_info.txt')
PROMPT_COMPARE_OLD_NEM_ARTICLE = load_prompt_file('PromptCompareOldNemArticle.txt')
PROMPT_NEW_FOR_EXTRACTOR = load_prompt_file('PromptNewForExtractor.txt')
TEXT = load_prompt_file('Text.txt')

# Dictionary mapping for easy access
PROMPTS = {
    'RERANK_PERSONAL': RERANK_PERSONAL,
    'PROMPT_EXTRACTOR': PROMPT_EXTRACTOR,
    'PROMPT_COMPARE_NEW_OLD_ORGANIZATION': PROMPT_COMPARE_NEW_OLD_ORGANIZATION,
    'PROMPT_COMPARE_NEW_OLD_PERSONAL_RISK_INFO': PROMPT_COMPARE_NEW_OLD_PERSONAL_RISK_INFO,
    'PROMPT_COMPARE_QUERY_PERSONAL': PROMPT_COMPARE_QUERY_PERSONAL,
    'PROMPT_COMPARE_QUERY_ORG': PROMPT_COMPARE_QUERY_ORG,
    'PROMPT_COMPARE_INFO': PROMPT_COMPARE_INFO,
    'PROMPT_COMPARE_OLD_NEM_ARTICLE': PROMPT_COMPARE_OLD_NEM_ARTICLE,
    'PROMPT_NEW_FOR_EXTRACTOR': PROMPT_NEW_FOR_EXTRACTOR,
    'TEXT': TEXT,
}

# Export all variables
__all__ = [
    'RERANK_PERSONAL',
    'PROMPT_EXTRACTOR', 
    'PROMPT_COMPARE_NEW_OLD_ORGANIZATION',
    'PROMPT_COMPARE_NEW_OLD_PERSONAL_RISK_INFO',
    'PROMPT_COMPARE_QUERY_PERSONAL',
    'PROMPT_COMPARE_QUERY_ORG',
    'PROMPT_COMPARE_INFO',
    'PROMPT_COMPARE_OLD_NEM_ARTICLE',
    'PROMPT_NEW_FOR_EXTRACTOR',
    'TEXT',
    'PROMPTS'
] 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for handling paths in a cross-platform way
"""

import os

def get_project_root():
    """Get the project root directory"""
    return os.path.dirname(os.path.abspath(__file__))

def get_data_path(relative_path):
    """Get path to data directory"""
    return os.path.join(get_project_root(), 'data', relative_path)

def get_prompts_path(relative_path):
    """Get path to prompts directory"""
    return os.path.join(get_project_root(), 'prompts', relative_path)

def get_faiss_index_path(index_name):
    """Get path to FAISS index directory"""
    return os.path.join(get_project_root(), 'data', 'faiss_indexs', index_name)

def get_config_path(relative_path):
    """Get path to config directory"""
    return os.path.join(get_project_root(), relative_path)

# Common path constants
FAISS_PERSONAL_INDEX = get_faiss_index_path('personal_faiss_index')
FAISS_ORG_INDEX = get_faiss_index_path('org_faiss_index')
PROMPT_EXTRACTOR = get_prompts_path('prompt_extractor.txt')
PROMPT_PERSONAL_COMPARE = get_prompts_path('prompt_compare_new_old_personal_risk_info.txt')
PROMPT_ORGANIZATION_COMPARE = get_prompts_path('prompt_compare_new_old_organization.txt')
PROMPT_RERANK_PERSONAL = get_prompts_path('rerank_personal.txt') 
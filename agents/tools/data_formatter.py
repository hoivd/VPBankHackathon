#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to format lookup result data according to expected format
Processes personal and organizational risk data from DynamoDB lookup results
"""
import json
import ast
from collections import Counter, defaultdict
from typing import Dict, List, Any

def load_lookup_data(file_path: str) -> Dict:
    """Load and parse the lookup result data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # The file contains Python dict format, need to convert to proper JSON
            data = ast.literal_eval(content)
            return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}

def get_most_frequent_violation_type(entries: List[Dict]) -> str:
    """Get the most frequently mentioned violation type"""
    violation_counts = Counter()
    
    for entry in entries:
        violation_type = entry.get('violation_type', '')
        if violation_type:
            # Split combined violation types
            violations = violation_type.split('/')
            for v in violations:
                v_clean = v.strip()
                if v_clean:
                    violation_counts[v_clean] += 1
    
    if violation_counts:
        return violation_counts.most_common(1)[0][0]
    return "Không có hành vi phạm được đề cập"

def get_most_frequent_customer_role(entries: List[Dict]) -> str:
    """Get the most frequently mentioned customer role"""
    role_counts = Counter()
    
    for entry in entries:
        customer_role = entry.get('customer_role', '')
        if customer_role:
            role_counts[customer_role] += 1
    
    if role_counts:
        return role_counts.most_common(1)[0][0]
    return "Không có liên quan rõ ràng trong bài báo"

def get_highest_legal_status(entries: List[Dict]) -> str:
    """Get the highest priority legal status based on severity"""
    # Priority order: Đã kết án > Đang trong quá trình điều tra > Others
    status_priority = {
        "Đã kết án": 1,
        "Đang trong quá trình điều tra": 2,
        "Đang trong quá trình điều tra / truy tố / chưa có phán quyết": 2,
        "Tin chưa rõ ràng": 3,
        "Được minh oan": 4
    }
    
    statuses = [entry.get('legal_status', '') for entry in entries]
    
    # If any entry has "Đã kết án", return that
    for status in statuses:
        if status == "Đã kết án":
            return status
    
    # Otherwise, find the highest priority status
    valid_statuses = [s for s in statuses if s in status_priority]
    if valid_statuses:
        return min(valid_statuses, key=lambda x: status_priority[x])
    
    return "Tin chưa rõ ràng"

def group_violations_by_media(entries: List[Dict]) -> Dict[str, Dict]:
    """Group violations by media_id and summarize"""
    media_groups = defaultdict(list)
    
    for entry in entries:
        media_id = entry.get('media_id', '')
        if media_id:
            media_groups[media_id].append(entry)
    
    violation_summary = {}
    
    for media_id, media_entries in media_groups.items():
        # Get most frequent violation type for this media
        violation_type = get_most_frequent_violation_type(media_entries)
        legal_status = get_highest_legal_status(media_entries)
        
        if violation_type not in violation_summary:
            violation_summary[violation_type] = {
                'legal_status': legal_status,
                'media_ids': []
            }
        
        violation_summary[violation_type]['media_ids'].append(media_id)
        
        # Update legal status if current is higher priority
        current_priority = {"Đã kết án": 1, "Đang trong quá trình điều tra": 2}.get(violation_summary[violation_type]['legal_status'], 3)
        new_priority = {"Đã kết án": 1, "Đang trong quá trình điều tra": 2}.get(legal_status, 3)
        
        if new_priority < current_priority:
            violation_summary[violation_type]['legal_status'] = legal_status
    
    return violation_summary

def create_personal_crime_summary(person_info: Dict, personal2media_info: List[Dict]) -> Dict:
    """Create personal crime summary - only for main person"""
    main_person_name = person_info.get('full_name', '')
    
    # Get entries for the main person only
    main_person_entries = [
        entry for entry in personal2media_info 
    ]
    
    crime_summary = {}
    
    if main_person_entries:
        violation_summary = group_violations_by_media(main_person_entries)
        crime_summary[main_person_name] = violation_summary
    
    return crime_summary

def create_organizational_crime_summary(org2media_info: List[Dict]) -> Dict:
    """Create organizational crime summary"""
    # Group by organization_name
    org_groups = defaultdict(list)
    
    for entry in org2media_info:
        org_name = entry.get('organization_name', '')
        if org_name:
            org_groups[org_name].append(entry)
    
    crime_summary = {}
    
    for org_name, org_entries in org_groups.items():
        violation_summary = group_violations_by_media(org_entries)
        crime_summary[org_name] = violation_summary
    
    return crime_summary

def create_personal_risks(person_info: Dict, personal2media_info: List[Dict]) -> List[Dict]:
    """Create list_personal_risks according to format - only for main person"""
    personal_risks = []
    
    # Get only the main person's name from person_info
    main_person_name = person_info.get('full_name', '')
    
    # Get entries for the main person only
    main_person_entries = [
        entry for entry in personal2media_info 
    ]
    
    if main_person_entries:
        violation_type = get_most_frequent_violation_type(main_person_entries)
        customer_role = get_most_frequent_customer_role(main_person_entries)
        legal_status = get_highest_legal_status(main_person_entries)
        
        personal_risk = {
            "per_id": person_info.get('per_id', ''),
            "per_name": person_info.get('full_name', ''),
            "is_individual": True,
            "violation_type": violation_type,
            "customer_role": customer_role,
            "legal_status": legal_status
        }
        
        personal_risks.append(personal_risk)
    
    return personal_risks

def create_organizer_risks(org2media_info: List[Dict]) -> List[Dict]:
    """Create list_organizer_risks according to format"""
    organizer_risks = []
    
    # Group by organization
    org_groups = defaultdict(list)
    
    for entry in org2media_info:
        org_id = entry.get('org_id', '')
        org_name = entry.get('organization_name', '')
        if org_id and org_name:
            org_groups[org_id].append(entry)
    
    for org_id, org_entries in org_groups.items():
        if org_entries:
            violation_type = get_most_frequent_violation_type(org_entries)
            customer_role = get_most_frequent_customer_role(org_entries)
            legal_status = get_highest_legal_status(org_entries)
            
            organizer_risk = {
                "org_id": org_id,
                "org_name": org_entries[0].get('organization_name', ''),
                "is_individual": False,
                "violation_type": violation_type,
                "customer_role": customer_role,
                "legal_status": legal_status
            }
            
            organizer_risks.append(organizer_risk)
    
    return organizer_risks

def format_lookup_result(input_file: str, output_file: str):
    """Main function to format lookup result according to expected format"""
    
    # Load data
    data = load_lookup_data(input_file)
    
    if not data:
        print("No data to process")
        return
    
    person_info = data.get('person_info', {})
    personal2media_info = data.get('personal2media_info', [])
    org2media_info = data.get('org2media_info', [])
    
    # Create crime summaries
    personal_crime_summary = create_personal_crime_summary(person_info, personal2media_info)
    organizational_crime_summary = create_organizational_crime_summary(org2media_info)
    
    # Create risk lists
    list_personal_risks = create_personal_risks(person_info, personal2media_info)
    list_organizer_risks = create_organizer_risks(org2media_info)
    
    # Create final formatted result
    formatted_result = {
        "invidual_AML": {
            "summarize": personal_crime_summary
        },
        "organization_AML": organizational_crime_summary,
        "personal_risk_analysis": list_personal_risks,
        "organizer_risk_analysis": list_organizer_risks
    }
    
    # Save to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(formatted_result, f, ensure_ascii=False, indent=2)
    
    print(f"Formatted result saved to {output_file}")
    print(f"Found {len(list_personal_risks)} personal risks")
    print(f"Found {len(list_organizer_risks)} organizer risks")
    
    return formatted_result

if __name__ == "__main__":
    # Process the lookup result
    input_file = "lookup_result.json"
    output_file = "formatted_result.json"
    
    result = format_lookup_result(input_file, output_file)
    
    # Print summary
    if result:
        print("\n=== SUMMARY ===")
        print(f"Personal crimes: {len(result.get('invidual_AML', {}).get('summarize', {}))}")
        print(f"Organizational crimes: {len(result.get('organization_AML', {}))}")
        print(f"Personal risks: {len(result.get('personal_risk_analysis', []))}")
        print(f"Organizer risks: {len(result.get('organizer_risk_analysis', []))}") 
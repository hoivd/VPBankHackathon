#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the new lookup_person_comprehensive_v2 function
"""
import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agents.tools.person_lookup_dynamodb import PersonLookupDynamoDB
except ImportError:
    from tools.person_lookup_dynamodb import PersonLookupDynamoDB

def test_lookup_v2():
    """Test the new formatted lookup function"""
    
    # Initialize the lookup service
    lookup = PersonLookupDynamoDB()
    
    # Test with Trương Mỹ Lan
    person_name = "Trương Mỹ Lan"
    
    print(f"🚀 Testing lookup_person_comprehensive_v2 for: {person_name}")
    print("=" * 60)
    
    # Call the new v2 function
    result = lookup.lookup_person_comprehensive_v2(person_name)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        if "suggestions" in result:
            print("💡 Suggestions:")
            for suggestion in result["suggestions"]:
                print(f"  - {suggestion}")
        return
    
    # Save the result to a JSON file
    output_file = "formatted_lookup_result_v4.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Result saved to: {output_file}")
    
    # Print summary
    print("\n📊 SUMMARY:")
    print("-" * 40)
    
    individual_aml = result.get('individual_AML', {}).get('summarize', {})
    organization_aml = result.get('organization_AML', {})
    personal_risks = result.get('personal_risk_analysis', [])
    organizer_risks = result.get('organizer_risk_analysis', [])
    
    print(f"👤 Individual AML entries: {len(individual_aml)}")
    print(f"🏢 Organization AML entries: {len(organization_aml)}")
    print(f"⚠️  Personal risks: {len(personal_risks)}")
    print(f"🏛️  Organizer risks: {len(organizer_risks)}")
    
    # Show individual crimes breakdown
    if individual_aml:
        print(f"\n🔍 Individual crimes for {person_name}:")
        for person, crimes in individual_aml.items():
            for crime_type, details in crimes.items():
                print(f"  - {crime_type}: {details['legal_status']} ({len(details['media_ids'])} media)")
    
    # Show personal risk details
    if personal_risks:
        print(f"\n⚠️  Personal risk analysis:")
        for risk in personal_risks:
            print(f"    Violation: {risk['violation_type']}")
            print(f"    Role: {risk['customer_role']}")
            print(f"    Status: {risk['legal_status']}")
    
    # Show organization details
    if organization_aml:
        print(f"\n🏢 Organization crimes:")
        for org_name, crimes in organization_aml.items():
            print(f"  - {org_name}:")
            for crime_type, details in crimes.items():
                print(f"    • {crime_type}: {details['legal_status']} ({len(details['media_ids'])} media)")
    
    print(f"\n✅ Test completed successfully!")
    print(f"📄 Full result available in: {output_file}")

if __name__ == "__main__":
    test_lookup_v2() 
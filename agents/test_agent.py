#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Person Risk Agent
Demonstrates the agent with the example query: "cho tôi thông tin về Trương Mỹ Lan"
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.person_risk_agent import PersonRiskAgent

def test_agent():
    """Test the agent with the example query"""
    print("🚀 TESTING PERSON RISK AGENT")
    print("=" * 80)
    
    try:
        # Initialize the agent
        print("🔧 Initializing agent...")
        agent = PersonRiskAgent()
        
        # Test query from user requirement
        test_query = "cho tôi thông tin về Trương Mỹ Lan"
        print(f"\n📝 Test Query: {test_query}")
        print("-" * 80)
        
        # Process the query
        response = agent.process_query(test_query)
        
        # Display the response
        print("\n🤖 AGENT RESPONSE:")
        print("=" * 80)
        print(response)
        print("=" * 80)
        
        # Also save detailed JSON result
        print("\n💾 Saving detailed analysis to JSON...")
        person_name = agent.extract_person_name_from_query(test_query)
        if person_name:
            lookup_result = agent.person_lookup.lookup_person_comprehensive(person_name)
            risk_analysis = agent.risk_analyzer.analyze_person_lookup_result(lookup_result)
            
            import json
            with open('test_analysis_result.json', 'w', encoding='utf-8') as f:
                json.dump(risk_analysis, f, ensure_ascii=False, indent=2, default=str)
            print("✅ Detailed analysis saved to test_analysis_result.json")
        
        print("\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")

if __name__ == "__main__":
    test_agent() 
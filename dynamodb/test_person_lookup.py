#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for person lookup functionality
Demonstrates how to use the PersonLookup class with sample names
"""
import os
import sys
import json
import dotenv
dotenv.load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from person_lookup import PersonLookup

def test_person_lookup():
    """Test the person lookup functionality"""
    
    # Get MongoDB URI from environment
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MONGO_URI environment variable not set")
        return
    
    print("🚀 Testing Person Lookup Functionality")
    print("="*60)
    
    try:
        # Initialize lookup
        lookup = PersonLookup(mongo_uri, "vpbank_hackathon")
        
        # Test with sample names from the database
        test_names = [
            "Trương Mỹ Lan",           # Main person from the case
            "Võ Tấn Hoàng Văn",       # Person from sample data
            "Nguyễn Phương Thủy",     # Person mentioned in content
            "John Doe"                # Non-existent person to test error handling
        ]
        
        for name in test_names:
            print(f"\n{'='*60}")
            print(f"🔍 Testing lookup for: {name}")
            print(f"{'='*60}")
            
            # Perform lookup
            result = lookup.lookup_person_comprehensive(name)
            
            # Print result
            lookup.print_formatted_result(result)
            
            # Save individual results
            filename = f"lookup_result_{name.replace(' ', '_')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n📄 Result saved to: {filename}")
            
            print("\n" + "="*60)
            input("Press Enter to continue to next test...")
        
        # Close connection
        lookup.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")

def interactive_lookup():
    """Interactive mode for person lookup"""
    
    # Get MongoDB URI from environment
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MONGO_URI environment variable not set")
        return
    
    print("🔍 Interactive Person Lookup")
    print("="*40)
    
    try:
        # Initialize lookup
        lookup = PersonLookup(mongo_uri, "vpbank_hackathon")
        
        while True:
            print("\n" + "="*40)
            name = input("Enter person's full name (or 'quit' to exit): ").strip()
            
            if name.lower() in ['quit', 'exit', 'q']:
                break
            
            if not name:
                print("❌ Please enter a valid name")
                continue
            
            # Perform lookup
            result = lookup.lookup_person_comprehensive(name)
            
            # Print result
            lookup.print_formatted_result(result)
            
            # Ask if user wants to save result
            save = input("\nSave result to JSON file? (y/n): ").strip().lower()
            if save in ['y', 'yes']:
                filename = f"lookup_result_{name.replace(' ', '_')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                print(f"📄 Result saved to: {filename}")
        
        # Close connection
        lookup.close()
        
    except Exception as e:
        print(f"❌ Interactive lookup failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")

def quick_lookup(name: str):
    """Quick lookup for a specific person"""
    
    # Get MongoDB URI from environment
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MONGO_URI environment variable not set")
        return
    
    try:
        # Initialize lookup
        lookup = PersonLookup(mongo_uri, "vpbank_hackathon")
        
        # Perform lookup
        result = lookup.lookup_person_comprehensive(name)
        
        # Print result
        lookup.print_formatted_result(result)
        
        # Close connection
        lookup.close()
        
        return result
        
    except Exception as e:
        print(f"❌ Quick lookup failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test person lookup functionality')
    parser.add_argument('--mode', choices=['test', 'interactive', 'quick'], 
                       default='interactive', help='Test mode')
    parser.add_argument('--name', help='Person name for quick lookup')
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        test_person_lookup()
    elif args.mode == 'interactive':
        interactive_lookup()
    elif args.mode == 'quick':
        if args.name:
            quick_lookup(args.name)
        else:
            print("❌ --name is required for quick mode")
            print("Example: python test_person_lookup.py --mode quick --name 'Trương Mỹ Lan'") 
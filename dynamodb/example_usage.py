#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example usage of DynamoDB Explorer tools
Demonstrates both comprehensive explorer and quick connect functionality
Supports Vietnamese content with UTF-8 encoding
"""

import os
import sys
import dotenv

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
dotenv.load_dotenv()

from dynamo_explorer import DynamoDBExplorer
from quick_connect import QuickDynamoConnect
from utils import Utils

def demonstrate_comprehensive_explorer():
    """Demonstrate the comprehensive DynamoDB explorer"""
    print("="*60)
    print("🔍 COMPREHENSIVE EXPLORER DEMONSTRATION")
    print("="*60)
    
    try:
        # Load AWS credentials
        aws_access_key = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
        aws_secret_key = Utils.load_api_key_from_env("AWS_SECRET_KEY")
        
        # Create explorer
        explorer = DynamoDBExplorer(
            region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        print("✅ Connected to DynamoDB")
        
        # Save comprehensive report
        print("\n📄 Saving comprehensive report...")
        explorer.save_report("comprehensive_report.txt")
        
        # Print a brief summary to console
        print("\n📊 Brief summary:")
        tables = explorer.list_all_tables()
        for table in tables:
            schema = explorer.get_table_schema(table)
            print(f"  • {table}: {schema.get('item_count', 0):,} items, {schema.get('table_size_bytes', 0):,} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in comprehensive explorer: {e}")
        return False

def demonstrate_quick_connect():
    """Demonstrate the quick connect tool"""
    print("\n" + "="*60)
    print("⚡ QUICK CONNECT DEMONSTRATION")
    print("="*60)
    
    try:
        # Create quick connect instance
        db = QuickDynamoConnect()
        
        # List tables
        tables = db.list_tables()
        
        # Describe first table if available
        if tables:
            print(f"\n📋 Describing first table: {tables[0]}")
            db.describe_table(tables[0])
            
            # Get sample data
            print(f"\n📄 Sample data from {tables[0]}:")
            db.scan_table(tables[0], limit=2)
        
        # Save quick overview
        print("\n💾 Saving quick overview...")
        db.save_overview("quick_overview.txt")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in quick connect: {e}")
        return False

def main():
    """Main demonstration function"""
    print("🚀 DynamoDB Explorer Tools Demonstration")
    print("This script demonstrates both exploration tools")
    print("\nMake sure you have:")
    print("1. AWS credentials in environment variables or .env file")
    print("2. DynamoDB access permissions")
    print("3. Active DynamoDB tables in your region")
    
    input("\nPress Enter to continue...")
    
    # Demonstrate comprehensive explorer
    comprehensive_success = demonstrate_comprehensive_explorer()
    
    # Demonstrate quick connect
    quick_success = demonstrate_quick_connect()
    
    # Summary
    print("\n" + "="*60)
    print("📋 DEMONSTRATION SUMMARY")
    print("="*60)
    
    if comprehensive_success:
        print("✅ Comprehensive Explorer: SUCCESS")
        print("   📄 Report saved to: comprehensive_report.txt")
    else:
        print("❌ Comprehensive Explorer: FAILED")
    
    if quick_success:
        print("✅ Quick Connect: SUCCESS")
        print("   📄 Overview saved to: quick_overview.txt")
    else:
        print("❌ Quick Connect: FAILED")
    
    if comprehensive_success and quick_success:
        print("\n🎉 All demonstrations completed successfully!")
        print("\nGenerated files:")
        print("  • comprehensive_report.txt - Detailed database analysis")
        print("  • quick_overview.txt - Quick table overview")
    else:
        print("\n⚠️  Some demonstrations failed. Check your AWS credentials and permissions.")

if __name__ == "__main__":
    main() 
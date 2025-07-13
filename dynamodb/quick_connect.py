#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick DynamoDB Connection Script
Simple script to connect to DynamoDB and perform basic operations
Supports Vietnamese content with UTF-8 encoding
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError
import json
import dotenv
dotenv.load_dotenv()

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import Utils

class QuickDynamoConnect:
    def __init__(self):
        """Initialize connection to DynamoDB"""
        try:
            # Load credentials
            aws_access_key = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
            aws_secret_key = Utils.load_api_key_from_env("AWS_SECRET_KEY")
            
            aws_region = os.getenv("AWS_REGION", "ap-southeast-1")
            
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
            
            self.client = boto3.client(
                'dynamodb',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
            
            print(f"✅ Connected to DynamoDB in region: {aws_region}")
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            raise

    def list_tables(self):
        """List all tables"""
        try:
            response = self.client.list_tables()
            tables = response.get('TableNames', [])
            
            print(f"\n📊 Found {len(tables)} tables:")
            for i, table in enumerate(tables, 1):
                print(f"   {i}. {table}")
            
            return tables
        except ClientError as e:
            print(f"❌ Error listing tables: {e}")
            return []

    def describe_table(self, table_name):
        """Get basic table information"""
        try:
            response = self.client.describe_table(TableName=table_name)
            table = response['Table']
            
            print(f"\n📋 Table: {table_name}")
            print(f"   Status: {table['TableStatus']}")
            print(f"   Items: {table.get('ItemCount', 0):,}")
            print(f"   Size: {table.get('TableSizeBytes', 0):,} bytes")
            
            # Keys
            print(f"   Keys:")
            for key in table['KeySchema']:
                key_type = "Partition" if key['KeyType'] == 'HASH' else "Sort"
                print(f"     • {key_type} Key: {key['AttributeName']}")
            
            # Attributes
            print(f"   Attributes:")
            for attr in table['AttributeDefinitions']:
                print(f"     • {attr['AttributeName']} ({attr['AttributeType']})")
            
            return table
        except ClientError as e:
            print(f"❌ Error describing table {table_name}: {e}")
            return None

    def scan_table(self, table_name, limit=5):
        """Scan table for sample data"""
        try:
            table = self.dynamodb.Table(table_name)
            response = table.scan(Limit=limit)
            items = response.get('Items', [])
            
            print(f"\n📄 Sample data from {table_name} (limit {limit}):")
            if items:
                for i, item in enumerate(items, 1):
                    # Ensure UTF-8 encoding for Vietnamese content in JSON output
                    print(f"   Item {i}: {json.dumps(item, indent=4, default=str, ensure_ascii=False)}")
            else:
                print("   No items found")
            
            return items
        except ClientError as e:
            print(f"❌ Error scanning table {table_name}: {e}")
            return []

    def quick_overview(self):
        """Get quick overview of all tables"""
        tables = self.list_tables()
        
        print(f"\n{'='*60}")
        print("📊 QUICK OVERVIEW")
        print(f"{'='*60}")
        
        for table_name in tables:
            self.describe_table(table_name)
            print("-" * 40)
    
    def save_overview(self, file_path: str):
        """Save quick overview to file"""
        try:
            tables = self.list_tables()
            
            # Ensure UTF-8 encoding for Vietnamese content
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write("="*60 + "\n")
                f.write("📊 DYNAMODB QUICK OVERVIEW\n")
                f.write("="*60 + "\n\n")
                
                f.write(f"📊 Found {len(tables)} tables:\n")
                for i, table in enumerate(tables, 1):
                    f.write(f"   {i}. {table}\n")
                f.write("\n")
                
                # Get basic info for each table
                for table_name in tables:
                    try:
                        response = self.client.describe_table(TableName=table_name)
                        table = response['Table']
                        
                        f.write(f"{'='*40}\n")
                        f.write(f"📋 Table: {table_name}\n")
                        f.write(f"{'='*40}\n")
                        f.write(f"Status: {table['TableStatus']}\n")
                        f.write(f"Items: {table.get('ItemCount', 0):,}\n")
                        f.write(f"Size: {table.get('TableSizeBytes', 0):,} bytes\n")
                        
                        # Keys
                        f.write(f"Keys:\n")
                        for key in table['KeySchema']:
                            key_type = "Partition" if key['KeyType'] == 'HASH' else "Sort"
                            f.write(f"  • {key_type} Key: {key['AttributeName']}\n")
                        
                        # Attributes
                        f.write(f"Attributes:\n")
                        for attr in table['AttributeDefinitions']:
                            f.write(f"  • {attr['AttributeName']} ({attr['AttributeType']})\n")
                        
                        f.write("\n")
                        
                    except Exception as e:
                        f.write(f"❌ Error describing table {table_name}: {e}\n\n")
            
            print(f"✅ Quick overview saved to: {file_path}")
            print(f"🌐 Encoding: UTF-8 (supports Vietnamese content)")
            
        except Exception as e:
            print(f"❌ Error saving overview to {file_path}: {e}")

def main():
    """Main function"""
    try:
        # Connect to DynamoDB
        db = QuickDynamoConnect()
        
        # Get overview
        db.quick_overview()
        
        # Interactive mode
        print(f"\n{'='*60}")
        print("🔍 INTERACTIVE MODE")
        print(f"{'='*60}")
        print("Commands:")
        print("  'list' - List all tables")
        print("  'desc <table_name>' - Describe a table")
        print("  'scan <table_name>' - Scan table for sample data")
        print("  'save <filename>' - Save overview to file")
        print("  'quit' - Exit")
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if command.lower() == 'quit':
                    break
                elif command.lower() == 'list':
                    db.list_tables()
                elif command.startswith('desc '):
                    table_name = command[5:].strip()
                    db.describe_table(table_name)
                elif command.startswith('scan '):
                    table_name = command[5:].strip()
                    db.scan_table(table_name)
                elif command.startswith('save '):
                    filename = command[5:].strip()
                    if filename:
                        db.save_overview(filename)
                    else:
                        print("❌ Please provide a filename. Usage: save <filename>")
                else:
                    print("❌ Unknown command. Use 'list', 'desc <table>', 'scan <table>', 'save <file>', or 'quit'")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DynamoDB Database Explorer
Connects to DynamoDB and provides comprehensive information about:
- All tables
- Table schemas
- Relationships between tables
- Sample data
- Supports Vietnamese content with UTF-8 encoding
"""
import os
import sys
import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional
import dotenv
dotenv.load_dotenv()
import logging

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import Utils

logger = logging.getLogger(__name__)

class DynamoDBExplorer:
    def __init__(self, region_name: str = None, aws_access_key_id: str = None, aws_secret_access_key: str = None):
        """
        Initialize DynamoDB explorer
        
        Args:
            region_name: AWS region (default from config)
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-southeast-1")
        
        if aws_access_key_id and aws_secret_access_key:
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=self.region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            self.client = boto3.client(
                'dynamodb',
                region_name=self.region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        else:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
            self.client = boto3.client('dynamodb', region_name=self.region_name)

    def list_all_tables(self) -> List[str]:
        """List all DynamoDB tables"""
        try:
            response = self.client.list_tables()
            tables = response.get('TableNames', [])
            final_tables = tables.copy()
            logger.info(f"Found {len(tables)} tables")
            for table in tables: 
                if 'demo' in table:
                    final_tables.remove(table)
            return final_tables
        except ClientError as e:
            logger.error(f"Error listing tables: {e}")
            return []

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get detailed schema information for a table"""
        try:
            response = self.client.describe_table(TableName=table_name)
            table_info = response['Table']
            
            schema = {
                'table_name': table_name,
                'table_status': table_info.get('TableStatus'),
                'creation_date': str(table_info.get('CreationDateTime', '')),
                'item_count': table_info.get('ItemCount', 0),
                'table_size_bytes': table_info.get('TableSizeBytes', 0),
                'partition_key': None,
                'sort_key': None,
                'attributes': [],
                'global_secondary_indexes': [],
                'local_secondary_indexes': []
            }
            
            # Extract key schema
            for key_schema in table_info.get('KeySchema', []):
                key_name = key_schema['AttributeName']
                key_type = key_schema['KeyType']
                
                if key_type == 'HASH':
                    schema['partition_key'] = key_name
                elif key_type == 'RANGE':
                    schema['sort_key'] = key_name
            
            # Extract attribute definitions
            for attr in table_info.get('AttributeDefinitions', []):
                schema['attributes'].append({
                    'name': attr['AttributeName'],
                    'type': attr['AttributeType']
                })
            
            # Extract Global Secondary Indexes
            for gsi in table_info.get('GlobalSecondaryIndexes', []):
                gsi_info = {
                    'index_name': gsi['IndexName'],
                    'partition_key': None,
                    'sort_key': None,
                    'projection_type': gsi.get('Projection', {}).get('ProjectionType')
                }
                
                for key_schema in gsi.get('KeySchema', []):
                    key_name = key_schema['AttributeName']
                    key_type = key_schema['KeyType']
                    
                    if key_type == 'HASH':
                        gsi_info['partition_key'] = key_name
                    elif key_type == 'RANGE':
                        gsi_info['sort_key'] = key_name
                
                schema['global_secondary_indexes'].append(gsi_info)
            
            # Extract Local Secondary Indexes
            for lsi in table_info.get('LocalSecondaryIndexes', []):
                lsi_info = {
                    'index_name': lsi['IndexName'],
                    'sort_key': None,
                    'projection_type': lsi.get('Projection', {}).get('ProjectionType')
                }
                
                for key_schema in lsi.get('KeySchema', []):
                    if key_schema['KeyType'] == 'RANGE':
                        lsi_info['sort_key'] = key_schema['AttributeName']
                
                schema['local_secondary_indexes'].append(lsi_info)
            
            return schema
            
        except ClientError as e:
            logger.error(f"Error getting schema for table {table_name}: {e}")
            return {}

    def get_sample_data(self, table_name: str, limit: int = 3) -> List[Dict]:
        """Get sample data from a table"""
        try:
            table = self.dynamodb.Table(table_name)
            response = table.scan(Limit=limit)
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error getting sample data from {table_name}: {e}")
            return []
    
    def get_all_fields_from_sample_data(self, table_name: str, limit: int = 10) -> List[str]:
        """Get all field names from sample data to understand actual table structure"""
        try:
            sample_data = self.get_sample_data(table_name, limit)
            all_fields = set()
            
            for item in sample_data:
                all_fields.update(item.keys())
            
            return sorted(list(all_fields))
        except Exception as e:
            logger.error(f"Error getting fields from sample data for {table_name}: {e}")
            return []

    def analyze_relationships(self, all_schemas: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Analyze relationships between tables based on naming conventions, sample data, and common fields
        """
        relationships = {}
        table_names = [s['table_name'] for s in all_schemas]
        
        for schema in all_schemas:
            table_name = schema['table_name']
            relationships[table_name] = []
            
            # 1. Check schema attributes for foreign key relationships
            for attr in schema['attributes']:
                attr_name = attr['name']
                
                # Look for potential foreign keys ending with _id
                if attr_name.endswith('_id') and attr_name != schema['partition_key']:
                    # Try to find corresponding table
                    potential_table = attr_name.replace('_id', '')
                    if potential_table in table_names:
                        relationships[table_name].append(f"🔗 {attr_name} -> {potential_table}")
                
                # Look for unix_id patterns (common in your data)
                if attr_name.endswith('_unix_id'):
                    base_name = attr_name.replace('_unix_id', '')
                    potential_table = f"{base_name}_info"
                    if potential_table in table_names:
                        relationships[table_name].append(f"🔗 {attr_name} -> {potential_table}")
            
            # 2. Analyze sample data for additional relationships
            sample_data = self.get_sample_data(table_name, limit=5)
            if sample_data:
                for item in sample_data:
                    for field_name, field_value in item.items():
                        if isinstance(field_value, str):
                            # Look for foreign key patterns in sample data
                            if field_name.endswith('_id') and field_name != schema['partition_key']:
                                potential_table = field_name.replace('_id', '')
                                if potential_table in table_names:
                                    rel_desc = f"🔗 {field_name} -> {potential_table}"
                                    if rel_desc not in relationships[table_name]:
                                        relationships[table_name].append(rel_desc)
                            
                            # Look for unix_id patterns in sample data
                            if field_name.endswith('_unix_id'):
                                base_name = field_name.replace('_unix_id', '')
                                potential_table = f"{base_name}_info"
                                if potential_table in table_names:
                                    rel_desc = f"🔗 {field_name} -> {potential_table}"
                                    if rel_desc not in relationships[table_name]:
                                        relationships[table_name].append(rel_desc)
                                
                                # Also check for direct table name matches
                                if base_name in table_names:
                                    rel_desc = f"🔗 {field_name} -> {base_name}"
                                    if rel_desc not in relationships[table_name]:
                                        relationships[table_name].append(rel_desc)
            
            # 3. Check for linking tables (many-to-many relationships)
            if '2' in table_name:  # e.g., personal2media, org2media
                parts = table_name.split('2')
                if len(parts) == 2:
                    table1, table2 = parts
                    # Check if the referenced tables exist
                    table1_exists = any(t for t in table_names if table1 in t)
                    table2_exists = any(t for t in table_names if table2 in t)
                    
                    if table1_exists and table2_exists:
                        relationships[table_name].append(f"🔗 Junction table: Links {table1} ↔ {table2}")
                    
                    # Find exact table matches
                    for other_table in table_names:
                        if table1 in other_table and other_table != table_name:
                            relationships[table_name].append(f"🔗 References {other_table}")
                        if table2 in other_table and other_table != table_name:
                            relationships[table_name].append(f"🔗 References {other_table}")
            
            # 4. Common field analysis - check for shared field names
            for other_schema in all_schemas:
                if other_schema['table_name'] != table_name:
                    # Check for shared partition keys or common fields
                    if schema['partition_key'] in [attr['name'] for attr in other_schema['attributes']]:
                        relationships[table_name].append(f"🔗 Shares key '{schema['partition_key']}' with {other_schema['table_name']}")
            
            # 5. Based on your specific schema patterns
            if table_name == 'personal_info':
                if 'personal2media' in table_names:
                    relationships[table_name].append("🔗 Links to adverse_media via personal2media")
            elif table_name == 'organization_info':
                if 'org2media' in table_names:
                    relationships[table_name].append("🔗 Links to adverse_media via org2media")
            elif table_name == 'adverse_media':
                if 'personal2media' in table_names:
                    relationships[table_name].append("🔗 Links to personal_info via personal2media")
                if 'org2media' in table_names:
                    relationships[table_name].append("🔗 Links to organization_info via org2media")
        
        return relationships

    def _generate_report_content(self) -> str:
        """Generate the comprehensive report content as a string"""
        report_lines = []
        
        report_lines.append("=" * 80)
        report_lines.append("🔍 DYNAMODB DATABASE EXPLORER REPORT")
        report_lines.append("=" * 80)
        
        # Get all tables
        tables = self.list_all_tables()
        if not tables:
            report_lines.append("❌ No tables found or unable to connect to DynamoDB")
            return "\n".join(report_lines)
        
        report_lines.append(f"\n📊 OVERVIEW:")
        report_lines.append(f"   • Region: {self.region_name}")
        report_lines.append(f"   • Total Tables: {len(tables)}")
        report_lines.append(f"   • Tables: {', '.join(tables)}")
        
        # Get schemas for all tables
        all_schemas = []
        for table_name in tables:
            schema = self.get_table_schema(table_name)
            if schema:
                all_schemas.append(schema)
        
        # Analyze relationships
        relationships = self.analyze_relationships(all_schemas)
        
        # Generate detailed information for each table
        for i, schema in enumerate(all_schemas, 1):
            report_lines.append(f"\n{'='*60}")
            report_lines.append(f"📋 TABLE {i}: {schema['table_name'].upper()}")
            report_lines.append(f"{'='*60}")
            
            report_lines.append(f"Status: {schema['table_status']}")
            report_lines.append(f"Items: {schema['item_count']:,}")
            report_lines.append(f"Size: {schema['table_size_bytes']:,} bytes")
            report_lines.append(f"Created: {schema['creation_date']}")
            
            report_lines.append(f"\n🔑 KEY SCHEMA:")
            report_lines.append(f"   • Partition Key: {schema['partition_key']}")
            if schema['sort_key']:
                report_lines.append(f"   • Sort Key: {schema['sort_key']}")
            
            report_lines.append(f"\n📝 SCHEMA ATTRIBUTES:")
            for attr in schema['attributes']:
                report_lines.append(f"   • {attr['name']} ({attr['type']}) - Key attribute")
            
            # Show actual fields from sample data
            actual_fields = self.get_all_fields_from_sample_data(schema['table_name'])
            if actual_fields:
                report_lines.append(f"\n📋 ACTUAL FIELDS (from sample data):")
                for field in actual_fields:
                    is_key = field in [attr['name'] for attr in schema['attributes']]
                    key_indicator = " 🔑" if is_key else ""
                    report_lines.append(f"   • {field}{key_indicator}")
            else:
                report_lines.append(f"\n📋 ACTUAL FIELDS: No sample data available")
            
            # Global Secondary Indexes
            if schema['global_secondary_indexes']:
                report_lines.append(f"\n🌐 GLOBAL SECONDARY INDEXES:")
                for gsi in schema['global_secondary_indexes']:
                    report_lines.append(f"   • {gsi['index_name']}")
                    report_lines.append(f"     - Partition Key: {gsi['partition_key']}")
                    if gsi['sort_key']:
                        report_lines.append(f"     - Sort Key: {gsi['sort_key']}")
                    report_lines.append(f"     - Projection: {gsi['projection_type']}")
            
            # Local Secondary Indexes
            if schema['local_secondary_indexes']:
                report_lines.append(f"\n🏠 LOCAL SECONDARY INDEXES:")
                for lsi in schema['local_secondary_indexes']:
                    report_lines.append(f"   • {lsi['index_name']}")
                    report_lines.append(f"     - Sort Key: {lsi['sort_key']}")
                    report_lines.append(f"     - Projection: {lsi['projection_type']}")
            
            # Relationships
            if relationships.get(schema['table_name']):
                report_lines.append(f"\n🔗 RELATIONSHIPS:")
                for rel in relationships[schema['table_name']]:
                    report_lines.append(f"   • {rel}")
            
            # Sample data
            report_lines.append(f"\n📄 SAMPLE DATA:")
            sample_data = self.get_sample_data(schema['table_name'])
            if sample_data:
                for j, item in enumerate(sample_data, 1):
                    # Ensure UTF-8 encoding for Vietnamese content in JSON
                    report_lines.append(f"   Sample {j}: {json.dumps(item, indent=6, default=str, ensure_ascii=False)}")
            else:
                report_lines.append("   No data available")
        
        # Generate relationship summary
        report_lines.append(f"\n{'='*60}")
        report_lines.append("🔗 RELATIONSHIP SUMMARY")
        report_lines.append(f"{'='*60}")
        
        has_relationships = False
        for table_name, rels in relationships.items():
            if rels:
                has_relationships = True
                report_lines.append(f"\n📋 {table_name}:")
                for rel in rels:
                    report_lines.append(f"   • {rel}")
        
        if not has_relationships:
            report_lines.append(f"\n⚠️  No relationships detected.")
            report_lines.append(f"   This could mean:")
            report_lines.append(f"   • Tables are independent")
            report_lines.append(f"   • Foreign keys use different naming conventions")
            report_lines.append(f"   • Sample data doesn't contain relationship fields")
            report_lines.append(f"   • Tables are empty")
        
        # Add debugging information
        report_lines.append(f"\n{'='*60}")
        report_lines.append("🔍 RELATIONSHIP ANALYSIS DEBUG")
        report_lines.append(f"{'='*60}")
        
        for schema in all_schemas:
            table_name = schema['table_name']
            report_lines.append(f"\n📋 {table_name}:")
            report_lines.append(f"   • Partition Key: {schema['partition_key']}")
            if schema['sort_key']:
                report_lines.append(f"   • Sort Key: {schema['sort_key']}")
            
            # Show actual fields for relationship analysis
            actual_fields = self.get_all_fields_from_sample_data(table_name)
            foreign_key_candidates = [f for f in actual_fields if f.endswith('_id') or f.endswith('_unix_id')]
            
            if foreign_key_candidates:
                report_lines.append(f"   • Potential foreign keys: {', '.join(foreign_key_candidates)}")
            else:
                report_lines.append(f"   • No foreign key patterns found")
        
        return "\n".join(report_lines)

    def save_report(self, file_path: str):
        """Save a comprehensive report of the database structure to a file"""
        try:
            report_content = self._generate_report_content()
            
            # Ensure UTF-8 encoding for Vietnamese content
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(report_content)
            
            print(f"✅ Report saved to: {file_path}")
            print(f"📄 Report contains {len(report_content.split(chr(10)))} lines")
            print(f"🌐 Encoding: UTF-8 (supports Vietnamese content)")
            
        except Exception as e:
            print(f"❌ Error saving report to {file_path}: {e}")
            logger.error(f"Error saving report: {e}")

    def print_comprehensive_report(self):
        """Print a comprehensive report of the database structure to console"""
        report_content = self._generate_report_content()
        print(report_content)

    def get_table_dependencies(self) -> Dict[str, List[str]]:
        """Get table dependencies for proper deletion order"""
        dependencies = {
            'personal_info': ['personal2media'],  # personal_info should be deleted after personal2media
            'organization_info': ['org2media'],
            'adverse_media': ['personal2media', 'org2media'],
            'personal2media': [],
            'org2media': [],
            'blacklist': []
        }
        return dependencies

def main():
    """Main function to run the explorer"""
    try:
        # Load AWS credentials from environment
        aws_access_key = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
        aws_secret_key = Utils.load_api_key_from_env("AWS_SECRET_KEY")
        
        # Create explorer instance
        explorer = DynamoDBExplorer(
            region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Check command line arguments
        import sys
        if len(sys.argv) > 1:
            if sys.argv[1] == "--print":
                # Print to console
                explorer.print_comprehensive_report()
            elif sys.argv[1] == "--save":
                # Save to file (default or specified path)
                file_path = sys.argv[2] if len(sys.argv) > 2 else "dynamodb_report.txt"
                explorer.save_report(file_path)
            elif sys.argv[1] == "--both":
                # Both print and save
                file_path = sys.argv[2] if len(sys.argv) > 2 else "dynamodb_report.txt"
                explorer.print_comprehensive_report()
                print(f"\n{'='*60}")
                print("💾 SAVING REPORT TO FILE...")
                print(f"{'='*60}")
                explorer.save_report(file_path)
            else:
                print("Usage:")
                print("  python dynamo_explorer.py --print         # Print to console")
                print("  python dynamo_explorer.py --save [file]   # Save to file")
                print("  python dynamo_explorer.py --both [file]   # Print and save")
                print("  python dynamo_explorer.py                 # Default: save to dynamodb_report.txt")
        else:
            # Default behavior: save to file
            explorer.save_report("dynamodb_report_final.txt")
        
    except Exception as e:
        logging.error(f"Error running DynamoDB explorer: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 
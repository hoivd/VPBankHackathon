#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DynamoDB to MongoDB Migration Script
Migrates all data from DynamoDB tables to MongoDB collections
Supports Vietnamese content with UTF-8 encoding
Enhanced with robust error handling and connection validation
"""
import os
import sys
import boto3
import json
from botocore.exceptions import ClientError
from pymongo import MongoClient
from pymongo.errors import PyMongoError, BulkWriteError
from typing import Dict, List, Any, Optional, Tuple
import dotenv
dotenv.load_dotenv()
import logging
from datetime import datetime
import time
import traceback

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import Utils

logger = logging.getLogger(__name__)

class DynamoToMongoMigrator:
    def __init__(self, 
                 mongo_uri: str,
                 mongo_db_name: str = "vpbank_hackathon",
                 region_name: str = None, 
                 aws_access_key_id: str = None, 
                 aws_secret_access_key: str = None):
        """
        Initialize DynamoDB to MongoDB migrator
        
        Args:
            mongo_uri: MongoDB connection string
            mongo_db_name: MongoDB database name
            region_name: AWS region (default from config)
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-southeast-1")
        
        # Initialize DynamoDB with better error handling
        try:
            aws_access_key_id = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
            aws_secret_access_key = Utils.load_api_key_from_env("AWS_SECRET_KEY")
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
            
            # Test DynamoDB connection
            self.client.list_tables(Limit=1)
            logger.info(f"🔗 Successfully connected to DynamoDB region: {self.region_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to DynamoDB: {e}")
            raise
        
        # Initialize MongoDB with better error handling
        try:
            self.mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            self.mongo_db = self.mongo_client[mongo_db_name]
            
            # Test MongoDB connection
            self.mongo_client.admin.command('ping')
            logger.info(f"🔗 Successfully connected to MongoDB database: {mongo_db_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    def list_all_tables(self) -> List[str]:
        """List all DynamoDB tables with better error handling"""
        try:
            response = self.client.list_tables()
            tables = response.get('TableNames', [])
            logger.info(f"📋 Found {len(tables)} DynamoDB tables")
            return tables
        except ClientError as e:
            logger.error(f"❌ Error listing tables: {e}")
            raise

    def get_all_table_data(self, table_name: str) -> List[Dict]:
        """Get all data from a DynamoDB table with improved scanning"""
        try:
            table = self.dynamodb.Table(table_name)
            
            # Use scan with consistent pagination
            items = []
            last_evaluated_key = None
            scan_count = 0
            
            while True:
                scan_count += 1
                logger.info(f"📊 Scanning {table_name} - batch {scan_count}")
                
                # Prepare scan parameters
                scan_kwargs = {
                    'Select': 'ALL_ATTRIBUTES',
                    'ReturnConsumedCapacity': 'TOTAL'
                }
                
                if last_evaluated_key:
                    scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
                
                # Perform scan
                response = table.scan(**scan_kwargs)
                
                # Add items to collection
                batch_items = response.get('Items', [])
                items.extend(batch_items)
                
                logger.info(f"📥 Retrieved {len(batch_items)} items in batch {scan_count} (total: {len(items)})")
                
                # Check if there are more items
                last_evaluated_key = response.get('LastEvaluatedKey')
                if not last_evaluated_key:
                    break
                
                # Small delay to avoid throttling
                time.sleep(0.1)
            
            logger.info(f"✅ Successfully retrieved {len(items)} total items from table: {table_name}")
            return items
            
        except ClientError as e:
            logger.error(f"❌ Error scanning table {table_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error scanning table {table_name}: {e}")
            raise

    def get_accurate_table_count(self, table_name: str) -> int:
        """Get accurate count of items in DynamoDB table"""
        try:
            # Use scan to get accurate count (item_count may be stale)
            items = self.get_all_table_data(table_name)
            return len(items)
        except Exception as e:
            logger.error(f"❌ Error getting accurate count for {table_name}: {e}")
            return 0

    def convert_dynamodb_to_mongo_format(self, items: List[Dict], table_name: str = None) -> List[Dict]:
        """Convert DynamoDB items to MongoDB format with proper data type handling"""
        converted_items = []
        
        # Get table schema if table_name is provided
        table_schema = None
        if table_name:
            try:
                table_schema = self.get_table_schema(table_name)
            except Exception as e:
                logger.warning(f"⚠️ Could not get schema for {table_name}: {e}")
        
        for i, item in enumerate(items):
            try:
                # Convert DynamoDB item to regular dict with proper type conversion
                converted_item = self._convert_dynamodb_item(item)
                
                # Add migration metadata
                converted_item['_migration_info'] = {
                    'migrated_at': datetime.utcnow(),
                    'source': 'dynamodb',
                    'migrated_by': 'dynamo_to_mongo_migrator',
                    'table_name': table_name,
                    'original_index': i,
                    'schema': table_schema
                }
                
                converted_items.append(converted_item)
                
            except Exception as e:
                logger.error(f"❌ Error converting item {i} from {table_name}: {e}")
                logger.error(f"Problematic item: {item}")
                # Continue with other items
                continue
        
        logger.info(f"✅ Successfully converted {len(converted_items)} items from {table_name}")
        return converted_items

    def _convert_dynamodb_item(self, item: Dict) -> Dict:
        """Convert a single DynamoDB item to MongoDB format with proper type handling"""
        from decimal import Decimal
        import json
        
        def convert_value(value):
            """Recursively convert DynamoDB values to MongoDB-compatible types"""
            if isinstance(value, Decimal):
                # Convert Decimal to float or int
                if value % 1 == 0:
                    return int(value)
                else:
                    return float(value)
            elif isinstance(value, dict):
                # Handle nested dictionaries
                return {k: convert_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                # Handle lists
                return [convert_value(item) for item in value]
            elif isinstance(value, set):
                # Convert sets to lists
                return [convert_value(item) for item in value]
            elif hasattr(value, '__dict__'):
                # Handle custom objects by converting to dict
                return convert_value(value.__dict__)
            else:
                # Return as-is for basic types (str, int, float, bool, None)
                return value
        
        # Convert the entire item
        converted_item = {}
        for key, value in item.items():
            converted_item[key] = convert_value(value)
        
        return converted_item

    def _extract_dynamodb_value(self, value_descriptor: Dict) -> Any:
        """Extract value from DynamoDB type descriptor"""
        if not isinstance(value_descriptor, dict) or len(value_descriptor) != 1:
            return value_descriptor
        
        type_key, type_value = list(value_descriptor.items())[0]
        
        if type_key == 'S':  # String
            return str(type_value)
        elif type_key == 'N':  # Number
            return float(type_value) if '.' in type_value else int(type_value)
        elif type_key == 'B':  # Binary
            return type_value
        elif type_key == 'SS':  # String Set
            return list(type_value)
        elif type_key == 'NS':  # Number Set
            return [float(n) if '.' in n else int(n) for n in type_value]
        elif type_key == 'BS':  # Binary Set
            return list(type_value)
        elif type_key == 'M':  # Map
            return {k: self._extract_dynamodb_value(v) for k, v in type_value.items()}
        elif type_key == 'L':  # List
            return [self._extract_dynamodb_value(item) for item in type_value]
        elif type_key == 'NULL':  # Null
            return None
        elif type_key == 'BOOL':  # Boolean
            return bool(type_value)
        else:
            return type_value

    def migrate_table(self, table_name: str, collection_name: str = None, clear_existing: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """Migrate a single table from DynamoDB to MongoDB with comprehensive error handling"""
        migration_info = {
            'table_name': table_name,
            'collection_name': collection_name or table_name.lower(),
            'start_time': datetime.utcnow(),
            'end_time': None,
            'items_retrieved': 0,
            'items_converted': 0,
            'items_inserted': 0,
            'errors': [],
            'success': False
        }
        
        try:
            if collection_name is None:
                collection_name = table_name.lower()
            
            migration_info['collection_name'] = collection_name
            
            logger.info(f"🔄 Starting migration: {table_name} -> {collection_name}")
            
            # Get all data from DynamoDB table
            logger.info(f"📥 Retrieving data from DynamoDB table: {table_name}")
            dynamo_data = self.get_all_table_data(table_name)
            migration_info['items_retrieved'] = len(dynamo_data)
            
            if not dynamo_data:
                logger.warning(f"⚠️ No data found in table: {table_name}")
                migration_info['success'] = True
                migration_info['end_time'] = datetime.utcnow()
                return True, migration_info
            
            # Convert to MongoDB format
            logger.info(f"🔄 Converting {len(dynamo_data)} items to MongoDB format")
            mongo_data = self.convert_dynamodb_to_mongo_format(dynamo_data, table_name)
            migration_info['items_converted'] = len(mongo_data)
            
            if not mongo_data:
                error_msg = f"No items successfully converted from {table_name}"
                logger.error(f"❌ {error_msg}")
                migration_info['errors'].append(error_msg)
                migration_info['end_time'] = datetime.utcnow()
                return False, migration_info
            
            # Get MongoDB collection
            collection = self.mongo_db[collection_name]
            
            # Clear existing data if requested
            if clear_existing:
                delete_result = collection.delete_many({})
                logger.info(f"🗑️ Cleared {delete_result.deleted_count} existing documents in collection: {collection_name}")
            else:
                logger.info(f"📝 Appending to existing collection: {collection_name}")
            
            # Insert data in batches with error handling
            batch_size = 100
            total_inserted = 0
            batch_errors = []
            
            for i in range(0, len(mongo_data), batch_size):
                batch = mongo_data[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                try:
                    logger.info(f"📥 Inserting batch {batch_num}: {len(batch)} items")
                    result = collection.insert_many(batch, ordered=False)
                    inserted_count = len(result.inserted_ids)
                    total_inserted += inserted_count
                    logger.info(f"✅ Successfully inserted {inserted_count} items in batch {batch_num}")
                    
                except BulkWriteError as bwe:
                    # Handle partial success in bulk write
                    inserted_count = bwe.details.get('nInserted', 0)
                    total_inserted += inserted_count
                    errors = bwe.details.get('writeErrors', [])
                    
                    logger.warning(f"⚠️ Batch {batch_num} partial success: {inserted_count}/{len(batch)} items inserted")
                    for error in errors:
                        error_msg = f"Batch {batch_num} item {error.get('index', 'unknown')}: {error.get('errmsg', 'unknown error')}"
                        batch_errors.append(error_msg)
                        logger.error(f"❌ {error_msg}")
                
                except Exception as e:
                    error_msg = f"Batch {batch_num} failed completely: {str(e)}"
                    batch_errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")
                    # Continue with next batch
                    continue
                
                # Small delay between batches
                time.sleep(0.1)
            
            migration_info['items_inserted'] = total_inserted
            migration_info['errors'] = batch_errors
            
            # Verify insertion
            final_count = collection.count_documents({})
            logger.info(f"📊 Final verification: {final_count} documents in MongoDB collection")
            
            if total_inserted > 0:
                logger.info(f"✅ Successfully migrated {total_inserted} items from {table_name} to {collection_name}")
                migration_info['success'] = True
            else:
                logger.error(f"❌ No items were successfully inserted to {collection_name}")
                migration_info['success'] = False
            
            migration_info['end_time'] = datetime.utcnow()
            return migration_info['success'], migration_info
            
        except Exception as e:
            error_msg = f"Critical error migrating table {table_name}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            migration_info['errors'].append(error_msg)
            migration_info['end_time'] = datetime.utcnow()
            return False, migration_info

    def get_existing_collections(self) -> List[str]:
        """Get list of existing MongoDB collections"""
        return self.mongo_db.list_collection_names()

    def detect_new_tables(self, exclude_demo: bool = True) -> List[str]:
        """Detect new DynamoDB tables that haven't been migrated yet"""
        # Get all DynamoDB tables
        dynamo_tables = self.list_all_tables()
        
        if exclude_demo:
            dynamo_tables = [table for table in dynamo_tables if '_demo' not in table.lower()]
        
        # Get existing MongoDB collections
        existing_collections = self.get_existing_collections()
        
        # Find new tables (tables that don't have corresponding collections)
        new_tables = []
        for table_name in dynamo_tables:
            collection_name = table_name.lower().replace('-', '_')
            if collection_name not in existing_collections:
                new_tables.append(table_name)
        
        logger.info(f"🔍 Found {len(new_tables)} new tables to migrate: {new_tables}")
        return new_tables

    def migrate_new_tables_only(self, exclude_demo: bool = True) -> Dict[str, Dict[str, Any]]:
        """Migrate only new tables that haven't been migrated yet"""
        logger.info("🆕 Starting migration of new tables only")
        
        # Get new tables
        new_tables = self.detect_new_tables(exclude_demo=exclude_demo)
        
        if not new_tables:
            logger.info("✅ No new tables found - all tables already migrated")
            return {}
        
        migration_results = {}
        successful_migrations = 0
        
        for table_name in new_tables:
            logger.info(f"🔄 Processing new table: {table_name}")
            
            # Create collection name (convert to lowercase and replace special chars)
            collection_name = table_name.lower().replace('-', '_')
            
            # Migrate table
            success, migration_info = self.migrate_table(table_name, collection_name)
            migration_results[table_name] = migration_info
            
            if success:
                successful_migrations += 1
            
            # Small delay between migrations
            time.sleep(1)
        
        logger.info(f"🎉 New tables migration complete! {successful_migrations}/{len(new_tables)} new tables migrated successfully")
        return migration_results

    def migrate_all_tables(self, exclude_demo: bool = True, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """Migrate all tables from DynamoDB to MongoDB with detailed results"""
        logger.info("🚀 Starting comprehensive migration from DynamoDB to MongoDB")
        
        # Get all tables
        tables = self.list_all_tables()
        
        if exclude_demo:
            # Filter out demo tables
            tables = [table for table in tables if '_demo' not in table.lower()]
            logger.info(f"📋 Excluding demo tables, migrating {len(tables)} main tables")
        
        # If not forcing refresh, check for existing collections
        if not force_refresh:
            existing_collections = self.get_existing_collections()
            logger.info(f"📊 Found {len(existing_collections)} existing collections")
        
        migration_results = {}
        successful_migrations = 0
        
        for table_name in tables:
            collection_name = table_name.lower().replace('-', '_')
            
            # Skip if collection already exists and not forcing refresh
            if not force_refresh and collection_name in self.get_existing_collections():
                logger.info(f"⏭️ Skipping {table_name} - collection already exists (use --force-refresh to override)")
                migration_results[table_name] = {
                    'success': True,
                    'skipped': True,
                    'reason': 'Collection already exists'
                }
                successful_migrations += 1
                continue
            
            logger.info(f"🔄 Processing table: {table_name}")
            
            # Migrate table
            success, migration_info = self.migrate_table(table_name, collection_name)
            migration_results[table_name] = migration_info
            
            if success:
                successful_migrations += 1
            
            # Small delay between migrations
            time.sleep(1)
        
        logger.info(f"🎉 Migration complete! {successful_migrations}/{len(tables)} tables migrated successfully")
        return migration_results

    def create_indexes(self):
        """Create indexes in MongoDB for better performance"""
        logger.info("🔧 Creating indexes in MongoDB collections")
        
        try:
            # Create indexes for main collections
            index_configs = {
                'adverse_media': [
                    ('media_id', 1),
                    ('created_at', -1),
                    ('news_sentiment_type', 1)
                ],
                'personal_info': [
                    ('per_id', 1),
                    ('full_name', 1),
                    ('created_at', -1)
                ],
                'organization_info': [
                    ('org_id', 1),
                    ('full_name', 1),
                    ('created_at', -1)
                ],
                'personal2media': [
                    ('p2m_id', 1),
                    ('per_id', 1),
                    ('media_id', 1),
                    ('created_at', -1)
                ],
                'org2media': [
                    ('o2m_id', 1),
                    ('org_id', 1),
                    ('media_id', 1),
                    ('created_at', -1)
                ]
            }
            
            for collection_name, indexes in index_configs.items():
                collection = self.mongo_db[collection_name]
                for index_fields in indexes:
                    collection.create_index([index_fields])
                    logger.info(f"📊 Created index on {collection_name}.{index_fields[0]}")
            
            logger.info("✅ All indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")

    def check_schema_changes(self, table_name: str) -> Dict[str, Any]:
        """Check if table schema has changed since last migration"""
        try:
            collection_name = table_name.lower().replace('-', '_')
            collection = self.mongo_db[collection_name]
            
            # Get current DynamoDB table schema
            current_schema = self.get_table_schema(table_name)
            
            # Get last migration info from MongoDB
            last_migration = collection.find_one(
                {"_migration_info": {"$exists": True}},
                sort=[("_migration_info.migrated_at", -1)]
            )
            
            if not last_migration:
                return {
                    'has_changes': True,
                    'reason': 'No previous migration found',
                    'current_schema': current_schema
                }
            
            # Compare schemas (simplified comparison)
            last_schema = last_migration.get('_migration_info', {}).get('schema')
            
            if last_schema != current_schema:
                return {
                    'has_changes': True,
                    'reason': 'Schema changed',
                    'current_schema': current_schema,
                    'last_schema': last_schema
                }
            
            return {
                'has_changes': False,
                'reason': 'No schema changes detected',
                'current_schema': current_schema
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking schema changes for {table_name}: {e}")
            return {
                'has_changes': True,
                'reason': f'Error checking schema: {e}',
                'current_schema': None
            }

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get simplified table schema information"""
        try:
            response = self.client.describe_table(TableName=table_name)
            table_info = response['Table']
            
            return {
                'key_schema': table_info.get('KeySchema', []),
                'attribute_definitions': table_info.get('AttributeDefinitions', []),
                'global_secondary_indexes': table_info.get('GlobalSecondaryIndexes', []),
                'local_secondary_indexes': table_info.get('LocalSecondaryIndexes', [])
            }
        except Exception as e:
            logger.error(f"❌ Error getting schema for {table_name}: {e}")
            return {}

    def verify_migration(self, exclude_demo: bool = True) -> Dict[str, Dict[str, int]]:
        """Verify migration by comparing accurate record counts"""
        logger.info("🔍 Verifying migration with accurate counts...")
        
        verification_results = {}
        
        # Get all tables
        tables = self.list_all_tables()
        if exclude_demo:
            tables = [table for table in tables if '_demo' not in table.lower()]
        
        for table_name in tables:
            collection_name = table_name.lower().replace('-', '_')
            
            logger.info(f"📊 Verifying {table_name}...")
            
            # Count DynamoDB records using accurate method
            try:
                dynamo_count = self.get_accurate_table_count(table_name)
                logger.info(f"📋 DynamoDB {table_name}: {dynamo_count} items")
            except Exception as e:
                logger.error(f"❌ Error counting DynamoDB records for {table_name}: {e}")
                dynamo_count = 0
            
            # Count MongoDB records
            try:
                mongo_count = self.mongo_db[collection_name].count_documents({})
                logger.info(f"🍃 MongoDB {collection_name}: {mongo_count} documents")
            except Exception as e:
                logger.error(f"❌ Error counting MongoDB documents for {collection_name}: {e}")
                mongo_count = 0
            
            verification_results[table_name] = {
                'dynamodb_count': dynamo_count,
                'mongodb_count': mongo_count,
                'match': dynamo_count == mongo_count
            }
            
            status = "✅" if dynamo_count == mongo_count else "❌"
            logger.info(f"{status} {table_name}: DynamoDB={dynamo_count}, MongoDB={mongo_count}")
        
        return verification_results

    def generate_migration_report(self, migration_results: Dict[str, Dict[str, Any]], 
                                verification_results: Dict[str, Dict[str, int]]) -> str:
        """Generate comprehensive migration report"""
        report = []
        report.append("=" * 80)
        report.append("🔄 COMPREHENSIVE DYNAMODB TO MONGODB MIGRATION REPORT")
        report.append("=" * 80)
        report.append(f"📅 Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"🌍 DynamoDB Region: {self.region_name}")
        report.append(f"🍃 MongoDB Database: {self.mongo_db.name}")
        report.append("")
        
        # Migration Results Summary
        report.append("📊 MIGRATION RESULTS SUMMARY:")
        report.append("-" * 40)
        successful = sum(1 for result in migration_results.values() if result.get('success', False))
        total = len(migration_results)
        report.append(f"✅ Successful: {successful}/{total}")
        report.append("")
        
        # Detailed Migration Results
        report.append("📋 DETAILED MIGRATION RESULTS:")
        report.append("-" * 40)
        
        for table_name, result in migration_results.items():
            status = "✅" if result.get('success', False) else "❌"
            report.append(f"{status} {table_name}:")
            
            if result.get('skipped'):
                report.append(f"   ⏭️ Skipped: {result.get('reason', 'Unknown')}")
            else:
                report.append(f"   📥 Retrieved: {result.get('items_retrieved', 0)} items")
                report.append(f"   🔄 Converted: {result.get('items_converted', 0)} items")
                report.append(f"   📤 Inserted: {result.get('items_inserted', 0)} items")
                
                if result.get('errors'):
                    report.append(f"   ⚠️ Errors: {len(result['errors'])}")
                    for error in result['errors'][:3]:  # Show first 3 errors
                        report.append(f"      - {error}")
                    if len(result['errors']) > 3:
                        report.append(f"      ... and {len(result['errors']) - 3} more errors")
            
            report.append("")
        
        # Verification Results
        report.append("🔍 VERIFICATION RESULTS:")
        report.append("-" * 40)
        for table_name, counts in verification_results.items():
            status = "✅" if counts['match'] else "❌"
            report.append(f"{status} {table_name}: DynamoDB={counts['dynamodb_count']}, MongoDB={counts['mongodb_count']}")
        
        report.append("")
        report.append("=" * 80)
        report.append("Migration completed successfully!" if successful == total else "Migration completed with errors!")
        report.append("=" * 80)
        
        return "\n".join(report)

    def close(self):
        """Close database connections"""
        self.mongo_client.close()
        logger.info("🔌 Database connections closed")

def main():
    """Main function to run the migration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate DynamoDB tables to MongoDB')
    parser.add_argument('--mongo-uri', required=True, help='MongoDB connection URI')
    parser.add_argument('--mongo-db', default='vpbank_hackathon', help='MongoDB database name')
    parser.add_argument('--exclude-demo', action='store_true', default=True, help='Exclude demo tables')
    parser.add_argument('--create-indexes', action='store_true', help='Create indexes after migration')
    parser.add_argument('--verify', action='store_true', default=True, help='Verify migration')
    parser.add_argument('--report-file', default='migration_report.txt', help='Migration report file')
    parser.add_argument('--new-tables-only', action='store_true', help='Migrate only new tables')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh of all tables')
    parser.add_argument('--check-schema', action='store_true', help='Check for schema changes')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('migration.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    try:
        # Initialize migrator
        migrator = DynamoToMongoMigrator(
            mongo_uri=args.mongo_uri,
            mongo_db_name=args.mongo_db
        )
        
        # Check for schema changes if requested
        if args.check_schema:
            logger.info("🔍 Checking for schema changes...")
            tables = migrator.list_all_tables()
            if args.exclude_demo:
                tables = [table for table in tables if '_demo' not in table.lower()]
            
            for table_name in tables:
                schema_check = migrator.check_schema_changes(table_name)
                if schema_check['has_changes']:
                    logger.info(f"📋 {table_name}: {schema_check['reason']}")
                else:
                    logger.info(f"✅ {table_name}: No changes")
        
        # Run migration based on mode
        migration_results = {}
        if args.new_tables_only:
            migration_results = migrator.migrate_new_tables_only(exclude_demo=args.exclude_demo)
        else:
            migration_results = migrator.migrate_all_tables(
                exclude_demo=args.exclude_demo, 
                force_refresh=args.force_refresh
            )
        
        # Create indexes if requested
        if args.create_indexes:
            migrator.create_indexes()
        
        # Verify migration if requested
        verification_results = {}
        if args.verify:
            verification_results = migrator.verify_migration(exclude_demo=args.exclude_demo)
        
        # Generate and save report
        report = migrator.generate_migration_report(migration_results, verification_results)
        
        with open(args.report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        print(f"\n📄 Full report saved to: {args.report_file}")
        
        # Close connections
        migrator.close()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    main() 
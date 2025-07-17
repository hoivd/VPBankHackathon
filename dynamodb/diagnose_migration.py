#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic script to troubleshoot migration issues
"""
import os
import sys
import logging
from dotenv import load_dotenv
from pymongo import MongoClient
import boto3

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dynamo_to_mongo_migrator import DynamoToMongoMigrator

def diagnose_migration():
    """Diagnose migration issues"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Get MongoDB URI from environment
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        logger.error("❌ MONGO_URI environment variable not set!")
        return
    
    mongo_db_name = os.getenv('MONGO_DB_NAME', 'vpbank_hackathon')
    
    logger.info("🔍 Starting migration diagnosis")
    logger.info(f"📍 MongoDB URI: {mongo_uri}")
    logger.info(f"🗄️ MongoDB Database: {mongo_db_name}")
    
    try:
        # Test MongoDB connection
        logger.info("🔗 Testing MongoDB connection...")
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[mongo_db_name]
        
        # List existing collections
        collections = mongo_db.list_collection_names()
        logger.info(f"📋 Found {len(collections)} collections in MongoDB: {collections}")
        
        # Check each collection
        for collection_name in collections:
            collection = mongo_db[collection_name]
            count = collection.count_documents({})
            logger.info(f"📊 Collection '{collection_name}': {count} documents")
            
            # Show sample document
            sample = collection.find_one()
            if sample:
                logger.info(f"📄 Sample document keys: {list(sample.keys())}")
            else:
                logger.warning(f"⚠️ No documents found in collection '{collection_name}'")
        
        # Test DynamoDB connection
        logger.info("🔗 Testing DynamoDB connection...")
        
        # Initialize DynamoDB using Utils
        from utils import Utils
        aws_access_key_id = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
        aws_secret_access_key = Utils.load_api_key_from_env("AWS_SECRET_KEY")
        region_name = os.getenv("AWS_REGION", "ap-southeast-1")
        
        if aws_access_key_id and aws_secret_access_key:
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            client = boto3.client(
                'dynamodb',
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        else:
            dynamodb = boto3.resource('dynamodb', region_name=region_name)
            client = boto3.client('dynamodb', region_name=region_name)
        
        # List DynamoDB tables
        response = client.list_tables()
        dynamo_tables = response.get('TableNames', [])
        logger.info(f"📋 Found {len(dynamo_tables)} DynamoDB tables: {dynamo_tables}")
        
        # Check each table
        main_tables = [table for table in dynamo_tables if '_demo' not in table.lower()]
        for table_name in main_tables:
            try:
                table = dynamodb.Table(table_name)
                
                # Get table info
                table_info = table.meta.client.describe_table(TableName=table_name)
                item_count = table_info['Table']['ItemCount']
                table_size = table_info['Table']['TableSizeBytes']
                
                logger.info(f"📊 Table '{table_name}': {item_count} items, {table_size} bytes")
                
                # Try to scan a few items
                response = table.scan(Limit=1)
                items = response.get('Items', [])
                if items:
                    logger.info(f"📄 Sample item keys: {list(items[0].keys())}")
                else:
                    logger.warning(f"⚠️ No items found in table '{table_name}'")
                    
            except Exception as e:
                logger.error(f"❌ Error checking table {table_name}: {e}")
        
        # Test migration process step by step
        logger.info("🔄 Testing migration process...")
        
        # Initialize migrator
        migrator = DynamoToMongoMigrator(
            mongo_uri=mongo_uri,
            mongo_db_name=mongo_db_name
        )
        
        # Test with one table
        test_table = 'adverse_media'
        if test_table in dynamo_tables:
            logger.info(f"🧪 Testing migration for table: {test_table}")
            
            # Get data from DynamoDB
            dynamo_data = migrator.get_all_table_data(test_table)
            logger.info(f"📊 Retrieved {len(dynamo_data)} items from DynamoDB")
            
            if dynamo_data:
                # Convert to MongoDB format
                mongo_data = migrator.convert_dynamodb_to_mongo_format(dynamo_data, test_table)
                logger.info(f"📊 Converted {len(mongo_data)} items to MongoDB format")
                
                # Test insertion
                collection = mongo_db[test_table.lower()]
                logger.info(f"📝 Testing insertion to collection: {test_table.lower()}")
                
                # Insert one document as test
                if mongo_data:
                    try:
                        result = collection.insert_one(mongo_data[0])
                        logger.info(f"✅ Test insertion successful: {result.inserted_id}")
                        
                        # Count documents
                        count = collection.count_documents({})
                        logger.info(f"📊 Collection now has {count} documents")
                        
                        # Remove test document
                        collection.delete_one({'_id': result.inserted_id})
                        logger.info("🗑️ Test document removed")
                        
                    except Exception as e:
                        logger.error(f"❌ Test insertion failed: {e}")
        
        # Close connections
        migrator.close()
        mongo_client.close()
        
        logger.info("🎉 Diagnosis complete!")
        
    except Exception as e:
        logger.error(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_migration() 
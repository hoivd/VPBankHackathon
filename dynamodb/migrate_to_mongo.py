#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple script to migrate DynamoDB to MongoDB using environment variables
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dynamo_to_mongo_migrator import DynamoToMongoMigrator

def main():
    """Run migration using environment variables"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('migration.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Get MongoDB URI from environment
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        logger.error("❌ MONGO_URI environment variable not set!")
        logger.info("Please set MONGO_URI in your .env file")
        logger.info("Example: MONGO_URI=mongodb://localhost:27017/")
        return
    
    # Get MongoDB database name (default to vpbank_hackathon)
    mongo_db_name = os.getenv('MONGO_DB_NAME', 'vpbank_hackathon')
    
    logger.info("🚀 Starting DynamoDB to MongoDB migration")
    logger.info(f"📍 MongoDB URI: {mongo_uri}")
    logger.info(f"🗄️ MongoDB Database: {mongo_db_name}")
    
    try:
        # Initialize migrator
        migrator = DynamoToMongoMigrator(
            mongo_uri=mongo_uri,
            mongo_db_name=mongo_db_name
        )
        
        # Check for new tables first
        new_tables = migrator.detect_new_tables(exclude_demo=True)
        if new_tables:
            logger.info(f"🆕 Found {len(new_tables)} new tables: {new_tables}")
            logger.info("🔄 Migrating new tables only")
            migration_results = migrator.migrate_new_tables_only(exclude_demo=True)
        else:
            logger.info("✅ No new tables found")
            logger.info("🔄 Running full migration check (will skip existing tables)")
            migration_results = migrator.migrate_all_tables(exclude_demo=True, force_refresh=False)
        
        # Create indexes for better performance
        logger.info("🔧 Creating indexes")
        migrator.create_indexes()
        
        # Verify migration
        logger.info("🔍 Verifying migration")
        verification_results = migrator.verify_migration()
        
        # Generate report
        report = migrator.generate_migration_report(migration_results, verification_results)
        
        # Save report
        report_file = 'migration_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("\n" + "="*80)
        print(report)
        print(f"\n📄 Full report saved to: {report_file}")
        print(f"📋 Migration log saved to: migration.log")
        
        # Close connections
        migrator.close()
        
        logger.info("✅ Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    main() 
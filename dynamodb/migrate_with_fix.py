#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test migration script with Decimal fix
Forces refresh to ensure all data is migrated properly
"""
import os
import sys
import logging
from datetime import datetime
import dotenv
dotenv.load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dynamo_to_mongo_migrator import DynamoToMongoMigrator

def main():
    """Test migration with proper Decimal handling"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('migration_test.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get MongoDB URI from environment
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.error("❌ MONGO_URI environment variable not set")
            return
        
        logger.info("🚀 Starting DynamoDB to MongoDB migration with Decimal fix")
        logger.info(f"📍 MongoDB URI: {mongo_uri}")
        logger.info(f"🗄️ MongoDB Database: vpbank_hackathon")
        
        # Initialize migrator
        migrator = DynamoToMongoMigrator(
            mongo_uri=mongo_uri,
            mongo_db_name="vpbank_hackathon"
        )
        
        logger.info("🔄 Migrating main tables with force refresh (excluding demo tables)")
        
        # Run migration with force refresh to ensure all data is migrated
        migration_results = migrator.migrate_all_tables(
            exclude_demo=True, 
            force_refresh=True  # Force refresh to overwrite existing data
        )
        
        # Create indexes
        logger.info("🔧 Creating indexes")
        migrator.create_indexes()
        
        # Verify migration
        logger.info("🔍 Verifying migration")
        verification_results = migrator.verify_migration(exclude_demo=True)
        
        # Generate and save report
        report = migrator.generate_migration_report(migration_results, verification_results)
        
        report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Check if migration was successful
        successful_tables = sum(1 for result in migration_results.values() if result.get('success', False))
        total_tables = len(migration_results)
        
        if successful_tables == total_tables:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.error(f"❌ Migration completed with errors: {successful_tables}/{total_tables} tables migrated")
        
        # Close connections
        migrator.close()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main() 
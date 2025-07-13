# DynamoDB to MongoDB Migration Tool

This tool migrates all data from DynamoDB tables to MongoDB collections with full support for Vietnamese content.

## Features

- ✅ Migrates all DynamoDB tables to MongoDB collections
- ✅ Supports Vietnamese content with UTF-8 encoding
- ✅ Excludes demo tables by default
- ✅ Creates indexes for better performance
- ✅ Verifies migration by comparing record counts
- ✅ Generates detailed migration reports
- ✅ Batch processing for large datasets
- ✅ Error handling and logging

## Files

- `dynamo_to_mongo_migrator.py` - Main migration class with full functionality
- `migrate_to_mongo.py` - Simple script using environment variables (auto-detects new tables)
- `migrate_new_tables.py` - Script to migrate only new tables
- `MIGRATION_README.md` - This documentation

## Setup

### 1. Install Dependencies

```bash
pip install pymongo boto3 python-dotenv
```

### 2. Environment Variables

Create a `.env` file in your project root with:

```env
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=vpbank_hackathon

# AWS DynamoDB Configuration
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

## Usage

### Option 1: Simple Migration (Recommended)

```bash
cd dynamodb
python migrate_to_mongo.py
```

This will:
- Auto-detect new tables and migrate them
- Skip existing tables (smart migration)
- Create indexes for better performance
- Verify the migration
- Generate a detailed report

### Option 1a: Migrate Only New Tables

```bash
cd dynamodb
python migrate_new_tables.py
```

This will:
- Detect and migrate only new tables
- Skip all existing collections
- Perfect for incremental updates

### Option 2: Advanced Migration

```bash
cd dynamodb
python dynamo_to_mongo_migrator.py \
    --mongo-uri "mongodb://localhost:27017/" \
    --mongo-db "vpbank_hackathon" \
    --exclude-demo \
    --create-indexes \
    --verify \
    --report-file "migration_report.txt"
```

#### Advanced Options:

- `--new-tables-only` - Migrate only new tables
- `--force-refresh` - Force refresh all tables (clear and re-migrate)
- `--check-schema` - Check for schema changes before migration

Examples:
```bash
# Migrate only new tables
python dynamo_to_mongo_migrator.py --mongo-uri "mongodb://localhost:27017/" --new-tables-only

# Force refresh all tables
python dynamo_to_mongo_migrator.py --mongo-uri "mongodb://localhost:27017/" --force-refresh

# Check schema changes
python dynamo_to_mongo_migrator.py --mongo-uri "mongodb://localhost:27017/" --check-schema
```

### Option 3: Programmatic Usage

```python
from dynamo_to_mongo_migrator import DynamoToMongoMigrator

# Initialize migrator
migrator = DynamoToMongoMigrator(
    mongo_uri="mongodb://localhost:27017/",
    mongo_db_name="vpbank_hackathon"
)

# Option A: Migrate only new tables
new_tables = migrator.detect_new_tables(exclude_demo=True)
if new_tables:
    migration_results = migrator.migrate_new_tables_only(exclude_demo=True)
else:
    print("No new tables found")

# Option B: Migrate all tables (smart - skips existing)
migration_results = migrator.migrate_all_tables(exclude_demo=True, force_refresh=False)

# Option C: Force refresh all tables
migration_results = migrator.migrate_all_tables(exclude_demo=True, force_refresh=True)

# Create indexes
migrator.create_indexes()

# Verify migration
verification_results = migrator.verify_migration(exclude_demo=True)

# Generate report
report = migrator.generate_migration_report(migration_results, verification_results)
print(report)

# Close connections
migrator.close()
```

## Migration Process

### 1. Table Discovery
- Lists all DynamoDB tables
- Optionally excludes demo tables (tables with `_demo` suffix)

### 2. Data Migration
- Scans all items from each DynamoDB table
- Handles pagination for large datasets
- Converts DynamoDB format to MongoDB format
- Adds migration metadata to each document
- Inserts data in batches for efficiency

### 3. Index Creation
- Creates indexes on key fields for better query performance:
  - `adverse_media`: media_id, created_at, news_sentiment_type
  - `personal_info`: per_id, full_name, created_at
  - `organization_info`: org_id, full_name, created_at
  - `personal2media`: p2m_id, per_id, media_id, created_at
  - `org2media`: o2m_id, org_id, media_id, created_at

### 4. Verification
- Compares record counts between DynamoDB and MongoDB
- Reports any discrepancies

### 5. Reporting
- Generates detailed migration report
- Saves logs to `migration.log`
- Creates `migration_report.txt` with results

## Output

### Migration Report Example

```
================================================================================
🔄 DYNAMODB TO MONGODB MIGRATION REPORT
================================================================================
📅 Migration Date: 2025-01-13 15:30:45
🌍 DynamoDB Region: ap-southeast-1
🍃 MongoDB Database: vpbank_hackathon

📊 MIGRATION RESULTS:
----------------------------------------
✅ Successful: 5/5
✅ adverse_media
✅ org2media
✅ organization_info
✅ personal2media
✅ personal_info

🔍 VERIFICATION RESULTS:
----------------------------------------
✅ adverse_media: DynamoDB=4, MongoDB=4
✅ org2media: DynamoDB=63, MongoDB=63
✅ organization_info: DynamoDB=79, MongoDB=79
✅ personal2media: DynamoDB=25, MongoDB=25
✅ personal_info: DynamoDB=35, MongoDB=35
```

## Data Structure

### DynamoDB Tables (Main Tables Only)
1. `adverse_media` - Media articles (4 items)
2. `org2media` - Organization-media relationships (63 items)
3. `organization_info` - Organization details (79 items)
4. `personal2media` - Person-media relationships (25 items)
5. `personal_info` - Person details (35 items)

### MongoDB Collections
- Table names are converted to lowercase
- Special characters are replaced with underscores
- Each document includes migration metadata:
  ```json
  {
    "_migration_info": {
      "migrated_at": "2025-01-13T15:30:45.123456",
      "source": "dynamodb",
      "migrated_by": "dynamo_to_mongo_migrator"
    }
  }
  ```

## Vietnamese Content Support

- Full UTF-8 encoding support
- Preserves Vietnamese characters in all fields
- Handles special characters in names and content
- Maintains data integrity during migration

## Error Handling

- Comprehensive error logging
- Graceful handling of connection issues
- Batch processing with retry logic
- Detailed error reporting

## Performance Considerations

- Batch processing (100 items per batch)
- Efficient scanning with pagination
- Index creation for optimal query performance
- Connection pooling for MongoDB

## Troubleshooting

### Common Issues

1. **Connection Error**: Check AWS credentials and MongoDB URI
2. **Permission Error**: Ensure AWS user has DynamoDB read permissions
3. **Memory Issues**: Large tables are processed in batches
4. **Character Encoding**: UTF-8 encoding is handled automatically

### Logs

Check the following files for detailed information:
- `migration.log` - Detailed migration logs
- `migration_report.txt` - Summary report

## Security Notes

- Never commit `.env` files with real credentials
- Use IAM roles in production environments
- Ensure MongoDB is properly secured
- Consider using MongoDB Atlas for production

## Support

For issues or questions:
1. Check the migration logs
2. Verify environment variables
3. Test connections independently
4. Review the migration report 
# DynamoDB Database Explorer

This directory contains scripts to connect to DynamoDB and explore your database structure, schemas, and relationships.

## Setup

### 1. Environment Variables
You can set environment variables in two ways:

**Option A: Create a .env file in the project root:**
```bash
# Create .env file in the project root (VPBankHackathon/.env)
AWS_ACCESS_KEY=your_aws_access_key_here
AWS_SECRET_KEY=your_aws_secret_key_here
AWS_REGION=ap-southeast-1
```

**Option B: Set environment variables directly:**
```bash
# Windows (PowerShell)
$env:AWS_ACCESS_KEY="your_access_key"
$env:AWS_SECRET_KEY="your_secret_key"
$env:AWS_REGION="ap-southeast-1"

# Linux/Mac
export AWS_ACCESS_KEY="your_access_key"
export AWS_SECRET_KEY="your_secret_key"
export AWS_REGION="ap-southeast-1"
```

### 2. AWS Configuration
The scripts use the region configured in `config.py`:
- Current region: `ap-southeast-1`
- You can modify this in `config.py` if needed

## Scripts Available

### 1. `dynamo_explorer.py` - Comprehensive Database Explorer
This is the main script that provides a complete overview of your DynamoDB database.

**Features:**
- Lists all tables
- Shows detailed schema for each table
- Analyzes relationships between tables
- Displays sample data
- Shows indexes (Global Secondary Indexes, Local Secondary Indexes)
- Provides table statistics

**Usage:**
```bash
# Save report to file (default behavior)
python dynamodb/dynamo_explorer.py

# Print report to console
python dynamodb/dynamo_explorer.py --print

# Save report to specific file
python dynamodb/dynamo_explorer.py --save my_report.txt

# Both print to console and save to file
python dynamodb/dynamo_explorer.py --both my_report.txt
```

**Output includes:**
- Database overview
- Detailed table schemas
- Key structures (partition keys, sort keys)
- Attribute definitions
- Index information
- Relationship analysis
- Sample data from each table

### 2. `quick_connect.py` - Simple Interactive Explorer
A lightweight script for quick database exploration with interactive commands.

**Features:**
- Quick connection test
- Interactive command-line interface
- Basic table operations

**Usage:**
```bash
python dynamodb/quick_connect.py
```

**Interactive Commands:**
- `list` - List all tables
- `desc <table_name>` - Describe a specific table
- `scan <table_name>` - Get sample data from a table
- `save <filename>` - Save overview to file
- `quit` - Exit the program

### 3. Existing Scripts
- `dynamo_pusher.py` - Insert data into DynamoDB tables
- `dynamo_deleter.py` - Delete data from DynamoDB tables
- `demo.py` - Basic connection example

## Database Schema Overview

Based on your current setup, your DynamoDB contains these tables:

### Core Tables:
1. **personal_info** - Individual person records
   - Partition Key: `per_id`
   - Contains personal information and risk assessments

2. **organization_info** - Organization records
   - Partition Key: `org_id`
   - Contains organization information

3. **adverse_media** - Media/news articles
   - Partition Key: `media_id`
   - Contains article content and metadata

### Relationship Tables:
4. **personal2media** - Links persons to media articles
   - Partition Key: `p2m_id`
   - Many-to-many relationship between persons and media

5. **org2media** - Links organizations to media articles
   - Partition Key: `o2m_id`
   - Many-to-many relationship between organizations and media

6. **blacklist** - Blacklisted entities
   - Partition Key: `user`
   - Contains blocked users/entities

### Relationship Structure:
```
personal_info ←→ personal2media ←→ adverse_media
                      ↕
organization_info ←→ org2media ←→ adverse_media
```

## Common Operations

### Connect and List Tables:
```python
from dynamodb.quick_connect import QuickDynamoConnect

db = QuickDynamoConnect()
tables = db.list_tables()
```

### Get Table Schema:
```python
db.describe_table('personal_info')
```

### Scan for Sample Data:
```python
items = db.scan_table('personal_info', limit=3)
```

### Full Database Report:
```python
from dynamodb.dynamo_explorer import DynamoDBExplorer

explorer = DynamoDBExplorer()

# Print to console
explorer.print_comprehensive_report()

# Save to file
explorer.save_report("my_database_report.txt")
```

### Save Quick Overview:
```python
from dynamodb.quick_connect import QuickDynamoConnect

db = QuickDynamoConnect()
db.save_overview("quick_overview.txt")
```

## Troubleshooting

### Connection Issues:
1. Verify AWS credentials are set correctly
2. Check AWS region in `config.py`
3. Ensure DynamoDB permissions are granted
4. Verify network connectivity to AWS

### Common Errors:
- `NoCredentialsError`: Set AWS_ACCESS_KEY and AWS_SECRET_KEY
- `EndpointConnectionError`: Check internet connection and region
- `AccessDenied`: Verify IAM permissions for DynamoDB

## Sample Output

When you run the comprehensive explorer, you'll see:
```
🔍 DYNAMODB DATABASE EXPLORER REPORT
================================================================================

📊 OVERVIEW:
   • Region: ap-southeast-1
   • Total Tables: 6
   • Tables: personal_info, organization_info, adverse_media, personal2media, org2media, blacklist

============================================================
📋 TABLE 1: PERSONAL_INFO
============================================================
Status: ACTIVE
Items: 1,250
Size: 256,000 bytes
Created: 2024-01-15 10:30:00

🔑 KEY SCHEMA:
   • Partition Key: per_id

📝 ATTRIBUTES:
   • per_id (S)
   • full_name (S)
   • risk_level (N)
   ...

🔗 RELATIONSHIPS:
   • Links to personal2media via per_id
   ...
```

## Next Steps

1. Run `python dynamodb/dynamo_explorer.py` to get a full database overview
2. Use `python dynamodb/quick_connect.py` for interactive exploration
3. Check the sample data to understand your data structure
4. Review the relationship analysis to understand data connections 
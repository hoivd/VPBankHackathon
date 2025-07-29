#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Resource Checker
Comprehensive script to check all AWS resources and DynamoDB data in the application.
"""

import os
import sys
import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import Utils
from config import AWS_REGION, S3_BUCKET_NAME

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AWSResourceChecker:
    def __init__(self, aws_access_key: str, aws_secret_key: str, region_name: str = None):
        """
        Initialize AWS Resource Checker
        
        Args:
            aws_access_key: AWS access key
            aws_secret_key: AWS secret key
            region_name: AWS region (default from config)
        """
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.region_name = region_name or AWS_REGION
        
        # Initialize AWS clients
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=self.region_name
        )
        
        # Initialize various AWS service clients
        self.dynamodb = self.session.resource('dynamodb')
        self.dynamodb_client = self.session.client('dynamodb')
        self.s3 = self.session.client('s3')
        self.ec2 = self.session.client('ec2')
        self.iam = self.session.client('iam')
        self.cloudwatch = self.session.client('cloudwatch')
        self.lambda_client = self.session.client('lambda')
        self.ecs = self.session.client('ecs')
        self.rds = self.session.client('rds')
        self.elasticache = self.session.client('elasticache')
        
        logger.info(f"✅ AWS Resource Checker initialized for region: {self.region_name}")

    def check_aws_credentials(self) -> Dict[str, Any]:
        """Check if AWS credentials are valid"""
        try:
            # Try to get caller identity
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            
            return {
                'status': 'success',
                'account_id': identity['Account'],
                'user_id': identity['UserId'],
                'arn': identity['Arn'],
                'region': self.region_name
            }
        except NoCredentialsError:
            return {
                'status': 'error',
                'message': 'No AWS credentials found'
            }
        except ClientError as e:
            return {
                'status': 'error',
                'message': f'AWS credentials error: {str(e)}'
            }

    def check_dynamodb_resources(self) -> Dict[str, Any]:
        """Check all DynamoDB resources"""
        try:
            # List all tables
            tables = self.dynamodb_client.list_tables()
            table_names = tables.get('TableNames', [])
            
            # Filter out demo tables
            production_tables = [table for table in table_names if 'demo' not in table]
            
            table_details = []
            total_items = 0
            total_size_bytes = 0
            
            for table_name in production_tables:
                try:
                    # Get table description
                    table_desc = self.dynamodb_client.describe_table(TableName=table_name)
                    table_info = table_desc['Table']
                    
                    # Get table statistics
                    table_stats = {
                        'table_name': table_name,
                        'status': table_info.get('TableStatus'),
                        'item_count': table_info.get('ItemCount', 0),
                        'table_size_bytes': table_info.get('TableSizeBytes', 0),
                        'creation_date': str(table_info.get('CreationDateTime', '')),
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
                            table_stats['partition_key'] = key_name
                        elif key_type == 'RANGE':
                            table_stats['sort_key'] = key_name
                    
                    # Extract attribute definitions
                    for attr in table_info.get('AttributeDefinitions', []):
                        table_stats['attributes'].append({
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
                        
                        table_stats['global_secondary_indexes'].append(gsi_info)
                    
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
                        
                        table_stats['local_secondary_indexes'].append(lsi_info)
                    
                    # Get sample data
                    try:
                        table = self.dynamodb.Table(table_name)
                        sample_response = table.scan(Limit=3)
                        table_stats['sample_data'] = sample_response.get('Items', [])
                    except Exception as e:
                        table_stats['sample_data'] = []
                        logger.warning(f"Could not get sample data for table {table_name}: {e}")
                    
                    table_details.append(table_stats)
                    total_items += table_stats['item_count']
                    total_size_bytes += table_stats['table_size_bytes']
                    
                except ClientError as e:
                    logger.error(f"Error getting details for table {table_name}: {e}")
                    table_details.append({
                        'table_name': table_name,
                        'error': str(e)
                    })
            
            return {
                'status': 'success',
                'total_tables': len(production_tables),
                'total_items': total_items,
                'total_size_bytes': total_size_bytes,
                'tables': table_details
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'message': f'DynamoDB error: {str(e)}'
            }

    def check_s3_resources(self) -> Dict[str, Any]:
        """Check S3 resources"""
        try:
            # List buckets
            buckets = self.s3.list_buckets()
            bucket_list = buckets.get('Buckets', [])
            
            bucket_details = []
            total_objects = 0
            total_size_bytes = 0
            
            for bucket in bucket_list:
                bucket_name = bucket['Name']
                bucket_info = {
                    'name': bucket_name,
                    'creation_date': str(bucket.get('CreationDate', '')),
                    'objects': 0,
                    'size_bytes': 0,
                    'sample_objects': []
                }
                
                try:
                    # List objects in bucket
                    paginator = self.s3.get_paginator('list_objects_v2')
                    page_iterator = paginator.paginate(Bucket=bucket_name)
                    
                    for page in page_iterator:
                        if 'Contents' in page:
                            for obj in page['Contents']:
                                bucket_info['objects'] += 1
                                bucket_info['size_bytes'] += obj.get('Size', 0)
                                
                                # Collect sample objects (first 5)
                                if len(bucket_info['sample_objects']) < 5:
                                    bucket_info['sample_objects'].append({
                                        'key': obj['Key'],
                                        'size': obj.get('Size', 0),
                                        'last_modified': str(obj.get('LastModified', ''))
                                    })
                    
                    bucket_details.append(bucket_info)
                    total_objects += bucket_info['objects']
                    total_size_bytes += bucket_info['size_bytes']
                    
                except ClientError as e:
                    logger.warning(f"Could not access bucket {bucket_name}: {e}")
                    bucket_info['error'] = str(e)
                    bucket_details.append(bucket_info)
            
            return {
                'status': 'success',
                'total_buckets': len(bucket_list),
                'total_objects': total_objects,
                'total_size_bytes': total_size_bytes,
                'buckets': bucket_details
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'message': f'S3 error: {str(e)}'
            }

    def check_ec2_resources(self) -> Dict[str, Any]:
        """Check EC2 resources"""
        try:
            # Describe instances
            instances = self.ec2.describe_instances()
            
            instance_details = []
            total_instances = 0
            running_instances = 0
            
            for reservation in instances.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_info = {
                        'instance_id': instance['InstanceId'],
                        'instance_type': instance.get('InstanceType', ''),
                        'state': instance['State']['Name'],
                        'launch_time': str(instance.get('LaunchTime', '')),
                        'public_ip': instance.get('PublicIpAddress', ''),
                        'private_ip': instance.get('PrivateIpAddress', ''),
                        'tags': instance.get('Tags', [])
                    }
                    
                    instance_details.append(instance_info)
                    total_instances += 1
                    
                    if instance['State']['Name'] == 'running':
                        running_instances += 1
            
            return {
                'status': 'success',
                'total_instances': total_instances,
                'running_instances': running_instances,
                'stopped_instances': total_instances - running_instances,
                'instances': instance_details
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'message': f'EC2 error: {str(e)}'
            }

    def check_lambda_functions(self) -> Dict[str, Any]:
        """Check Lambda functions"""
        try:
            functions = self.lambda_client.list_functions()
            function_list = functions.get('Functions', [])
            
            function_details = []
            total_functions = len(function_list)
            
            for func in function_list:
                function_info = {
                    'function_name': func['FunctionName'],
                    'runtime': func.get('Runtime', ''),
                    'handler': func.get('Handler', ''),
                    'code_size': func.get('CodeSize', 0),
                    'description': func.get('Description', ''),
                    'timeout': func.get('Timeout', 0),
                    'memory_size': func.get('MemorySize', 0),
                    'last_modified': str(func.get('LastModified', ''))
                }
                function_details.append(function_info)
            
            return {
                'status': 'success',
                'total_functions': total_functions,
                'functions': function_details
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'message': f'Lambda error: {str(e)}'
            }

    def check_rds_instances(self) -> Dict[str, Any]:
        """Check RDS instances"""
        try:
            instances = self.rds.describe_db_instances()
            instance_list = instances.get('DBInstances', [])
            
            instance_details = []
            total_instances = len(instance_list)
            
            for instance in instance_list:
                instance_info = {
                    'db_instance_identifier': instance.get('DBInstanceIdentifier', ''),
                    'engine': instance.get('Engine', ''),
                    'db_instance_status': instance.get('DBInstanceStatus', ''),
                    'db_instance_class': instance.get('DBInstanceClass', ''),
                    'allocated_storage': instance.get('AllocatedStorage', 0),
                    'endpoint': instance.get('Endpoint', {}),
                    'availability_zone': instance.get('AvailabilityZone', ''),
                    'multi_az': instance.get('MultiAZ', False)
                }
                instance_details.append(instance_info)
            
            return {
                'status': 'success',
                'total_instances': total_instances,
                'instances': instance_details
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'message': f'RDS error: {str(e)}'
            }

    def check_iam_resources(self) -> Dict[str, Any]:
        """Check IAM resources"""
        try:
            # List users
            users = self.iam.list_users()
            user_list = users.get('Users', [])
            
            # List roles
            roles = self.iam.list_roles()
            role_list = roles.get('Roles', [])
            
            # List groups
            groups = self.iam.list_groups()
            group_list = groups.get('Groups', [])
            
            return {
                'status': 'success',
                'total_users': len(user_list),
                'total_roles': len(role_list),
                'total_groups': len(group_list),
                'users': [{'user_name': user['UserName'], 'arn': user['Arn']} for user in user_list],
                'roles': [{'role_name': role['RoleName'], 'arn': role['Arn']} for role in role_list],
                'groups': [{'group_name': group['GroupName'], 'arn': group['Arn']} for group in group_list]
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'message': f'IAM error: {str(e)}'
            }

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of all AWS resources"""
        logger.info("🔍 Starting comprehensive AWS resource check...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'region': self.region_name,
            'credentials': self.check_aws_credentials(),
            'dynamodb': self.check_dynamodb_resources(),
            's3': self.check_s3_resources(),
            'ec2': self.check_ec2_resources(),
            'lambda': self.check_lambda_functions(),
            'rds': self.check_rds_instances(),
            'iam': self.check_iam_resources()
        }
        
        return report

    def save_report(self, file_path: str, report: Dict[str, Any]):
        """Save the report to a file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"✅ Report saved to: {file_path}")
            
        except Exception as e:
            logger.error(f"❌ Error saving report: {e}")

    def print_summary(self, report: Dict[str, Any]):
        """Print a summary of the AWS resources"""
        print("\n" + "="*80)
        print("🔍 AWS RESOURCE SUMMARY")
        print("="*80)
        
        # Credentials
        creds = report['credentials']
        if creds['status'] == 'success':
            print(f"✅ AWS Credentials: Valid")
            print(f"   Account ID: {creds['account_id']}")
            print(f"   User ARN: {creds['arn']}")
        else:
            print(f"❌ AWS Credentials: {creds['message']}")
        
        print(f"\n🌍 Region: {report['region']}")
        print(f"📅 Timestamp: {report['timestamp']}")
        
        # DynamoDB Summary
        dynamodb = report['dynamodb']
        if dynamodb['status'] == 'success':
            print(f"\n📊 DynamoDB:")
            print(f"   Tables: {dynamodb['total_tables']}")
            print(f"   Total Items: {dynamodb['total_items']:,}")
            print(f"   Total Size: {dynamodb['total_size_bytes']:,} bytes")
        else:
            print(f"\n❌ DynamoDB: {dynamodb['message']}")
        
        # S3 Summary
        s3 = report['s3']
        if s3['status'] == 'success':
            print(f"\n🪣 S3:")
            print(f"   Buckets: {s3['total_buckets']}")
            print(f"   Total Objects: {s3['total_objects']:,}")
            print(f"   Total Size: {s3['total_size_bytes']:,} bytes")
        else:
            print(f"\n❌ S3: {s3['message']}")
        
        # EC2 Summary
        ec2 = report['ec2']
        if ec2['status'] == 'success':
            print(f"\n🖥️  EC2:")
            print(f"   Total Instances: {ec2['total_instances']}")
            print(f"   Running: {ec2['running_instances']}")
            print(f"   Stopped: {ec2['stopped_instances']}")
        else:
            print(f"\n❌ EC2: {ec2['message']}")
        
        # Lambda Summary
        lambda_funcs = report['lambda']
        if lambda_funcs['status'] == 'success':
            print(f"\n⚡ Lambda:")
            print(f"   Functions: {lambda_funcs['total_functions']}")
        else:
            print(f"\n❌ Lambda: {lambda_funcs['message']}")
        
        # RDS Summary
        rds = report['rds']
        if rds['status'] == 'success':
            print(f"\n🗄️  RDS:")
            print(f"   Instances: {rds['total_instances']}")
        else:
            print(f"\n❌ RDS: {rds['message']}")
        
        # IAM Summary
        iam = report['iam']
        if iam['status'] == 'success':
            print(f"\n👤 IAM:")
            print(f"   Users: {iam['total_users']}")
            print(f"   Roles: {iam['total_roles']}")
            print(f"   Groups: {iam['total_groups']}")
        else:
            print(f"\n❌ IAM: {iam['message']}")

def main():
    """Main function"""
    try:
        # Load AWS credentials from environment
        aws_access_key = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
        aws_secret_key = Utils.load_api_key_from_env("AWS_SECRET_KEY")
        
        # Create checker instance
        checker = AWSResourceChecker(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key
        )
        
        # Generate comprehensive report
        report = checker.generate_comprehensive_report()
        
        # Print summary
        checker.print_summary(report)
        
        # Save detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"aws_resource_report_{timestamp}.json"
        checker.save_report(report_file, report)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Check command line arguments for additional options
        if len(sys.argv) > 1:
            if sys.argv[1] == "--dynamodb-only":
                print("\n" + "="*80)
                print("📊 DYNAMODB DETAILED REPORT")
                print("="*80)
                dynamodb = report['dynamodb']
                if dynamodb['status'] == 'success':
                    for table in dynamodb['tables']:
                        print(f"\n📋 Table: {table['table_name']}")
                        print(f"   Status: {table.get('status', 'N/A')}")
                        print(f"   Items: {table.get('item_count', 0):,}")
                        print(f"   Size: {table.get('table_size_bytes', 0):,} bytes")
                        print(f"   Partition Key: {table.get('partition_key', 'N/A')}")
                        if table.get('sort_key'):
                            print(f"   Sort Key: {table.get('sort_key')}")
                        
                        # Show sample data
                        if table.get('sample_data'):
                            print(f"   Sample Data:")
                            for i, item in enumerate(table['sample_data'], 1):
                                print(f"     Sample {i}: {json.dumps(item, indent=6, default=str, ensure_ascii=False)}")
        
    except Exception as e:
        logger.error(f"❌ Error running AWS resource checker: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from logger import _setup_logger
import config

class DynamoQuery:
    def __init__(self, dynamodb):
        self.dynamodb = dynamodb

    def query_by_key(self, table_name, key_name, key_value, index_name=None):
        table = self.dynamodb.Table(table_name)
        try:
            query_params = {
                "KeyConditionExpression": Key(key_name).eq(key_value)
            }
            if index_name:
                query_params["IndexName"] = index_name

            response = table.query(**query_params)
            return response.get("Items", [])
        except ClientError as e:
            print(f"[ERROR] Query failed on table {table_name}: {e.response['Error']['Message']}")
            return []

    def scan_by_filter(self, table_name, filter_expression):
        table = self.dynamodb.Table(table_name)
        try:
            response = table.scan(FilterExpression=filter_expression)
            return response.get("Items", [])
        except ClientError as e:
            print(f"[ERROR] Scan failed on table {table_name}: {e.response['Error']['Message']}")
            return []

    def get_item_by_key(self, table_name, key_dict):
        table = self.dynamodb.Table(table_name)
        try:
            response = table.get_item(Key=key_dict)
            return response.get("Item", None)
        except ClientError as e:
            print(f"[ERROR] GetItem failed on table {table_name}: {e.response['Error']['Message']}")
            return None

    def scan_all(self, table_name):
        table = self.dynamodb.Table(table_name)
        try:
            response = table.scan()
            return response.get("Items", [])
        except ClientError as e:
            print(f"[ERROR] Scan failed on table {table_name}: {e.response['Error']['Message']}")
            return []
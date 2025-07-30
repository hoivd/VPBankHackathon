import boto3
# from logger import _setup_logger
import config
import logging
# logger = _setup_logger(__name__, config.LOG_LEVEL)

class BaseDynamoDB:
    def __init__(self, region_name, access_key, secret_key):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        
        logging.info(f"Connected to DynamoDB in region {region_name}")
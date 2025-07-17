import boto3
from botocore.exceptions import ClientError
from logger import _setup_logger
import config
from utils import Utils
from dynamodb.base_dynamo import BaseDynamoDB

logger = _setup_logger(__name__, config.LOG_LEVEL)

class DynamoDBTableChecker:
    def __init__(self, dynamodb):
        self.dynamodb = dynamodb

    def is_table_empty(self, table_name):
        try:
            table = self.dynamodb.Table(table_name)
            response = table.scan(Limit=1)
            items = response.get("Items", [])
            return len(items) == 0
        except ClientError as e:
            print(f"Lỗi khi truy vấn bảng {table_name}: {e.response['Error']['Message']}")
            return None

if __name__ == "__main__":
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )
    checker = DynamoDBTableChecker(dynamodb=base_dynamo.dynamodb)

    table_name = "organization_info"
    is_empty = checker.is_table_empty(table_name)

    if is_empty is True:
        print(f"✅ Bảng '{table_name}' trống.")
    elif is_empty is False:
        print(f"❌ Bảng '{table_name}' có dữ liệu.")
    else:
        print(f"⚠️ Không thể kiểm tra bảng '{table_name}'.")
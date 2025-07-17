import time
import boto3
import copy
from botocore.exceptions import ClientError
import config
from logger import _setup_logger
from utils import Utils
from dynamodb.base_dynamo import BaseDynamoDB

logger = _setup_logger(__name__, config.LOG_LEVEL)

class DynamoPusher:
    def __init__(self, dynamodb):
        self.dynamodb = dynamodb

    def insert(self, data, table_config: dict):
        """
        :param data: dict hoặc list[dict]
        :param table_config: dict với key là tên bảng, value là partition key
               Ví dụ: {"customer2media": "per_unix_id"}
        """
        if len(table_config) != 1:
            raise ValueError("table_config phải chứa đúng một cặp {table_name: partition_key}")

        table_name, partition_key = next(iter(table_config.items()))
        table = self.dynamodb.Table(table_name)

        if isinstance(data, list):
            self.insert_many_dicts(table, data, partition_key)
        elif isinstance(data, dict):
            self.insert_one_dict(table, data, partition_key)
        else:
            raise TypeError("Data phải là dict hoặc list[dict]")

    def insert_one_dict(self, table, data_dict: dict, partition_key: str):
        item = copy.deepcopy(data_dict)

        if partition_key not in item:
            generated_key = f"{partition_key}_{int(time.time() * 1000)}"
            item[partition_key] = generated_key
            logger.info(f"⚠️ Tự động thêm partition key '{partition_key}': {generated_key}")

        try:
            table.put_item(Item=item)
            logger.info(f"✅ Inserted item with {partition_key}: {item.get(partition_key)}")
        except ClientError as e:
            logger.info(f"❌ Error inserting item: {e.response['Error']['Message']}")

    def insert_many_dicts(self, table, data_list: list[dict], partition_key: str):
        for item in data_list:
            self.insert_one_dict(table, item, partition_key)

if __name__ == "__main__":
    sample_data = {
            "full_name": "Trương Mỹ Lan",
            "role_in_case": "Bị cáo",
            "customer_role_in_news": "Subject",
            "frequency": "repeated",
            "event_severity_level": "Very High",
            "event_status_outcome": "Convicted",
            "high_risk_industry_link": True,
            "media_unix_id": "media_1752259766481",
            "per_unix_id": "user_1752259766482"
        }

    # Cấu hình kết nối DynamoDB
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    TABLE_NAME = "personal_info"
    PARTITION_KEY = "per_id"

    # Khởi tạo và insert
    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )
    pusher = DynamoPusher(base_dynamo.dynamodb)
    
    pusher.insert(
        data=sample_data,
        table_config={TABLE_NAME: PARTITION_KEY}
    )
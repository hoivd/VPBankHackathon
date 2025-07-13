import boto3
from botocore.exceptions import ClientError
from logger import _setup_logger
import config
from utils import Utils
from dynamodb.base_dynamo import BaseDynamoDB
from utils import Utils

logger = _setup_logger(__name__, config.LOG_LEVEL)

class DynamoDBDeleter:
    def __init__(self, dynamodb):
        self.dynamodb = dynamodb

    def delete_item(self, table_config: dict, partition_value, sort_key=None, sort_value=None):
        """
        Xoá một item theo khoá chính (PK hoặc PK + SK).
        :param table_config: dict dạng {table_name: partition_key}
        """
        table_name, partition_key = list(table_config.items())[0]
        table = self.dynamodb.Table(table_name)

        key = {partition_key: partition_value}
        if sort_key and sort_value is not None:
            key[sort_key] = sort_value

        try:
            response = table.delete_item(Key=key, ReturnValues='ALL_OLD')
            if 'Attributes' in response:
                print(f"✅ Đã xóa item trong bảng '{table_name}':", Utils.json_to_str(response['Attributes']))
            else:
                print(f"⚠️ Item không tồn tại trong bảng '{table_name}'.")
        except ClientError as e:
            print(f"❌ Lỗi khi xoá item trong bảng '{table_name}':", e.response['Error']['Message'])

    def delete_all_items(self, table_config: dict, sort_key=None):
        """
        Xoá toàn bộ item trong bảng (batch delete).
        :param table_config: dict dạng {table_name: partition_key}
        """
        table_name, partition_key = list(table_config.items())[0]
        table = self.dynamodb.Table(table_name)

        print(f"⚠️ Đang xoá toàn bộ dữ liệu trong bảng '{table_name}'...")
        try:
            scan = table.scan()
            with table.batch_writer() as batch:
                for item in scan['Items']:
                    key = {partition_key: item[partition_key]}
                    if sort_key:
                        key[sort_key] = item[sort_key]
                    batch.delete_item(Key=key)
            print(f"✅ Đã xoá xong toàn bộ item trong bảng '{table_name}'.")
        except ClientError as e:
            print(f"❌ Lỗi khi xoá tất cả item trong bảng '{table_name}':", e.response['Error']['Message'])

    def delete_multiple_tables_items(self, tables_config):
        """
        Xoá toàn bộ item cho nhiều bảng.
        Args:
            tables_config (list of dict): Mỗi dict gồm:
                {
                    'table_name': 'abc',
                    'partition_key': 'id',
                    'sort_key': 'optional_sort_key'  # (tuỳ chọn)
                }
        """
        for _, table_config in tables_config.items():
            self.delete_all_items(
                table_config=table_config,
            )

if __name__ == "__main__":
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )

    deleter = DynamoDBDeleter(base_dynamo.dynamodb)

    table_config = {
        'media_config': {"adverse_media": "media_id"},
        'person_config': {"personal_info": "per_id"},
        'organization_config': {"organization_info": "org_id"},
        'p2m_config':{"personal2media": "p2m_id"},
        'o2m_config': {"org2media": "o2m_id"}
    }

    deleter.delete_multiple_tables_items(table_config)
    # table_name, partition_key = 'personal_info', 'per_id'
    # partition_value = 'per_id_1752384018355865'
    # deleter.delete_item(table_name=table_name, partition_key=partition_key, partition_value=partition_value)


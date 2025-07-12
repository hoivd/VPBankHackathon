import boto3
from botocore.exceptions import ClientError
from logger import _setup_logger
import config
from utils import Utils

logger = _setup_logger(__name__, config.LOG_LEVEL)

class DynamoDBDeleter:
    def __init__(self,
                 region_name='ap-southeast-1',
                 aws_access_key_id=None,
                 aws_secret_access_key=None,
                 aws_session_token=None):
        """Khởi tạo DynamoDB client"""
        if aws_access_key_id and aws_secret_access_key:
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token
            )
        else:
            self.dynamodb = boto3.resource('dynamodb', region_name=region_name)

    def delete_item(self, table_name, partition_key, partition_value, sort_key=None, sort_value=None):
        """Xoá một item theo khoá chính"""
        table = self.dynamodb.Table(table_name)
        key = {partition_key: partition_value}
        if sort_key and sort_value is not None:
            key[sort_key] = sort_value

        try:
            response = table.delete_item(Key=key, ReturnValues='ALL_OLD')
            if 'Attributes' in response:
                print(f"✅ Đã xóa item trong bảng '{table_name}':", response['Attributes'])
            else:
                print(f"⚠️ Item không tồn tại trong bảng '{table_name}'.")
        except ClientError as e:
            print(f"❌ Lỗi khi xoá item trong bảng '{table_name}':", e.response['Error']['Message'])

    def delete_all_items(self, table_name, partition_key, sort_key=None):
        """Xoá toàn bộ dữ liệu trong bảng"""
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
        for config in tables_config:
            self.delete_all_items(
                table_name=config['table_name'],
                partition_key=config['partition_key'],
                sort_key=config.get('sort_key')
            )

if __name__ == "__main__":
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION

    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION

    deleter = DynamoDBDeleter(
        region_name=REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    tables_to_clear = [
        {'table_name': 'adverse_media',      'partition_key': 'media_id'},
        {'table_name': 'org2media',          'partition_key': 'o2m_id'},
        {'table_name': 'organization_info',  'partition_key': 'org_id'},
        {'table_name': 'personal_info',      'partition_key': 'per_id'},
        {'table_name': 'personal2media',     'partition_key': 'p2m_id'}
    ]

    deleter.delete_multiple_tables_items(tables_to_clear)
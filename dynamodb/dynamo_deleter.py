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

    # def delete_item(self, table_config: dict, partition_value, sort_key=None, sort_value=None):
    #     """
    #     Xoá một item theo khoá chính (PK hoặc PK + SK).
    #     :param table_config: dict dạng {table_name: partition_key}
    #     """
    #     table_name, partition_key = list(table_config.items())[0]
    #     table = self.dynamodb.Table(table_name)

    #     key = {partition_key: partition_value}
    #     if sort_key and sort_value is not None:
    #         key[sort_key] = sort_value

    #     try:
    #         response = table.delete_item(Key=key, ReturnValues='ALL_OLD')
    #         if 'Attributes' in response:
    #             print(f"✅ Đã xóa item trong bảng '{table_name}':", Utils.json_to_str(response['Attributes']))
    #         else:
    #             print(f"⚠️ Item không tồn tại trong bảng '{table_name}'.")
    #     except ClientError as e:
    #         print(f"❌ Lỗi khi xoá item trong bảng '{table_name}':", e.response['Error']['Message'])

    def delete_item(self, table_config: dict, partition_value, sort_key=None, sort_value=None):
        """
        Xoá một hoặc nhiều item theo partition key (và sort key nếu có).
        :param table_config: dict dạng {table_name: partition_key}
        :param partition_value: str hoặc list[str] (nhiều khoá chính)

        """
        table_name, partition_key = list(table_config.items())[0]
        table = self.dynamodb.Table(table_name)

        # Chuyển sang danh sách nếu chỉ truyền 1 giá trị
        partition_values = partition_value if isinstance(partition_value, list) else [partition_value]

        for pv in partition_values:
            key = {partition_key: pv}
            if sort_key and sort_value is not None:
                key[sort_key] = sort_value

            try:
                response = table.delete_item(Key=key, ReturnValues='ALL_OLD')
                if 'Attributes' in response:
                    print(f"✅ Đã xóa item [{key}] trong bảng '{table_name}':", Utils.json_to_str(response['Attributes']))
                else:
                    print(f"⚠️ Item [{key}] không tồn tại trong bảng '{table_name}'.")
            except ClientError as e:
                print(f"❌ Lỗi khi xoá item [{key}] trong bảng '{table_name}':", e.response['Error']['Message'])


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
            
def main():
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("NEW_AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("NEW_AWS_SECRET_KEY")

    REGION = config.AWS_REGION

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )

    deleter = DynamoDBDeleter(base_dynamo.dynamodb)

    table_config = config.TABLE_CONFIG_DEMO

    deleter.delete_multiple_tables_items(table_config)
    # org_embedd2media_config = table_config['org_embedd2media_config']
    # ids = [100000, 100001]
    # deleter.delete_item(org_embedd2media_config, partition_value=ids)


if __name__ == "__main__":
    main()
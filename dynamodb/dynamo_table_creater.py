from dynamodb.base_dynamo import BaseDynamoDB
from logger import _setup_logger
from utils import Utils
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)


class DynamoTableManager:
    def __init__(self, table_config: dict, aws_access_key, aws_secret_key, region):
        self.table_config = table_config

        self.base_dynamo = BaseDynamoDB(
            region_name=region,
            access_key=aws_access_key,
            secret_key=aws_secret_key
        )

        self.dynamodb_resource = self.base_dynamo.dynamodb
        logger.info("✅ Đã kết nối tới DynamoDB")

    def convert_table_config(self) -> dict:
        """
        Chuyển TABLE_CONFIG dạng đơn giản sang schema chuẩn để tạo bảng DynamoDB
        """
        tables_to_create = {}

        for _, config in self.table_config.items():
            for table_name, partition_key in config.items():
                tables_to_create[table_name] = {
                    "KeySchema": [
                        {"AttributeName": partition_key, "KeyType": "HASH"}
                    ],
                    "AttributeDefinitions": [
                        {"AttributeName": partition_key, "AttributeType": "S"}
                    ],
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                }

        return tables_to_create

    def create_table(self, table_name, table_schema):
        """
        Tạo một bảng DynamoDB
        """
        try:
            table = self.dynamodb_resource.create_table(
                TableName=table_name,
                KeySchema=table_schema["KeySchema"],
                AttributeDefinitions=table_schema["AttributeDefinitions"],
                ProvisionedThroughput=table_schema["ProvisionedThroughput"]
            )
            logger.info(f"⏳ Đang tạo bảng: {table_name} ...")
            table.wait_until_exists()
            logger.info(f"✅ Bảng '{table_name}' đã được tạo thành công.")
        except self.dynamodb_resource.meta.client.exceptions.ResourceInUseException:
            logger.warning(f"⚠️ Bảng '{table_name}' đã tồn tại. Bỏ qua.")
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo bảng '{table_name}': {e}")

    def create_all_tables(self):
        """
        Tạo toàn bộ bảng từ TABLE_CONFIG
        """
        tables_to_create = self.convert_table_config()
        for table_name, schema in tables_to_create.items():
            self.create_table(table_name, schema)

def main():
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    print(f"AWS_ACCESS_KEY: {AWS_ACCESS_KEY}")
    print(f"AWS_SECRET_KEY: {AWS_SECRET_KEY}")
    print(f"REGION: {REGION}")

    manager = DynamoTableManager(
        aws_secret_key=AWS_SECRET_KEY,
        aws_access_key=AWS_ACCESS_KEY,
        region=REGION,
        table_config=config.TABLE_CONFIG_DEMO)
    
    manager.create_all_tables()

if __name__ == "__main__":
    main()

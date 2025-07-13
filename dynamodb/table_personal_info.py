from dynamodb.dynamo_query import DynamoQuery
from utils import Utils
import config
from dynamodb.base_dynamo import BaseDynamoDB

class TablePersonalInfo:
    def __init__(self, query: DynamoQuery):
        self.query = query

    def get_by_per_id(self, per_id: str):
        return self.query.get_item_by_key(
            table_name="personal_info",
            key_dict={"per_id": per_id}
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
    
    query = DynamoQuery(base_dynamo.dynamodb)

    personal2media_table = TablePersonalInfo(query=query)

    # Ví dụ sử dụng
    per_id = "per_id_1752346833994845"
    item = personal2media_table.get_by_per_id(per_id)
    print(f"Item with per_id '{per_id}': {item}")
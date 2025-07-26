from dynamodb.dynamo_query import DynamoQuery
from utils import Utils
import config
from dynamodb.base_dynamo import BaseDynamoDB

class TablePersonalInfo:
    def __init__(self, query: DynamoQuery, table_config):
        self.query = query
        self.table_name, _ = list(table_config['person_config'].items())[0]

    def get_by_per_id(self, per_id: str):
        return self.query.get_item_by_key(
            table_name=self.table_name,
            key_dict={"per_id": per_id}
        )

    def get_items_by_per_ids(self, per_ids: list[str]) -> list[dict]:
        """
        Lấy thông tin cá nhân từ danh sách per_id
        """
        items = []
        for pid in per_ids:
            item = self.get_by_per_id(pid)
            if item:
                items.append(item)
        return items

    def get_all_items(self) -> list[dict]:
        """
        Lấy tất cả item trong bảng cá nhân từ DynamoDB
        """
        return self.query.scan_all(self.table_name)
    
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

    personal2media_table = TablePersonalInfo(query=query, table_config=config.TABLE_CONFIG)

    # # Ví dụ sử dụng
    # per_id = "per_id_1752346833994845"
    # item = personal2media_table.get_by_per_id(per_id)
    # print(f"Item with per_id '{per_id}': {item}")

    all_items = personal2media_table.get_all_items()
    print(type(all_items))
    print(f"Tổng số item: {len(all_items)}")
    for item in all_items[:5]:  # In thử 5 item đầu tiên
        print(item)

    Utils.save_json(all_items, "./data/personal_info_items.json")
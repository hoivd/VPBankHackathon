# table_personal2media.py
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from utils import Utils
import config
from boto3.dynamodb.conditions import Attr


class TablePersonal2Media:
    def __init__(self, query: DynamoQuery, table_config):
        self.query = query
        self.table_name, _ = list(table_config['p2m_config'].items())[0]

    def get_person_ids_by_media(self, media_id: str) -> list:
        results = self.query.scan_by_filter(
            table_name=self.table_name,
            filter_expression=Attr("media_id").eq(media_id)
        )
        return [item["per_id"] for item in results]
    
    def get_items_by_person(self, per_id: str) -> list:
        results = self.query.scan_by_filter(
            table_name=self.table_name,
            filter_expression=Attr("per_id").eq(per_id)
        )
        return results  # Trả toàn bộ item liên quan đến per_id
    
def main():
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )
    
    query = DynamoQuery(base_dynamo.dynamodb)

    personal2media_table = TablePersonal2Media(query=query, table_config=config.TABLE_CONFIG)

    # # Ví dụ sử dụng
    # media_id = "media_id_1752346833994764"
    # person_ids = personal2media_table.get_person_ids_by_media(media_id)
    # print(f"Person IDs associated with media '{media_id}': {person_ids}")
    
    # --- Ví dụ 2: Lấy danh sách media liên quan đến per_id ---
    per_id = "per_id_1752778464752931"
    media_items = personal2media_table.get_items_by_person(per_id)
    print(f"[Theo per_id] Media items associated with person '{per_id}':")
    for item in media_items:
        item.pop("created_at", None) 
        item.pop("media_id", None) 
        item.pop("per_id", None)
        item.pop("p2m_id", None)
        item.pop("entity_name", None)  
         # Loại bỏ trường created_at nếu không cần thiết
        print(Utils.json_to_str(item))

if __name__ == "__main__":
    main()
# table_personal2media.py
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from utils import Utils
import config
from boto3.dynamodb.conditions import Attr


class TablePersonal2Media:
    def __init__(self, query: DynamoQuery):
        self.query = query

    def get_person_ids_by_media(self, media_id: str) -> list:
        results = self.query.scan_by_filter(
            table_name="personal2media",
            filter_expression=Attr("media_id").eq(media_id)
        )
        return [item["per_id"] for item in results]

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

    personal2media_table = TablePersonal2Media(query=query)

    # Ví dụ sử dụng
    media_id = "media_id_1752346833994764"
    person_ids = personal2media_table.get_person_ids_by_media(media_id)
    print(f"Person IDs associated with media '{media_id}': {person_ids}")
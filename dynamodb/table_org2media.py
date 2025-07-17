# table_org2media.py
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from utils import Utils
import config
from boto3.dynamodb.conditions import Attr


class TableOrg2Media:
    def __init__(self, query: DynamoQuery, table_config):
        self.query = query
        self.table_name, _ = list(table_config['o2m_config'].items())[0]

    def get_org_ids_by_media(self, media_id: str) -> list:
        results = self.query.scan_by_filter(
            table_name=self.table_name,
            filter_expression=Attr("media_id").eq(media_id)
        )
        return [item["org_id"] for item in results]

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

    org2media_table = TableOrg2Media(query=query)

    # Ví dụ sử dụng
    media_id = "media_id_1752377694323783"
    org_ids = org2media_table.get_org_ids_by_media(media_id)
    print(f"Org IDs associated with media '{media_id}': {org_ids}")
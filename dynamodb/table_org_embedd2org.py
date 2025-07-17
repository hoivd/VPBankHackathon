from dynamodb.dynamo_query import DynamoQuery
from utils import Utils
import config
from dynamodb.base_dynamo import BaseDynamoDB
from boto3.dynamodb.conditions import Attr
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class TableOrgEmbedd2Org:
    def __init__(self, query: DynamoQuery, table_config):
        self.query = query
        self.table_name, _ = list(table_config['org_embedd2org_config'].items())[0]

    def get_by_org_id(self, org_id: str):
        return self.query.get_item_by_key(
            table_name=self.table_name,
            key_dict={"org_id": org_id}
        )

    def get_embedd_by_org_id(self, org_id: str) -> list:
        results = self.query.scan_by_filter(
            table_name=self.table_name,
            filter_expression=Attr("org_id").eq(org_id)
        )
        logger.info(f"Found {len(results)} embeddings for org_id '{org_id}'")
        return [item["org_embedd_id"] for item in results]
    

    def get_embedd_by_org_id_list(self, org_ids: list[str]) -> list:
        all_embedds = []
        for org_id in org_ids:
            results = self.query.scan_by_filter(
                table_name=self.table_name,
                filter_expression=Attr("org_id").eq(org_id)
            )
            all_embedds.extend([item["org_embedd_id"] for item in results])
        return all_embedds

    
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

    personal2media_table = TableOrgEmbedd2Org(query=query, table_config=config.TABLE_CONFIG)

    # Ví dụ sử dụng
    org_ids = ["org_id_1752666855228966", "org_id_1752666855229713"]
    embedd_id = personal2media_table.get_embedd_by_org_id_list(org_ids)
    print(embedd_id)
from dynamodb.dynamo_query import DynamoQuery
from utils import Utils
import config
from dynamodb.base_dynamo import BaseDynamoDB
from boto3.dynamodb.conditions import Attr
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class TablePersonalEmbedd2Personal:
    def __init__(self, query: DynamoQuery, table_config):
        self.query = query
        self.table_name, _ = list(table_config['personal_embedd2per_config'].items())[0]

    def get_by_per_embedd_id(self, personal_embedd_id: str):
        return self.query.get_item_by_key(
            table_name=self.table_name,
            key_dict={"personal_embedd_id": personal_embedd_id}
        )

    def get_embedd_by_per_id(self, per_id: str) -> list:
        results = self.query.scan_by_filter(
            table_name=self.table_name,
            filter_expression=Attr("per_id").eq(per_id)
        )
        logger.info(f"Found {len(results)} embeddings for per_id '{per_id}'")
        return [item["personal_embedd_id"] for item in results]

    def get_embedd_by_per_id_list(self, per_ids: list[str]) -> list:
        all_embedds = []
        for per_id in per_ids:
            results = self.query.scan_by_filter(
                table_name=self.table_name,
                filter_expression=Attr("per_id").eq(per_id)
            )
            all_embedds.extend([item["personal_embedd_id"] for item in results])
        return all_embedds

    def map_embedd_ids_to_per_ids(self, embedd_ids: list[str]) -> dict[str, str]:
        """
        Trả về dict ánh xạ từ personal_embedd_id -> per_id

        :param embedd_ids: danh sách các personal_embedd_id
        :return: dict {personal_embedd_id: per_id}
        """
        mapping = {}
        for embedd_id in embedd_ids:
            item = self.get_by_per_embedd_id(embedd_id)
            if item and "per_id" in item:
                mapping[embedd_id] = item["per_id"]
            else:
                logger.warning(f"Không tìm thấy per_id cho personal_embedd_id: {embedd_id}")
        return mapping

    
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

    personal2media_table = TablePersonalEmbedd2Personal(query=query, table_config=config.TABLE_CONFIG)

    # # Ví dụ sử dụng
    # per_ids = ["per_id_1752666855224801", "per_id_1752666855225827", 'per_id_1752666855227701']
    # embedd_id = personal2media_table.get_embedd_by_per_id_list(per_ids)

    per_embed_ids = [100208, 100213]
    per_id_mapping = personal2media_table.map_embedd_ids_to_per_ids(per_embed_ids)
    print(per_id_mapping)
    # print(embedd_id)

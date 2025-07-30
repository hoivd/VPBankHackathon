from dynamodb.dynamo_query import DynamoQuery
from utils import Utils
import config
from dynamodb.base_dynamo import BaseDynamoDB
from boto3.dynamodb.conditions import Attr
# from logging import _setup_logging
import config
import logging
# logging = _setup_logging(__name__, config.LOG_LEVEL)

class TablePersonalRiskEmbedd2Personal:
    def __init__(self, query: DynamoQuery, table_config):
        self.query = query
        self.table_name, _ = list(table_config['personal_risk_embedd2per_config'].items())[0]

    def get_by_per_embedd_id(self, personal_embedd_id: str):
        return self.query.get_item_by_key(
            table_name=self.table_name,
            key_dict={"personal_risk_embedd_id": personal_embedd_id}
        )

    def get_embedd_by_per_id(self, per_id: str) -> list:
        results = self.query.scan_by_filter(
            table_name=self.table_name,
            filter_expression=Attr("per_id").eq(per_id)
        )
        logging.info(f"Found {len(results)} embeddings for per_id '{per_id}'")
        return [item["personal_risk_embedd_id"] for item in results]

    def get_embedd_by_per_id_list(self, per_ids: list[str]) -> list:
        all_embedds = []
        for per_id in per_ids:
            results = self.query.scan_by_filter(
                table_name=self.table_name,
                filter_expression=Attr("per_id").eq(per_id)
            )
            all_embedds.extend([item["personal_risk_embedd_id"] for item in results])
        return all_embedds

    def map_embedd_ids_to_per_ids(self, embedd_ids: list[str]) -> dict[str, str]:
        """
        Trả về dict ánh xạ từ personal_embedd_id -> per_id

        :param embedd_ids: danh sách các personal_embedd_id
        :return: dict {personal_embedd_id: per_id}
        """
        embedd_ids = [str(id) for id in embedd_ids]
        mapping = {}
        for embedd_id in embedd_ids:
            item = self.get_by_per_embedd_id(embedd_id)
            if item and "per_id" in item:
                mapping[embedd_id] = item["per_id"]
            else:
                logging.warning(f"Không tìm thấy per_id cho personal_embedd_id: {embedd_id}")
        return mapping
    
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

    personal_risk_embedd2media_table = TablePersonalRiskEmbedd2Personal(query=query, table_config=config.TABLE_CONFIG_DEMO)

    # # Ví dụ sử dụng
    # per_ids = ["per_id_1752666855224801", "per_id_1752666855225827", 'per_id_1752666855227701']
    # embedd_id = personal2media_table.get_embedd_by_per_id_list(per_ids)

    per_embed_ids = ["per_id_1753601865338008", "per_id_1753601865335117", "per_id_1753601865340027"]

    per_id_mapping = personal_risk_embedd2media_table.get_embedd_by_per_id_list(per_embed_ids)
    print(per_id_mapping)
    # print(embedd_id)

    
if __name__ == "__main__":
    main()

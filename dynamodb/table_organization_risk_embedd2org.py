from dynamodb.dynamo_query import DynamoQuery
from utils import Utils
import config
from dynamodb.base_dynamo import BaseDynamoDB
from boto3.dynamodb.conditions import Attr
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class TableOrgainzationRiskEmbedd2Orgainzation:
    def __init__(self, query: DynamoQuery, table_config):
        self.query = query
        self.table_name, _ = list(table_config['organization_risk_embedd2org_config'].items())[0]

    def get_by_org_embedd_id(self, orgainzation_embedd_id: str):
        return self.query.get_item_by_key(
            table_name=self.table_name,
            key_dict={"organization_risk_embedd_id": orgainzation_embedd_id}
        )

    def get_embedd_by_org_id(self, org_id: str) -> list:
        results = self.query.scan_by_filter(
            table_name=self.table_name,
            filter_expression=Attr("org_id").eq(org_id)
        )
        logger.info(f"Found {len(results)} embeddings for org_id '{org_id}'")
        return [item["orgainzation_risk_embedd_id"] for item in results]

    def get_embedd_by_org_id_list(self, org_ids: list[str]) -> list:
        all_embedds = []
        for org_id in org_ids:
            results = self.query.scan_by_filter(
                table_name=self.table_name,
                filter_expression=Attr("org_id").eq(org_id)
            )
            logger.debug(f"Found {results} embeddings for org_id '{org_id}'")
            all_embedds.extend([item["organization_risk_embedd_id"] for item in results])
        return all_embedds

    def map_embedd_ids_to_org_ids(self, embedd_ids: list[str]) -> dict[str, str]:
        """
        Trả về dict ánh xạ từ orgainzation_embedd_id -> org_id

        :param embedd_ids: danh sách các orgainzation_embedd_id
        :return: dict {orgainzation_embedd_id: org_id}
        """
        embedd_ids = [str(id) for id in embedd_ids]
        mapping = {}
        for embedd_id in embedd_ids:
            item = self.get_by_org_embedd_id(embedd_id)
            if item and "org_id" in item:
                mapping[embedd_id] = item["org_id"]
            else:
                logger.warning(f"Không tìm thấy org_id cho orgainzation_embedd_id: {embedd_id}")
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

    organization_risk_embedd2media_table = TableOrgainzationRiskEmbedd2Orgainzation(query=query, table_config=config.TABLE_CONFIG_DEMO)

    # # Ví dụ sử dụng
    # per_ids = ["per_id_1752666855224801", "per_id_1752666855225827", 'per_id_1752666855227701']
    # embedd_id = personal2media_table.get_embedd_by_per_id_list(per_ids)

    org_embed_ids = ["100001", "100000"]

    org_id_mapping = organization_risk_embedd2media_table.map_embedd_ids_to_org_ids(org_embed_ids)
    print(org_id_mapping)

    # print(embedd_id)

    
if __name__ == "__main__":
    main()

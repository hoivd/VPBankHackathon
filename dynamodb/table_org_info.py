from dynamodb.dynamo_query import DynamoQuery
from utils import Utils
import config
from dynamodb.base_dynamo import BaseDynamoDB

class TableOrganizationInfo:
    def __init__(self, query: DynamoQuery):
        self.query = query

    def get_by_org_id(self, org_id: str):
        return self.query.get_item_by_key(
            table_name="organization_info",
            key_dict={"org_id": org_id}
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

    org_info_table = TableOrganizationInfo(query=query)

    # Ví dụ sử dụng
    org_id = "org_id_1752354097255287"
    item = org_info_table.get_by_org_id(org_id)
    print(f"Item with org_id '{org_id}': {item}")
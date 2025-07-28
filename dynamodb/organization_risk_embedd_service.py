
from dynamodb.base_dynamo import BaseDynamoDB
from dynamodb.table_organization_risk_embedd2org import TableOrgainzationRiskEmbedd2Orgainzation
from dynamodb.table_org_info import TableOrganizationInfo
from dynamodb.table_org2media import TableOrg2Media
from utils import Utils
import config
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.table_org2media import TableOrg2Media
from dynamodb.table_org_info import TableOrganizationInfo
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class OrganizationRiskEmbeddService:
    def __init__(self,
                  organization_risk_embedd_org_linker: TableOrgainzationRiskEmbedd2Orgainzation,
                  org_info: TableOrganizationInfo,
                  org_media_linker: TableOrg2Media):
        self.organization_risk_embedd_org_linker = organization_risk_embedd_org_linker
        self.org_info = org_info
        self.org_media_linker = org_media_linker

    def get_organization_info_by_organization_risk_embedd_id(self, organization_risk_embedd_id: str):
        assert isinstance(organization_risk_embedd_id, str) == True, "organization_risk_embedd_id phai la str"
             
        result = self.organization_risk_embedd_org_linker.get_by_org_embedd_id(organization_risk_embedd_id)
        if result:
            org_id = result.get('org_id', None)
        else:
            logger.error(f"Khong tim thay organization_risk_embedd_id: {organization_risk_embedd_id}")

        organization_info = self.org_info.get_by_org_id(org_id) 

        return organization_info, org_id

    def get_org_media_info_by_organization_risk_embedd_id(self, organization_risk_embedd_id: str):
        organization_info, org_id = self.get_organization_info_by_organization_risk_embedd_id(organization_risk_embedd_id)
        violent_details = self.org_media_linker.get_items_by_org(org_id)
        
        if organization_info is None:
            logger.error(f"Khong tim thay thong tin org_id: {org_id} tu organization_risk_embedd_id: {organization_risk_embedd_id}")
            return None
        organization_info['violent_details'] = violent_details

        return organization_info
    
    def get_org_media_info_by_organization_risk_embedd_ids(self, organization_risk_embedd_ids: list[str]):
        organization_infos = []
        for embedding_id in organization_risk_embedd_ids:
            organization_info = self.get_org_media_info_by_organization_risk_embedd_id(embedding_id)
            organization_infos.append(organization_info)

        return organization_infos

def main():
    from utils import Utils
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )

    query = DynamoQuery(base_dynamo.dynamodb)

    orgainzation_risk_embedd_per_linker = TableOrgainzationRiskEmbedd2Orgainzation(query, table_config=config.TABLE_CONFIG_DEMO)
    org_info = TableOrganizationInfo(query, table_config=config.TABLE_CONFIG_DEMO)
    org_media_linker = TableOrg2Media(query, table_config=config.TABLE_CONFIG_DEMO)

    # ✅ Khởi tạo MediaService với tất cả các dependency
    organization_risk_embedd_service = OrganizationRiskEmbeddService(
        organization_risk_embedd_org_linker=orgainzation_risk_embedd_per_linker,
        org_info=org_info,
        org_media_linker=org_media_linker
    )

    embedding_id = ['100000', '100001']

    # ✅ Gọi hàm không cần truyền thêm đối tượng
    organization_info = organization_risk_embedd_service.get_org_media_info_by_organization_risk_embedd_ids(embedding_id)

    print(Utils.json_to_str(organization_info))

if __name__ == "__main__":
    main()
from dynamodb.table_personal2media import TablePersonal2Media
from dynamodb.table_personal_info import TablePersonalInfo
from dynamodb.base_dynamo import BaseDynamoDB
from dynamodb.table_personal_risk_embedd2per import TablePersonalRiskEmbedd2Personal
from utils import Utils
import config
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.table_org2media import TableOrg2Media
from dynamodb.table_org_info import TableOrganizationInfo
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class PersonalRiskEmbeddService:
    def __init__(self, personal_risk_embedd_per_linker, per_info, per_media_linker):
        self.personal_risk_embedd_per_linker = personal_risk_embedd_per_linker
        self.per_info = per_info
        self.per_media_linker = per_media_linker

    def get_personal_info_by_personal_risk_embedd_id(self, personal_risk_embedd_id: str):
        assert isinstance(personal_risk_embedd_id, str) == True, "personal_risk_embedd_id phai la str"
             
        result = self.personal_risk_embedd_per_linker.get_by_per_embedd_id(personal_risk_embedd_id)

        if result is None:
            logger.error(f"Khong tim thay personal_risk_embedd_id: {personal_risk_embedd_id}")
            return None, None
        
        per_id = result.get('per_id', None)

        personal_info = self.per_info.get_by_per_id(per_id) 

        return personal_info, per_id

    def get_per_media_info_by_personal_risk_embedd_id(self, personal_risk_embedd_id: str):
        personal_info, per_id = self.get_personal_info_by_personal_risk_embedd_id(personal_risk_embedd_id)

        if personal_info is None:
            return None

        violent_details = self.per_media_linker.get_items_by_person(per_id)

        personal_info['violent_details'] = violent_details

        return personal_info
    
    def get_per_media_info_by_personal_risk_embedd_ids(self, personal_risk_embedd_ids: list[str]):
        personal_infos = []
        for embedding_id in personal_risk_embedd_ids:
            personal_info = self.get_per_media_info_by_personal_risk_embedd_id(embedding_id)
            personal_infos.append(personal_info)

        return personal_infos


if __name__ == "__main__":
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

    personal_risk_embedd_per_linker = TablePersonalRiskEmbedd2Personal(query, table_config=config.TABLE_CONFIG_DEMO)
    per_info = TablePersonalInfo(query, table_config=config.TABLE_CONFIG_DEMO)
    per_media_linker = TablePersonal2Media(query, table_config=config.TABLE_CONFIG_DEMO)

    # ✅ Khởi tạo MediaService với tất cả các dependency
    personal_risk_embedd_service = PersonalRiskEmbeddService(
        personal_risk_embedd_per_linker=personal_risk_embedd_per_linker,
        per_info=per_info,
        per_media_linker=per_media_linker
    )

    embedding_id = ['100004', '100001']

    # ✅ Gọi hàm không cần truyền thêm đối tượng
    personal_info = personal_risk_embedd_service.get_per_media_info_by_personal_risk_embedd_ids(embedding_id)

    print(Utils.json_to_str(personal_info))
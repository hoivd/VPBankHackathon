from dynamodb.table_personal2media import TablePersonal2Media
from dynamodb.table_personal_info import TablePersonalInfo
from dynamodb.base_dynamo import BaseDynamoDB
from utils import Utils
import config
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.table_org2media import TableOrg2Media
from dynamodb.table_org_info import TableOrganizationInfo

class MediaService:
    def __init__(self, per_linker, per_info, org_linker, org_info):
        self.per_linker = per_linker
        self.per_info = per_info
        self.org_linker = org_linker
        self.org_info = org_info

    def get_personal_info_by_media(self, media_id: str):
        per_ids = self.per_linker.get_person_ids_by_media(media_id)
        personal_infos = []

        for per_id in per_ids:
            data = self.per_info.get_by_per_id(per_id)
            if data:
                personal_infos.append(data)
        return personal_infos

    def get_org_info_by_media(self, media_id: str):
        org_ids = self.org_linker.get_org_ids_by_media(media_id)
        org_infos = []

        for org_id in org_ids:
            data = self.org_info.get_by_org_id(org_id)
            if data:
                org_infos.append(data)
        return org_infos

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

    personal_linker = TablePersonal2Media(query)
    personal_info = TablePersonalInfo(query)
    org_linker = TableOrg2Media(query)
    org_info = TableOrganizationInfo(query)

    # ✅ Khởi tạo MediaService với tất cả các dependency
    media_service = MediaService(
        per_linker=personal_linker,
        per_info=personal_info,
        org_linker=org_linker,
        org_info=org_info
    )

    media_id = "media_id_1752383993651068"

    # ✅ Gọi hàm không cần truyền thêm đối tượng
    personals_info = media_service.get_personal_info_by_media(media_id)
    orgs_info = media_service.get_org_info_by_media(media_id)

    for item in personals_info:
        print(item)

    for item in orgs_info:
        print(item)
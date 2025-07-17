from dynamodb.dynamo_query import DynamoQuery
from utils import Utils
from dynamodb.base_dynamo import BaseDynamoDB
import config
import json

class TableAdverseMedia:
    def __init__(self, query: DynamoQuery):
        self.query = query
        self.table_name = "adverse_media"

    def get_all_media_ids(self) -> list[str]:
        """
        Scan toàn bộ bảng adverse_media và trả về danh sách media_id.
        """
        try:
            items = self.query.scan_all(self.table_name)
            return [item["media_id"] for item in items if "media_id" in item]
        except Exception as e:
            print(f"❌ Lỗi khi lấy media_id: {str(e)}")
            return []

    def get_document_by_media_id(self, media_id: str) -> dict:
        """
        Truy xuất một document từ bảng adverse_media dựa vào media_id.
        """
        try:
            items = self.query.query_by_key(
                table_name=self.table_name,
                key_name="media_id",
                key_value=media_id
            )
            return items[0] if items else {}
        except Exception as e:
            print(f"❌ Lỗi khi lấy document theo media_id: {str(e)}")
            return {}

if __name__ == "__main__":
    AWS_ACCESS_KEY='AKIAQWLOPNIDXAC4BJWD'
    AWS_SECRET_KEY='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'
    REGION = config.AWS_REGION

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )

    query = DynamoQuery(base_dynamo.dynamodb)
    table_adverse_media = TableAdverseMedia(query)

    media_ids = table_adverse_media.get_all_media_ids()
    for mid in media_ids:
        print(mid)
        document = table_adverse_media.get_document_by_media_id(mid)
        print(json.dumps(document, ensure_ascii=False, indent=2, default=str))
import time
import copy
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from logger import _setup_logger
import config
from mongodb.mongo_pusher import MongoPusher
from utils import Utils
from blacklist_builder.article_extractor import ArticlePersonExtractor
from dynamodb.dynamo_pusher import DynamoPusher

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleRiskProcessor:
    def __init__(self, gemini_extractor, dynamo_pusher):
        """
        :param gemini_extractor: công cụ trích xuất từ Gemini API
        :param dynamo_pusher: đối tượng DynamoPusher (bắt buộc)
        """
        self.extractor = gemini_extractor
        self.dynamo_pusher = dynamo_pusher

    def extract_json_blocks(self, raw_text: str):
        json_blocks = re.findall(r"```json\s*\n(.*?)```", raw_text, re.DOTALL)
        if len(json_blocks) >= 1:
            try:
                resp = json.loads(json_blocks[0])
                personal_info_json = resp[0]
                risk_info_json = resp[1]
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON decode error: {e}")
        else:
            raise ValueError("Không tìm thấy đủ hai khối JSON.")
        return personal_info_json, risk_info_json

    def assign_unix_ids(
        self,
        risk_json: dict,
        personal_json: list[dict],
        article_text: str,
        person_id_key: str = "per_id",
        media_id_key: str = "media_id"
    ):
        unix_id = int(time.time() * 1000)
        customer2media = risk_json.get("list_customer", [])
        customer2media_copy = copy.deepcopy(customer2media)
        adverse_media = {k: v for k, v in risk_json.items() if k != "list_customer"}
        adverse_media[media_id_key] = f"media_{unix_id}"
        adverse_media["context"] = article_text

        personal_id_to_custom_id = {}
        for item in customer2media_copy:
            per_id = int(time.time() * 1000)
            item[media_id_key] = adverse_media[media_id_key]
            item[person_id_key] = f"user_{per_id}"
            personal_id_to_custom_id[item["personal_id"]] = f"user_{per_id}"
            item.pop("personal_id", None)
            time.sleep(0.001)

        updated_personal = []
        for person in personal_json:
            person_copy = copy.deepcopy(person)
            pid = person_copy["personal_id"]
            if pid in personal_id_to_custom_id:
                person_copy[person_id_key] = personal_id_to_custom_id[pid]
                person_copy.pop("personal_id", None)
            updated_personal.append(person_copy)

        return adverse_media, customer2media_copy, updated_personal

    def process_article(self, article_text: str,
                    table_person_config: dict,
                    table_c2m_config: dict,
                    table_media_config: dict):
        logger.info("🧠 Gọi Gemini để trích xuất bài báo...")
        raw_response = self.extractor.extract_from_article(article_text)

        logger.debug(f"[process_article] Raw response:\n{raw_response}")
        logger.info("📦 Đang xử lý kết quả trích xuất...")

        personal_json, risk_json = self.extract_json_blocks(raw_response)

        adverse_media, customer2media, updated_personal = self.assign_unix_ids(
            risk_json, personal_json, article_text
        )

        logger.debug(f"[process_article] Adverse media: {adverse_media}")
        logger.debug(f"[process_article] Customer to media: {customer2media}")
        logger.debug(f"[process_article] Updated personal info: {updated_personal}")

        logger.info("📝 Đang lưu vào DynamoDB...")

        self.dynamo_pusher.insert(updated_personal, table_config=table_person_config)
        self.dynamo_pusher.insert(customer2media, table_config=table_c2m_config)
        self.dynamo_pusher.insert(adverse_media, table_config=table_media_config)

        logger.info("✅ Xử lý bài báo hoàn tất.")

if __name__ == "__main__":
    # Cấu hình tết nối Gemini API
    gemini_api = Utils.load_api_key_from_env("GEMINI_API_KEY")
    logger.info(f'''Đã tải API key từ biến môi trường: 
                    - Gemini API: {gemini_api}''')
    
    REGION = config.AWS_REGION

    # Khởi tạo và insert
    dynamo_pusher = DynamoPusher(region_name=REGION)
    extractor = ArticlePersonExtractor(api_key=gemini_api)

    processor = ArticleRiskProcessor(
        gemini_extractor=extractor,
        dynamo_pusher=dynamo_pusher
    )

    content_path = 'data/contents_old.json'
    contents_json = Utils.load_json(content_path)
    logger.info(f"Đã load {len(contents_json)} bài báo từ file {content_path}")

    content_30 = contents_json[33]

    table_person_config={"personal_info": "per_id"}
    table_c2m_config={"personal2media": "p2m_id"}
    table_media_config={"adverse_media": "media_id"}

    processor.process_article(
        article_text=content_30,
        table_person_config=table_person_config,
        table_c2m_config=table_c2m_config,
        table_media_config=table_media_config
    )

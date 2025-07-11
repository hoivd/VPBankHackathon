import time
import copy
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from logger import _setup_logger
import config
from mongo_pusher import MongoPusher
from utils import Utils
from article_extractor import ArticlePersonExtractor

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleRiskProcessor:
    def __init__(self, gemini_extractor, mongo_pusher: MongoPusher):
        self.extractor = gemini_extractor
        self.mongo_pusher = mongo_pusher

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

    def assign_unix_ids(self, risk_json: dict, personal_json: list[dict]):
        unix_id = int(time.time() * 1000)
        customer2media = risk_json.get("list_customer", [])
        customer2media_copy = copy.deepcopy(customer2media)
        adverse_media = {k: v for k, v in risk_json.items() if k != "list_customer"}
        adverse_media["unix_id"] = f"media_{unix_id}"

        personal_id_to_per_unix = {}
        for item in customer2media_copy:
            per_unix_id = int(time.time() * 1000)
            item['media_unix_id'] = adverse_media["unix_id"]
            item["per_unix_id"] = f"user_{per_unix_id}"
            personal_id_to_per_unix[item["personal_id"]] = f"user_{per_unix_id}"
            item.pop("personal_id", None)
            time.sleep(0.001)

        updated_personal = []
        for person in personal_json:
            person_copy = copy.deepcopy(person)
            pid = person_copy["personal_id"]
            if pid in personal_id_to_per_unix:
                person_copy["unix_id"] = personal_id_to_per_unix[pid]
                person_copy.pop("personal_id", None)
            updated_personal.append(person_copy)

        return adverse_media, customer2media_copy, updated_personal

    def process_article(self, article_text: str, col_person: str, col_c2m: str, col_media: str):
        logger.info("🧠 Gọi Gemini để trích xuất bài báo...")
        raw_response = self.extractor.extract_from_article(article_text)

        logger.debug(f"[process_article] Raw response:\n{raw_response}")
        logger.info("📦 Đang xử lý kết quả trích xuất...")

        personal_json, risk_json = self.extract_json_blocks(raw_response)
        adverse_media, customer2media, updated_personal = self.assign_unix_ids(risk_json, personal_json)

        logger.info("📝 Đang lưu vào MongoDB...")
        self.mongo_pusher.insert(col_person, updated_personal)
        self.mongo_pusher.insert(col_c2m, customer2media)
        self.mongo_pusher.insert(col_media, adverse_media)

        logger.info("✅ Xử lý bài báo hoàn tất.")

if __name__ == "__main__":
    mongo_uri = Utils.load_api_key_from_env("MONGO_URI")
    gemini_api = Utils.load_api_key_from_env("GEMINI_API_KEY")
    logger.info(f'''Đã tải API key từ biến môi trường: 
                    - Gemini API: {gemini_api}
                    - Mongo URI: {mongo_uri}''')

    db_name = 'blacklist'
    customer_collection = 'customer_info'
    cust2media_collection = 'customer2media'
    media_collection = 'adverse_media'

    extractor = ArticlePersonExtractor(api_key=gemini_api)
    mongo_pusher = MongoPusher(mongo_uri=mongo_uri, db_name=db_name)

    processor = ArticleRiskProcessor(
        gemini_extractor=extractor,
        mongo_pusher=mongo_pusher
    )

    content_path = 'data/contents_old.json'
    contents_json = Utils.load_json(content_path)
    logger.info(f"Đã load {len(contents_json)} bài báo từ file {content_path}")

    content_30 = contents_json[33]

    processor.process_article(
        article_text=content_30,
        col_person=customer_collection,
        col_c2m=cust2media_collection,
        col_media=media_collection
    )

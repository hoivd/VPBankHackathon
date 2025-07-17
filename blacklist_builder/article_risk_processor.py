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
from llm_model.bedrock_manager import BedrockModelManager
from dynamodb.base_dynamo import BaseDynamoDB

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleRiskProcessor:
    def __init__(self, info_extractor, base_dynamo):
        """
        :param gemini_extractor: công cụ trích xuất từ Gemini API
        :param dynamo_pusher: đối tượng DynamoPusher (bắt buộc)
        """
        self.extractor = info_extractor
        self.base_dynamo = base_dynamo
        self.dynamo_pusher = DynamoPusher(dynamodb=self.base_dynamo)

    def extract_json_blocks(self, raw_text: str):
        json_blocks = json.loads(raw_text)
        if len(json_blocks) == 3:
            try:
                personal_info_json = json_blocks[0]
                org_info_json = json_blocks[1]
                risk_info_json = json_blocks[2]
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON decode error: {e}")
        else:
            raise ValueError("Không tìm thấy đủ ba khối.")
        return personal_info_json, org_info_json, risk_info_json

    def create_adverse_media_item(self, risk_info: dict, partition_key: str, context: str): 
        risk_info_copy = copy.deepcopy(risk_info)

        unix_time = Utils.get_current_unix_time()
        item = {k: v for k, v in risk_info_copy.items() if k not in ["list_personal_risks", "list_organizer_risks"]}  
        item[partition_key] = partition_key + "_" + str(unix_time)
        item['content'] = context
        item["created_at"] = unix_time

        return item

    def create_personal_items(self, person_info: dict, partition_key: str):
        person_info_copy = copy.deepcopy(person_info)

        batch_unix_time = Utils.get_current_unix_time()
        per_id_gen_to_per_id = {}
        for item in person_info_copy:
            unix_time = Utils.get_current_unix_time()
            item[partition_key] = partition_key + "_" + str(unix_time)
            item["created_at"] = batch_unix_time
            
            per_id_gen_to_per_id[item["personal_id"]] = item[partition_key]
            item.pop("personal_id", None)

        return person_info_copy, per_id_gen_to_per_id

    def create_organization_items(self, org_info: dict, partition_key: str):
        org_info_copy = copy.deepcopy(org_info)

        batch_unix_time = Utils.get_current_unix_time()
        org_id_gen_to_per_id = {}
        for item in org_info_copy:
            unix_time = Utils.get_current_unix_time()
            item[partition_key] = partition_key + "_" + str(unix_time)
            item["created_at"] = batch_unix_time
            
            org_id_gen_to_per_id[item["organizer_id"]] = item[partition_key]
            item.pop("organizer_id", None)

        return org_info_copy, org_id_gen_to_per_id

    def create_personal2media_items(self, risk_info: dict, partition_key: str, per_id_gen_to_per_id: dict, media_id: str ):
        risk_info_copy = copy.deepcopy(risk_info)

        personal2media = risk_info_copy.get("list_personal_risks", [])
        personal2media_copy = copy.deepcopy(personal2media)

        batch_unix_time = Utils.get_current_unix_time()

        for item in personal2media_copy:
            item[partition_key] = partition_key + "_" + str(Utils.get_current_unix_time())
            item["media_id"] = media_id
            item["created_at"] = batch_unix_time
            item["per_id"] = per_id_gen_to_per_id.get(item["entity_id"], None)
            item.pop("entity_id", None)

        return personal2media_copy

    def create_org2media_items(self, risk_info: dict, partition_key: str, org_id_gen_to_per_id: dict, media_id: str ):
        risk_info_copy = copy.deepcopy(risk_info)

        organizer2media = risk_info_copy.get("list_organizer_risks", [])
        organizer2media_copy = copy.deepcopy(organizer2media)

        batch_unix_time = Utils.get_current_unix_time()
        for item in organizer2media_copy:
            item[partition_key] = partition_key + "_" + str(Utils.get_current_unix_time())
            item["media_id"] = media_id
            item["created_at"] = batch_unix_time
            item["org_id"] = org_id_gen_to_per_id.get(item["entity_id"], None)
            item.pop("entity_id", None)

        return organizer2media_copy

    def create_items_from_response(self, raw_text:str, article_text: str, partition_key: dict):
        personal_info_json, org_info_json, risk_info_json = self.extract_json_blocks(raw_text)
        adverse_media_item = self.create_adverse_media_item(risk_info_json, partition_key['media_config'], article_text)
        personal_info_items, per_id_gen_to_per_id = self.create_personal_items(personal_info_json, partition_key['person_config'])
        organization_info_items, org_id_gen_to_per_id = self.create_organization_items(org_info_json, partition_key['organization_config'])
        personal2media_items = self.create_personal2media_items(risk_info_json, partition_key['p2m_config'], per_id_gen_to_per_id, adverse_media_item['media_id'])
        org2media_items = self.create_org2media_items(risk_info_json, partition_key['o2m_config'], org_id_gen_to_per_id, adverse_media_item['media_id'])
        return {
            "adverse_media_item": adverse_media_item,
            "organization_info_items": organization_info_items,
            "personal_info_items": personal_info_items,
            "org2media_items": org2media_items,
            "personal2media_items": personal2media_items,
        }

    

    def extract_info_from_article(self, article_text: str, table_config: dict):
        logger.info("🧠 Gọi LLM để trích xuất bài báo...")
        answer, thinking = self.extractor.extract_from_article(article_text)

        logger.debug(f"[process_article] Raw response:\n{answer}")
        logger.info("📦 Đang xử lý kết quả trích xuất...")
        
        partition_key = {outer_key: list(inner_dict.values())[0] for outer_key, inner_dict in table_config.items()}
        logger.debug(f"[process_article] Partition keys: {partition_key}")

        items = self.create_items_from_response(answer, article_text, partition_key)
        logger.debug(f"[process_article] Adverse media: {items['adverse_media_item']}")
        logger.debug(f"[process_article] Personal info: {Utils.json_to_str(items['personal_info_items'])}")
        logger.debug(f"[process_article] Organization info: {Utils.json_to_str(items['organization_info_items'])}")
        logger.debug(f"[process_article] Personal to media: {Utils.json_to_str(items['personal2media_items'])}")
        logger.debug(f"[process_article] Org to media: {Utils.json_to_str(items['org2media_items'])}")

        logger.debug(f"Tim thay {len(items['personal_info_items'])} personal info")
        logger.debug(f"Tim thay {len(items['organization_info_items'])} organization info")
        logger.debug(f"Tim thay {len(items['personal2media_items'])} personal to media")
        logger.debug(f"Tim thay {len(items['org2media_items'])} org to media")

        return items
    
    def push_to_dynamodb(self, items: dict, table_config: dict):
        logger.info("📝 Đang lưu vào DynamoDB...")

        self.dynamo_pusher.insert(items['adverse_media_item'], table_config=table_config['media_config'])
        self.dynamo_pusher.insert(items['organization_info_items'], table_config=table_config['organization_config'])
        self.dynamo_pusher.insert(items['personal_info_items'], table_config=table_config['person_config'])
        self.dynamo_pusher.insert(items['org2media_items'], table_config=table_config['o2m_config'])
        self.dynamo_pusher.insert(items['personal2media_items'], table_config=table_config['p2m_config'])


        logger.info("✅ Xử lý bài báo hoàn tất.")
        

    def process_article(self, article_text: str,
                    table_config: dict):
        items = self.extract_info_from_article(article_text, table_config)
        self.push_to_dynamodb(items, table_config)

if __name__ == "__main__":

    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION

    # Khởi tạo và insert
    dynamo_pusher = DynamoPusher(access_key=AWS_ACCESS_KEY, 
                          secret_key=AWS_SECRET_KEY,                      
                          region_name=REGION)
    
    MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    # Khởi tạo manager
    bedrock_manager = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION,
        default_model_id=MODEL_ID
    )

    extractor_prompt_file = config.PROMPT_EXTRACTOR_FILE
    extractor_prompt = Utils.load_text(extractor_prompt_file)
    logger.info(f"Đã tải prompt từ {extractor_prompt_file}")

    extractor = ArticlePersonExtractor(model_manager=bedrock_manager, prompt_template=extractor_prompt)
    logger.info("Đã khởi tạo ArticlePersonExtractor")

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )

    processor = ArticleRiskProcessor(
        info_extractor=extractor,
        base_dynamo=base_dynamo.dynamodb
    )

    context_file = 'data/contents_old.json'
    bucket_name = "team253vpbank"
    key = "adverse_media_data/case1.json"

    contents = Utils.fetch_json_from_s3(bucket_name, key)
    logger.info(f"Đã load {len(contents)} bài báo từ file {context_file}")

    content = contents[0]

    table_config = {
        'media_config': {"adverse_media": "media_id"},
        'person_config': {"personal_info": "per_id"},
        'organization_config': {"organization_info": "org_id"},
        'p2m_config':{"personal2media": "p2m_id"},
        'o2m_config': {"org2media": "o2m_id"}
    }
    table_media_config={"adverse_media": "media_id"}
    table_person_config={"personal_info": "per_id"}
    table_organization_config={"organization_info": "org_id"}
    table_p2m_config={"personal2media": "p2m_id"}
    table_o2m_config={"org2media": "o2m_id"}

    processor.process_article(
        article_text=content,
        table_config=table_config
    )
        

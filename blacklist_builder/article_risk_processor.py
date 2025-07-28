from logger import _setup_logger
import config
from utils import Utils
from blacklist_builder.article_extractor import ArticlePersonExtractor
from dynamodb.dynamo_pusher import DynamoPusher
from llm_model.bedrock_manager import BedrockModelManager
from dynamodb.base_dynamo import BaseDynamoDB
from blacklist_builder.builder.new_item_builder import NewItemBuilder
from blacklist_builder.builder.rebuild_item_builder import RebuildItemBuilder
from faiss_manager.faiss_index_manager import FaissIndexManager
from embedder.bedrock_base import BedrockBaseClient
from embedder.cohere_embedder import CohereMultilingualEmbedder
from blacklist_builder.faiss_handler.faiss_personal_and_risk_handler import PersonalAndRiskHandler
from blacklist_builder.faiss_handler.faiss_organization_and_risk_handler import OrganizationAndRiskHandler
import numpy as np
import os
import json

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleRiskProcessor:
    def __init__(self, 
                 info_extractor, 
                 base_dynamo, 
                 personal_and_risk_handler: PersonalAndRiskHandler,
                 organization_and_risk_handler: OrganizationAndRiskHandler):
        """
        :param gemini_extractor: công cụ trích xuất từ Gemini API
        :param dynamo_pusher: đối tượng DynamoPusher (bắt buộc)
        """
        self.extractor = info_extractor
        self.base_dynamo = base_dynamo
        self.dynamo_pusher = DynamoPusher(dynamodb=self.base_dynamo)

        self.new_item_builder = NewItemBuilder
        self.rebuild_item_builder = RebuildItemBuilder

        # self.article_faiss_manager = article_faiss_manager
        # self.personal_faiss_manager = personal_faiss_manager
        # self.org_faiss_manager = org_faiss_manager

        # self.article_embedder = article_embedder
        # self.personal_embedder = personal_embedder
        # self.org_embedder =  org_embedder

        self.personal_and_risk_handler = personal_and_risk_handler
        self.organization_and_risk_handler = organization_and_risk_handler

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

    def create_items_from_response(self, raw_text:str, article_text: str, partition_key: dict):
        personal_info_json, org_info_json, risk_info_json = self.extract_json_blocks(raw_text)
        adverse_media_item, media_id = self.new_item_builder.create_adverse_media_item(risk_info_json, partition_key['media_config'], article_text)
        personal_info_items, per_id_gen_to_per_id = self.new_item_builder.create_personal_items(personal_info_json, partition_key['person_config'])
        organization_info_items, org_id_gen_to_per_id = self.new_item_builder.create_organization_items(org_info_json, partition_key['organization_config'])
        personal2media_items = self.new_item_builder.create_personal2media_items(risk_info_json, partition_key['p2m_config'], per_id_gen_to_per_id, media_id)
        org2media_items = self.new_item_builder.create_org2media_items(risk_info_json, partition_key['o2m_config'], org_id_gen_to_per_id, adverse_media_item['media_id'])
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
        self.dynamo_pusher.insert(items['personal_risk_embedd2per_items'], table_config=table_config['personal_risk_embedd2per_config'])
        self.dynamo_pusher.insert(items['organization_risk_embedd2org_items'], table_config=table_config['organization_risk_embedd2org_config'])
        # self.dynamo_pusher.insert(items['article_embedd2media_item'], table_config=table_config['article_embedd2media_config'])
        # self.dynamo_pusher.insert(items['personal_embedd2per_items'], table_config=table_config['personal_embedd2per_config'])
        # self.dynamo_pusher.insert(items['org_embedd2org_items'], table_config=table_config['org_embedd2org_config'])
        logger.info("✅ Xử lý bài báo hoàn tất.")

    # def embed_article_and_add_to_faiss(self, article_text: str, table_config: dict): 
    #     article_embedding = self.article_embedder.embed_article(article_text) 
    #     logger.debug(f"[embed_article_and_add_to_faiss] Article embedding: {article_embedding[0, :10]}")

    #     article_embedding_id = self.article_faiss_manager.add(article_embedding)
    #     logger.info(f"✅ Đã thêm embedding của bài báo vào FAISS với ID: {article_embedding_id}")
    #     return str(article_embedding_id[0])

    # def create_article_embedd2media_item(self, media_id: str, article_embedding_id: int, table_config: dict):
    #     _, partition_key = list(table_config['article_embedd2media_config'].items())[0]
    #     logger.debug(f"[create_article_embedding2media_item] Tạo item cho media_id: {media_id}, article_embedding_id: {article_embedding_id}")
    #     item = {
    #         "media_id": media_id,
    #         partition_key: article_embedding_id
    #     }
    #     return item
    
    # def embed_peronsal_org_embedd2media_and_add_to_faiss(self, personal_info_items: list[dict], organization_info_items: list[dict], table_config: dict):
    #     personal_info_items_str = [Utils.json_to_str(item) for item in personal_info_items]
    #     org_info_items_str = [Utils.json_to_str(item) for item in organization_info_items]

    #     logger.info("🧠 Đang encode cá nhân và tổ chức...")
    #     personal_embeddings = self.personal_embedder.embed_personal(personal_info_items_str)
    #     org_embeddings = self.org_embedder.embed_organization(org_info_items_str)
    #     logger.debug(f"[embed_personal_org_embedd2media] Personal embeddings: {personal_embeddings[0, :10]} {len(personal_embeddings)} items")
    #     logger.debug(f"[embed_personal_org_embedd2media] Organization embeddings: {org_embeddings[0, :10]} {len(org_embeddings)} items")
    #     logger.info("✅ Đã encode cá nhân và tổ chức xong.")

    #     personal_embedding_ids = self.personal_faiss_manager.add(personal_embeddings)
    #     org_embedding_ids = self.org_faiss_manager.add(org_embeddings)

    #     personal_embedding_ids = [str(id) for id in personal_embedding_ids]
    #     org_embedding_ids = [str(id) for id in org_embedding_ids]
    #     logger.info(f"✅ Đã thêm embedding cá nhân vào FAISS với IDs: {personal_embedding_ids}")
    #     logger.info(f"✅ Đã thêm embedding tổ chức vào FAISS với IDs: {org_embedding_ids}")

    #     return personal_embedding_ids, org_embedding_ids

    # def create_personal_embedd2media_items(self, personal_info_items: list[dict], personal_embedding_ids: list[int], table_config: dict):
    #     _, personal_embedd_partition_key = list(table_config['personal_embedd2per_config'].items())[0]
    #     _, personal_partition_key = list(table_config['person_config'].items())[0]
    #     logger.debug(f"[create_personal_embedd2media_items] Tạo item cho {len(personal_info_items)} cá nhân")
    #     def create_item(item: dict, embedding_id: int):
    #         item = {
    #             personal_embedd_partition_key: embedding_id,
    #             personal_partition_key: item[personal_partition_key]
    #         }
    #         return item

    #     personal_embedd2media_items = [create_item(item, embedding_id) for item, embedding_id in zip(personal_info_items, personal_embedding_ids)]
    #     logger.debug(f"[create_personal_embedd2media_items] Đã tạo {len(personal_embedd2media_items)} items cá nhân")
    #     return personal_embedd2media_items

    # def create_org_embedd2media_items(self, organization_info_items: list[dict], org_embedding_ids: list[int], table_config: dict):
    #     _, org_embedd_partition_key = list(table_config['org_embedd2org_config'].items())[0]
    #     _, org_partition_key = list(table_config['organization_config'].items())[0]
    #     logger.debug(f"[create_org_embedd2media_items] Tạo item cho {len(organization_info_items)} tổ chức")    

    #     def create_item(item: dict, embedding_id: int):
    #         item = {
    #             org_embedd_partition_key: embedding_id,
    #             org_partition_key: item[org_partition_key]
    #         }
    #         return item    

    #     org_embedd2media_items = [create_item(item, embedding_id) for item, embedding_id in zip(organization_info_items, org_embedding_ids)]
    #     logger.debug(f"[create_org_embedd2media_items] Đã tạo {len(org_embedd2media_items)} items tổ chức")
    #     return org_embedd2media_items            

    def handle_faiss_personal_risk_items(self, personal_info_items: list[dict], personal2media_items: list[dict], table_config: dict):
        personal_risk_embedding_ids, per_ids = self.personal_and_risk_handler.embed_and_index(
            personal_info_items=personal_info_items,
            personal2media_items=personal2media_items
        )

        personal_risk_embedding_ids = [str(id) for id in personal_risk_embedding_ids]
        per_ids = [str(id) for id in per_ids]

        personal_risk_embedd2per_items = self.new_item_builder.create_personal_risk_embedd2per(
            per_ids=per_ids,
            personal_risk_embedding_ids=personal_risk_embedding_ids,
            table_config=table_config
        ) 

        return personal_risk_embedd2per_items

    def handle_faiss_organization_risk_items(self, organization_info_items: list[dict], organization2media_items: list[dict], table_config: dict):
        organization_risk_embedding_ids, org_ids = self.organization_and_risk_handler.embed_and_index(
            organization_info_items=organization_info_items,
            organization2media_items=organization2media_items
        )

        organization_risk_embedding_ids = [str(id) for id in organization_risk_embedding_ids]
        org_ids = [str(id) for id in org_ids]

        organization_risk_embedd2org_items = self.new_item_builder.create_organization_risk_embedd2org(
            org_ids=org_ids,
            organization_risk_embedding_ids=organization_risk_embedding_ids,
            table_config=table_config
        ) 

        return organization_risk_embedd2org_items

    def prepare_items_from_info_extracted(self,
                                          items: dict,
                                          table_config: dict):
        personal_info_items = items['personal_info_items']
        personal2media_items = items['personal2media_items']

        items['personal_risk_embedd2per_items'] = self.handle_faiss_personal_risk_items(
            personal_info_items=personal_info_items,
            personal2media_items=personal2media_items,
            table_config=table_config
        )       
        
        organization_info_items = items['organization_info_items']
        org2media_items = items['org2media_items']

        items['organization_risk_embedd2org_items'] = self.handle_faiss_organization_risk_items(
            organization_info_items=organization_info_items,
            organization2media_items=org2media_items,
            table_config=table_config
        )

        return items


    def process_article(self, article_text: str,
                    table_config: dict):
        # Extract info from article
        items = self.extract_info_from_article(article_text, table_config)
        
        items = self.prepare_items_from_info_extracted(items, table_config)

        self.push_to_dynamodb(items, table_config)

def main():
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION_MODEL = config.AWS_VIRGINA_REGION
    REGION = config.AWS_REGION

    # Khởi 
    MODEL_ID = config.DEEPSEEK_MODEL_VIRGINA_ID

    # Khởi tạo manager
    bedrock_manager = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION_MODEL,
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

    bedrock_base = BedrockBaseClient(
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY,
        region_name=REGION_MODEL
    )

    # Khởi tạo Cohere embedder
    embedder = CohereMultilingualEmbedder(bedrock_client=bedrock_base.get_client())
    personal_faiss_manager = FaissIndexManager(1024)
    organization_faiss_manager = FaissIndexManager(1024)
    
    personal_risk_handler = PersonalAndRiskHandler(embedder=embedder, faiss_manager=personal_faiss_manager)
    organization_risk_handler = OrganizationAndRiskHandler(embedder=embedder, faiss_manager=organization_faiss_manager)

    processor = ArticleRiskProcessor(
        info_extractor=extractor,
        base_dynamo=base_dynamo.dynamodb,
        personal_and_risk_handler=personal_risk_handler,
        organization_and_risk_handler=organization_risk_handler
    )

    context_file = 'data/contents_old.json'
    bucket_name = "team253vpbank"
    key = "adverse_media_data/case1.json"

    contents = Utils.fetch_json_from_s3(bucket=bucket_name, 
                                        key=key,
                                        aws_access_key=AWS_ACCESS_KEY,
                                        aws_secret_key=AWS_SECRET_KEY,
                                        region_name=REGION)
    logger.info(f"Đã load {len(contents)} bài báo từ file {context_file}")

    content = contents[1]

    table_config = config.TABLE_CONFIG_DEMO

    processor.process_article(
        article_text=content,
        table_config=table_config,
    )
    
    faiss_index_path = 'data/faiss_indexs'
    os.makedirs(faiss_index_path, exist_ok=True)

    personal_index_path = 'data/faiss_indexs/personal_faiss_index'
    personal_faiss_manager.save_index(personal_index_path)

    org_index_path = 'data/faiss_indexs/org_faiss_index'
    organization_faiss_manager.save_index(org_index_path)

    # logger.info(f"Đã lưu FAISS index tại {article_index_path}")
    logger.info("✅ Xử lý bài báo hoàn tất.")

if __name__ == "__main__":
    main()
import json
import os
import re
from logger import _setup_logger
import config
from utils import Utils
from blacklist_builder.article_extractor import ArticlePersonExtractor
from dynamodb.dynamo_pusher import DynamoPusher
from llm_model.bedrock_manager import BedrockModelManager
from dynamodb.base_dynamo import BaseDynamoDB
from blacklist_builder.info_comparer import InfoComparer
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.table_adverse_media import TableAdverseMedia
from blacklist_builder.builder.new_item_builder import NewItemBuilder
from blacklist_builder.builder.rebuild_item_builder import RebuildItemBuilder
from dynamodb.dynamo_deleter import DynamoDBDeleter
from dynamodb.table_org_embedd2org import TableOrgEmbedd2Org
from dynamodb.table_personal_embedd2personal import TablePersonalEmbedd2Personal
from dynamodb.table_personal_risk_embedd2per import TablePersonalRiskEmbedd2Personal
from dynamodb.table_organization_risk_embedd2org import TableOrgainzationRiskEmbedd2Orgainzation
from blacklist_builder.faiss_handler.faiss_personal_and_risk_handler import PersonalAndRiskHandler
from blacklist_builder.faiss_handler.faiss_organization_and_risk_handler import OrganizationAndRiskHandler
from blacklist_builder.faiss_handler.retrieval_faiss_personal_and_risk import PersonalInfoSimilarRetriever
from blacklist_builder.faiss_handler.retrieval_faiss_organization_and_risk import OrganizationInfoSimilarRetriever
from embedder.bedrock_base import BedrockBaseClient
from embedder.cohere_embedder import CohereMultilingualEmbedder
from faiss_manager.faiss_index_manager import FaissIndexManager

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleRiskMatchingExtractor:
    def __init__(self, 
                 info_extractor, 
                 base_dynamo,
                 info_comparer,
                personal_and_risk_handler: PersonalAndRiskHandler,
                organization_and_risk_handler: OrganizationAndRiskHandler,
                personal_info_similar_retriever: PersonalInfoSimilarRetriever,
                organization_info_similar_retriever: OrganizationInfoSimilarRetriever):
        """
        :param gemini_extractor: công cụ trích xuất từ Gemini API
        :param dynamo_pusher: đối tượng DynamoPusher (bắt buộc)
        """
        self.extractor = info_extractor
        self.base_dynamo = base_dynamo
        self.dynamo_pusher = DynamoPusher(dynamodb=self.base_dynamo)

        self.table_config = config.TABLE_CONFIG_DEMO

        self.query = DynamoQuery(self.base_dynamo)
        self.table_adverse_media = TableAdverseMedia(self.query, self.table_config)
        self.table_personal_embedd2media = TablePersonalEmbedd2Personal(self.query, self.table_config)
        self.table_org_embedd2media = TableOrgEmbedd2Org(self.query, self.table_config)
        self.personal_risk_embedd2media_table = TablePersonalRiskEmbedd2Personal(self.query, self.table_config)
        self.organization_risk_embedd2media_table = TableOrgainzationRiskEmbedd2Orgainzation(self.query, self.table_config)

        self.comparer = info_comparer

        self.new_item_builder = NewItemBuilder
        self.rebuild_item_builder = RebuildItemBuilder

        self.dynamo_deleter = DynamoDBDeleter(self.base_dynamo)

        self.personal_and_risk_handler = personal_and_risk_handler
        self.organization_and_risk_handler = organization_and_risk_handler
        
        self.personal_info_similar_retriever = personal_info_similar_retriever
        self.organization_info_similar_retriever = organization_info_similar_retriever

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

    def extract_info_from_article(self, article_text: str):
        logger.info("🧠 Gọi LLM để trích xuất bài báo...")
        answer, thinking = self.extractor.extract_from_article(article_text)

        logger.debug(f"[process_article] Raw response:\n{answer}")
        logger.info("📦 Đang xử lý kết quả trích xuất...")

        # answer = Utils.load_text('./prepare_data/response_extractor.txt')

        personal_info_json, org_info_json, risk_info_json = self.extract_json_blocks(answer)

        logger.debug(f"[process_article] Personal info: {Utils.json_to_str(personal_info_json)}")  
        logger.debug(f"[process_article] Organization info: {Utils.json_to_str(org_info_json)}")
        logger.debug(f"[process_article] Risk info: {Utils.json_to_str(risk_info_json)}")

        return personal_info_json, org_info_json, risk_info_json

    def delete_old_personal_items(self, old_personal_ids, table_config: dict):
        personal_config = table_config['person_config']

        for old_personal_id in old_personal_ids:
            self.dynamo_deleter.delete_item(personal_config, old_personal_id)

        logger.info("Xoa du lieu PERSONAL_ITEMS cu trung thanh cong")

    def delete_old_organization_items(self, old_organization_ids, table_config: dict):
        organization_config = table_config['organization_config']

        for old_organization_id in old_organization_ids:
            self.dynamo_deleter.delete_item(organization_config, old_organization_id)

        logger.info("Xoa du lieu cu trung thanh cong")

    def push_to_dynamodb(self, items: dict, table_config: dict):
        logger.info("📝 Đang lưu vào DynamoDB...")

        self.dynamo_pusher.insert(items['adverse_media_item'], table_config=table_config['media_config'])
        self.dynamo_pusher.insert(items['organization_info_items'], table_config=table_config['organization_config'])
        self.dynamo_pusher.insert(items['personal_info_items'], table_config=table_config['person_config'])
        self.dynamo_pusher.insert(items['organization2media_items'], table_config=table_config['o2m_config'])
        self.dynamo_pusher.insert(items['personal2media_items'], table_config=table_config['p2m_config'])
        self.dynamo_pusher.insert(items['personal_risk_embedd2per_items'], table_config=table_config['personal_risk_embedd2per_config'])
        self.dynamo_pusher.insert(items['organization_risk_embedd2org_items'], table_config=table_config['organization_risk_embedd2org_config'])

        logger.info("Day du lieu moi len Database thanh cong")

    def handler_new_personal_info_json(self, new_personal_info_jsons: list[dict], new_risk_info_json, table_config: dict):
        def prepare_new_personal_risk_info(new_personal_info_jsons, new_risk_info_json):
            personal_risk_infos = new_risk_info_json["list_personal_risks"]

            personal_id2_risk_info = {} 
            for personal_risk_info in personal_risk_infos:
                violent_details = {k: v for k, v in personal_risk_info.items() if k != "entity_id"}
                personal_id = personal_risk_info["entity_id"]
                personal_id2_risk_info[personal_id] = violent_details

            new_personal_risk_infos = []
            for new_personal_info_json in new_personal_info_jsons:
                personal_id = new_personal_info_json["personal_id"]
                personal_info = {k: v for k, v in new_personal_info_json.items()}
                personal_info['violent_details'] = personal_id2_risk_info.get(personal_id, {})
                new_personal_risk_infos.append(personal_info)

            logger.debug(f"[prepare_new_personal_risk_info] Personal risk info: {Utils.json_to_str(new_personal_risk_infos)}")

            return new_personal_risk_infos

        personal_risk_infos = prepare_new_personal_risk_info(new_personal_info_jsons, new_risk_info_json) 

        top_k_similar_results = self.personal_info_similar_retriever.retrieve_personal_risk_info(personal_risk_infos)
        top_k_similar_personal_risks = [result["top_k_personal_risk_infos"] for result in top_k_similar_results]

        # logger.debug(f"[handler_new_personal_info_json] Top k similar personal risk: {Utils.json_to_str(top_k_similar_results)}")

        duplicated_personal_infos = []
        new_personal_infos = []
        for idx, (personal_risk_info, similar_personal_risk) in enumerate(zip(personal_risk_infos, top_k_similar_personal_risks)):
            logger.debug(f"So sanh lan {idx + 1} voi {len(similar_personal_risk)} ket qua tu FAIS")
            logger.debug(f"{50 * '-'}")
            logger.debug(f"[handler_new_personal_info_json] Personal risk info: {Utils.json_to_str(personal_risk_info)}")
            logger.debug(f"[handler_new_personal_info_json] Similar personal risk info: {Utils.json_to_str(similar_personal_risk)}")

            new_personal_info = self.comparer.compare_personal_info(
                new_personal_info=personal_risk_info,
                old_personal_infos=similar_personal_risk
            )

            if new_personal_info: 
                duplicated_personal_infos.append(new_personal_info)
            else:
                new_personal_infos.append(new_personal_info_jsons[idx])

            logger.debug(f"{50 * '-'}")
            logger.debug(f"[handler_new_personal_info_json] New personal info: {Utils.json_to_str(new_personal_info)}")
            logger.debug(f"{50 * '-'}")

        logger.info(f"[handler_new_personal_info_json] So luong personal_info trung: {len(duplicated_personal_infos)}")
        logger.info(f"[handler_new_personal_info_json] So luong personal_info moi: {len(new_personal_infos)}")

        return duplicated_personal_infos, new_personal_infos

    def handler_new_organization_info_json(self, new_organization_info_jsons: list[dict], new_risk_info_json, table_config: dict):
        def prepare_new_organization_risk_info(new_organization_info_jsons, new_risk_info_json):
            organization_risk_infos = new_risk_info_json["list_organizer_risks"]

            organization_id2_risk_info = {} 
            for organization_risk_info in organization_risk_infos:
                violent_details = {k: v for k, v in organization_risk_info.items() if k != "entity_id"}
                organization_id = organization_risk_info["entity_id"]
                organization_id2_risk_info[organization_id] = violent_details

            new_organization_risk_infos = []
            for new_organization_info_json in new_organization_info_jsons:
                organization_id = new_organization_info_json["organizer_id"]
                organization_info = {k: v for k, v in new_organization_info_json.items()}
                organization_info['violent_details'] = organization_id2_risk_info.get(organization_id, {})
                new_organization_risk_infos.append(organization_info)

            logger.debug(f"[prepare_new_organization_risk_info] organization risk info: {Utils.json_to_str(new_organization_risk_infos)}")

            return new_organization_risk_infos

        organization_risk_infos = prepare_new_organization_risk_info(new_organization_info_jsons, new_risk_info_json) 

        top_k_similar_results = self.organization_info_similar_retriever.retrieve_organization_risk_info(organization_risk_infos)
        top_k_similar_organization_risks = [result["top_k_organization_risk_infos"] for result in top_k_similar_results]

        # logger.debug(f"[handler_new_organization_info_json] Top k similar organization risk: {Utils.json_to_str(top_k_similar_results)}")

        duplicated_organization_infos = []
        new_organization_infos = []
        for idx, (organization_risk_info, similar_organization_risk) in enumerate(zip(organization_risk_infos, top_k_similar_organization_risks)):
            logger.debug(f"So sanh lan {idx + 1} voi {len(similar_organization_risk)} ket qua tu FAIS")
            logger.debug(f"{50 * '-'}")
            logger.debug(f"[handler_new_organization_info_json] organization risk info: {Utils.json_to_str(organization_risk_info)}")
            logger.debug(f"[handler_new_organization_info_json] Similar organization risk info: {Utils.json_to_str(similar_organization_risk)}")

            new_organization_info = self.comparer.compare_organization_info(
                new_organization_info=organization_risk_info,
                old_organization_infos=similar_organization_risk
            )

            if new_organization_info: 
                duplicated_organization_infos.append(new_organization_info)
            else:
                new_organization_infos.append(new_organization_info_jsons[idx])

            logger.debug(f"{50 * '-'}")
            logger.debug(f"[handler_new_organization_info_json] New organization info: {Utils.json_to_str(new_organization_info)}")
            logger.debug(f"{50 * '-'}")

        logger.info(f"[handler_new_organization_info_json] So luong organization_info trung: {len(duplicated_organization_infos)}")
        logger.info(f"[handler_new_organization_info_json] So luong organization_info moi: {len(new_organization_infos)}")

        return duplicated_organization_infos, new_organization_infos

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
    
    def delete_old_organization_embeddings_faiss_and_dynamodb(self, old_organization_ids: list[str], table_config: dict):
        organization_risk_embedd2_org_config = table_config['organization_risk_embedd2org_config']
        old_embedding_ids = self.organization_risk_embedd2media_table.get_embedd_by_org_id_list(old_organization_ids)

        logger.debug(f"[delete_old_embeddings_faiss_and_dynamodb] Old embedding IDs: {old_embedding_ids}")
        self.organization_and_risk_handler.remove_old_embeddings_faiss(old_embedding_ids)

        for old_embedding_id in old_embedding_ids:
            self.dynamo_deleter.delete_item(organization_risk_embedd2_org_config, old_embedding_id)

    def delete_old_personal_embeddings_faiss_and_dynamodb(self, old_personal_ids: list[str], table_config: dict):
        personal_risk_embedd2_per_config = table_config['personal_risk_embedd2per_config']
        old_embedding_ids = self.personal_risk_embedd2media_table.get_embedd_by_per_id_list(old_personal_ids)

        logger.debug(f"[delete_old_embeddings_faiss_and_dynamodb] Old embedding IDs: {old_embedding_ids}")
        self.personal_and_risk_handler.remove_old_embeddings_faiss(old_embedding_ids)

        for old_embedding_id in old_embedding_ids:
            self.dynamo_deleter.delete_item(personal_risk_embedd2_per_config, old_embedding_id)

    def prepare_organization_items(self,
                                   duplicated_organization_infos: list[dict],
                                   new_organization_infos: list[dict],
                                   new_risk_info_json: dict,
                                   media_id: str,
                                   table_config: dict):
        organization_info_duplicated_items, organization_id2org_id_duplicated, old_org_ids = self.rebuild_item_builder.create_rebuild_organization_items(duplicated_organization_infos, partition_key='org_id')
        organization_info_new_items, organization_id2org_id_new = self.new_item_builder.create_organization_items(new_organization_infos, partition_key='org_id')

        organization_info_items = organization_info_duplicated_items + organization_info_new_items
        organization_id2org_id = {**organization_id2org_id_duplicated, **organization_id2org_id_new}

        logger.debug(f"[process_article] Organization info items: {Utils.json_to_str(organization_info_items)}")
        logger.debug(f"[process_article] Organization ID to Org ID: {Utils.json_to_str(organization_id2org_id)}")

        organization2media_items = self.new_item_builder.create_org2media_items(
            risk_info=new_risk_info_json, 
            partition_key='o2m_id', 
            org_id_gen_to_org_id=organization_id2org_id, 
            media_id=media_id
        )

        logger.debug(f"[process_article] Organization2Media items: {Utils.json_to_str(organization2media_items)}")

        organization_risk_embedd2org_items = self.handle_faiss_organization_risk_items(
            organization_info_items=organization_info_items,
            organization2media_items=organization2media_items,
            table_config=table_config
        )

        return {
            "organization_info_items": organization_info_items,
            "organization2media_items": organization2media_items,
            "organization_risk_embedd2org_items": organization_risk_embedd2org_items,
            "old_org_ids": old_org_ids
        }
    
    def prepare_personal_items(self,
                               duplicated_personal_infos: list[dict],
                               new_personal_infos: list[dict],
                               new_risk_info_json: dict,
                               media_id: str,
                               table_config: dict):
        personal_info_duplicated_items, personal_id2per_id_duplicated, old_per_ids = self.rebuild_item_builder.create_rebuild_personal_items(duplicated_personal_infos, partition_key='per_id')
        personal_info_new_items, personal_id2per_id_new = self.new_item_builder.create_personal_items(new_personal_infos, partition_key='per_id')

        personal_info_items = personal_info_duplicated_items + personal_info_new_items
        personal_id2per_id = {**personal_id2per_id_duplicated, **personal_id2per_id_new}

        logger.debug(f"[process_article] Personal info items: {Utils.json_to_str(personal_info_items)}")
        logger.debug(f"[process_article] Personal ID to Per ID: {Utils.json_to_str(personal_id2per_id)}")
        
        personal2media_items = self.new_item_builder.create_personal2media_items(
            risk_info=new_risk_info_json, 
            partition_key='p2m_id', 
            per_id_gen_to_per_id=personal_id2per_id, 
            media_id=media_id
        )

        logger.debug(f"[process_article] Personal2Media items: {Utils.json_to_str(personal2media_items)}")

        personal_risk_embedd2per_items = self.handle_faiss_personal_risk_items(
            personal_info_items=personal_info_items,
            personal2media_items=personal2media_items,
            table_config=table_config
        )       

        return {
            "personal_info_items": personal_info_items,
            "personal2media_items": personal2media_items,
            "personal_risk_embedd2per_items": personal_risk_embedd2per_items,
            "old_per_ids": old_per_ids
        }
    
    def prepare_items_from_info_extracted(self,
                                          new_personal_info_json: list[dict],
                                          new_org_info_json: list[dict],
                                          new_risk_info_json: dict,
                                          article_text: str,
                                          table_config: dict):
        adverse_media_item, media_id = self.new_item_builder.create_adverse_media_item(risk_info=new_risk_info_json, partition_key='media_id', context=article_text)

        logger.debug(f"[process_article] Personal info: {Utils.json_to_str(new_personal_info_json)}")
        logger.debug(f"[process_article] Organization info: {Utils.json_to_str(new_org_info_json)}")
        logger.debug(f"[process_article] Risk info: {Utils.json_to_str(new_risk_info_json)}")

        duplicated_organization_infos, new_organization_infos = self.handler_new_organization_info_json(new_org_info_json, new_risk_info_json, table_config)
        logger.debug(f"[process_article] Duplicated organization infos: {Utils.json_to_str(duplicated_organization_infos)}")
        logger.debug(f"[process_article] New organization infos: {Utils.json_to_str(new_organization_infos)}")

        organization_items = self.prepare_organization_items(
            duplicated_organization_infos=duplicated_organization_infos,
            new_organization_infos=new_organization_infos,
            new_risk_info_json=new_risk_info_json,
            media_id=media_id,
            table_config=table_config
        )

        duplicated_personal_infos, new_personal_infos = self.handler_new_personal_info_json(new_personal_info_json, new_risk_info_json, table_config)

        logger.info(f"[process_article] Số lượng thông tin cá nhân trùng lặp: {len(duplicated_personal_infos)}")
        logger.info(f"[process_article] Số lượng thông tin cá nhân mới: {len(new_personal_infos)}")

        personal_items = self.prepare_personal_items(
            duplicated_personal_infos=duplicated_personal_infos,
            new_personal_infos=new_personal_infos,
            new_risk_info_json=new_risk_info_json,
            media_id=media_id,
            table_config=table_config
        )


        items = {
            "adverse_media_item": adverse_media_item,
            "personal_info_items": personal_items['personal_info_items'],
            "personal2media_items": personal_items['personal2media_items'],
            "personal_risk_embedd2per_items": personal_items['personal_risk_embedd2per_items'],
            "organization_info_items": organization_items["organization_info_items"],
            "organization2media_items": organization_items["organization2media_items"],
            "organization_risk_embedd2org_items": organization_items["organization_risk_embedd2org_items"]
        }

        return items, organization_items, personal_items

    def save_items_to_dynamodb(self,
                               items: dict,
                               organization_items: dict,
                               personal_items: dict,
                               table_config: dict):
        logger.info("📝 Đang lưu vào DynamoDB...")
        self.delete_old_organization_items(old_organization_ids=organization_items['old_org_ids'], table_config=table_config)
        self.delete_old_organization_embeddings_faiss_and_dynamodb(old_organization_ids=organization_items['old_org_ids'], table_config=table_config)

        self.delete_old_personal_items(old_personal_ids=personal_items['old_per_ids'], table_config=table_config)
        self.delete_old_personal_embeddings_faiss_and_dynamodb(old_personal_ids=personal_items['old_per_ids'], table_config=table_config)

        logger.info("📝 Đang lưu vào DynamoDB...")
        logger.debug(f"[process_article] Old personal IDs to delete: {Utils.json_to_str(personal_items['old_per_ids'])}")
        self.push_to_dynamodb(items, table_config)

        logger.info('Lưu adverse media mới vào DynamoDB thành công')


    def process_article(self, article_text: str, table_config):
        logger.info(f"Tien hanh so sanh bao moi voi cac bai bao cu")
        logger.info(f"Noi dung bao moi {article_text[:100]}")

        new_personal_info_json, new_org_info_json, new_risk_info_json = self.extract_info_from_article(article_text)

        items, organization_items, personal_items = self.prepare_items_from_info_extracted(
            new_personal_info_json=new_personal_info_json,
            new_org_info_json=new_org_info_json,
            new_risk_info_json=new_risk_info_json,
            article_text=article_text,
            table_config=table_config
        )

        self.save_items_to_dynamodb(items, organization_items, personal_items, table_config)

        logger.info('Xu ly so sanh bai bao cu va luu bai bao moi thanh cong')
        logger.info(f"\n {'-' * 50} \n")

def main():
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    REGION_MODEL = config.AWS_VIRGINA_REGION
    MODEL_ID = config.CLAUDE_35_HAIKU_CROSS_REGION_VIRGINA_MODEL_ID

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

    # Tạo retriever với client đã có
    personal_faiss_index_path = 'D:/VPBankHackathon/data/faiss_indexs/personal_faiss_index'

    personal_retriever = PersonalInfoSimilarRetriever(index_dir=personal_faiss_index_path,
                                     bedrock_base_client=bedrock_base.get_client(), 
                                     base_dynamo=base_dynamo)

    organization_faiss_index_path = 'D:/VPBankHackathon/data/faiss_indexs/org_faiss_index'

    organization_retriever = OrganizationInfoSimilarRetriever(index_dir=organization_faiss_index_path,
                                     bedrock_base_client=bedrock_base.get_client(), 
                                     base_dynamo=base_dynamo)


    # Khởi tạo Cohere embedder
    embedder = CohereMultilingualEmbedder(bedrock_client=bedrock_base.get_client())
    personal_faiss_manager = FaissIndexManager.load_index(personal_faiss_index_path)
    personal_risk_handler = PersonalAndRiskHandler(embedder=embedder, faiss_manager=personal_faiss_manager)

    organization_faiss_manager = FaissIndexManager.load_index(organization_faiss_index_path)
    organization_risk_handler = OrganizationAndRiskHandler(embedder=embedder, faiss_manager=organization_faiss_manager)

    personal_compare_prompt_file = './prompts/prompt_compare_new_old_personal_risk_info.txt' 
    personal_compare_prompt = Utils.load_text(personal_compare_prompt_file)
    logger.info(f"Đã tải prompt từ {personal_compare_prompt_file}")
    logger.debug(f"Prompt nội dung: {personal_compare_prompt}")

    organization_compare_prompt_file = 'D:/VPBankHackathon/prompts/prompt_compare_new_old_organization.txt' 
    organization_compare_prompt = Utils.load_text(organization_compare_prompt_file)
    logger.info(f"Đã tải prompt từ {organization_compare_prompt_file}")
    logger.debug(f"Prompt nội dung: {organization_compare_prompt}")

    info_comparer = InfoComparer(base_dynamo, 
                                bedrock_manager, 
                                personal_compare_prompt,
                                organization_compare_prompt)

    processor = ArticleRiskMatchingExtractor(
        info_extractor=extractor,
        base_dynamo=base_dynamo.dynamodb,
        info_comparer=info_comparer,
        personal_info_similar_retriever=personal_retriever,
        organization_info_similar_retriever=organization_retriever,
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
    # table_media_config={"adverse_media": "media_id"}
    # table_person_config={"personal_info": "per_id"}
    # table_organization_config={"organization_info": "org_id"}
    # table_p2m_config={"personal2media": "p2m_id"}
    # table_o2m_config={"org2media": "o2m_id"}

    processor.process_article(
        article_text=content,
        table_config=table_config
    )

    personal_faiss_manager.save_index(personal_faiss_index_path)
    organization_faiss_manager.save_index(organization_faiss_index_path)

    logger.info("Đã lưu FAISS index cá nhân sau khi xử lý bài báo.")

    logger.info("Xử lý bài báo hoàn tất.")
        
if __name__ == "__main__":
    main()    

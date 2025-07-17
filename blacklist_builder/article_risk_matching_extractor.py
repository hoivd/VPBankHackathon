import json
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

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleRiskMatchingExtractor:
    def __init__(self, 
                 info_extractor, 
                 base_dynamo, 
                 llm_manager, compare_prompt_template, 
                 article_embedder, personal_embedder, org_embedder, 
                 article_faiss_manager, personal_faiss_manager, org_faiss_manager):
        """
        :param gemini_extractor: công cụ trích xuất từ Gemini API
        :param dynamo_pusher: đối tượng DynamoPusher (bắt buộc)
        """
        self.extractor = info_extractor
        self.base_dynamo = base_dynamo
        self.dynamo_pusher = DynamoPusher(dynamodb=self.base_dynamo)

        self.table_config = config.TABLE_CONFIG

        self.query = DynamoQuery(self.base_dynamo)
        self.table_adverse_media = TableAdverseMedia(self.query, self.table_config)
        self.table_personal_embedd2media = TablePersonalEmbedd2Personal(self.query, self.table_config)
        self.table_org_embedd2media = TableOrgEmbedd2Org(self.query, self.table_config)

        self.comparer = InfoComparer(base_dynamo, llm_manager, compare_prompt_template)

        self.new_item_builder = NewItemBuilder
        self.rebuild_item_builder = RebuildItemBuilder

        self.dynamo_deleter = DynamoDBDeleter(self.base_dynamo)

        self.article_embedder = article_embedder
        self.personal_embedder = personal_embedder
        self.org_embedder = org_embedder

        self.article_faiss_manager = article_faiss_manager
        self.personal_faiss_manager = personal_faiss_manager
        self.org_faiss_manager = org_faiss_manager

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

    def delete_old_object(self, old_personal_ids, old_organization_ids, table_config: dict):
        orgnization_config = table_config['organization_config']
        personal_config = table_config['person_config']

        for old_org_id in old_organization_ids:
            self.dynamo_deleter.delete_item(orgnization_config, old_org_id)

        for old_personal_id in old_personal_ids:
            self.dynamo_deleter.delete_item(personal_config, old_personal_id)

        logger.info("Xoa du lieu cu trung thanh cong")

    def push_to_dynamodb(self, items: dict, table_config: dict):
        logger.info("📝 Đang lưu vào DynamoDB...")
        self.dynamo_pusher.insert(items['organization_info_items'], table_config=table_config['organization_config'])
        self.dynamo_pusher.insert(items['personal_info_items'], table_config=table_config['person_config'])
        self.dynamo_pusher.insert(items['org2media_items'], table_config=table_config['o2m_config'])
        self.dynamo_pusher.insert(items['personal2media_items'], table_config=table_config['p2m_config'])

        logger.info("Day du lieu moi len Database thanh cong")

    def process_dynamodb(self, new_items: dict, old_ids: dict, table_config: dict):
        self.delete_old_object(old_ids['old_personal_ids'], old_ids['old_organization_ids'], table_config)

        self.push_to_dynamodb(new_items, table_config)
        logger.info("✅ Xử lý data mới cũ thành công")

    def prepare_dynamodb_items(self, 
                               personal_duplicated, 
                               organization_duplicated, 
                               risk_info, 
                               media_id):
        org_rebuilt_items, org_id_gen_to_org_id, org_ids = self.rebuild_item_builder.create_rebuild_organization_items(organization_duplicated, partition_key="org_id")
        per_rebuilt_items, per_id_gen_to_per_id, per_ids = self.rebuild_item_builder.create_rebuild_personal_items(personal_duplicated, partition_key="per_id")

        org_gen_ids = list(org_id_gen_to_org_id.keys())
        per_gen_ids = list(per_id_gen_to_per_id.keys())

        personal2media_items = self.new_item_builder.create_personal2media_items(risk_info=risk_info, partition_key='p2m_id', per_id_gen_to_per_id=per_id_gen_to_per_id, media_id=media_id)
        org2media_items = self.new_item_builder.create_org2media_items(risk_info=risk_info, partition_key='o2m_id', org_id_gen_to_org_id=org_id_gen_to_org_id, media_id=media_id)
        
        logger.info("✅ Rebuilt Organization Items:")
        logger.info(json.dumps(org_rebuilt_items, indent=2, ensure_ascii=False))
        logger.debug(Utils.json_to_str(org_id_gen_to_org_id))
        
        logger.info("✅ Rebuilt Personal Items:")
        logger.info(json.dumps(per_rebuilt_items, indent=2, ensure_ascii=False))
        logger.debug(Utils.json_to_str(per_id_gen_to_per_id))

        logger.debug(Utils.json_to_str(personal2media_items))
        logger.debug(Utils.json_to_str(org2media_items))

        logger.info(f"List Personal info per_ids: {per_ids}")
        logger.info(f"List Organization info org_ids: {org_ids}")

        logger.info(f"Tim thay {len(per_ids)} personal info trung")
        logger.info(f"Tim thay {len(org_ids)} organization info trung")
        logger.info(f"Tim thay {len(personal2media_items)} personal2media_items moi")
        logger.info(f"Tim thay {len(org2media_items)} organization2media_items moi")

        logger.info("Chuan bi items thanh cong")

        return (
            {
                'personal_info_items': per_rebuilt_items,
                'organization_info_items': org_rebuilt_items,
                'personal2media_items': personal2media_items,
                'org2media_items': org2media_items
            } ,
            {   
                'old_personal_ids': per_ids,
                'old_organization_ids': org_ids,
                'new_personal_ids': per_gen_ids,
                'new_organization_ids': org_gen_ids
            }
        )
    
    def prepare_new_items(self, new_personal_info_json, new_org_info_json, risk_info, media_id):
        new_personal_info_items, per_id_gen_to_per_id = self.new_item_builder.create_personal_items(new_personal_info_json, partition_key='per_id')
        new_organization_info_items, org_id_gen_to_org_id = self.new_item_builder.create_organization_items(new_org_info_json, partition_key='org_id')
        new_personal2media_items = self.new_item_builder.create_personal2media_items(risk_info=risk_info, partition_key='p2m_id', per_id_gen_to_per_id=per_id_gen_to_per_id, media_id=media_id)
        new_org2media_items = self.new_item_builder.create_org2media_items(risk_info=risk_info, partition_key='o2m_id', org_id_gen_to_org_id=org_id_gen_to_org_id, media_id=media_id)

        logger.debug(f"new_personal_info_items: {new_personal_info_items}")
        logger.debug(f"new_organization_info_items: {new_organization_info_items}")
        logger.debug(f"new_personal2media_items: {new_personal2media_items}")
        logger.debug(f"new_org2media_items: {new_org2media_items}")

        logger.info("Chuan bi items thanh cong ")
        return {
            'personal_info_items': new_personal_info_items,
            'organization_info_items': new_organization_info_items,
            'personal2media_items': new_personal2media_items,
            'org2media_items': new_org2media_items
        }
    
    def push_unduplicated_items_to_dynamodb(self, unduplicated_items: dict, table_config: dict):
        logger.info("📝 Đang lưu vào DynamoDB...")

        self.dynamo_pusher.insert(unduplicated_items['organization_info_items'], table_config=table_config['organization_config'])
        self.dynamo_pusher.insert(unduplicated_items['personal_info_items'], table_config=table_config['person_config'])
        self.dynamo_pusher.insert(unduplicated_items['org2media_items'], table_config=table_config['o2m_config'])
        self.dynamo_pusher.insert(unduplicated_items['personal2media_items'], table_config=table_config['p2m_config'])

        logger.info("Day du lieu moi len Database thanh cong")
        
    
    def updated_new_items_after_compare(self, new_personal_info_json, new_org_info_json, old_ids):
        new_personal_ids = old_ids['new_personal_ids']
        new_organization_ids = old_ids['new_organization_ids']

        # Lọc bỏ các personal_id đã có
        filtered_personal_info = [
            item for item in new_personal_info_json
            if item.get("personal_id") not in new_personal_ids
        ]

        # Lọc bỏ các organizer_id đã có
        filtered_org_info = [
            item for item in new_org_info_json
            if item.get("organizer_id") not in new_organization_ids
        ]

        return filtered_personal_info, filtered_org_info

    def embed_article_and_add_to_faiss(self, article_text: str, table_config: dict): 
        article_embedding = self.article_embedder.embed_article(article_text) 
        logger.debug(f"[embed_article_and_add_to_faiss] Article embedding: {article_embedding[0, :10]}")

        article_embedding_id = self.article_faiss_manager.add(article_embedding)
        logger.info(f"✅ Đã thêm embedding của bài báo vào FAISS với ID: {article_embedding_id}")
        return str(article_embedding_id[0])

    def create_article_embedd2media_item(self, media_id: str, article_embedding_id: int, table_config: dict):
        table_name, partition_key = list(table_config['article_embedd2media_config'].items())[0]
        logger.debug(f"[create_article_embedding2media_item] Tạo item cho media_id: {media_id}, article_embedding_id: {article_embedding_id}")
        item = {
            "media_id": media_id,
            partition_key: article_embedding_id
        }
        return item

    def embed_peronsal_org_embedd2media_and_add_to_faiss(self, personal_info_items: list[dict], organization_info_items: list[dict], table_config: dict):
        personal_info_items_str = [Utils.json_to_str(item) for item in personal_info_items]
        org_info_items_str = [Utils.json_to_str(item) for item in organization_info_items]

        logger.info("🧠 Đang encode cá nhân và tổ chức...")
        personal_embeddings = self.personal_embedder.embed_personal(personal_info_items_str)
        org_embeddings = self.org_embedder.embed_organization(org_info_items_str)
        logger.debug(f"[embed_personal_org_embedd2media] Personal embeddings: {personal_embeddings[0, :10]} {len(personal_embeddings)} items")
        logger.debug(f"[embed_personal_org_embedd2media] Organization embeddings: {org_embeddings[0, :10]} {len(org_embeddings)} items")
        logger.info("✅ Đã encode cá nhân và tổ chức xong.")

        personal_embedding_ids = self.personal_faiss_manager.add(personal_embeddings)
        org_embedding_ids = self.org_faiss_manager.add(org_embeddings)

        personal_embedding_ids = [str(id) for id in personal_embedding_ids]
        org_embedding_ids = [str(id) for id in org_embedding_ids]
        logger.info(f"✅ Đã thêm embedding cá nhân vào FAISS với IDs: {personal_embedding_ids}")
        logger.info(f"✅ Đã thêm embedding tổ chức vào FAISS với IDs: {org_embedding_ids}")

        return personal_embedding_ids, org_embedding_ids

    def delete_personal_org_embedd2media(self, personal_ids: list[int], org_ids: list[int], table_config: dict):
        if not personal_ids and not org_ids:
            logger.info("Không có personal_ids hoặc org_ids để xóa.")
        
        if personal_ids:
            personal_embedding_ids = self.table_personal_embedd2media.get_embedd_by_per_id_list(personal_ids)
            personal_ids = [str(id) for id in personal_embedding_ids]
            logger.debug(f"[delete_personal_org_embedd2media] Personal embedding {personal_embedding_ids}")
            self.personal_faiss_manager.remove_by_ids(personal_embedding_ids)
            self.dynamo_deleter.delete_item(table_config['personal_embedd2per_config'], personal_ids)
            logger.info(f"🗑️ Đang xóa {len(personal_ids)} cá nhân khỏi FAIS... Dynamo")

        if org_ids:
            org_embedding_ids = self.table_org_embedd2media.get_embedd_by_org_id_list(org_ids)
            org_ids = [str(id) for id in org_embedding_ids]
            logger.debug(f"[delete_personal_org_embedd2media] Organization embedding {org_embedding_ids}")

            self.org_faiss_manager.remove_by_ids(org_embedding_ids)
            self.dynamo_deleter.delete_item(table_config['org_embedd2org_config'], org_ids)
            logger.info(f"🗑️ Đang xóa {len(org_ids)} tổ chức khỏi FAIS... Dynamo")

        logger.info("✅ Đã xóa cá nhân và tổ chức khỏi FAISS.")

    def create_personal_embedd2media_items(self, personal_info_items: list[dict], personal_embedding_ids: list[int], table_config: dict):
        _, personal_embedd_partition_key = list(table_config['personal_embedd2per_config'].items())[0]
        _, personal_partition_key = list(table_config['person_config'].items())[0]
        logger.debug(f"[create_personal_embedd2media_items] Tạo item cho {len(personal_info_items)} cá nhân")
        def create_item(item: dict, embedding_id: int):
            item = {
                personal_embedd_partition_key: embedding_id,
                personal_partition_key: item[personal_partition_key]
            }
            return item

        personal_embedd2media_items = [create_item(item, embedding_id) for item, embedding_id in zip(personal_info_items, personal_embedding_ids)]
        logger.debug(f"[create_personal_embedd2media_items] Đã tạo {len(personal_embedd2media_items)} items cá nhân")
        return personal_embedd2media_items

    def create_org_embedd2media_items(self, organization_info_items: list[dict], org_embedding_ids: list[int], table_config: dict):
        _, org_embedd_partition_key = list(table_config['org_embedd2org_config'].items())[0]
        _, org_partition_key = list(table_config['organization_config'].items())[0]
        logger.debug(f"[create_org_embedd2media_items] Tạo item cho {len(organization_info_items)} tổ chức")    

        def create_item(item: dict, embedding_id: int):
            item = {
                org_embedd_partition_key: embedding_id,
                org_partition_key: item[org_partition_key]
            }
            return item    

        org_embedd2media_items = [create_item(item, embedding_id) for item, embedding_id in zip(organization_info_items, org_embedding_ids)]
        logger.debug(f"[create_org_embedd2media_items] Đã tạo {len(org_embedd2media_items)} items tổ chức")
        return org_embedd2media_items 


    def process_article(self, article_text: str, table_config):
        logger.info(f"Tien hanh so sanh bao moi voi cac bai bao cu")
        logger.info(f"Noi dung bao moi {article_text[:100]}")
        new_personal_info_json, new_org_info_json, new_risk_info_json = self.extract_info_from_article(article_text)
        adverse_media_item, media_id = self.new_item_builder.create_adverse_media_item(risk_info=new_risk_info_json, partition_key='media_id', context=article_text)
       
        #Embedd bai bao va day vao faiss index
        article_embedding_id = self.embed_article_and_add_to_faiss(article_text, table_config)

        #Tao item article_embedd2media
        article_embedd2media_item = self.create_article_embedd2media_item(media_id, article_embedding_id, table_config)

        logger.debug(Utils.json_to_str(adverse_media_item))
        logger.debug(media_id)
        
        old_media_ids = self.table_adverse_media.get_all_media_ids()
        logger.info(f" Tìm thấy {len(old_media_ids)} old media \n List OLD MEDIA: {old_media_ids}")


        old_per_ids_to_delete = []
        old_org_ids_to_delete = []

        personal_items_to_embed = []
        organization_items_to_embed = []
        for idx, old_media_id in enumerate(old_media_ids):
            try:
                logger.info(f"\n {'-' * 50} \n")
                logger.info(f'Đang xu ly media_id: {old_media_id}')

                logger.info(f"[SO SANH LAN {idx + 1}] SO LUONG PERSONAL_INFO BAN DAU MOI XET: {len(new_personal_info_json)}")
                logger.info(f"[SO SANH LAN {idx + 1}] SO LUONG ORGANIZATION_INFO BAN DAU MOI XET: {len(new_org_info_json)}")
                personal_duplicated, organization_duplicated = self.comparer.compare_info(new_article_text=article_text,
                                                                            new_personal_info=new_personal_info_json,
                                                                            new_org_info=new_org_info_json,
                                                                            media_id=old_media_id)

                
                logger.debug(f"Tien hanh khoi tao items")
                rebuild_items, old_ids = self.prepare_dynamodb_items(personal_duplicated, organization_duplicated, new_risk_info_json, media_id)
                self.process_dynamodb(rebuild_items, old_ids, table_config)
                
                personal_items_to_embed.extend(rebuild_items['personal_info_items'])
                organization_items_to_embed.extend(rebuild_items['organization_info_items'])

                old_per_ids_to_delete.extend(old_ids['old_personal_ids'])
                old_org_ids_to_delete.extend(old_ids['old_organization_ids'])

                new_personal_info_json, new_org_info_json = self.updated_new_items_after_compare(new_personal_info_json, new_org_info_json, old_ids)
                logger.info(f"[SO SANH LAN {idx + 1}] SO LUONG PERSONAL_INFO TRUNG: {len(personal_duplicated)}")
                logger.info(f"[SO SANH LAN {idx + 1}] SO LUONG ORGANIZATION_INFO TRUNG: {len(organization_duplicated)}")
                
                logger.info(f"[SO SANH LAN {idx + 1}] SO LUONG PERSONAL_INFO MOI CON LAI: {len(new_personal_info_json)}")
                logger.info(f"[SO SANH LAN {idx + 1}] SO LUONG ORGANIZATION_INFO CON LAI: {len(new_org_info_json)}")    


                
                if len(new_personal_info_json) == 0 and len(new_org_info_json) == 0:
                    logger.info(f"KHONG CON PERSONAL_INFO MOI")
                    logger.info(f"KHONG CON ORGANIZATION_INFO MOI")
                    logger.info('Xu ly so sanh bai bao cu va luu bai bao moi thanh cong')
                    logger.info(f"\n {'-' * 50} \n")

                    personal_embedd_ids, org_embedd_ids =  self.embed_peronsal_org_embedd2media_and_add_to_faiss(personal_items_to_embed, organization_items_to_embed, table_config)
                    personal_embedd2media_items = self.create_personal_embedd2media_items(
                        personal_info_items=personal_items_to_embed,
                        personal_embedding_ids=personal_embedd_ids,
                        table_config=table_config
                    )

                    org_embedd2media_items = self.create_org_embedd2media_items(
                        organization_info_items=organization_items_to_embed,
                        org_embedding_ids=org_embedd_ids,
                        table_config=table_config
                    )
                    logger.debug(f"[process_article] Personal embedd2media items: {personal_embedd2media_items}")
                    logger.debug(f"[process_article] Organization embedd2media items: {org_embedd2media_items}")
                    self.delete_personal_org_embedd2media(old_per_ids_to_delete, old_org_ids_to_delete, table_config)
                    logger.info(f"Đã embedd {len(personal_embedd_ids)} cá nhân và {len(org_embedd_ids)} tổ chức mới vào FAISS.")
                    self.dynamo_pusher.insert(adverse_media_item, table_config=table_config['media_config'])
                    self.dynamo_pusher.insert(article_embedd2media_item, table_config=table_config['article_embedd2media_config'])
                    self.dynamo_pusher.insert(personal_embedd2media_items, table_config=table_config['personal_embedd2per_config'])
                    self.dynamo_pusher.insert(org_embedd2media_items, table_config=table_config['org_embedd2org_config'])
                    return
            except Exception as e:
                logger.error(f"Loi khi so sanh lan thu {idx + 1} {e}")
        
        unduplicated_items = self.prepare_new_items(new_personal_info_json, new_org_info_json, new_risk_info_json, media_id)

        #Them nguoi moi khong trung vao danh sach can embedd
        new_personal_info_items = unduplicated_items['personal_info_items']
        new_organization_info_items = unduplicated_items['organization_info_items']

        personal_items_to_embed.extend(new_personal_info_items)
        organization_items_to_embed.extend(new_organization_info_items)

        personal_embedd_ids, org_embedd_ids =  self.embed_peronsal_org_embedd2media_and_add_to_faiss(personal_items_to_embed, organization_items_to_embed, table_config)
        personal_embedd2media_items = self.create_personal_embedd2media_items(
            personal_info_items=personal_items_to_embed,
            personal_embedding_ids=personal_embedd_ids,
            table_config=table_config
        )

        org_embedd2media_items = self.create_org_embedd2media_items(
            organization_info_items=organization_items_to_embed,
            org_embedding_ids=org_embedd_ids,
            table_config=table_config
        )
        logger.debug(f"[process_article] Personal embedd2media items: {personal_embedd2media_items}")
        logger.debug(f"[process_article] Organization embedd2media items: {org_embedd2media_items}")
        self.delete_personal_org_embedd2media(old_per_ids_to_delete, old_org_ids_to_delete, table_config)
        logger.info(f"Đã embedd {len(personal_embedd_ids)} cá nhân và {len(org_embedd_ids)} tổ chức mới vào FAISS.")

        self.push_unduplicated_items_to_dynamodb(unduplicated_items, table_config)
        self.dynamo_pusher.insert(adverse_media_item, table_config=table_config['media_config'])
        self.dynamo_pusher.insert(article_embedd2media_item, table_config=table_config['article_embedd2media_config'])
        self.dynamo_pusher.insert(personal_embedd2media_items, table_config=table_config['personal_embedd2per_config'])
        self.dynamo_pusher.insert(org_embedd2media_items, table_config=table_config['org_embedd2org_config'])

        logger.info("✅ Đã lưu adverse media mới vào DynamoDB")
        logger.info("✅ Đã lưu article_embedd2media mới vào DynamoDB")
        
        logger.info('Lưu adverse media mới vào DynamoDB thành công')
        logger.info('Xu ly so sanh bai bao cu va luu bai bao moi thanh cong')
        logger.info(f"\n {'-' * 50} \n")
        

if __name__ == "__main__":

    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    REGION_MODEL = config.AWS_VIRGINA_REGION
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

    compare_prompt_file = config.PROMPT_COMPARE_INFO_FILE
    compare_prompt = Utils.load_text(compare_prompt_file)
    logger.info(f"Đã tải prompt từ {compare_prompt_file}")

    processor = ArticleRiskMatchingExtractor(
        info_extractor=extractor,
        base_dynamo=base_dynamo.dynamodb,
        llm_manager=bedrock_manager,
        compare_prompt_template=compare_prompt
    )

    context_file = 'data/contents_old.json'
    bucket_name = "team253vpbank"
    key = "adverse_media_data/case1.json"

    contents = Utils.fetch_json_from_s3(bucket_name, key)
    logger.info(f"Đã load {len(contents)} bài báo từ file {context_file}")

    content = contents[1]

    table_config = {
        'media_config': {"adverse_media": "media_id"},
        'person_config': {"personal_info": "per_id"},
        'organization_config': {"organization_info": "org_id"},
        'p2m_config':{"personal2media": "p2m_id"},
        'o2m_config': {"org2media": "o2m_id"}
    }
    # table_media_config={"adverse_media": "media_id"}
    # table_person_config={"personal_info": "per_id"}
    # table_organization_config={"organization_info": "org_id"}
    # table_p2m_config={"personal2media": "p2m_id"}
    # table_o2m_config={"org2media": "o2m_id"}

    processor.process_article(
        article_text=content,
        table_config=table_config
    )
        

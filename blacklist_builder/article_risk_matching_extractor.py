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

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleRiskMatchingExtractor:
    def __init__(self, info_extractor, base_dynamo, llm_manager, compare_prompt_template):
        """
        :param gemini_extractor: công cụ trích xuất từ Gemini API
        :param dynamo_pusher: đối tượng DynamoPusher (bắt buộc)
        """
        self.extractor = info_extractor
        self.base_dynamo = base_dynamo
        self.dynamo_pusher = DynamoPusher(dynamodb=self.base_dynamo)

        self.query = DynamoQuery(self.base_dynamo)
        self.table_adverse_media = TableAdverseMedia(self.query)

        self.comparer = InfoComparer(base_dynamo, llm_manager, compare_prompt_template)

        self.new_item_builder = NewItemBuilder
        self.rebuild_item_builder = RebuildItemBuilder

        self.dynamo_deleter = DynamoDBDeleter(self.base_dynamo)


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
        # logger.info("🧠 Gọi LLM để trích xuất bài báo...")
        # answer, thinking = self.extractor.extract_from_article(article_text)

        # logger.debug(f"[process_article] Raw response:\n{answer}")
        # logger.info("📦 Đang xử lý kết quả trích xuất...")

        answer = Utils.load_text('./prepare_data/response_extractor.txt')

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
                'old_organization_ids': org_ids
            }
        )

    def process_article(self, article_text: str, table_config):
        logger.info(f"Tien hanh so sanh bao moi voi cac bai bao cu")
        logger.info(f"Noi dung bao moi {article_text[:100]}")
        new_personal_info_json, new_org_info_json, new_risk_info_json = self.extract_info_from_article(article_text)
        adverse_media_item, media_id = self.new_item_builder.create_adverse_media_item(risk_info=new_risk_info_json, partition_key='media_id', context=article_text)
       
        logger.debug(Utils.json_to_str(adverse_media_item))
        logger.debug(media_id)
        
        old_media_ids = self.table_adverse_media.get_all_media_ids()
        logger.info(f" Tìm thấy {len(old_media_ids)} old media \n List OLD MEDIA: {old_media_ids}")

        

        for old_media_id in old_media_ids:
            logger.info(f'Đang xu ly media_id: {old_media_id}')

            personal_duplicated, organization_duplicated = self.comparer.compare_info(new_article_text=article_text,
                                                                        new_personal_info=new_personal_info_json,
                                                                        new_org_info=new_org_info_json,
                                                                        media_id=old_media_id)


            rebuild_items, old_ids = self.prepare_dynamodb_items(personal_duplicated, organization_duplicated, new_risk_info_json, media_id)
            self.process_dynamodb(rebuild_items, old_ids, table_config)
        
        self.dynamo_pusher.insert(adverse_media_item, table_config=table_config['media_config'])
        
        logger.info('Lưu adverse media mới vào DynamoDB thành công')
        logger.info('Xu ly so sanh bai bao cu va luu bai bao moi thanh cong')
        

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
    bucket_name = "team253"
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
        

from typing import List, Dict, Any
from dynamodb.base_dynamo import BaseDynamoDB
from dynamodb.media_service import MediaService
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.table_personal2media import TablePersonal2Media
from dynamodb.table_personal_info import TablePersonalInfo
from dynamodb.table_org2media import TableOrg2Media
from dynamodb.table_org_info import TableOrganizationInfo
from dynamodb.table_adverse_media import TableAdverseMedia
import config
from dynamodb.base_dynamo import BaseDynamoDB
from utils import Utils
from logger import _setup_logger
from llm_model.bedrock_manager import BedrockModelManager
from blacklist_builder.faiss_handler.retrieval_faiss_personal_and_risk import PersonalInfoSimilarRetriever
import json
import re
import time 

logger = _setup_logger(__name__, config.LOG_LEVEL)

class InfoComparer:
    def __init__(self, base_dynamo,
                 llm_manager,
                 personal_prompt_compare_template,
                 organization_prompt_compare_template,
                 personal_info_similar_retriever: PersonalInfoSimilarRetriever = None):
        self.base_dynamo = base_dynamo
        self.query = DynamoQuery(base_dynamo)

        # Khởi tạo các bảng DynamoDB
        self.table_config = config.TABLE_CONFIG
        self.table_adverse_media = TableAdverseMedia(self.query, self.table_config)
        self.personal_linker = TablePersonal2Media(self.query, self.table_config)
        self.personal_info = TablePersonalInfo(self.query, self.table_config)
        self.org_linker = TableOrg2Media(self.query, self.table_config)
        self.org_info = TableOrganizationInfo(self.query, self.table_config)

        # Service tổng hợp để truy xuất dữ liệu theo media_id
        self.media_service = MediaService(
            per_linker=self.personal_linker,
            per_info=self.personal_info,
            org_linker=self.org_linker,
            org_info=self.org_info
        )

        self.personal_prompt_compare_template = personal_prompt_compare_template
        self.organization_prompt_compare_template = organization_prompt_compare_template
        self.llm_manager = llm_manager
        self.personal_info_similar_retriever = personal_info_similar_retriever

    def _create_compare_personal_info_prompt(self,
                                             new_personal_info: Dict[str, Any],
                                             old_personal_infos: List[Dict[str, Any]]):
        prompt = self.personal_prompt_compare_template.format(
                                            new_personal_info=Utils.json_to_str(new_personal_info),
                                            old_personal_infos=Utils.json_to_str(old_personal_infos)
                                            )
        logger.debug(f"[create_prompt] Đã tạo prompt: {prompt}...")
        return prompt

    def extract_personal_info_from_response(self, response: str) -> Dict[str, Any]: 
        pattern = r'(\{.*?\})'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1)
        else:
            return None
        
    
    def call_bedrock_to_compare_personal_info(self,
                                              new_personal_info: Dict[str, Any],
                                              old_personal_infos: List[Dict[str, Any]]):
        try:
            logger.debug("Khởi tạo prompt")
            prompt = self._create_compare_personal_info_prompt(
                new_personal_info=new_personal_info,
                old_personal_infos=old_personal_infos
            )

            logger.debug("Tiến hành gọi LLM COMPARER INFO")

            result, reasoning = self.llm_manager.generate(prompt, 'claude')
            logger.info(f"📌 Thinking :{reasoning}")
            logger.info(f"📌 Result : {result}")
            logger.info(f"Goi mo hinh so sanh thanh cong")
            return result
        except Exception as e:
            logger.error(f"❌ Lỗi khi gọi LLM COMPARE INFO: {e}")
            return ""
         
    def compare_personal_info(self, new_personal_info: Dict, 
                              old_personal_infos: List[Dict]):
        logger.debug("So sánh thông tin cá nhân mới với thông tin cũ")
        logger.debug(f"Thông tin cá nhân mới: {Utils.json_to_str(new_personal_info)}")
        logger.debug(f"Thông tin cá nhân cũ: {Utils.json_to_str(old_personal_infos)}")
        resp = self.call_bedrock_to_compare_personal_info(
            new_personal_info=new_personal_info,
            old_personal_infos=old_personal_infos
        )

        personal_info = self.extract_personal_info_from_response(resp)
        personal_info = Utils.json_str_to_dict(personal_info)
        logger.info(f"Phản hồi từ mô hình: {personal_info}")
        # logger.info(f"Phản hồi từ mô hình: {resp}")
        return personal_info

    def _create_compare_organization_info_prompt(self,
                                             new_organization_info: Dict[str, Any],
                                             old_organization_infos: List[Dict[str, Any]]):
        prompt = self.organization_prompt_compare_template.format(
                                            new_organization_info=Utils.json_to_str(new_organization_info),
                                            old_organization_infos=Utils.json_to_str(old_organization_infos)
                                            )
        logger.debug(f"[create_prompt] Đã tạo prompt: {prompt}...")
        return prompt

    def extract_organization_info_from_response(self, response: str) -> Dict[str, Any]: 
        pattern = r'(\{.*?\})'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1)
        else:
            return None
        
    
    def call_bedrock_to_compare_organization_info(self,
                                              new_organization_info: Dict[str, Any],
                                              old_organization_infos: List[Dict[str, Any]]):
        try:
            logger.debug("Khởi tạo prompt")
            prompt = self._create_compare_organization_info_prompt(
                new_organization_info=new_organization_info,
                old_organization_infos=old_organization_infos
            )

            logger.debug("Tiến hành gọi LLM COMPARER INFO")

            result, reasoning = self.llm_manager.generate(prompt, 'claude')
            logger.info(f"📌 Thinking :{reasoning}")
            logger.info(f"📌 Result : {result}")
            logger.info(f"Goi mo hinh so sanh thanh cong")
            return result
        except Exception as e:
            logger.error(f"❌ Lỗi khi gọi LLM COMPARE INFO: {e}")
            return ""
         
    def compare_organization_info(self, new_organization_info: Dict, 
                              old_organization_infos: List[Dict]):
        logger.debug("So sánh thông tin cá nhân mới với thông tin cũ")
        logger.debug(f"Thông tin cá nhân mới: {Utils.json_to_str(new_organization_info)}")
        logger.debug(f"Thông tin cá nhân cũ: {Utils.json_to_str(old_organization_infos)}")
        resp = self.call_bedrock_to_compare_organization_info(
            new_organization_info=new_organization_info,
            old_organization_infos=old_organization_infos
        )

        organization_info = self.extract_organization_info_from_response(resp)
        organization_info = Utils.json_str_to_dict(organization_info)
        logger.info(f"Phản hồi từ mô hình: {organization_info}")
        # logger.info(f"Phản hồi từ mô hình: {resp}")
        return organization_info

def main():
    # Load AWS credentials
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    REGION_MODEL = config.AWS_VIRGINA_REGION
    MODEL_ID = config.CLAUDE_35_HAIKU_CROSS_REGION_VIRGINA_MODEL_ID

    bedrock_manager = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION_MODEL,
        default_model_id=MODEL_ID
    )

    # Khởi tạo kết nối DynamoDB
    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )

    personal_compare_prompt_file = './prompts/prompt_compare_new_old_personal_risk_info.txt' 
    personal_compare_prompt = Utils.load_text(personal_compare_prompt_file)
    logger.info(f"Đã tải prompt từ {personal_compare_prompt_file}")
    logger.debug(f"Prompt nội dung: {personal_compare_prompt}")

    organization_compare_prompt_file = 'D:/VPBankHackathon/prompts/prompt_compare_new_old_organization.txt' 
    organization_compare_prompt = Utils.load_text(organization_compare_prompt_file)
    logger.info(f"Đã tải prompt từ {organization_compare_prompt_file}")
    logger.debug(f"Prompt nội dung: {organization_compare_prompt}")

    # Khởi tạo class InfoComparer
    comparer = InfoComparer(base_dynamo.dynamodb, 
                            bedrock_manager, 
                            personal_prompt_compare_template=personal_compare_prompt,
                            organization_prompt_compare_template=organization_compare_prompt)

    new_personal_info = Utils.load_json('./data/items/new_personal_info.json')
    old_personal_infos = Utils.load_json('./data/items/old_personal_infos.json')

    start = time.time()
    comparer.compare_personal_info(new_personal_info=new_personal_info, 
                                   old_personal_infos=old_personal_infos)
    end = time.time()
    logger.info(f"Thời gian so sánh thông tin cá nhân: {end - start} giây")
                                   


    # # Khởi tạo class InfoComparer
    # comparer = InfoComparer(base_dynamo.dynamodb, bedrock_manager, compare_prompt)

    # new_organization_info = Utils.load_json('./data/items/new_organization_info.json')
    # old_organization_infos = Utils.load_json('./data/items/old_organization_infos.json')

    # comparer.compare_organization_info(new_organization_info=new_organization_info, 
    #                                old_organization_infos=old_organization_infos)

    # # Nhập media_id để test
    # media_id = "media_id_1752428383368304"

    # Gọi hàm lấy dữ liệu cũ
    # old_article_text, old_personal_info, old_org_info = comparer.get_old_info(media_id)

    # # In ra thông tin đã lấy
    # print("📄 Nội dung bài báo cũ:")
    # print(old_article_text)

    # print("\n👤 Personal Info:")
    # print(Utils.json_to_str(old_personal_info))

    # print("\n🏢 Organization Info:")
    # print(Utils.json_to_str(old_org_info))

    # new_org_info = Utils.load_json('./prepare_data/new_org_info.json')
    # new_personal_info = Utils.load_json('./prepare_data/new_personal_info.json')


    # print(Utils.json_to_str(new_org_info))
    # print(Utils.json_to_str(new_personal_info))

    # context_file = 'data/contents_old.json'
    # bucket_name = "team253vpbank"
    # key = "adverse_media_data/case1.json"

    # contents = Utils.fetch_json_from_s3(bucket_name, key)
    # logger.info(f"Đã load {len(contents)} bài báo từ file {context_file}")

    # content = contents[1]

    # personal_duplicated, organization_duplicated = comparer.compare_info(new_article_text=content,
    #                                                                     new_personal_info=new_personal_info,
    #                                                                     new_org_info=new_org_info,
    #                                                                     media_id=media_id
    #                                                                     )

        

if __name__ == "__main__":
    main()
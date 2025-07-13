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
import json

logger = _setup_logger(__name__, config.LOG_LEVEL)

class InfoComparer:
    def __init__(self, base_dynamo, llm_manager, prompt_compare_template):
        self.base_dynamo = base_dynamo
        self.query = DynamoQuery(base_dynamo)

        # Khởi tạo các bảng DynamoDB
        self.table_adverse_media = TableAdverseMedia(self.query)
        self.personal_linker = TablePersonal2Media(self.query)
        self.personal_info = TablePersonalInfo(self.query)
        self.org_linker = TableOrg2Media(self.query)
        self.org_info = TableOrganizationInfo(self.query)

        # Service tổng hợp để truy xuất dữ liệu theo media_id
        self.media_service = MediaService(
            per_linker=self.personal_linker,
            per_info=self.personal_info,
            org_linker=self.org_linker,
            org_info=self.org_info
        )

        self.prompt_template = prompt_compare_template
        self.llm_manager = llm_manager

    def _create_compare_prompt(self, 
                               old_article_text: str, 
                               old_personal_info: List[Dict[str, Any]],
                               old_organizer_info: List[Dict[str, Any]], 
                               new_article_text: str, 
                               new_personal_info: str,
                               new_organizer_info: str):
        prompt = self.prompt_template.format(old_article_text=old_article_text,
                                            old_personal_info=Utils.json_to_str(old_personal_info),
                                            old_organizer_info=Utils.json_to_str(old_organizer_info),
                                            new_article_text=new_article_text,
                                            new_personal_info=Utils.json_to_str(new_personal_info),
                                            new_organizer_info=Utils.json_to_str(new_organizer_info)
                                            )
        logger.debug(f"[create_prompt] Đã tạo prompt: {prompt}...")
        return prompt

    def call_deepseek_to_compare(self, 
                                 old_article_text: str, 
                                 old_personal_info: List[Dict[str, Any]], 
                                 old_organizer_info: List[Dict[str, Any]],
                                 new_article_text: str, 
                                 new_personal_info: str,
                                 new_organizer_info: str) -> str:
        """
        Gọi mô hình DeepSeek-R1 để phân tích prompt.
        """
        try:
            logger.debug("Khởi tạo prompt")
            prompt = self._create_compare_prompt(
                old_article_text=old_article_text,
                old_personal_info=old_personal_info,
                old_organizer_info=old_organizer_info,
                new_article_text=new_article_text,
                new_personal_info=new_personal_info,
                new_organizer_info=new_organizer_info
            )

            logger.debug("Tiến hành gọi deepseek")

            result, reasoning = self.llm_manager.generate_deepseek(prompt)
            logger.info(f"📌 Thinking (DeepSeek):{reasoning}")
            logger.info(f"📌 Result (DeepSeek): {result}")
            logger.info(f"Goi mo hinh so sanh thanh cong")
            return result
        except Exception as e:
            logger.error(f"❌ Lỗi khi gọi DeepSeek: {e}")
            return ""

    def extract_resp_json(self, json_str):
        """
        Loại bỏ dấu markdown ```json và ``` rồi chuyển đổi nội dung JSON thành dict.
        """
        # Bỏ dấu markdown đầu và cuối nếu có
        cleaned_str = json_str.strip()
        if cleaned_str.startswith("```json"):
            cleaned_str = cleaned_str[len("```json"):].strip()
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-len("```")].strip()

        # Parse thành dict
        try:
            parsed = json.loads(cleaned_str)
            personal_duplicated = parsed[0]
            organization_duplicated = parsed[1]

            logger.info(f"Trich xuat response tu LLM thanh cong")
            return personal_duplicated, organization_duplicated
        except json.JSONDecodeError as e:
            raise ValueError(f"Lỗi khi parse JSON: {e}")

    def get_old_info(self, media_id: str) -> tuple[str, List[dict], List[dict]]:
        """
        Lấy thông tin cũ từ media_id gồm: nội dung bài báo, personal_info, org_info.
        """
        try:
            old_media_item = self.table_adverse_media.get_document_by_media_id(media_id)
            logger.debug(Utils.json_to_str(old_media_item))
            old_article_text = old_media_item['content']
            old_personal_info = self.media_service.get_personal_info_by_media(media_id)
            old_org_info = self.media_service.get_org_info_by_media(media_id)

            logger.info(f"Lay thong tin cua bai bao cu {media_id} thanh cong")
            return old_article_text, old_personal_info, old_org_info
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy thông tin cũ từ media_id {media_id}: {e}")
            return "", [], []
        
    def compare_info(self, new_article_text: str, 
                    new_personal_info: List[Dict[str, Any]], 
                    new_org_info: List[Dict[str, Any]],
                    media_id: str) -> List[Dict[str, Any]]:
        """
        So sánh personal_info mới với dữ liệu cũ theo media_id.
        """
        old_article_text, old_personal_info, old_org_info = self.get_old_info(media_id)

        logger.debug("📄 Nội dung bài báo cũ:")
        logger.debug(old_article_text)

        logger.debug("\n👤 Personal Info:")
        logger.debug(Utils.json_to_str(old_personal_info))

        logger.debug("\n🏢 Organization Info:")
        logger.debug(Utils.json_to_str(old_org_info))

        resp = self.call_deepseek_to_compare(old_article_text=old_article_text,
                                               old_personal_info=old_personal_info,
                                               old_organizer_info=old_org_info,
                                               new_article_text=new_article_text,
                                               new_personal_info=new_personal_info,
                                               new_organizer_info=new_org_info)

        personal_duplicated, organization_duplicated = self.extract_resp_json(resp)
        logger.info(f"Tim thay {len(personal_duplicated)} CA NHAN TRUNG")
        logger.info(f"Tim thay {len(organization_duplicated)} TO CHUC TRUNG")

        return personal_duplicated, organization_duplicated

if __name__ == "__main__":
    # Load AWS credentials
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    REGION_MODEL = config.AWS_VIRGINA_REGION
    MODEL_ID = config.DEEPSEEK_MODEL_VIRGINA_ID

    manager = BedrockModelManager(
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

    compare_prompt_file = config.PROMPT_COMPARE_INFO_FILE
    compare_prompt = Utils.load_text(compare_prompt_file)
    logger.info(f"Đã tải prompt từ {compare_prompt_file}")

    # Khởi tạo class InfoComparer
    comparer = InfoComparer(base_dynamo.dynamodb, manager, compare_prompt)

    # Nhập media_id để test
    media_id = "media_id_1752428383368304"

    # Gọi hàm lấy dữ liệu cũ
    # old_article_text, old_personal_info, old_org_info = comparer.get_old_info(media_id)

    # # In ra thông tin đã lấy
    # print("📄 Nội dung bài báo cũ:")
    # print(old_article_text)

    # print("\n👤 Personal Info:")
    # print(Utils.json_to_str(old_personal_info))

    # print("\n🏢 Organization Info:")
    # print(Utils.json_to_str(old_org_info))

    new_org_info = Utils.load_json('./prepare_data/new_org_info.json')
    new_personal_info = Utils.load_json('./prepare_data/new_personal_info.json')


    print(Utils.json_to_str(new_org_info))
    print(Utils.json_to_str(new_personal_info))

    context_file = 'data/contents_old.json'
    bucket_name = "team253"
    key = "adverse_media_data/case1.json"

    contents = Utils.fetch_json_from_s3(bucket_name, key)
    logger.info(f"Đã load {len(contents)} bài báo từ file {context_file}")

    content = contents[1]

    personal_duplicated, organization_duplicated = comparer.compare_info(new_article_text=content,
                                                                        new_personal_info=new_personal_info,
                                                                        new_org_info=new_org_info,
                                                                        media_id=media_id
                                                                        )
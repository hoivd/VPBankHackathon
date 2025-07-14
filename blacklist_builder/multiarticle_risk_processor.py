import logging
from blacklist_builder.article_risk_processor import ArticleRiskProcessor
from logger import _setup_logger
import config
from utils import Utils
from blacklist_builder.article_extractor import ArticlePersonExtractor
import time
from llm_model.bedrock_manager import BedrockModelManager
from dynamodb.dynamo_table_checker import DynamoDBTableChecker
from dynamodb.base_dynamo import BaseDynamoDB
from dynamodb.media_service import MediaService
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.table_personal2media import TablePersonal2Media
from dynamodb.table_personal_info import TablePersonalInfo
from dynamodb.table_org2media import TableOrg2Media
from dynamodb.table_org_info import TableOrganizationInfo
from blacklist_builder.article_risk_matching_extractor import ArticleRiskMatchingExtractor


logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleBatchRunner:
    def __init__(self, new_article_processor, rebuild_article_processor, base_dynamo):
        """
        Args:
            article_risk_processor (ArticleRiskProcessor): bộ xử lý từng bài báo
        """
        self.new_processor = new_article_processor
        self.rebuild_processor = rebuild_article_processor
        self.base_dynamo = base_dynamo
        self.dynamo_checker = DynamoDBTableChecker(dynamodb=self.base_dynamo.dynamodb)

    def is_per_and_org_empty(self) -> bool:
        person_empty = self.dynamo_checker.is_table_empty("personal_info")
        org_empty = self.dynamo_checker.is_table_empty("organization_info")
        if person_empty == False or org_empty == False:
            logger.info("✅ Bảng 'personal_info' và 'organization_info' đều có dữ liệu.")
            return False
        elif person_empty == True and org_empty == True:
            logger.info("✅ Bảng 'personal_info' và 'organization_info' đều trống.")
            return True

    def run_from_list(self, article_list: list[str], table_config: dict):
        logger.info(f"[ArticleBatchRunner] Bắt đầu xử lý {len(article_list)} bài báo...")
        success = 0
        failure = 0

        total_start = time.time()
        for idx, article in enumerate(article_list):
            logger.info(f"[Batch] 🔎 Bài báo {idx + 1}/{len(article_list)}")
            try:
                start = time.time()
                if self.is_per_and_org_empty():
                    logger.info("Bảng 'personal_info' hoặc 'organization_info' chưa có dữ liệu, Tiến hành trích xuất xử lý bài báo mới.")
                    logger.info("Tiến hành trích xuất thông tin và insert vào DynamoDB...")
                    self.new_processor.process_article(
                        article_text=article,
                        table_config=table_config
                    )
                else:
                    logger.info("Bảng 'personal_info' hoặc 'organization_info' đã có dữ liệu, Tiến hành so sánh ghép nối với bài báo cũ.")
                    self.rebuild_processor.process_article(
                        article_text=article,
                        table_config=table_config
                    )
                    
                    logger.info("Tiến hành so sánh với bài báo cũ và cập nhật vào DynamoDB...")
                success += 1
                end = time.time()
                logger.info(f"[Batch] ✅ Bài báo {idx + 1} xử lý thành công! Thời gian: {end - start:.2f} giây")
            except Exception as e:
                logger.error(f"[Batch] ❌ Lỗi khi xử lý bài báo {idx + 1}: {e}")
                failure += 1
                end = time.time()
                logger.error(f"[Batch] Thời gian xử lý bài báo {idx + 1} thất bại: {end - start:.2f} giây")

        total_end = time.time()
        logger.info(f"[ArticleBatchRunner] ✅ Hoàn tất: {success} thành công, {failure} lỗi. Tong thoi gian {total_end - total_start:.2f} giay")

    def run_from_jsonl(self, file_path: str, text_key: str, table_config: dict):
        """
        Đọc nhiều bài báo từ file .jsonl, mỗi dòng chứa bài báo dạng dict (có key chứa nội dung)

        Args:
            file_path (str): đường dẫn file .jsonl
            text_key (str): tên key chứa bài báo trong mỗi dòng json
            table_config (dict): thông tin cấu hình bảng DynamoDB
        """
        from utils import Utils
        data = Utils.load_jsonl(file_path)
        articles = [item[text_key] for item in data if text_key in item]
        self.run_from_list(articles, table_config=table_config)

if __name__ == "__main__":
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION_MODEL = config.AWS_VIRGINA_REGION
    REGION = config.AWS_REGION

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )
    
    MODEL_ID = "arn:aws:bedrock:us-east-1:048013208071:inference-profile/us.deepseek.r1-v1:0"

    # Khởi tạo manager
    llm_person_extractor = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION_MODEL,
        default_model_id=MODEL_ID
    )

    extractor_prompt_file = config.PROMPT_EXTRACTOR_FILE
    extractor_prompt = Utils.load_text(extractor_prompt_file)
    logger.info(f"Đã tải prompt từ {extractor_prompt_file}")

    personal_extractor = ArticlePersonExtractor(model_manager=llm_person_extractor, prompt_template=extractor_prompt)
    logger.info("Đã khởi tạo ArticlePersonExtractor")

    new_processor = ArticleRiskProcessor(
        info_extractor=personal_extractor,
        base_dynamo=base_dynamo.dynamodb
    )


    extractor_prompt_file = config.PROMPT_EXTRACTOR_FILE
    extractor_prompt = Utils.load_text(extractor_prompt_file)
    logger.info(f"Đã tải prompt từ {extractor_prompt_file}")

    compare_prompt_file = config.PROMPT_COMPARE_INFO_FILE
    compare_prompt = Utils.load_text(compare_prompt_file)
    logger.info(f"Đã tải prompt từ {compare_prompt_file}")

    COMPARE_INFO_MODEL_ID =  config.CLAUDE_35_HAIKU_MODEL_ID

    llm_compare_info = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION_MODEL,
        default_model_id=COMPARE_INFO_MODEL_ID
    )


    rebuild_processor = ArticleRiskMatchingExtractor(
        info_extractor=personal_extractor,
        base_dynamo=base_dynamo.dynamodb,
        llm_manager=llm_compare_info,
        compare_prompt_template=compare_prompt
    )



    table_config = config.TABLE_CONFIG

    batch_runner = ArticleBatchRunner(new_article_processor=new_processor, rebuild_article_processor=rebuild_processor, base_dynamo=base_dynamo)

    context_file = 'data/contents_old.json'
    bucket_name = "team253"
    key = "adverse_media_data/case1.json"

    contents = Utils.fetch_json_from_s3(bucket_name, key)
    logger.info(f"Đã load {len(contents)} bài báo từ file {context_file}")

    batch_runner.run_from_list(
        article_list=contents,
        table_config=table_config
    )
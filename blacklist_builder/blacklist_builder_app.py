import config
import logging
from utils import Utils
from logger import _setup_logger

from dynamodb.base_dynamo import BaseDynamoDB
from llm_model.bedrock_manager import BedrockModelManager
from blacklist_builder.article_extractor import ArticlePersonExtractor
from blacklist_builder.article_risk_processor import ArticleRiskProcessor
from blacklist_builder.article_risk_matching_extractor import ArticleRiskMatchingExtractor
from blacklist_builder.multiarticle_risk_processor import ArticleBatchRunner
from embedder.model_embedder import ModelEmbedder
from embedder.article_embedder import ArticleEmbedder
from embedder.personal_embedder import PersonalEmbedder
from embedder.organization_embedder import OrganizationEmbedder
from faiss_manager.faiss_index_manager import FaissIndexManager
from datetime import datetime
import os
from dotenv import load_dotenv
from S3.s3_connector import S3Connector
from S3.s3_uploader import S3Uploader

# Load từ file .env (mặc định ở thư mục hiện tại)
load_dotenv()

logger = _setup_logger(__name__, config.LOG_LEVEL)

class BlacklistBuilderApp:
    def __init__(self):
         # ===== Dinh nghia credentials aws =====
        self.AWS_ACCESS_KEY = Utils.load_api_key_from_env("NEW_AWS_ACCESS_KEY")
        self.AWS_SECRET_KEY = Utils.load_api_key_from_env("NEW_AWS_SECRET_KEY")

        # ===== Dinh nghia region =====
        self.REGION_MODEL = config.AWS_VIRGINA_REGION
        self.REGION = config.AWS_REGION

        # ===== Dinh nghia id model =====
        self.PERSONAL_MODEL = config.DEEPSEEK_MODEL_VIRGINA_ID
        self.COMPARE_MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

        # ===== Dinh nghia id model =====
        self.EXTRACTOR_PROMPT =  config.PROMPT_EXTRACTOR_FILE
        self.COMPARE_INFO_PROMPT = config.PROMPT_COMPARE_INFO_FILE

        # ===== Dinh nghia table config =====
        self.TABLE_CONFIG = config.TABLE_CONFIG

        # ===== Khởi tạo DynamoDB =====
        self.base_dynamo = BaseDynamoDB(
            region_name=self.REGION,
            access_key=self.AWS_ACCESS_KEY,
            secret_key=self.AWS_SECRET_KEY
        )

        model_name = config.EMBEDDING_MODEL_NAME
        self.base_model_embedder = ModelEmbedder(model_name=model_name)
        self.article_embedder = ArticleEmbedder(base_embedder=self.base_model_embedder)
        self.personal_embeder = PersonalEmbedder(base_embedder=self.base_model_embedder)
        self.org_embedder = OrganizationEmbedder(base_embedder=self.base_model_embedder)

        self.article_faiss_manager = FaissIndexManager(config.EMBEDDING_DIM)
        self.personal_faiss_manager = FaissIndexManager(config.EMBEDDING_DIM)
        self.org_faiss_manager = FaissIndexManager(config.EMBEDDING_DIM)

        # ===== Khởi tạo model trích xuất thông tin cá nhân =====
        self._init_person_extractor()

        # ===== Khởi tạo model so sánh thông tin cũ =====
        self._init_compare_extractor()

        # ===== Khởi tạo runner =====
        self.batch_runner = ArticleBatchRunner(
            new_article_processor=self.new_processor,
            rebuild_article_processor=self.rebuild_processor,
            base_dynamo=self.base_dynamo
        )

    def _init_person_extractor(self):
        person_model_id = self.PERSONAL_MODEL
        person_model_manager = BedrockModelManager(
            aws_access_key_id=self.AWS_ACCESS_KEY,
            aws_secret_access_key=self.AWS_SECRET_KEY,
            region_name=self.REGION_MODEL,
            default_model_id=person_model_id
        )

        prompt_path = self.EXTRACTOR_PROMPT
        extractor_prompt = Utils.load_text(prompt_path)
        logger.info(f"✅ Đã load prompt trích xuất từ {prompt_path}")

        self.personal_extractor = ArticlePersonExtractor(
            model_manager=person_model_manager,
            prompt_template=extractor_prompt
        )

        self.new_processor = ArticleRiskProcessor(
            info_extractor=self.personal_extractor,
            base_dynamo=self.base_dynamo.dynamodb,
            article_embedder=self.article_embedder,
            personal_embedder=self.personal_embeder,
            org_embedder=self.org_embedder,
            article_faiss_manager=self.article_faiss_manager,
            personal_faiss_manager=self.personal_faiss_manager,
            org_faiss_manager=self.org_faiss_manager
        )

    def _init_compare_extractor(self):
        compare_model_id = self.COMPARE_MODEL
        compare_model_manager = BedrockModelManager(
            aws_access_key_id=self.AWS_ACCESS_KEY,
            aws_secret_access_key=self.AWS_SECRET_KEY,
            region_name=self.REGION_MODEL,
            default_model_id=compare_model_id
        )

        compare_prompt_path = self.COMPARE_INFO_PROMPT
        compare_prompt = Utils.load_text(compare_prompt_path)
        logger.info(f"✅ Đã load prompt so sánh từ {compare_prompt_path}")

        self.rebuild_processor = ArticleRiskMatchingExtractor(
            info_extractor=self.personal_extractor,
            base_dynamo=self.base_dynamo.dynamodb,
            llm_manager=compare_model_manager,
            compare_prompt_template=compare_prompt,
            article_embedder=self.article_embedder,
            personal_embedder=self.personal_embeder,
            org_embedder=self.org_embedder,
            article_faiss_manager=self.article_faiss_manager,
            personal_faiss_manager=self.personal_faiss_manager,
            org_faiss_manager=self.org_faiss_manager
        )

    def save_article_faiss_index(self, article_index_path: str):
        logger.info(f"💾 Đang lưu FAISS index bài viết tại {article_index_path}...")
        self.article_faiss_manager.save_index(article_index_path)
        logger.info("✅ Đã lưu FAISS index bài viết thành công.")

    def save_personal_faiss_index(self, personal_index_path: str):
        logger.info(f"💾 Đang lưu FAISS index cá nhân tại {personal_index_path}...")
        self.personal_faiss_manager.save_index(personal_index_path)
        logger.info("✅ Đã lưu FAISS index cá nhân thành công.")

    def save_org_faiss_index(self, org_index_path: str):
        logger.info(f"💾 Đang lưu FAISS index tổ chức tại {org_index_path}...")
        self.org_faiss_manager.save_index(org_index_path)
        logger.info("✅ Đã lưu FAISS index tổ chức thành công.")

    def save_all_faiss_indexes(
        self,
        base_dir: str = "faiss_indexes",
        s3_uploader=None,
        s3_bucket: str = None,
        s3_prefix: str = None
    ):
        """
        Lưu toàn bộ FAISS index vào thư mục con theo timestamp trong thư mục gốc chỉ định.
        Đồng thời upload lên S3 nếu được cấu hình.

        :param base_dir: thư mục gốc chứa các bản ghi FAISS index theo thời gian
        :param s3_uploader: instance S3Uploader nếu cần đẩy lên S3
        :param s3_bucket: tên bucket S3 (nếu có)
        :param s3_prefix: tiền tố đường dẫn trên S3 (nếu không truyền sẽ dùng theo ngày giờ)
        """
        # ==== Tạo thư mục mới theo thời gian thực ====
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        local_dir = os.path.join(base_dir, timestamp)
        os.makedirs(local_dir, exist_ok=True)

        article_index_path = os.path.join(local_dir, "article_faiss_index")
        personal_index_path = os.path.join(local_dir, "personal_faiss_index")
        org_index_path = os.path.join(local_dir, "org_faiss_index")

        # ==== Tạo prefix S3 nếu không có ====
        s3_prefix = s3_prefix or f"{base_dir}/{timestamp}/"

        logger.info(f"💾 Đang lưu tất cả FAISS indexes vào thư mục: {local_dir}")

        self.save_article_faiss_index(article_index_path)

        self.save_personal_faiss_index(personal_index_path)

        self.save_org_faiss_index(org_index_path)

        logger.info("✅ Đã lưu tất cả FAISS indexes thành công.")
        logger.info(f"📂 Đường dẫn local: {local_dir}")
        if s3_bucket:
            logger.info(f"Đang upload thu muc {local_dir} lên S3...")
            uploader.upload_folder(folder_path=local_dir, bucket_name=bucket_name, object_key_prefix=base_dir)
            logger.info(f"☁️ Đã đẩy lên S3: s3://{s3_bucket}/{s3_prefix}")

    def run_from_s3(self, bucket_name: str, key: str):
        logger.info(f"⬇️ Đang tải dữ liệu từ S3: bucket='{bucket_name}', key='{key}'...")
        articles = Utils.fetch_json_from_s3(bucket_name, key)
        logger.info(f"✅ Đã load {len(articles)} bài báo từ S3.")
        self.batch_runner.run_from_list(articles, table_config=self.TABLE_CONFIG)

    def run_from_jsonl(self, file_path: str, text_key: str):
        logger.info(f"⬇️ Đang tải dữ liệu từ file JSONL: {file_path}")
        self.batch_runner.run_from_jsonl(file_path, text_key, table_config=self.TABLE_CONFIG)

    def run_from_list(self, articles: list[str]):
        logger.info(f"📝 Đang xử lý danh sách bài báo ({len(articles)} bài)...")
        self.batch_runner.run_from_list(articles, table_config=self.TABLE_CONFIG)

if __name__ == "__main__":
    app = BlacklistBuilderApp()

    # bucket_name = "team253"
    # key = "adverse_media_data/case1.json"
    # app.run_from_s3(bucket_name, key)
    S3_AWS_ACCESS_KEY = Utils.load_api_key_from_env("NEW_AWS_ACCESS_KEY")
    S3_AWS_SECRET_KEY = Utils.load_api_key_from_env("NEW_AWS_SECRET_KEY")
    S3_REGION = config.AWS_REGION

    bucket_name = "team253vpbank"
    key = "adverse_media_data/case1.json"

    contents_case1 = Utils.fetch_json_from_s3(bucket_name, 
                                            key,
                                            region_name=S3_REGION,
                                            aws_access_key=S3_AWS_ACCESS_KEY,
                                            aws_secret_key=S3_AWS_SECRET_KEY)
    logger.info(f"Đã load {len(contents_case1)} bài báo từ file {key}")


    context_file = 'data/contents_old.json'
    bucket_name = "team253vpbank"
    key2 = "adverse_media_data/case2.json"

    contents_case2 = Utils.fetch_json_from_s3(bucket_name, 
                                            key2,
                                            region_name=S3_REGION,
                                            aws_access_key=S3_AWS_ACCESS_KEY,
                                            aws_secret_key=S3_AWS_SECRET_KEY)
    logger.info(f"Đã load {len(contents_case2)} bài báo từ file {key2}")
    
    corpus = contents_case1 + contents_case2
    app.run_from_list(corpus)

    AWS_ACCESS_KEY = os.getenv("NEW_AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("NEW_AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    print(f"AWS_ACCESS_KEY: {AWS_ACCESS_KEY}")
    print(f"AWS_SECRET_KEY: {AWS_SECRET_KEY}")
    print(f"REGION: {REGION}")

    # Tạo kết nối và fetcher
    connector = S3Connector(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION
    )
    uploader = S3Uploader(connector.get_client())

    app.save_all_faiss_indexes(
        base_dir="faiss_indexes",
        s3_uploader=None,  # Hoặc truyền vào instance S3Uploader nếu cần upload lên S3
        s3_bucket=bucket_name,  # Hoặc tên bucket S3 nếu cần
        s3_prefix="faiss_indexes"
    )

    logger.info("✅ Hoàn thành xử lý bài báo.")
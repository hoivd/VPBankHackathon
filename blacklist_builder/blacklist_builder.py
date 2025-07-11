import logging
from blacklist_builder.article_risk_processor import ArticleRiskProcessor
from mongodb.mongo_pusher import MongoPusher
from logger import _setup_logger
import config
from utils import Utils
from blacklist_builder.article_extractor import ArticlePersonExtractor
import time

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleBatchRunner:
    def __init__(self, article_risk_processor, mongo_pusher):
        """
        Args:
            article_risk_processor (ArticleRiskProcessor): bộ xử lý từng bài báo
            mongo_pusher (MongoPusher): đối tượng thao tác với MongoDB
        """
        self.processor = article_risk_processor
        self.mongo_pusher = mongo_pusher

    def run_from_list(self, article_list: list[str], col_person: str, col_c2m: str, col_media: str):
        logger.info(f"[ArticleBatchRunner] Bắt đầu xử lý {len(article_list)} bài báo...")
        success = 0
        failure = 0

        for idx, article in enumerate(article_list):
            logger.info(f"[Batch] 🔎 Bài báo {idx + 1}/{len(article_list)}")
            try:
                start = time.time()
                self.processor.process_article(
                    article_text=article,
                    col_person=col_person,
                    col_c2m=col_c2m,
                    col_media=col_media
                )
                success += 1
                end = time.time()
                logger.info(f"[Batch] ✅ Bài báo {idx + 1} xử lý thành công! Thời gian: {end - start:.2f} giây")
            except Exception as e:
                logger.error(f"[Batch] ❌ Lỗi khi xử lý bài báo {idx + 1}: {e}")
                failure += 1
                end = time.time()
                logger.error(f"[Batch] Thời gian xử lý bài báo {idx + 1} thất bại: {end - start:.2f} giây")

        logger.info(f"[ArticleBatchRunner] ✅ Hoàn tất: {success} thành công, {failure} lỗi.")

    def run_from_jsonl(self, file_path: str, text_key: str, col_person: str, col_c2m: str, col_media: str):
        """
        Đọc nhiều bài báo từ file .jsonl, mỗi dòng chứa bài báo dạng dict (có key chứa nội dung)

        Args:
            file_path (str): đường dẫn file .jsonl
            text_key (str): tên key chứa bài báo trong mỗi dòng json
        """
        from utils import Utils
        data = Utils.load_jsonl(file_path)
        articles = [item[text_key] for item in data if text_key in item]
        self.run_from_list(articles, col_person, col_c2m, col_media)

if __name__ == "__main__":
    # 1. Tạo các đối tượng
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
    processor = ArticleRiskProcessor(gemini_extractor=extractor, mongo_pusher=mongo_pusher)

    context_file = 'data/contents_old.json'
    json = Utils.load_json(context_file)
    logger.info(f"Đã load {len(json)} bài báo từ file {context_file}")

    # 2. Tạo batch runner
    batch_runner = ArticleBatchRunner(article_risk_processor=processor, mongo_pusher=mongo_pusher)


    # 3. Chạy từ danh sách bài báo
    batch_runner.run_from_list(article_list=json, 
                            col_person=customer_collection, 
                            col_c2m=cust2media_collection, 
                            col_media=media_collection)

    # # 4. Hoặc chạy từ file .jsonl
    # batch_runner.run_from_jsonl(file_path="data/articles.jsonl", 
    #                             text_key="content", 
    #                             col_person="personal_info", 
    #                             col_c2m="customer2media", 
    #                             col_media="adverse_media")
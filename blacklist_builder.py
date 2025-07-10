import logging
from article_risk_processor import ArticleRiskProcessor
from mongo_pusher import MongoPusher
from logger import _setup_logger
import config

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
                self.processor.process_article(
                    article_text=article,
                    col_person=col_person,
                    col_c2m=col_c2m,
                    col_media=col_media
                )
                success += 1
            except Exception as e:
                logger.error(f"[Batch] ❌ Lỗi khi xử lý bài báo {idx + 1}: {e}")
                failure += 1

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
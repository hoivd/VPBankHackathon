from utils import Utils
from logger import _setup_logger
import config
import time
from llm_model.model_manager import LlmModelManager
from llm_model.bedrock_manager import BedrockModelManager

logger = _setup_logger(__name__, config.LOG_LEVEL)


class ArticlePersonExtractor:
    def __init__(self, model_manager: LlmModelManager, prompt_template: str):
        # Thiết lập API key và mô hình
        self.model_manager = model_manager

        self.extractor_prompt_template = prompt_template

    def _create_prompt(self, article_text: str) -> str:
        prompt = self.extractor_prompt_template.format(article_text=article_text)
        logger.debug(f"[create_prompt] Đã tạo prompt: {prompt}...")
        return prompt

    def extract_from_article(self, article_text: str) -> str:
        prompt = self._create_prompt(article_text)
        logger.debug("[extract_from_article] Prompt đã được tạo.")
        start = time.time()
        answer, thinking = self.model_manager.generate(prompt=prompt, model_type='deepseek')
        end = time.time()
        logger.info(f"[extract_from_article] Thời gian gọi mô hình: {end - start:.2f} giây")
        logger.debug("[extract_from_article] Phản hồi đã nhận từ mô hình Gemini.")
        return (answer, thinking)

    def extract_from_articles(self, article_list: list[str]) -> list[str | None]:
        results = []
        for idx, article in enumerate(article_list):
            logger.info(f"[extract_from_articles] Đang xử lý bài báo {idx + 1}/{len(article_list)}...")
            try:
                result = self.extract_from_article(article)
                results.append(result)
            except Exception as e:
                logger.error(f"[extract_from_articles] ❌ Lỗi ở bài báo {idx + 1}: {e}")
                results.append(None)
        return results
    
def main():
    context_file = 'data/contents_old.json'
    bucket_name = "team253vpbank"
    key = "adverse_media_data/case1.json"

    json = Utils.fetch_json_from_s3(bucket_name, key)
    logger.info(f"Đã load {len(json)} bài báo từ file {context_file}")

    api_key = Utils.load_api_key_from_env("GEMINI_API_KEY")
    logger.info(f"Đã tải API key từ biến môi trường {api_key}")

    gemini_manager = GeminiModelManager(api_key=api_key, default_model_name="gemini-2.5-flash")
    
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = 'ap-southeast-1'
    MODEL_ID = "arn:aws:bedrock:ap-southeast-1:048013208071:inference-profile/apac.anthropic.claude-3-7-sonnet-20250219-v1:0"

    # Khởi tạo manager
    bedrock_manager = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION,
        default_model_id=MODEL_ID
    )

    extractor_prompt_file = config.PROMPT_EXTRACTOR_FILE
    extractor_prompt = Utils.load_text(extractor_prompt_file)
    logger.info(f"Đã tải prompt từ {extractor_prompt_file}")

    extractor = ArticlePersonExtractor(model_manager=bedrock_manager, prompt_template=extractor_prompt)
    logger.info("Đã khởi tạo ArticlePersonExtractor")

    content_33 = json[0]
    logger.info(f"Đang xử lý bài báo thứ 33: {content_33}")

    answer, thinking = extractor.extract_from_article(content_33)
    logger.info(f"Kết quả: {answer}")

    
    
if __name__ == "__main__":
    main()
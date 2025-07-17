import json
from logger import _setup_logger
import config
import os
from llm_model.bedrock_manager import BedrockModelManager
from utils import Utils
import config
import re


logger = _setup_logger(__name__, config.LOG_LEVEL)



class LlmRerankerPersonal:
    def __init__(self, llm_manager, model_type: str = "claude", prompt_template: str = None):
        """
        :param llm_manager: Instance của BedrockModelManager
        :param model_type: 'claude' hoặc 'deepseek'
        :param prompt_template: Prompt template có chứa {query} và {per_info}
        """
        self.llm_manager = llm_manager
        self.model_type = model_type.lower()
        self.prompt_template = prompt_template or self.default_prompt_template()

    def default_prompt_template(self) -> str:
        return (
            "Bạn là một trợ lý phân tích dữ liệu.\n"
            "Dưới đây là một truy vấn từ hệ thống và một hồ sơ cá nhân từ cơ sở dữ liệu.\n\n"
            "### Truy vấn:\n{query}\n\n"
            "### Hồ sơ cá nhân:\n{per_info}\n\n"
            "Hãy đánh giá mức độ phù hợp giữa truy vấn và hồ sơ này trên thang điểm từ 1 đến 10.\n"
            "Sau đó trả về kết quả dưới dạng JSON như sau:\n"
            '{{"score": <điểm từ 1 đến 10>, "reason": "<giải thích ngắn gọn>"}}'
        )

    def build_prompt(self, query: str, per_item: dict) -> str:
        """
        Áp dụng template đã nạp sẵn để tạo prompt hoàn chỉnh.
        """
        print(self.prompt_template)
        return self.prompt_template.format(
            query_personal=query.strip(),
            db_personal=json.dumps(per_item, ensure_ascii=False, indent=2, default=str)
        )

    def rerank(self, query: str, per_items: list[dict]) -> dict:
        """
        Thực hiện rerank các per_item bằng LLM.
        :return: dict {'per': per_item tốt nhất, 'per_id': ..., 'raw': ..., 'index': ...}
        """
        results = []
        for i, item in enumerate(per_items, 1):
            prompt = self.build_prompt(query, item)
            try:
                logger.info(f"🤖 Đang đánh giá cá nhân #{i} bằng LLM...")
                print(prompt)

                answer = self.llm_manager.generate(
                    prompt=prompt,
                    model_type=self.model_type
                )[0]  # chỉ lấy answer, bỏ reasoning

                print(answer)

                match = re.search(r"Per_id:\s*(\S+)", answer)
                per_id = match.group(1) if match else "none"

                results.append({
                    "per": item,
                    "per_id": per_id,
                    "raw": answer,
                    "index": i - 1
                })

            except Exception as e:
                logger.warning(f"⚠️ Lỗi khi gọi LLM cho cá nhân #{i}: {e}")
                results.append({
                    "per": item,
                    "per_id": "none",
                    "raw": str(e),
                    "index": i - 1
                })

        # Trả về cá nhân đầu tiên có per_id khác "none", nếu có
        for r in results:
            if r["per_id"].lower() != "none":
                return r

        return {"per_id": "none"}

if __name__ == "__main__":
    # ===== Load prompt template từ file =====
    prompt_path = './prompts/rerank_personal.txt'
    prompt_template = Utils.load_text(prompt_path)
    print(prompt_template)

    # ===== AWS Bedrock Model =====
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_VIRGINA_REGION
    print(REGION)
    MODEL_ID = config.CLAUDE_30_HAIKU_ON_DEMAND_VIRGINA_MODEL_ID  

    llm_manager = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION,
        default_model_id=MODEL_ID
    )

    # ===== Dữ liệu test =====
    query = "Một người nữ tên Phương Hằng, 53 tuổi, doanh nhân tại TP.HCM, giữ chức tổng giám đốc."
    per_item = {
        "full_name": "Nguyễn Phương Linh",
        "per_id": "P0001",
        "birth_year_or_age": "53",
        "gender": "Female",
        "occupation_or_position": "Tổng giám đốc",
        "organization": "Công ty Cổ phần Đại Nam",
        "hometown_or_residence": None,
        "personal_relationships": "Chủ mưu vụ án, người tổ chức livestream"
    }

    # ===== Khởi tạo reranker và chạy thử =====
    reranker = LlmRerankerPersonal(llm_manager=llm_manager, model_type="claude", prompt_template=prompt_template)
    result = reranker.rerank(query=query, per_items=[per_item])
    print(result)
    print("Per_id được chọn:", result["per_id"])
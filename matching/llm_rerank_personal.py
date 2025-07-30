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

    def build_prompt(self,
                      query: str,
                    per_item: dict,
                    top_k_result: int = 5) -> str:
        """
        Áp dụng template đã nạp sẵn để tạo prompt hoàn chỉnh.
        """
        print(self.prompt_template)
        return self.prompt_template.format(
            query_personal=query.strip(),
            top_k_personal=json.dumps(per_item, ensure_ascii=False, indent=2, default=str),
            top_k_result=top_k_result
        )

    def extract_per_ids(self, answer: str) -> list[str]:
        """
        Trích danh sách per_id từ chuỗi có định dạng:
        Per_id:
        [per_id_..., per_id_..., ...]
        """
        # Tìm đoạn Per_id: [ ... ] kể cả xuống dòng
        pattern = r'\[\s*(\{[^}]+\}\s*,?\s*)+\]'

        match = re.search(pattern, answer, re.DOTALL)
        if not match:
            return []

        result = match.group(0)
        result = Utils.json_str_to_dict(result)
        return result
    
    def rerank(self, query: str, per_items: list[dict], top_k_result:  int = 5) -> list[str]:
        """
        Gọi LLM một lần với danh sách per_items và trả về danh sách per_id được trích ra.
        :return: List các per_id (nếu có)
        """
        try:
            prompt = self.build_prompt(query, per_items, top_k_result=top_k_result)

            logger.info("🤖 Đang gọi LLM để đánh giá danh sách...")
            # print(prompt)

            answer = self.llm_manager.generate(
                prompt=prompt,
                model_type=self.model_type
            )[0]

            logger.info(f"✅ LLM trả về: {answer}")

            result = self.extract_per_ids(answer)
            return result

        except Exception as e:
            logger.warning(f"⚠️ Lỗi khi gọi LLM: {e}")
            return []

if __name__ == "__main__":
    # ===== Load prompt template từ file =====
    prompt_path = './prompts/rerank_personal.txt'
    prompt_template = Utils.load_text(prompt_path)
    print(prompt_template)

    # ===== AWS Bedrock Model =====
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("NEW_AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("NEW_AWS_SECRET_KEY")
    REGION = config.AWS_VIRGINA_REGION
    print(REGION)
    MODEL_ID = 'arn:aws:bedrock:us-east-1:538830382271:inference-profile/us.deepseek.r1-v1:0'  

    llm_manager = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION,
        default_model_id=MODEL_ID
    )

    # ===== Dữ liệu test =====
    query = """Trương Mỹ Lan, chủ tịch tập đoàn Vạn Thịnh Phát"""

    per_item = [
                    {
                    "organization": "Tập đoàn Vạn Thịnh Phát",
                    "created_at": "1752686701534958",
                    "per_id": "per_id_1752683428698187",
                    "full_name": "Trương Mỹ Lan",
                    "occupation_or_position": "Chủ tịch Tập đoàn Vạn Thịnh Phát",
                    "hometown_or_residence": None,
                    "gender": "Female",
                    "personal_relationships": "Bị cáo chính trong vụ án Vạn Thịnh Phát; Cổ đông lớn, người nắm giữ 91.5% cổ phần SCB; Chỉ đạo các bị cáo Đinh Văn Thành, Bùi Anh Dũng, Võ Tấn Hoàng Văn, Tạ Chiêu Trung, Trương Khánh Hoàng, Trần Thị Mỹ Dung",
                    "birth_year_or_age": "68"
                    },
                    {
                    "organization": "Tập đoàn Vạn Thịnh Phát",
                    "created_at": "1752686796606635",
                    "per_id": "per_id_1752683428701219",
                    "full_name": "Anh Quân",
                    "occupation_or_position": "Giảng viên đại học",
                    "hometown_or_residence": None,
                    "gender": "Female",
                    "personal_relationships": "Bị cáo chính trong vụ án Vạn Thịnh Phát; Cổ đông lớn, người nắm giữ 91.5% cổ phần SCB; Chỉ đạo các bị cáo Đinh Văn Thành, Bùi Anh Dũng, Võ Tấn Hoàng Văn, Tạ Chiêu Trung, Trương Khánh Hoàng, Trần Thị Mỹ Dung",
                    "birth_year_or_age": "68"
                    },
                    {
                    "organization": "Tập đoàn Vạn Thịnh Phát",
                    "created_at": "1752683993756702",
                    "per_id": "per_id_1752683967548635",
                    "full_name": "Trương Mỹ Lan",
                    "occupation_or_position": "Chủ tịch hội đồng quản trị",
                    "hometown_or_residence": "TP Hồ Chí Minh",
                    "gender": "Female",
                    "personal_relationships": "Cổ đông lớn, nắm giữ gần tuyệt đối cổ phần Ngân hàng SCB; Chỉ đạo các bị cáo Đinh Văn Thành, Bùi Anh Dũng, Võ Tấn Hoàng Văn, Tạ Chiêu Trung, Trương Khánh Hoàng, Trần Thị Mỹ Dung",
                    "birth_year_or_age": "68"
                    },
                    {
                    "organization": "Tập đoàn Vạn Thịnh Phát",
                    "created_at": "1752686305988720",
                    "per_id": "per_id_1752686292652654",
                    "full_name": "Trương Mỹ Lan",
                    "occupation_or_position": "Chủ tịch Tập đoàn Vạn Thịnh Phát",
                    "hometown_or_residence": None,
                    "gender": "Female",
                    "personal_relationships": "Cổ đông lớn nắm 91.5% cổ phần SCB; Chỉ đạo các bị cáo Đinh Văn Thành, Bùi Anh Dũng, Võ Tấn Hoàng Văn, Tạ Chiêu Trung, Trương Khánh Hoàng, Trần Thị Mỹ Dung",
                    "birth_year_or_age": "68"
                    },
                    {
                    "organization": "Trường Đại học Luật TP HCM",
                    "created_at": "1752685729911490",
                    "per_id": "per_id_1752683428700044",
                    "full_name": "Đặng Anh Quân",
                    "occupation_or_position": "Tiến sĩ luật, Giảng viên",
                    "hometown_or_residence": None,
                    "gender": "Male",
                    "personal_relationships": "Đồng phạm, cố vấn pháp lý trong các buổi livestream của bà Nguyễn Phương Hằng",
                    "birth_year_or_age": "43"
                    },
                    {
                    "organization": "Ngân hàng SCB",
                    "created_at": "1752686604600630",
                    "per_id": "per_id_1752686100029686",
                    "full_name": "Trần Thị Mỹ Dung",
                    "occupation_or_position": None,
                    "hometown_or_residence": "phường Chương Dương, quận Hoàn Kiếm, thành phố Hà Nội",
                    "gender": "Female",
                    "personal_relationships": "Đồng phạm giúp sức Trương Mỹ Lan rút tiền trái phép",
                    "birth_year_or_age": "1967"
                    }
    ]

    # ===== Khởi tạo reranker và chạy thử =====
    reranker = LlmRerankerPersonal(llm_manager=llm_manager, model_type="deepseek", prompt_template=prompt_template)
    result = reranker.rerank(query=query, per_items=[per_item])
    print(result)

from google import genai
from google.genai import types
from utils import Utils
from logger import _setup_logger
import config
import time

logger = _setup_logger(__name__, config.LOG_LEVEL)


class ArticlePersonExtractor:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash", custom_prompt_template: str = None):
        # Thiết lập API key và mô hình
        self.client = genai.Client(api_key=api_key)
        self.model = self.client.models
        self.model_name = model_name
        self.custom_prompt_template = custom_prompt_template

    def _create_prompt(self, article_text: str) -> str:
        # Nếu có prompt tùy chỉnh, sử dụng nó với placeholder {article_text}
        if self.custom_prompt_template:
            return self.custom_prompt_template.format(article_text=article_text)
        # Ngược lại dùng prompt mặc định

        prompt = f"""
        🧭 BƯỚC 1: TRÍCH XUẤT THÔNG TIN CÁ NHÂN

                

                Hãy đọc kỹ bài báo dưới đây và xác định tất cả các cá nhân được đề cập trong nội dung.

                

                Đối với mỗi cá nhân được nêu trong bài, hãy trích xuất đầy đủ các thông tin sau (nếu có):

                

                - ID định danh duy nhất cho người xuất hiện trong bài báo

                - Họ và tên đầy đủ  

                - Năm sinh hoặc tuổi  

                - Giới tính  

                - Nghề nghiệp hoặc chức vụ  

                - Cơ quan hoặc tổ chức liên quan  

                - Vai trò trong sự việc (ví dụ: bị cáo, người tố cáo, người đại diện, bị hại, nhân chứng, ...)  

                - Quê quán hoặc nơi cư trú  

                - Mối quan hệ cá nhân với các nhân vật khác trong bài báo (nếu có)

                

                📌 Đầu ra yêu cầu: Trả về dưới dạng danh sách JSON, trong đó mỗi phần tử là một đối tượng chứa thông tin của một cá nhân. Các key trong JSON phải viết bằng **tiếng Anh** theo mẫu sau:

                

                [

                {{

                    "personal_id": "...." 

                    "full_name": "...",

                    "birth_year_or_age": "...",

                    "gender": "...",

                    "occupation_or_position": "...",

                    "organization": "...",

                    "hometown_or_residence": "...",

                    "personal_relationships": "..."

                }},

                ...

                ]

                

                🧭 BƯỚC 2: PHÂN TÍCH ĐẶC TRƯNG RỦI RO THEO TỪNG CÁ NHÂN

                

                ✅ 1. news_sentiment_type (Bản chất của tin tức tổng thể)  

                → Chỉ định cho toàn bài: "Negative", "Neutral", hoặc "Positive".

                ✅ 2. recency (Thời gian xuất hiện bài báo so với thời gian hiện tại là 10 năm)

                -> Chỉ định cho toàn bài: "recent", "old"

                ✅ 3. source_credibility (Độ tin cậy của bài báo)

                -> Chỉ định cho toàn bài: "High", "Medium" hoặc "Low"

                

                Dựa trên danh sách cá nhân được trích xuất ở Bước 1, hãy đánh giá **từng người** theo các đặc trưng rủi ro sau:

                

                ✅ 4. Đặc trưng rủi ro theo từng cá nhân (mỗi người là một phần tử trong danh sách):

                    list_customer (key)

                [

                {{

                    "personal_id": "..." ← Lưu ý personal_id phải trùng với personal_id của cá nhân ở bước 1 nếu hai cá nhân này trùng nhau

                    "full_name": "...",  ← tên cá nhân khớp với Bước 1

                    "role_in_case": "...",

                    "customer_role_in_news": "...",       ← Subject / Related Party / Commentator

                    "frequency": "..."                  ← once / repeated

                    "event_severity_level": "...",        ← Very High / High / Medium / Low

                    "event_status_outcome": "...",        ← Convicted / Fined / Investigated / Cleared / Unresolved
        "high_risk_industry_link": false      ← true / false

                }},

                ...

                ]

                

                📌 Lưu ý: Mỗi cá nhân trong danh sách phải được đánh giá độc lập, không gộp chung. Nếu không đủ thông tin để xác định, hãy để null.

                LƯU Ý: Chỉ trả về **hai danh sách JSON như trên**, không thêm giải thích, tiêu đề, mô tả hay bất kỳ nội dung nào khác.

                📰 Nội dung bài báo cần phân tích:

                \"\"\"

                {article_text}

                \"\"\"

                Lưu ý tuân thủ theo format sau: 
                [
                    [
                      dict_person_1,
                      dict_person_2,
                      ...
                    ],
                    dict_risk_info
                ]

        Mẫu đầu ra mẫu:
        [
            [
                {{
                "personal_id": "P001",
                "full_name": "Trương Mỹ Lan",
                "birth_year_or_age": null,
                "gender": "Female",
                "occupation_or_position": "Chủ tịch hội đồng quản trị",
                "organization": "Tập đoàn Vạn Thịnh Phát",
                "hometown_or_residence": null,
                "personal_relationships": "Bị cáo chính trong vụ án Vạn Thịnh Phát; Cổ đông lớn, người nắm giữ gần tuyệt đối cổ phần Ngân hàng SCB; Người ra chỉ thị cho các bị cáo Đinh Văn Thành, Bùi Anh Dũng, Võ Tấn Hoàng Văn, Tạ Chiêu Trung, Trương Khánh Hoàng, Trần Thị Mỹ Dung"
                }},
                {{
                "personal_id": "P002",
                "full_name": "Huỳnh Thanh Duyên",
                "birth_year_or_age": null,
                "gender": "Female",
                "occupation_or_position": "Thẩm phán chủ tọa",
                "organization": "Tòa án nhân dân cấp cao tại TP.HCM",
                "hometown_or_residence": null,
                "personal_relationships": "Chủ tọa phiên tòa phúc thẩm vụ Vạn Thịnh Phát giai đoạn 1"
                }},
                {{
                "personal_id": "P003",
                "full_name": "Phạm Công Mười",
                "birth_year_or_age": null,
                "gender": "Male",
                "occupation_or_position": "Thẩm phán",
                "organization": "Tòa án nhân dân cấp cao tại TP.HCM",
                "hometown_or_residence": null,
                "personal_relationships": "Thẩm phán trong hội đồng xét xử phúc thẩm vụ Vạn Thịnh Phát giai đoạn 1"
                }}
            ],
            {{
            "news_sentiment_type": "Negative",
                "recency": "recent",
                "source_credibility": "High",
                "list_customer": [
                {{
                    "personal_id": "P001",
                    "full_name": "Trương Mỹ Lan",
                    "role_in_case": "Bị cáo",
                    "customer_role_in_news": "Subject",
                    "frequency": "repeated",
                    "event_severity_level": "Very High",
                    "event_status_outcome": "Convicted",
                    "high_risk_industry_link": true
                }},
                {{
                    "personal_id": "P002",
                    "full_name": "Huỳnh Thanh Duyên",
                    "role_in_case": "Thẩm phán chủ tọa",
                    "customer_role_in_news": "Related Party",
                    "frequency": "once",
                    "event_severity_level": "Low",
                    "event_status_outcome": "Unresolved",
                    "high_risk_industry_link": false
                }},
                {{
                    "personal_id": "P003",
                    "full_name": "Phạm Công Mười",
                    "role_in_case": "Thẩm phán",
                    "customer_role_in_news": "Related Party",
                    "frequency": "once",
                    "event_severity_level": "Low",
                    "event_status_outcome": "Unresolved",
                    "high_risk_industry_link": false
                }}
                ]
            }}
        ]
        """        # Trả về prompt đã tạo
        return prompt

    def extract_from_article(self, article_text: str) -> str:
        prompt = self._create_prompt(article_text)
        logger.debug("[extract_from_article] Prompt đã được tạo.")
        start = time.time()
        response = self.model.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
            # Turn off thinking:
            # thinking_config=types.ThinkingConfig(thinking_budget=0)
            # Turn on dynamic thinking:
            # thinking_config=types.ThinkingConfig(thinking_budget=-1)
            ),
        )
        end = time.time()
        logger.info(f"[extract_from_article] Thời gian gọi mô hình: {end - start:.2f} giây")
        logger.debug("[extract_from_article] Phản hồi đã nhận từ mô hình Gemini.")
        return response.text

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
    
if __name__ == "__main__":
    context_file = 'data/contents_old.json'
    json = Utils.load_json(context_file)
    logger.info(f"Đã load {len(json)} bài báo từ file {context_file}")

    api_key = Utils.load_api_key_from_env("GEMINI_API_KEY")
    logger.info(f"Đã tải API key từ biến môi trường {api_key}")

    extractor = ArticlePersonExtractor(api_key=api_key, custom_prompt_template=None)
    logger.info("Đã khởi tạo ArticlePersonExtractor")

    content_33 = json[33]
    logger.info(f"Đang xử lý bài báo thứ 33: {content_33}")
    results = extractor.extract_from_article(content_33)
    logger.info(f"Kết quả: {results}")
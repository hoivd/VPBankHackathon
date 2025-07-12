import boto3
import json
from llm_model.model_manager import LlmModelManager
from utils import Utils
import config
from botocore.exceptions import ClientError
from logger import _setup_logger

logger = _setup_logger(__name__, config.LOG_LEVEL)

class BedrockModelManager(LlmModelManager):
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        default_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    ):
        self.client = boto3.client(
            "bedrock-runtime",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self.default_model_id = default_model_id

    def get_model(self, model_name: str = None) -> str:
        return model_name or self.default_model_id

    def generate(
        self,
        prompt: str,
        model_name: str = None,
        max_token: int = 10000,
        temperature: float = 0.5,
        enable_thinking: bool = False,
        thinking_budget_tokens: int = 2000
    ) -> str:
        model_id = self.get_model(model_name)

        # Claude 3 request format
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_token,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        }

        # ✅ Thêm reasoning nếu được bật
        if enable_thinking:
            body['temperature'] = 1
            body["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget_tokens
            }
        else:
            body["thinking"] = {"type": "disabled"}

        try:
            logger.debug(f"Calling Bedrock model {model_id} with body: {body}")
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                accept="application/json",
                contentType="application/json"
            )
        except (ClientError, Exception) as e:
            raise RuntimeError(f"❌ Lỗi khi gọi mô hình {model_id}: {e}")

        result = json.loads(response["body"].read())

        # ✅ Lấy content list từ Claude 3.7
        content_blocks = result.get("content", [])

        # ✅ Reasoning (type == "thinking") → giá trị nằm trực tiếp trong "thinking"
        reasoning_text = None
        final_text = None

        for block in content_blocks:
            if block.get("type") == "thinking":
                reasoning_text = block.get("thinking")
            elif block.get("type") == "text":
                final_text = block.get("text")

        # ✅ Trả kết quả kèm reasoning nếu có
        if reasoning_text:
            return final_text, reasoning_text
        else:
            return final_text, ""

if __name__ == "__main__":
    import json

    # Cấu hình cố định
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    MODEL_ID = "arn:aws:bedrock:ap-southeast-1:048013208071:inference-profile/apac.anthropic.claude-3-7-sonnet-20250219-v1:0"
    prompt = "Viết một đoạn văn ngắn về lợi ích của AI trong y tế."

    # Khởi tạo manager
    manager = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION,
        default_model_id=MODEL_ID
    )

    # Gọi mô hình
    try:
        print("🚀 Đang gọi mô hình Bedrock Claude 3...")
        result, thinking = manager.generate(prompt=prompt, enable_thinking=False)
        print("\n✅ Kết quả phản hồi:")
        print(f"Thinking: {thinking}")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Lỗi khi gọi mô hình: {e}")    

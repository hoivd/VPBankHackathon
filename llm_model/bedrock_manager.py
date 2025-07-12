import boto3
import json
from llm_model.model_manager import LlmModelManager
from utils import Utils
import config
from botocore.exceptions import ClientError

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

    def generate(self, prompt: str, model_name: str = None, temperature: float = 0.5) -> str:
        model_id = self.get_model(model_name)

        # ✅ Claude 3 request format
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10000,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        }

        try:
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                accept="application/json",
                contentType="application/json"
            )
        except (ClientError, Exception) as e:
            raise RuntimeError(f"❌ Lỗi khi gọi mô hình {model_id}: {e}")

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

if __name__ == "__main__":
    import json

    # Cấu hình cố định
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
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
        result = manager.generate(prompt=prompt)
        print("\n✅ Kết quả phản hồi:")
        print(result)
    except Exception as e:
        print(f"❌ Lỗi khi gọi mô hình: {e}")    

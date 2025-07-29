import boto3
import json
from llm_model.model_manager import LlmModelManager
from utils import Utils
import config
from botocore.exceptions import ClientError
from logger import _setup_logger
import re
import time 

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

    def extract_thinking_and_answer(self, response: str):
        """
        Tách phần trước (gồm <think>...</think>) và phần sau </think> từ một chuỗi văn bản.
        
        Trả về:
            thinking_part (str): nội dung từ đầu đến hết </think>
            json_part (str): phần sau </think>
        """
        match = re.search(r"(.*?</think>)(.*)", response, re.DOTALL)
        if not match:
            raise ValueError("Không tìm thấy thẻ </think> trong chuỗi.")
        
        thinking = match.group(1).strip()
        answer = match.group(2).strip()
        return answer, thinking
    
    def generate_deepseek(
        self,
        prompt: str,
        max_tokens: int = 12000,
        temperature: float = 0.5,
        top_p: float = 0.9,
        model_id: str = "us.deepseek.r1-v1:0"
    ) -> str:
        """
        Gửi prompt đến mô hình DeepSeek-R1 và trả về kết quả text (hoặc raise lỗi nếu thất bại sau 3 lần).
        """

        logger.info(f"🚀 Đang gọi mô hình DeepSeek...{model_id}")
        formatted_prompt = f"<｜begin▁of▁sentence｜><｜User｜>{prompt}<｜Assistant｜><think>\n"

        body = json.dumps({
            "prompt": formatted_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        })

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = self.client.invoke_model(
                    modelId=model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json"
                )
                model_response = json.loads(response["body"].read())
                choices = model_response.get("choices", [])

                if not choices:
                    raise RuntimeError("No choices returned from DeepSeek.")

                resp = choices[0]["text"]
                answer, thinking = self.extract_thinking_and_answer(resp)

                logger.debug(f"[DeepSeek] Đã nhận phản hồi: {answer}")
                if thinking:
                    logger.debug(f"[DeepSeek] Reasoning: {thinking}")
                else:
                    logger.debug("[DeepSeek] Không có reasoning.")

                return answer, thinking

            except (ClientError, Exception) as e:
                logger.warning(f"[DeepSeek] Thử lần {attempt + 1} thất bại: {e}")
                if attempt < max_retries:
                    time.sleep(10 ** attempt)  # exponential backoff: 1s, 2s
                else:
                    raise RuntimeError(f"[DeepSeek] Lỗi sau {max_retries + 1} lần thử: {e}")

    def generate_claude(
        self,
        prompt: str,
        model_name: str = None,
        max_token: int = 50000,
        temperature: float = 0.5,
        enable_thinking: bool = False,
        thinking_budget_tokens: int = 2000,
        max_retries: int = 3,
        retry_delay: int = 2  # giây
    ) -> str:
        
        logger.info(f"🚀 Đang gọi mô hình Bedrock...{model_name}")
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

        if enable_thinking:
            body['temperature'] = 1
            body["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget_tokens
            }

        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"🔁 Gọi Bedrock (thử lần {attempt}) model {model_id}")
                response = self.client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    accept="application/json",
                    contentType="application/json"
                )
                break  # Thành công, thoát vòng lặp

            except (ClientError, Exception) as e:
                logger.warning(f"❌ Lỗi khi gọi mô hình {model_id} (thử lần {attempt}): {e}")
                if attempt == max_retries:
                    raise RuntimeError(f"🚨 Đã thử {max_retries} lần nhưng không thành công: {e}")
                time.sleep(retry_delay)

        result = json.loads(response["body"].read())

        content_blocks = result.get("content", [])
        reasoning_text = None
        final_text = None

        for block in content_blocks:
            if block.get("type") == "thinking":
                reasoning_text = block.get("thinking")
            elif block.get("type") == "text":
                final_text = block.get("text")

        if reasoning_text:
            logger.debug(f"[generate] ✅ Đã nhận phản hồi từ mô hình {model_id} với reasoning.")
            logger.debug(f"[generate] Reasoning: {reasoning_text}")
            return final_text, reasoning_text
        else:
            logger.debug(f"[generate] ✅ Đã nhận phản hồi từ mô hình {model_id} mà không có reasoning.")
            return final_text, ""

    def generate_amazon(
            self,
            prompt: str,
            model_id: str = "amazon.titan-nova-pro-v1",  # Cập nhật model_id chính xác
            temperature: float = 0.5,
            top_p: float = 0.9
        ) -> tuple[str, str]:
            """
            Gửi prompt đến mô hình Amazon Titan Nova Pro và trả về kết quả (answer, reasoning="").
            Lưu ý: Sử dụng định dạng messages cho Amazon Bedrock API.
            """
            logger.info(f"🚀 Đang gọi mô hình Amazon Titan Nova Pro... {model_id}")

            # Định dạng body theo yêu cầu của Amazon Bedrock
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": max(0.0, min(temperature, 1.0)),  # Đảm bảo temperature trong khoảng hợp lệ
                "topP": max(0.0, min(top_p, 1.0)),  # Thêm top_p vào body
                "maxTokens": 2048  # Giới hạn số token tối đa, có thể tùy chỉnh
            }

            try:
                # Gọi API Amazon Bedrock
                response = self.client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json"
                )
                
                # Giải mã phản hồi
                result = json.loads(response["body"].read().decode("utf-8"))
                # Lấy nội dung từ phản hồi, giả sử định dạng phản hồi có trường 'choices'
                output_text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                logger.debug(f"[Amazon Titan Nova Pro] ✅ Phản hồi: {output_text}")
                return output_text, ""  # Không có reasoning

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                error_message = e.response.get("Error", {}).get("Message")
                logger.error(f"❌ Lỗi ClientError khi gọi mô hình Amazon Titan Nova Pro {model_id}: {error_code} - {error_message}")
                raise RuntimeError(f"❌ Lỗi khi gọi mô hình Amazon Titan Nova Pro {model_id}: {error_message}")
            except Exception as e:
                logger.error(f"❌ Lỗi không xác định khi gọi mô hình Amazon Titan Nova Pro {model_id}: {str(e)}")
                raise RuntimeError(f"❌ Lỗi khi gọi mô hình Amazon Titan Nova Pro {model_id}: {str(e)}")

    def generate(
        self,
        prompt: str,
        model_type: str,  # hoặc "claude"
        model_name: str = None,
        max_tokens: int = 12000,
        temperature: float = 1,
        top_p: float = 0.9,
        enable_thinking: bool = False,
        thinking_budget_tokens: int = 2000
    ) -> tuple[str, str]:
        """
        Gọi mô hình tương ứng theo model_type và trả về (answer, reasoning).
        """
        start = time.time()
        if model_type.lower() == "deepseek":
            result = self.generate_deepseek(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )

        elif model_type.lower() == "claude":
            result =  self.generate_claude(
                prompt=prompt,
                model_name=model_name,
                max_token=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                thinking_budget_tokens=thinking_budget_tokens
            )
        elif model_type.lower() == "amazon":
            result =  self.generate_amazon(
                prompt=prompt,
                model_id=model_name or "amazon.nova-pro-v1:0",
                temperature=temperature,
                top_p=top_p
            ) 
        else:
            raise ValueError(f"Unsupported model_type: {model_type}")
        
        end = time.time()
        logger.info(f"[generate] Thời gian gọi mô hình {model_type} ({model_name}): {end - start:.2f} giây")
        return result


def main():
    import json

    # Cấu hình cố định
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = config.AWS_VIRGINA_REGION
    MODEL_ID = "arn:aws:bedrock:us-east-1:538830382271:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0" 

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
        result, thinking = manager.generate(prompt=prompt, enable_thinking=False, model_type='claude')
        print("\n✅ Kết quả phản hồi:")
        print(f"Thinking: {thinking}")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Lỗi khi gọi mô hình: {e}")    

if __name__ == "__main__":
    main()
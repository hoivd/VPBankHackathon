# cohere_embedder.py
import json
from utils import Utils
from embedder.bedrock_base import BedrockBaseClient
# from logger import _setup_logger
import config
import logging
# logger = _setup_logger(__name__, config.LOG_LEVEL)
class CohereMultilingualEmbedder:
    def __init__(self, bedrock_client=None):
        self.client = bedrock_client
        self.model_id = "cohere.embed-multilingual-v3"

    def embed(self, texts: list[str], input_type="search_document") -> list[list[float]]:
        """
        texts: list văn bản hoặc tên thực thể cần embedding
        input_type: 'search_document' hoặc 'search_query' (tùy mục đích)
        """
        logging.debug(f"Thuc hien embedding {texts[:20]} bang CohereMultilingualEmbedder")
        
        payload = {
            "texts": texts,
            "input_type": input_type
        }

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response["body"].read())
        return result["embeddings"]

def main():
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION = "us-east-1"

    # Khởi tạo Bedrock client
    bedrock_base = BedrockBaseClient(
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY,
        region_name=REGION
    )

    # Khởi tạo Cohere embedder
    embedder = CohereMultilingualEmbedder(bedrock_client=bedrock_base.get_client())

    # Danh sách văn bản hoặc thực thể để embedding
    texts = [
        "Trương Mỹ Lan",
        "T. M. Lan",
        "Chủ tịch Vạn Thịnh Phát"
    ]

    # Gọi embedding
    embeddings = embedder.embed(texts)

    # In ra kết quả
    for i, emb in enumerate(embeddings):
        print(f"{texts[i]} → vector[:5] = {emb[:5]}")

if __name__ == "__main__":
    main()
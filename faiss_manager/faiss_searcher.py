import os
import numpy as np
from faiss_manager.faiss_index_manager import FaissIndexManager  # hoặc import trực tiếp class nếu cùng file
from utils import Utils
from logger import _setup_logger
import config
from embedder.model_embedder import ModelEmbedder
from embedder.article_embedder import ArticleEmbedder
from embedder.bedrock_base import BedrockBaseClient
from embedder.cohere_embedder import CohereMultilingualEmbedder

logger = _setup_logger(__name__, config.LOG_LEVEL)
class FaissSearcher:
    def __init__(self, faiss_manager: FaissIndexManager):
        """
        Tải FAISS index từ thư mục và chuẩn bị cho search.
        """
        self.manager = faiss_manager      
        print(f"Đã tải FAISS index với {self.manager.get_total()} vector.")

    def search_top_k(self, query_vector: np.ndarray, top_k: int = 5, return_embeddings: bool = False):
        if self.manager.get_total() == 0:
            raise ValueError("FAISS index đang rỗng. Hãy kiểm tra dữ liệu đã load.")

        # Kiểm tra và chuẩn hóa vector đầu vào
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        elif query_vector.shape[1] != self.manager.dim:
            raise ValueError(f"Query vector phải có shape (_, {self.manager.dim})")

        query_vector = query_vector.astype('float32')
        D, I = self.manager.index.search(query_vector, top_k)

        results = []
        for id_, dist in zip(I[0], D[0]):
            if id_ == -1:
                continue
            item = {
                "id": int(id_),
                "distance": float(dist)
            }
            if return_embeddings:
                embedding = self.manager.get_embedding_by_id(int(id_))
                item["embedding"] = embedding.tolist() if embedding is not None else None
            results.append(item)

        return results

def main():
    # bucket_name = "team253"
    # key = "adverse_media_data/case1.json"

    # contents_case1 = Utils.fetch_json_from_s3(bucket_name, key)
    # logger.info(f"Đã load {len(contents_case1)} bài báo từ file {key}")

    # query = contents_case1[3]
    # logger.info(f"Đang tìm kiếm với bài báo: {query[:100]}...")

    # model_name = config.EMBEDDING_MODEL_NAME
    # base_model_embedder = ModelEmbedder(model_name=model_name)
    # article_embedder = ArticleEmbedder(base_embedder=base_model_embedder)

    
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

    faiss_index_path = 'data/faiss_indexs/personal_faiss_index'
    faiss_searcher = FaissSearcher(faiss_index_path)

    top_k = 3
    query = '''
        Trương Khánh Hoàng, ngân hàng SCB'''
    print(f"Đang tìm kiếm với bài báo: {query[:100]}...")
    query_embedding = embedder.embed([query])
    print(type(query_embedding))
    results = faiss_searcher.search_top_k(np.array(query_embedding[0]), top_k=5)

    print("Kết quả tìm kiếm:")
    print(f"\nTop-{top_k} kết quả gần nhất:")
    for i, item in enumerate(results, 1):
        print(f"{i}. ID: {item['id']}, Distance: {item['distance']:.4f}")


if __name__ == "__main__":
    main()
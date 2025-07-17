import os
import numpy as np
from faiss_manager.faiss_index_manager import FaissIndexManager  # hoặc import trực tiếp class nếu cùng file
from utils import Utils
from logger import _setup_logger
import config
from embedder.model_embedder import ModelEmbedder
from embedder.article_embedder import ArticleEmbedder

logger = _setup_logger(__name__, config.LOG_LEVEL)
class FaissSearcher:
    def __init__(self, index_dir: str):
        """
        Tải FAISS index từ thư mục và chuẩn bị cho search.
        """
        if not os.path.exists(index_dir):
            raise FileNotFoundError(f"Không tìm thấy thư mục: {index_dir}")
        
        self.manager = FaissIndexManager.load_index(index_dir)
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


if __name__ == "__main__":
    # bucket_name = "team253"
    # key = "adverse_media_data/case1.json"

    # contents_case1 = Utils.fetch_json_from_s3(bucket_name, key)
    # logger.info(f"Đã load {len(contents_case1)} bài báo từ file {key}")

    # query = contents_case1[3]
    # logger.info(f"Đang tìm kiếm với bài báo: {query[:100]}...")

    model_name = config.EMBEDDING_MODEL_NAME
    base_model_embedder = ModelEmbedder(model_name=model_name)
    article_embedder = ArticleEmbedder(base_embedder=base_model_embedder)

    faiss_index_path = 'data/personal_faiss_index'
    faiss_searcher = FaissSearcher(faiss_index_path)

    top_k = 3
    query = '''
        Văn Quân, là người đàn ông 43 tuổi, từng là giảng viên đại học, không phải là chủ tịch'''
    print(f"Đang tìm kiếm với bài báo: {query[:100]}...")
    query_embedding = article_embedder.embed_article(query)
    results = faiss_searcher.search_top_k(query_embedding, top_k=5)

    print("Kết quả tìm kiếm:")
    print(f"\nTop-{top_k} kết quả gần nhất:")
    for i, item in enumerate(results, 1):
        print(f"{i}. ID: {item['id']}, Distance: {item['distance']:.4f}")
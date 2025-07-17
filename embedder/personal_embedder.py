from embedder.model_embedder import ModelEmbedder
import numpy as np
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class PersonalEmbedder:
    def __init__(self, base_embedder):
        """
        Khởi tạo ArticleEmbedder với model đã lưu local hoặc từ Hugging Face hub.
        """
        self.embedder = base_embedder
        
    def embed_personal(self, personal: str | list[str], return_numpy: bool = True) -> np.ndarray:
        """
        Nhận vào một bài báo hoặc danh sách bài báo, trả về embedding.

        Args:
            article (str | list[str]): nội dung bài báo hoặc danh sách bài báo.
            return_numpy (bool): trả về numpy array nếu True, ngược lại là torch tensor.

        Returns:
            np.ndarray hoặc torch.Tensor: embedding (n, 768)
        """
        logger.info(f"⏳ Đang encode cá nhân {'(nhiều)' if isinstance(personal, list) else '(1 cá nhân)'}")
        embeddings = self.embedder.encode(personal, return_numpy=return_numpy)
        logger.info("✅ Đã encode xong các cá nhân")
        return embeddings

if __name__ == "__main__":
    article_text = """
    Ngày 4/2, Công an tỉnh Đồng Nai cho biết đã bắt giữ nhóm trộm tài sản...
    """

    embedder = PersonalEmbedder()
    embedding = embedder.embed_article(article_text)

    print("Shape:", embedding.shape)  # (1, 768)
    print("10 vector đầu tiên:", embedding[0][:10])
from embedder.model_embedder import ModelEmbedder
import numpy as np
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class OrganizationEmbedder:
    def __init__(self, base_embedder):
        """
        Khởi tạo ArticleEmbedder với model đã lưu local hoặc từ Hugging Face hub.
        """
        self.embedder = base_embedder
        
    def embed_organization(self, organization: str | list[str], return_numpy: bool = True) -> np.ndarray:
        """
        Nhận vào một bài báo hoặc danh sách bài báo, trả về embedding.

        Args:
            article (str | list[str]): nội dung bài báo hoặc danh sách bài báo.
            return_numpy (bool): trả về numpy array nếu True, ngược lại là torch tensor.

        Returns:
            np.ndarray hoặc torch.Tensor: embedding (n, 768)
        """
        logger.info(f"⏳ Đang encode tổ chức {'(nhiều)' if isinstance(organization, list) else '(1 tổ chức)'}")
        embeddings = self.embedder.encode(organization, return_numpy=return_numpy)
        logger.info("✅ Đã encode xong tổ chức")
        return embeddings

if __name__ == "__main__":
    article_text = """
    Ngày 4/2, Công an tỉnh Đồng Nai cho biết đã bắt giữ nhóm trộm tài sản...
    """

    embedder = OrganizationEmbedder()
    embedding = embedder.embed_article(article_text)

    print("Shape:", embedding.shape)  # (1, 768)
    print("10 vector đầu tiên:", embedding[0][:10])
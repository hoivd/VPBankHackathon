from logger import _setup_logger
from config import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class ArticleEmbeddingHandler:
    def __init__(self, embedder, faiss_manager):
        """
        Wrapper class to manage article embedding and indexing in FAISS.

        Parameters:
        - embedder: an instance with a method `embed_article(text: str) -> np.ndarray`
        - faiss_manager: an instance with a method `add(vectors: np.ndarray) -> list[int]`
        """
        self.article_embedder = embedder
        self.article_faiss_manager = faiss_manager

    def embed_and_index(self, article_text: str) -> str:
        """
        Embeds the article and adds the vector to FAISS.

        Parameters:
        - article_text (str): The full text of the article.

        Returns:
        - str: The ID of the inserted embedding in FAISS.
        """
        article_embedding = self.article_embedder.embed_article(article_text)
        logger.debug(f"[embed_and_index] Article embedding preview: {article_embedding[0, :10]}")

        embedding_id = self.article_faiss_manager.add(article_embedding)
        logger.info(f"✅ Embedded article added to FAISS with ID: {embedding_id}")
        return str(embedding_id[0])
    
    
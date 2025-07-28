from logger import _setup_logger
import config
from utils import Utils
from embedder.bedrock_base import BedrockBaseClient
from embedder.cohere_embedder import CohereMultilingualEmbedder
import copy
from faiss_manager.faiss_index_manager import FaissIndexManager
import os

logger = _setup_logger(__name__, config.LOG_LEVEL)

class PersonalAndRiskHandler:
    def __init__(self, embedder, faiss_manager):
        """
        Wrapper class to manage article embedding and indexing in FAISS.

        Parameters:
        - embedder: an instance with a method `embed_article(text: str) -> np.ndarray`
        - faiss_manager: an instance with a method `add(vectors: np.ndarray) -> list[int]`
        """
        self.embedder = embedder
        self.faiss_manager = faiss_manager

    def create_personal_and_risk_item(self, personal_info: list[dict], personal2media_items: list[dict]) -> str:
        def remove_keys(item: dict, keys_to_remove: list[str]) -> dict:
            """
            Remove specified keys from a dictionary.
            """
            return {k: v for k, v in item.items() if k not in keys_to_remove}

        per_id2_risk_info = {}

        for risk_item in personal2media_items:
            keys_to_remove = ["entity_name", "p2m_id", "media_id", "created_at", "per_id"]
            per_id = risk_item.get("per_id", "")
            risk_item_copy = remove_keys(risk_item, keys_to_remove=keys_to_remove)
            per_id2_risk_info[per_id] = risk_item_copy
            
        personal_and_risk = copy.deepcopy(personal_info)
        per_ids = []
        for i, personal_item in enumerate(personal_and_risk):
            per_id = personal_item.get("per_id", "")
            per_ids.append(per_id)
            violent_details = per_id2_risk_info.get(per_id, {})
            personal_item["violent_details"] = violent_details

            keys_to_remove = ["per_id", "created_at"]
            personal_and_risk[i] = remove_keys(personal_item, keys_to_remove=keys_to_remove)

        # personal_and_risk = [str(item) for item in personal_and_risk]
        return personal_and_risk, per_ids

    def embed_and_index(self, personal_info_items: list[dict], personal2media_items: list[dict]) -> str:
        """
        Embeds the article and adds the vector to FAISS.

        Parameters:
        - article_text (str): The full text of the article.

        Returns:
        - str: The ID of the inserted embedding in FAISS.
        """
        personal_and_risk, per_ids = self.create_personal_and_risk_item(
            personal_info=personal_info_items,
            personal2media_items=personal2media_items
        )

        for item in personal_and_risk:
            print(f"Personal and risk item: {Utils.json_to_str(item)}")

        personal_and_risk_texts = [str(item) for item in personal_and_risk]        

        personal_and_risk_embeddings = self.embedder.embed(personal_and_risk_texts)

        embedding_ids = self.faiss_manager.add(personal_and_risk_embeddings)

        logger.info(f"✅ Embedded personal and risk items added to FAISS")

        return embedding_ids, per_ids        
    
    def remove_old_embeddings_faiss(self, old_embedding_ids: list[str]):
        old_embedding_ids = [int(id) for id in old_embedding_ids]
        self.faiss_manager.remove_by_ids(old_embedding_ids)
        logger.debug(f"Xoa embedding cu thanh cong {old_embedding_ids}")
    
def main():
    items_file = './data/items/extracted_items.json'
    items = Utils.load_json(items_file)
    logger.debug(f"Loaded items from {items_file}")
    personal_info_items = items['personal_info_items']
    personal2media_items = items['personal2media_items']
    logger.info(f"Loaded {len(personal_info_items)} personal info items and {len(personal2media_items)} personal2media items from {items_file}")

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
    faiss_manager = FaissIndexManager(1024)
    personal_risk_handler = PersonalAndRiskHandler(embedder=embedder, faiss_manager=faiss_manager)

    embedding_id, per_ids = personal_risk_handler.embed_and_index(
        personal_info_items=personal_info_items,
        personal2media_items=personal2media_items
    )

    print(f"Embedded personal and risk items added to FAISS with ID: {embedding_id}")
    print(f"Per ids: {per_ids}")

    faiss_index_folder = './data/faiss_indexs'
    os.makedirs(faiss_index_folder, exist_ok=True)
    faiss_index_path = 'data/faiss_indexs/personal_risk_faiss_index'

    faiss_manager.save_index(faiss_index_path)

if __name__ == "__main__":
    main()









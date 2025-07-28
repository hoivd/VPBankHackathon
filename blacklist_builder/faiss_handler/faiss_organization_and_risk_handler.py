from logger import _setup_logger
import config
from utils import Utils
from embedder.bedrock_base import BedrockBaseClient
from embedder.cohere_embedder import CohereMultilingualEmbedder
import copy
from faiss_manager.faiss_index_manager import FaissIndexManager
import os

logger = _setup_logger(__name__, config.LOG_LEVEL)

class OrganizationAndRiskHandler:
    def __init__(self, embedder, faiss_manager):
        """
        Wrapper class to manage article embedding and indexing in FAISS.

        Parameters:
        - embedder: an instance with a method `embed_article(text: str) -> np.ndarray`
        - faiss_manager: an instance with a method `add(vectors: np.ndarray) -> list[int]`
        """
        self.embedder = embedder
        self.faiss_manager = faiss_manager

    def create_organization_and_risk_item(self, organization_info_items: list[dict], organization2media_items: list[dict]) -> str:
        def remove_keys(item: dict, keys_to_remove: list[str]) -> dict:
            """
            Remove specified keys from a dictionary.
            """
            return {k: v for k, v in item.items() if k not in keys_to_remove}

        organization_id2_risk_info = {}

        for risk_item in organization2media_items:
            keys_to_remove = ["entity_name", "p2m_id", "media_id", "created_at", "org_id"]
            organization_id = risk_item.get("org_id", "")
            risk_item_copy = remove_keys(risk_item, keys_to_remove=keys_to_remove)
            organization_id2_risk_info[organization_id] = risk_item_copy
            
        organization_and_risk = copy.deepcopy(organization_info_items)
        organization_ids = []
        for i, organization_item in enumerate(organization_and_risk):
            org_id = organization_item.get("org_id", "")
            organization_ids.append(org_id)
            violent_details = organization_id2_risk_info.get(org_id, {})
            organization_item["violent_details"] = violent_details

            keys_to_remove = ["org_id", "created_at"]
            organization_and_risk[i] = remove_keys(organization_item, keys_to_remove=keys_to_remove)

        # personal_and_risk = [str(item) for item in personal_and_risk]
        return organization_and_risk, organization_ids

    def embed_and_index(self, organization_info_items: list[dict], organization2media_items: list[dict]) -> str:
        """
        Embeds the article and adds the vector to FAISS.

        Parameters:
        - article_text (str): The full text of the article.

        Returns:
        - str: The ID of the inserted embedding in FAISS.
        """
        organization_and_risk, organization_ids = self.create_organization_and_risk_item(
            organization_info_items=organization_info_items,
            organization2media_items=organization2media_items
        )

        for item in organization_and_risk:
            print(f"Organization and risk item: {Utils.json_to_str(item)}")

        organization_and_risk_texts = [str(item) for item in organization_and_risk]        

        organization_and_risk_texts_embeddings = self.embedder.embed(organization_and_risk_texts)

        embedding_ids = self.faiss_manager.add(organization_and_risk_texts_embeddings)

        logger.info(f"✅ Embedded organization and risk items added to FAISS")

        return embedding_ids, organization_ids        
        
    def remove_old_embeddings_faiss(self, old_embedding_ids: list[str]):
        old_embedding_ids = [int(id) for id in old_embedding_ids]
        self.faiss_manager.remove_by_ids(old_embedding_ids)
        logger.debug(f"Xoa embedding cu thanh cong {old_embedding_ids}")
    
def main():
    items_file = './data/items/extracted_items.json'
    items = Utils.load_json(items_file)
    logger.debug(f"Loaded items from {items_file}")
    organization_info_items = items['organization_info_items']
    organization2media_items = items['org2media_items']

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
    organization_risk_handler = OrganizationAndRiskHandler(embedder=embedder, faiss_manager=faiss_manager)

    embedding_id, org_ids = organization_risk_handler.embed_and_index(
        organization_info_items=organization_info_items,
        organization2media_items=organization2media_items
    )

    print(f"Embedded organization and risk items added to FAISS with ID: {embedding_id}")
    print(f"Org ids: {org_ids}")

    faiss_index_folder = './data/faiss_indexs'
    os.makedirs(faiss_index_folder, exist_ok=True)
    faiss_index_path = 'data/faiss_indexs/organization_risk_faiss_index'

    faiss_manager.save_index(faiss_index_path)

if __name__ == "__main__":
    main()









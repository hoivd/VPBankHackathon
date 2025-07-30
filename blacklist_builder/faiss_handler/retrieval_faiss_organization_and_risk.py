import numpy as np
from typing import List, Dict
from faiss_manager.faiss_searcher import FaissSearcher  # class bạn đã viết ở trên
from embedder.cohere_embedder import CohereMultilingualEmbedder
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from dynamodb.table_org_info import TableOrganizationInfo
from dynamodb.table_organization_risk_embedd2org import TableOrgainzationRiskEmbedd2Orgainzation
from dynamodb.table_org2media import TableOrg2Media
from dynamodb.organization_risk_embedd_service import OrganizationRiskEmbeddService
from faiss_manager.faiss_index_manager import FaissIndexManager
from logger import _setup_logger
import config
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class OrganizationInfoSimilarRetriever:
    def __init__(self, faiss_manager: FaissIndexManager, 
                 bedrock_base_client,
                 base_dynamo: BaseDynamoDB):

        """
        index_dir: đường dẫn đến FAISS index đã lưu
        bedrock_base_client: client Bedrock đã được khởi tạo từ bên ngoài
        """
        self.faiss_searcher = FaissSearcher(faiss_manager)
        self.embedder = CohereMultilingualEmbedder(bedrock_client=bedrock_base_client)
        self.query = DynamoQuery(base_dynamo.dynamodb)

        orgainzation_risk_embedd_per_linker = TableOrgainzationRiskEmbedd2Orgainzation(self.query, table_config=config.TABLE_CONFIG_DEMO)
        org_info = TableOrganizationInfo(self.query, table_config=config.TABLE_CONFIG_DEMO)
        org_media_linker = TableOrg2Media(self.query, table_config=config.TABLE_CONFIG_DEMO)

        # ✅ Khởi tạo MediaService với tất cả các dependency
        self.organization_risk_embedd_service = OrganizationRiskEmbeddService(
            organization_risk_embedd_org_linker=orgainzation_risk_embedd_per_linker,
            org_info=org_info,
            org_media_linker=org_media_linker
        )


    def retrieve_embedding_ids(self, new_organization_info_jsons: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Nhận list bài viết mới và tìm top-k văn bản tương tự từ FAISS index.

        Returns:
            List gồm mỗi phần tử là dict:
                {
                    "query": bài báo gốc,
                    "results": danh sách top-k kết quả FAISS
                }
        """
        queries = [str(d) for d in new_organization_info_jsons]
        embeddings = self.embedder.embed(queries)

        all_results = []
        for doc, embedding in zip(new_organization_info_jsons, embeddings):
            search_results = self.faiss_searcher.search_top_k(
                np.array(embedding), top_k=top_k
            )
            top_k_ids = [result['id'] for result in search_results]
            all_results.append({
                "query": doc,
                "top_k_ids": top_k_ids
            })

        logger.debug(f"Retrieval thanh cong embeddings ids thanh cong {len(all_results)}")
        return all_results
    
    def retrieve_organization_risk_info(self, new_organization_info_jsons: List[Dict], top_k: int = 5) -> List[Dict]:
        embedding_id_results = self.retrieve_embedding_ids(new_organization_info_jsons, top_k)

        logger.debug(f"Retrieved {embedding_id_results} embedding IDs from FAISS")
        results = []
        for idx, result in enumerate(embedding_id_results):
            top_k_ids = result['top_k_ids']
            top_k_ids = [str(id) for id in top_k_ids]
            top_k_organization_risk_infos = self.organization_risk_embedd_service.get_org_media_info_by_organization_risk_embedd_ids(top_k_ids)
            result['top_k_organization_risk_infos'] = top_k_organization_risk_infos
            
            results.append(result)
        
        logger.debug(f"Retrieval organization_infos thanh cong {len(results)}")
        
        return results

def main():
    from embedder.bedrock_base import BedrockBaseClient
    from utils import Utils
    import config

    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    REGION_MODEL = "us-east-1"
    REGION = config.AWS_REGION

    # Đã khởi tạo bedrock từ bên ngoài
    bedrock_base = BedrockBaseClient(
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY,
        region_name=REGION_MODEL
    )

    # Tạo retriever với client đã có
    faiss_index_path = 'data/faiss_indexs/org_faiss_index'

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )
    
    # query = DynamoQuery(base_dynamo.dynamodb)

    # personal2media_table = TablePersonalInfo(query=query, table_config=config.TABLE_CONFIG_DEMO)
    # personal_risk_embedd2media_table = TablePersonalRiskEmbedd2Personal(query=query, table_config=config.TABLE_CONFIG_DEMO)
    
    retriever = OrganizationInfoSimilarRetriever(index_dir=faiss_index_path,
                                     bedrock_base_client=bedrock_base.get_client(), 
                                     base_dynamo=base_dynamo)

    # Bài viết mới
    new_articles = [
        {
            "organizer_id": "O001",
            "full_name": "Tập đoàn Vạn Thịnh Phát",
            "founded_year": None,
            "industry_or_sector": None,
            "legal_structure": None,
            "occupation_or_position": None,
            "headquarters_location": None,
            "organization": None,
            "related_entities_type": None,
            "website": None
        },
        {
            "organizer_id": "O002",
            "full_name": "Ngân hàng SCB",
            "founded_year": None,
            "industry_or_sector": "Ngân hàng",
            "legal_structure": "Ngân hàng thương mại cổ phần",
            "occupation_or_position": None,
            "headquarters_location": None,
            "organization": None,
            "related_entities_type": None,
            "website": None
        }
    ]

    # Truy xuất
    results = retriever.retrieve_organization_risk_info(new_articles, top_k=3)
    for i, res in enumerate(results, 1):
        print(f"\n[{i}] Bài báo gốc: {Utils.json_to_str(res)}")
        print(f"Ket qua top k: {Utils.json_to_str(res)}")
    print(f"So luong results {len(results)}")

if __name__ == "__main__":
    main()
    

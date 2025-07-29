import numpy as np
from typing import List, Dict
from faiss_manager.faiss_searcher import FaissSearcher  # class bạn đã viết ở trên
from embedder.cohere_embedder import CohereMultilingualEmbedder
from dynamodb.table_personal_info import TablePersonalInfo
from dynamodb.table_personal_risk_embedd2per import TablePersonalRiskEmbedd2Personal
from dynamodb.personal_risk_embedd_service import PersonalRiskEmbeddService
from dynamodb.table_personal2media import TablePersonal2Media
from faiss_manager.faiss_index_manager import FaissIndexManager
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class PersonalInfoSimilarRetriever:
    def __init__(self, faiss_manager: FaissIndexManager, 
                 bedrock_base_client,
                 base_dynamo: BaseDynamoDB):

        """
        index_dir: đường dẫn đến FAISS index đã lưu
        bedrock_base_client: client Bedrock đã được khởi tạo từ bên ngoài
        """
        self.faiss_searcher = FaissSearcher(faiss_manager=faiss_manager)
        self.embedder = CohereMultilingualEmbedder(bedrock_client=bedrock_base_client)
        self.query = DynamoQuery(base_dynamo.dynamodb)

        personal_risk_embedd_per_linker = TablePersonalRiskEmbedd2Personal(self.query, table_config=config.TABLE_CONFIG_DEMO)
        per_info = TablePersonalInfo(self.query, table_config=config.TABLE_CONFIG_DEMO)
        per_media_linker = TablePersonal2Media(self.query, table_config=config.TABLE_CONFIG_DEMO)

        # ✅ Khởi tạo MediaService với tất cả các dependency
        self.personal_risk_embedd_service = PersonalRiskEmbeddService(
            personal_risk_embedd_per_linker=personal_risk_embedd_per_linker,
            per_info=per_info,
            per_media_linker=per_media_linker
        )
  

    def retrieve_embedding_ids(self, new_personal_info_jsons: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Nhận list bài viết mới và tìm top-k văn bản tương tự từ FAISS index.

        Returns:
            List gồm mỗi phần tử là dict:
                {
                    "query": bài báo gốc,
                    "results": danh sách top-k kết quả FAISS
                }
        """
        queries = [str(d) for d in new_personal_info_jsons]
        embeddings = self.embedder.embed(queries)

        all_results = []
        for doc, embedding in zip(new_personal_info_jsons, embeddings):
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
    
    def retrieve_personal_risk_info(self, new_personal_info_jsons: List[Dict], top_k: int = 5) -> List[Dict]:
        embedding_id_results = self.retrieve_embedding_ids(new_personal_info_jsons, top_k)

        def map_embedd_ids_to_personal_info(embedd_ids):
            embedd_ids = [str(id) for id in embedd_ids]
            embedding_ids2per_ids = self.table_personal_risk_embedd2per_config.map_embedd_ids_to_per_ids(embedd_ids)
            top_k_per_ids = [v for k, v in embedding_ids2per_ids.items()]

            top_k_personal_infos = self.table_personal_info.get_items_by_per_ids(top_k_per_ids)
            return top_k_per_ids, top_k_personal_infos
            
        results = []
        for idx, result in enumerate(embedding_id_results):
            top_k_ids = result['top_k_ids']
            top_k_ids = [str(id) for id in top_k_ids]
            # top_k_per_ids, top_k_personal_infos = map_embedd_ids_to_personal_info(top_k_ids)
            # result['top_k_per_ids'] = top_k_per_ids
            # result['top_k_personal_infos'] = top_k_personal_infos
            top_k_personal_risk_infos = self.personal_risk_embedd_service.get_per_media_info_by_personal_risk_embedd_ids(top_k_ids)
            result['top_k_personal_risk_infos'] = top_k_personal_risk_infos
            
            results.append(result)
        
        logger.debug(f"Retrieval personal_infos thanh cong {len(results)}")
        
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
    faiss_index_path = 'D:/VPBankHackathon/data/faiss_indexs/personal_faiss_index'

    base_dynamo = BaseDynamoDB(
        region_name=REGION,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )
    
    # query = DynamoQuery(base_dynamo.dynamodb)

    # personal2media_table = TablePersonalInfo(query=query, table_config=config.TABLE_CONFIG_DEMO)
    # personal_risk_embedd2media_table = TablePersonalRiskEmbedd2Personal(query=query, table_config=config.TABLE_CONFIG_DEMO)
    
    retriever = PersonalInfoSimilarRetriever(index_dir=faiss_index_path,
                                     bedrock_base_client=bedrock_base.get_client(), 
                                     base_dynamo=base_dynamo)

    # Bài viết mới
    new_articles = [
        {
            "full_name": "Trương Mỹ Lan",
            "birth_year_or_age": None,
            "gender": "Female",
            "occupation_or_position": "Chủ tịch hội đồng quản trị",
            "organization": "Tập đoàn Vạn Thịnh Phát",
            "hometown_or_residence": None,
            "personal_relationships": "Cổ đông lớn, người nắm giữ gần tuyệt đối cổ phần Ngân hàng SCB; Chỉ đạo các bị cáo Đinh Văn Thành, Bùi Anh Dũng, Võ Tấn Hoàng Văn, Tạ Chiêu Trung, Trương Khánh Hoàng, Trần Thị Mỹ Dung",
            "per_id": "per_id_1753515158960955",
            "created_at": 1753515158960955
        },
        {
            "full_name": "Đinh Văn Thành",
            "birth_year_or_age": None,
            "gender": "Male",
            "occupation_or_position": None,
            "organization": "Ngân hàng SCB",
            "hometown_or_residence": None,
            "personal_relationships": "Thực hiện ý chí của Trương Mỹ Lan",
            "per_id": "per_id_1753515158961721",
            "created_at": 1753515158960955
        },
        {
            "full_name": "Bùi Anh Dũng",
            "birth_year_or_age": None,
            "gender": "Male",
            "occupation_or_position": None,
            "organization": "Ngân hàng SCB",
            "hometown_or_residence": None,
            "personal_relationships": "Thực hiện ý chí của Trương Mỹ Lan",
            "per_id": "per_id_1753515158962350",
            "created_at": 1753515158960955
        },
        {
            "full_name": "Võ Tấn Hoàng Văn",
            "birth_year_or_age": None,
            "gender": "Male",
            "occupation_or_position": None,
            "organization": "Ngân hàng SCB",
            "hometown_or_residence": None,
            "personal_relationships": "Thực hiện ý chí của Trương Mỹ Lan",
            "per_id": "per_id_1753515158962980",
            "created_at": 1753515158960955
        }
    ]

    # Truy xuất
    results = retriever.retrieve_personal_risk_info(new_articles, top_k=3)
    for i, res in enumerate(results, 1):
        print(f"\n[{i}] Bài báo gốc: {Utils.json_to_str(res)}")
        print(f"Ket qua top k: {Utils.json_to_str(res)}")
    print(f"So luong results {len(results)}")

if __name__ == "__main__":
    main()
    

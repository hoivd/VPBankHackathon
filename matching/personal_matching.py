import numpy as np
# from logging import _setup_logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from faiss_manager.faiss_searcher import FaissSearcher
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from dynamodb.table_personal_info import TablePersonalInfo
from utils import Utils  # dùng để lấy AWS key từ môi trường
import json
from llm_model.bedrock_manager import BedrockModelManager
from matching.llm_rerank_personal import LlmRerankerPersonal
from embedder.bedrock_base import BedrockBaseClient
from embedder.cohere_embedder import CohereMultilingualEmbedder
from faiss_manager.faiss_index_manager import FaissIndexManager
from dynamodb.table_personal_risk_embedd2per import TablePersonalRiskEmbedd2Personal
import time
from S3.s3_fetcher import S3DataFetcher
from S3.s3_connector import S3Connector
import logging
from path_utils import get_prompts_path

logging = logging.getLogger(__name__)


class PersonMatcherFAISS:
    def __init__(self, embedder: CohereMultilingualEmbedder,
                  faiss_searcher: FaissSearcher,
                 personal_risk_embedd_table: TablePersonalRiskEmbedd2Personal,
                 personal_info_table: TablePersonalInfo,
                 llm_reranker: LlmRerankerPersonal):  # ⚠️ Lưu ý: đây là instance của class reranker, không phải LLM manager nữa
        self.embedder = embedder
        self.faiss_searcher = faiss_searcher
        self.personal_risk_embedd_table = personal_risk_embedd_table
        self.personal_info_table = personal_info_table
        self.llm_reranker = llm_reranker

    def match(self, query: list[str], top_k: int = 1) -> list[str]:
        logging.info(f"⚙️ Đang tạo embedding cho {query}...")
        query_embeddings = self.embedder.embed(query)
        query_embedding = query_embeddings[0]
        query_embedding = np.array(query_embedding).astype('float32') 
        logging.info("🔍 Đang tìm kiếm trong FAISS index...")
        results = self.faiss_searcher.search_top_k(query_embedding, top_k=top_k)

        faiss_ids = [item["id"] for item in results]
        logging.info(f"📌 Tìm thấy các FAISS ID: {faiss_ids}")

        personal_embedd_ids = [str(faiss_id) for faiss_id in faiss_ids]
        logging.info("🔗 Đang ánh xạ personal_embedd_id → per_id...")
        embedd_to_per = self.personal_risk_embedd_table.map_embedd_ids_to_per_ids(personal_embedd_ids)

        matched_per_ids = [embedd_to_per[eid] for eid in personal_embedd_ids if eid in embedd_to_per]
        return matched_per_ids

    def match_full_info(self, query: list[str], top_k: int = 1) -> list[dict]:
        """
        Trả về danh sách thông tin đầy đủ (dict) của các per_id khớp nhất với query.
        """
        per_ids = self.match(query, top_k)
        return self.personal_info_table.get_items_by_per_ids(per_ids)

    def rerank_by_llm(self, query: list[str], candidates: list[dict], top_k_result=5) -> dict:
        """
        Gọi mô hình LLM thông qua LlmRerankerPersonal để so sánh query với từng candidate.
        Trả về dict có dạng:
        {'per': ..., 'per_id': ..., 'raw': ..., 'index': ...} hoặc {'per_id': 'none'}
        """
        query = query[0]
        return self.llm_reranker.rerank(query=query, per_items=candidates, top_k_result=top_k_result)

def main():
    # ==== Bước 1: Cấu hình ====
    local_faiss_index_path = './s3_downloads/faiss_indexes/personal_faiss_index'
    bucket_name = "team253vpbank"
    faiss_key = f"faiss_indexes/personal_faiss_index"

    # ==== Bước 2: Khởi tạo các thành phần chính ====

    # ==== DynamoDB ====
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")

    REGION = config.AWS_REGION
    REGION_MODEL = config.AWS_VIRGINA_REGION
    DEFAULT_MODEL_ID = config.CLAUDE_37_SONNET_CROSS_REGION_MODEL_ID

    s3_client = S3Connector(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION
    ).get_client()
    fetcher = S3DataFetcher(s3_client)

    fetcher.download_folder(bucket_name=bucket_name, s3_folder_prefix=faiss_key, local_dir=local_faiss_index_path)
    print("📁 Đã tải toàn bộ thư mục.")

    base_dynamo = BaseDynamoDB(region_name=REGION, access_key=AWS_ACCESS_KEY, secret_key=AWS_SECRET_KEY)
    dynamo_query = DynamoQuery(base_dynamo.dynamodb)

    personal_embedd_table = TablePersonalRiskEmbedd2Personal(query=dynamo_query, table_config=config.TABLE_CONFIG_DEMO)
    personal_info_table = TablePersonalInfo(query=dynamo_query, table_config=config.TABLE_CONFIG_DEMO)

    bedrock_base = BedrockBaseClient(
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY,
        region_name=REGION
    )

    # Khởi tạo Cohere embedder
    personal_embedder = CohereMultilingualEmbedder(bedrock_client=bedrock_base.get_client())

    llm_manager = BedrockModelManager(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION_MODEL,
        default_model_id=DEFAULT_MODEL_ID
    )
    
    prompt_path = get_prompts_path('rerank_personal.txt')
    prompt_template = Utils.load_text(prompt_path)
    # print(prompt_template)

    reranker = LlmRerankerPersonal(llm_manager=llm_manager, model_type="claude", prompt_template=prompt_template)

    faiss_manager = FaissIndexManager.load_index(
        directory=local_faiss_index_path
    )
    faiss_searcher = FaissSearcher(faiss_manager)


    # ==== Khởi tạo matcher với thông tin đầy đủ ====
    matcher = PersonMatcherFAISS(
        personal_embedder,
        faiss_searcher,
        personal_embedd_table,
        personal_info_table,
        reranker
    )
    start = time.time()
    # ==== Tìm kiếm ====
    query = ["Trương Mỹ Lan, chủ tịch Vạn thịnh phát"]
    results = matcher.match_full_info(query, top_k=20)

    print(Utils.json_to_str(results))

    print("✅ Kết quả khớp cá nhân đầy đủ:")
    for i, item in enumerate(results, 1):
        print(f"\n🔹 Kết quả #{i}")
        for k, v in item.items():
            print(f"{k}: {v}")

    print("✅ Đang đánh giá lại bằng LLM...")
    result = matcher.rerank_by_llm(query, results, top_k_result=10)

    print("🎯 Kết quả LLM đánh giá:")
    end = time.time()
    print(f"Thời gian thực hiện: {end - start:.2f} giây") 

    print(Utils.json_to_str(result))
    return result

if __name__ == "__main__":
    main()
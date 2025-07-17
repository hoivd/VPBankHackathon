import os
import numpy as np
from embedder.model_embedder import ModelEmbedder
from logger import _setup_logger
import config

from embedder.personal_embedder import PersonalEmbedder
from faiss_manager.faiss_searcher import FaissSearcher
from dynamodb.table_personal_embedd2personal import TablePersonalEmbedd2Personal
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from dynamodb.table_personal_info import TablePersonalInfo
from utils import Utils  # dùng để lấy AWS key từ môi trường
import json
from llm_model.bedrock_manager import BedrockModelManager
from matching.llm_rerank_personal import LlmRerankerPersonal

logger = _setup_logger(__name__, config.LOG_LEVEL)


class PersonMatcherFAISS:
    def __init__(self, embedder: PersonalEmbedder, faiss_searcher: FaissSearcher,
                 personal_embedd_table: TablePersonalEmbedd2Personal,
                 personal_info_table: TablePersonalInfo,
                 llm_reranker: LlmRerankerPersonal):  # ⚠️ Lưu ý: đây là instance của class reranker, không phải LLM manager nữa
        self.embedder = embedder
        self.faiss_searcher = faiss_searcher
        self.personal_embedd_table = personal_embedd_table
        self.personal_info_table = personal_info_table
        self.llm_reranker = llm_reranker

    def match(self, query: str, top_k: int = 1) -> list[str]:
        logger.info("⚙️ Đang tạo embedding cho query...")
        query_embedding = self.embedder.embed_personal(query)

        logger.info("🔍 Đang tìm kiếm trong FAISS index...")
        results = self.faiss_searcher.search_top_k(query_embedding, top_k=top_k)

        faiss_ids = [item["id"] for item in results]
        logger.info(f"📌 Tìm thấy các FAISS ID: {faiss_ids}")

        personal_embedd_ids = [int(faiss_id) for faiss_id in faiss_ids]
        logger.info("🔗 Đang ánh xạ personal_embedd_id → per_id...")
        embedd_to_per = self.personal_embedd_table.map_embedd_ids_to_per_ids(personal_embedd_ids)

        matched_per_ids = [embedd_to_per[eid] for eid in personal_embedd_ids if eid in embedd_to_per]
        return matched_per_ids

    def match_full_info(self, query: str, top_k: int = 1) -> list[dict]:
        """
        Trả về danh sách thông tin đầy đủ (dict) của các per_id khớp nhất với query.
        """
        per_ids = self.match(query, top_k)
        return self.personal_info_table.get_items_by_per_ids(per_ids)

    def rerank_by_llm(self, query: str, candidates: list[dict]) -> dict:
        """
        Gọi mô hình LLM thông qua LlmRerankerPersonal để so sánh query với từng candidate.
        Trả về dict có dạng:
        {'per': ..., 'per_id': ..., 'raw': ..., 'index': ...} hoặc {'per_id': 'none'}
        """
        return self.llm_reranker.rerank(query=query, per_items=candidates)


if __name__ == "__main__":
    # ==== Bước 1: Cấu hình ====
    model_name = config.EMBEDDING_MODEL_NAME
    faiss_index_path = 'data/personal_faiss_index'

    # ==== Bước 2: Khởi tạo các thành phần chính ====
    base_embedder = ModelEmbedder(model_name=model_name)
    personal_embedder = PersonalEmbedder(base_embedder=base_embedder)
    faiss_searcher = FaissSearcher(index_dir=faiss_index_path)

    # ==== DynamoDB ====
    AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
    NEW_AWS_ACCESS_KEY = Utils.load_api_key_from_env("NEW_AWS_ACCESS_KEY")
    NEW_AWS_SECRET_KEY = Utils.load_api_key_from_env("NEW_AWS_SECRET_KEY")

    REGION = config.AWS_REGION
    REGION_MODEL = config.AWS_VIRGINA_REGION
    DEFAULT_MODEL_ID = 'arn:aws:bedrock:us-east-1:538830382271:inference-profile/us.anthropic.claude-3-haiku-20240307-v1:0'

    base_dynamo = BaseDynamoDB(region_name=REGION, access_key=AWS_ACCESS_KEY, secret_key=AWS_SECRET_KEY)
    dynamo_query = DynamoQuery(base_dynamo.dynamodb)

    personal_embedd_table = TablePersonalEmbedd2Personal(query=dynamo_query, table_config=config.TABLE_CONFIG_DEMO)
    personal_info_table = TablePersonalInfo(query=dynamo_query, table_config=config.TABLE_CONFIG_DEMO)


    llm_manager = BedrockModelManager(
        aws_access_key_id=NEW_AWS_ACCESS_KEY,
        aws_secret_access_key=NEW_AWS_SECRET_KEY,
        region_name=REGION_MODEL,
        default_model_id=DEFAULT_MODEL_ID
    )

    prompt_path = './prompts/prompt_compare_query_personal.txt'
    prompt_template = Utils.load_text(prompt_path)
    print(prompt_template)

    reranker = LlmRerankerPersonal(llm_manager=llm_manager, model_type="claude", prompt_template=prompt_template)


    # ==== Khởi tạo matcher với thông tin đầy đủ ====
    matcher = PersonMatcherFAISS(
        personal_embedder,
        faiss_searcher,
        personal_embedd_table,
        personal_info_table,
        reranker
    )

    # ==== Tìm kiếm ====
    query = """Anh Quân, là người đàn ông 43 tuổi, từng là giảng viên đại học, không phải là chủ tịch"""
    results = matcher.match_full_info(query, top_k=10)

    print("✅ Kết quả khớp cá nhân đầy đủ:")
    for i, item in enumerate(results, 1):
        print(f"\n🔹 Kết quả #{i}")
        for k, v in item.items():
            print(f"{k}: {v}")

    print("✅ Đang đánh giá lại bằng LLM...")
    best_match = matcher.rerank_by_llm(query, results)

    print("🎯 Kết quả LLM đánh giá:")
    print("Per_id:", best_match["per_id"])
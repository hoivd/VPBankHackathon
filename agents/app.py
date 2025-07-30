#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embedder.cohere_embedder import CohereMultilingualEmbedder
from embedder.personal_embedder import PersonalEmbedder
from embedder.bedrock_base import BedrockBaseClient
from faiss_manager.faiss_searcher import FaissSearcher
from agents.tools.person_risk_agent import PersonRiskAgent
from dynamodb.table_adverse_media import TableAdverseMedia
from dynamodb.table_personal_info import TablePersonalInfo
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from utils import Utils
import config
from S3.s3_fetcher import S3DataFetcher
from S3.s3_connector import S3Connector
from llm_model.bedrock_manager import BedrockModelManager
from faiss_manager.faiss_index_manager import FaissIndexManager
from dynamodb.table_personal_risk_embedd2per import TablePersonalRiskEmbedd2Personal
from matching.personal_matching import PersonMatcherFAISS
from matching.llm_rerank_personal import LlmRerankerPersonal
import time 
from path_utils import get_prompts_path
import logging
app = FastAPI(
    title="VP Bank Person Risk Analysis API",
    description="Vietnamese-language API for person risk analysis using DynamoDB lookup and characteristic scoring",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = None
media_service = None
personal_embedder = None
faiss_searcher = None
matcher = None

@app.on_event("startup")
async def  startup_event():
    global agent, media_service, personal_embedder, faiss_searcher, matcher
    try:
        # Initialize AWS credentials first
        local_faiss_index_path = './s3_downloads/faiss_indexes/personal_faiss_index'
        bucket_name = "team253vpbank"
        faiss_key = f"faiss_indexes/personal_faiss_index"
    
        AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
        AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
        REGION = config.AWS_REGION
        REGION_MODEL = config.AWS_VIRGINA_REGION
        DEFAULT_MODEL_ID = config.CLAUDE_37_SONNET_CROSS_REGION_MODEL_ID
        
        print("🚀 Initializing Embedding Services...")
        # faiss_index_path = 'faiss_indexes/new_table/personal_faiss_index'
        # Initialize Bedrock client
        
        s3_client = S3Connector(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=REGION
        ).get_client()
        
        fetcher = S3DataFetcher(s3_client)
        
        fetcher.download_folder(bucket_name=bucket_name, s3_folder_prefix=faiss_key, local_dir=local_faiss_index_path)

        base_dynamo = BaseDynamoDB(
            region_name=REGION,
            access_key=AWS_ACCESS_KEY,
            secret_key=AWS_SECRET_KEY
        )
        
        dynamo_query = DynamoQuery(base_dynamo.dynamodb)
        
        personal_embedd_table = TablePersonalRiskEmbedd2Personal(query=dynamo_query, table_config=config.TABLE_CONFIG_DEMO)
        personal_info_table = TablePersonalInfo(query=dynamo_query, table_config=config.TABLE_CONFIG_DEMO)
       
        bedrock_base = BedrockBaseClient(
            access_key=AWS_ACCESS_KEY,
            secret_key=AWS_SECRET_KEY,
            region_name=REGION
        )

        personal_embedder = CohereMultilingualEmbedder(bedrock_client=bedrock_base.get_client())

        llm_manager = BedrockModelManager(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            default_model_id=DEFAULT_MODEL_ID
        )
        prompt_path = get_prompts_path('rerank_personal.txt')
        prompt_template = Utils.load_text(prompt_path)
        
        reranker = LlmRerankerPersonal(llm_manager=llm_manager, model_type="claude", prompt_template=prompt_template)

        faiss_manager = FaissIndexManager.load_index(
            directory=local_faiss_index_path
        )
        faiss_searcher = FaissSearcher(faiss_manager)
        matcher = PersonMatcherFAISS(
            personal_embedder,
            faiss_searcher,
            personal_embedd_table,
            personal_info_table,
            reranker
        )
        agent = PersonRiskAgent(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=REGION
        )

        table_config = config.TABLE_CONFIG
        media_service = TableAdverseMedia(dynamo_query, table_config)
        print("✅ Media Service initialized successfully!")
        
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        raise e

# Request/Response models
class QueryRequest(BaseModel):
    person_id: str
    top_k: int = 5

class QueryPerson(BaseModel):
    person_id: str
    person_name: str = None
class PersonLookupRequest(BaseModel):
    person_name: str

class QueryResponse(BaseModel):
    success: bool
    response: dict
    person_id: Optional[str] = None
    person_name: Optional[str] = None
    error: Optional[str] = None

class DetailedAnalysisResponse(BaseModel):
    success: bool
    person_name: Optional[str] = None
    risk_analysis: Optional[Dict[str, Any]] = None
    lookup_result: Optional[Dict[str, Any]] = None
    formatted_response: Optional[str] = None
    error: Optional[str] = None

class MediaContentResponse(BaseModel):
    success: bool
    media_id: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    message: str

# New models for get_name endpoint
class PersonMatchItem(BaseModel):
    per_id: str
    per_name: str
    relevance_score: int

class NameListResponse(BaseModel):
    success: bool
    results: List[PersonMatchItem]
    query: str
    top_k: int
    processing_time: Optional[float] = None
    error: Optional[str] = None

# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="VP Bank Person Risk Analysis API is running"
    )

@app.get("/health", response_model=HealthResponse)
async def health():
    """Detailed health check"""
    global agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return HealthResponse(
        status="healthy",
        message="Agent is ready and all systems operational"
    )

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryPerson):
    """
    Process a person ID to get risk analysis
    
    Args:
        request: QueryRequest with the person ID
        
    Returns:
        QueryResponse with formatted Vietnamese response
    """
    global agent, personal_embedder, faiss_searcher
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        person_id = request.person_id
        person_name =  request.person_name
        # Process the person ID directly
        response = agent.process_query_v2(person_id=person_id,person_name=person_name)
        print(f"___________________{type(response)}___________________")
        print(f"____________________Response: {response}________________")
        return QueryResponse(
            success=True,
            response=response,
            person_id=person_id
        )
        
    except Exception as e:
        return QueryResponse(
            success=False,
            response="",
            error=f"Error processing person ID: {str(e)}"
        )

@app.post("/analyze", response_model=DetailedAnalysisResponse)
async def detailed_analysis(request: PersonLookupRequest):
    """
    Get detailed risk analysis for a specific person
    
    Args:
        request: PersonLookupRequest with person name
        
    Returns:
        DetailedAnalysisResponse with complete analysis data
    """
    global agent, personal_embedder, faiss_searcher
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Perform person lookup
        lookup_result = agent.person_lookup.lookup_person_comprehensive_v2(
            request.person_name, 
            personal_embedder, 
            faiss_searcher
        )
        
        # Analyze risk characteristics
        risk_analysis = agent.calculate_risk_score_v2(lookup_result)
        
        # Generate formatted response
        if "error" not in risk_analysis:
            formatted_response = agent.generate_vietnamese_response_v2(
                request.person_name, 
                risk_analysis, 
                lookup_result
            )
        else:
            formatted_response = f"❌ Không tìm thấy thông tin về '{request.person_name}' trong hệ thống."
            if risk_analysis.get("suggestions"):
                formatted_response += "\n\n💡 Có thể bạn đang tìm:\n"
                for suggestion in risk_analysis["suggestions"]:
                    formatted_response += f"• {suggestion}\n"
        
        return DetailedAnalysisResponse(
            success=True,
            person_name=request.person_name,
            risk_analysis=risk_analysis,
            lookup_result=lookup_result,
            formatted_response=formatted_response
        )
        
    except Exception as e:
        return DetailedAnalysisResponse(
            success=False,
            error=f"Error analyzing person: {str(e)}"
        )

@app.post("/get-name-list", response_model=NameListResponse)
async def get_name(request: QueryRequest):
    """
    Get a list of person matches based on the query
    
    Args:
        request: QueryRequest with person_id and top_k parameter
        
    Returns:
        NameListResponse with list of person matches and relevance scores
    """
    global matcher, agent
    if matcher is None:
        return NameListResponse(
            success=False,
            results=[],
            query=request.person_id,
            top_k=request.top_k,
            error="Matcher not initialized"
        )
    
    try:
        person_id = request.person_id
        top_k = request.top_k
        start = time.time()
        query  = [person_id]
        # query = ["Trương Mỹ Lan, chủ tịch Vạn thịnh phát"]
        results = matcher.match_full_info(query, top_k=2*top_k)
        print(f"final_result: {results}")
        final_result = matcher.rerank_by_llm(query, results, top_k_result=top_k)
        print(f"after rerank: {final_result}")
        end = time.time()
        
        person_matches = []
        for result in final_result:
            if isinstance(result, dict) and 'per_id' in result and 'relevance_score' in result:
                per_id = result['per_id']
                relevance_score = result['relevance_score']
                
                # Get person name using the find_person_by_id function
                # person_info = agent.person_lookup.find_person_by_id(per_id)
                person_info = matcher.personal_info_table.get_by_per_id(per_id)
                # print(f"person info is: {person_info}")
                per_name = person_info.get('full_name', 'Unknown') if person_info else 'Unknown'
                
                person_matches.append(PersonMatchItem(
                    per_id=per_id,
                    per_name=per_name,
                    relevance_score=relevance_score
                ))
        logging.info(f"person_matches: {person_matches}")
        return NameListResponse(
            success=True,
            results=person_matches,
            query=person_id,
            top_k=top_k,
            processing_time=end-start
        )
    except Exception as e:
        return NameListResponse(
            success=False,
            results=[],
            query=request.person_id,
            top_k=request.top_k,
            error=f"Error processing person ID: {str(e)}"
        )

@app.post("/extract-name")
async def extract_name(request: QueryRequest):
    global agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:  
        # Try LLM if regex fails
        llm_name = agent.extract_person_name_with_llm(request.person_id)
        
        # Final result
        final_name = llm_name
        
        return {
            "success": True,
            "person_name": final_name,
            "llm_result": llm_name,
            "method_used": "llm" if llm_name else "none",
            "llm_enabled": agent.llm_enabled,
            "original_query": request.person_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error extracting name: {str(e)}"
        }

@app.get("/media/{media_id}", response_model=MediaContentResponse)
async def get_media_content(media_id: str = Path(..., description="The media ID to retrieve content for")):
    """
    Get news content from adverse_media table by media_id
    
    Args:
        media_id: The media ID to look up in the adverse_media table
        
    Returns:
        MediaContentResponse with the full media document content
    """
    try:
        # Get media content from DynamoDB
        AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
        AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
        REGION = config.AWS_REGION

        base_dynamo = BaseDynamoDB(
            region_name=REGION,
            access_key=AWS_ACCESS_KEY,
            secret_key=AWS_SECRET_KEY
        )

        query = DynamoQuery(base_dynamo.dynamodb)
        table_adverse_media = TableAdverseMedia(query, config.TABLE_CONFIG)
        media_content = table_adverse_media.get_document_by_media_id(media_id)
        if not media_content:
            return MediaContentResponse(
                success=False,
                media_id=media_id,
                error=f"No media content found for media_id: {media_id}"
            )
        
        return MediaContentResponse(
            success=True,
            media_id=media_id,
            content=media_content
        )
        
    except Exception as e:
        return MediaContentResponse(
            success=False,
            media_id=media_id,
            error=f"Error retrieving media content: {str(e)}"
        )

@app.get("/api-docs")
async def get_api_docs():
    """Get API documentation and usage examples"""
    return {
        "title": "VP Bank Person Risk Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "/": "Health check",
            "/health": "Detailed health check",
            "/query": "Process person ID to get risk analysis",
            "/analyze": "Get detailed risk analysis for a person",
            "/get-name-list": "Get list of person matches",
            "/extract-name": "Extract person name from Vietnamese text",
            "/media/{media_id}": "Get news content from adverse_media table by media_id"
        },
        "examples": {
            "query": {
                "endpoint": "/query",
                "method": "POST",
                "body": {
                    "person_id": "per_id_1753806629409294",
                    "top_k": 5
                }
            },
            "get-name-list": {
                "endpoint": "/get-name-list",
                "method": "POST",
                "body": {
                    "person_id": "per_id_1753806629409294",
                    "top_k": 5
                }
            },
            "analyze": {
                "endpoint": "/analyze", 
                "method": "POST",
                "body": {
                    "person_name": "Trương Mỹ Lan"
                }
            },
            "media": {
                "endpoint": "/media/{media_id}",
                "method": "GET",
                "description": "Replace {media_id} with actual media ID, e.g., /media/123"
            }
        }
    }

if __name__ == "__main__":
    print(" Starting VP Bank Person Risk Analysis API...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
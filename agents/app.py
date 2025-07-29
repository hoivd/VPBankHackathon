#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Backend for Person Risk Analysis Agent
Provides REST API endpoints for the Vietnamese person risk analysis system
"""
import os
import sys
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from embedder.model_embedder import ModelEmbedder
    from embedder.personal_embedder import PersonalEmbedder
    from faiss_manager.faiss_searcher import FaissSearcher
    from agents.tools.person_risk_agent import PersonRiskAgent
    from dynamodb.table_adverse_media import TableAdverseMedia
    from dynamodb.dynamo_query import DynamoQuery
    from dynamodb.base_dynamo import BaseDynamoDB
    from utils import Utils
    import config
except ImportError:
    from tools.person_risk_agent import PersonRiskAgent
    sys.path.append('..')
    from dynamodb.table_adverse_media import TableAdverseMedia
    from dynamodb.dynamo_query import DynamoQuery
    from dynamodb.base_dynamo import BaseDynamoDB
    from utils import Utils
    import config

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

@app.on_event("startup")
async def startup_event():
    """Initialize the agent and media service on startup"""
    global agent, media_service, personal_embedder, faiss_searcher
    try:
        
        # model_name = config.EMBEDDING_MODEL_NAME
        faiss_index_path = 'D:/VPBankHackathon/faiss_indexes/new_table/personal_faiss_index'

        # ==== Bước 2: Khởi tạo các thành phần chính ====
        base_embedder = ModelEmbedder(model_name=model_name)
        personal_embedder = PersonalEmbedder(base_embedder=base_embedder)
        faiss_searcher = FaissSearcher(index_dir=faiss_index_path)
        print("🚀 Initializing Person Risk Agent...")
        agent = PersonRiskAgent()
        print("✅ Agent initialized successfully!")
        
        print("🚀 Initializing Media Service...")
        # Initialize DynamoDB components for media service
        AWS_ACCESS_KEY = Utils.load_api_key_from_env("AWS_ACCESS_KEY")
        AWS_SECRET_KEY = Utils.load_api_key_from_env("AWS_SECRET_KEY")
        REGION = config.AWS_REGION

        base_dynamo = BaseDynamoDB(
            region_name=REGION,
            access_key=AWS_ACCESS_KEY,
            secret_key=AWS_SECRET_KEY
        )
        
        query = DynamoQuery(base_dynamo.dynamodb)
        table_config=config.TABLE_CONFIG
        media_service = TableAdverseMedia(query,table_config)
        print("✅ Media Service initialized successfully!")
        
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        raise e

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    
class PersonLookupRequest(BaseModel):
    person_name: str

class QueryResponse(BaseModel):
    success: bool
    response: dict
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
async def process_query(request: QueryRequest):
    """
    Process a Vietnamese natural language query about a person
    
    Args:
        request: QueryRequest with the Vietnamese query
        
    Returns:
        QueryResponse with formatted Vietnamese response
    """
    global agent, personal_embedder, faiss_searcher
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # os.chdir("..")
        # print(os.getcwd())

        # Extract person name first
        person_name = agent.extract_person_name_from_query(request.query)
        # full_name = 
        # person_name = "Trương Mỹ Lan"
        # Process the query
        response = agent.process_query_v2(person_name, request.query, personal_embedder, faiss_searcher)
        print(f"___________________{type(response)}___________________")
        print(f"____________________Response: {response}________________")
        return QueryResponse(
            success=True,
            response=response,
            person_name=person_name
        )
        
    except Exception as e:
        return QueryResponse(
            success=False,
            response="",
            error=f"Error processing query: {str(e)}"
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
    global agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Perform person lookup
        lookup_result = agent.person_lookup.lookup_person_comprehensive_v2(request.person_name)
        
        # Analyze risk characteristics
        risk_analysis = agent.calculate_risk_score_v2(lookup_result)
        
        # Generate formatted response
        if "error" not in risk_analysis:
            formatted_response = agent.generate_vietnamese_response_v2(request.person_name, risk_analysis)
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

@app.post("/extract-name")
async def extract_name(request: QueryRequest):
    """
    Extract person name from Vietnamese query using both regex and LLM
    
    Args:
        request: QueryRequest with Vietnamese text
        
    Returns:
        Dict with extracted person name and method used
    """
    global agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:  
        # Try LLM if regex fails
        llm_name = agent.extract_person_name_with_llm(request.query)
        
        # Final result
        final_name = llm_name
        
        return {
            "success": True,
            "person_name": final_name,
            "llm_result": llm_name,
            "method_used": "llm" if llm_name else "none",
            "llm_enabled": agent.llm_enabled,
            "original_query": request.query
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error extracting name: {str(e)}"
        }

@app.post("/extract-name-llm-only")
async def extract_name_llm_only(request: QueryRequest):
    """
    Extract person name from Vietnamese query using LLM only (for testing)
    
    Args:
        request: QueryRequest with Vietnamese text
        
    Returns:
        Dict with LLM-extracted person name
    """
    global agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not agent.llm_enabled:
        return {
            "success": False,
            "error": "LLM not enabled or not available"
        }
    
    try:
        llm_name = agent.extract_person_name_with_llm(request.query)
        return {
            "success": True,
            "person_name": llm_name,
            "method_used": "llm",
            "original_query": request.query
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error with LLM extraction: {str(e)}"
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
        # AWS_ACCESS_KEY='AKIAQWLOPNIDXAC4BJWD'
        # AWS_SECRET_KEY='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'
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
            "/query": "Process Vietnamese natural language query",
            "/analyze": "Get detailed risk analysis for a person",
            "/extract-name": "Extract person name from Vietnamese text",
            "/media/{media_id}": "Get news content from adverse_media table by media_id"
        },
        "examples": {
            "query": {
                "endpoint": "/query",
                "method": "POST",
                "body": {
                    "query": "cho tôi thông tin về Trương Mỹ Lan"
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
    # Run the server
    print("🚀 Starting VP Bank Person Risk Analysis API...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
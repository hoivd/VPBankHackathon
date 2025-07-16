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
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agents.tools.person_risk_agent import PersonRiskAgent
except ImportError:
    from tools.person_risk_agent import PersonRiskAgent

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

@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    global agent
    try:
        print("🚀 Initializing Person Risk Agent...")
        agent = PersonRiskAgent()
        print("✅ Agent initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        raise e

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    
class PersonLookupRequest(BaseModel):
    person_name: str

class QueryResponse(BaseModel):
    success: bool
    response: str
    person_name: Optional[str] = None
    error: Optional[str] = None

class DetailedAnalysisResponse(BaseModel):
    success: bool
    person_name: Optional[str] = None
    risk_analysis: Optional[Dict[str, Any]] = None
    lookup_result: Optional[Dict[str, Any]] = None
    formatted_response: Optional[str] = None
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
    global agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Extract person name first
        # person_name = agent.extract_person_name_from_query(request.query)
        person_name = "Trương Mỹ Lan"
        # Process the query
        response = agent.process_query_v2(request.query)
        
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
            "/extract-name": "Extract person name from Vietnamese text"
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
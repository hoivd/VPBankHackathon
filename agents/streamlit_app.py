#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit UI for VP Bank Person Risk Analysis
User-friendly interface for Vietnamese person risk analysis system
"""
import streamlit as st
import requests
import json
from typing import Dict, Any
import time

# Page configuration
st.set_page_config(
    page_title="VP Bank - Phân Tích Rủi Ro Cá Nhân",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Vietnamese styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .risk-high {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 1rem;
        margin: 1rem 0;
    }
    .risk-medium {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 1rem;
        margin: 1rem 0;
    }
    .risk-low {
        background-color: #e8f5e8;
        border-left: 5px solid #4caf50;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        margin: 0.5rem 0;
    }
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = "http://localhost:8000"

# Helper functions
def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def call_api(endpoint, data=None, method="GET"):
    """Make API calls with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"API Error: {response.status_code} - {response.text}"
    except requests.exceptions.Timeout:
        return False, "API timeout - vui lòng thử lại"
    except requests.exceptions.ConnectionError:
        return False, "Không thể kết nối đến API server"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"

def format_risk_level(risk_level, score):
    """Format risk level with appropriate styling"""
    if risk_level in ["Rất Cao", "Cao"]:
        return f'<div class="risk-high"><strong>🚨 Mức Rủi Ro: {risk_level}</strong> (Điểm: {score})</div>'
    elif risk_level == "Trung Bình":
        return f'<div class="risk-medium"><strong>⚠️ Mức Rủi Ro: {risk_level}</strong> (Điểm: {score})</div>'
    else:
        return f'<div class="risk-low"><strong>✅ Mức Rủi Ro: {risk_level}</strong> (Điểm: {score})</div>'

def display_characteristic_scores(characteristics):
    """Display characteristic scores in a nice format"""
    if not characteristics:
        return
    
    st.subheader("📊 Chi Tiết Đánh Giá Rủi Ro")
    
    cols = st.columns(2)
    
    with cols[0]:
        st.markdown("### Loại Vi Phạm")
        if "violation_type" in characteristics:
            vt = characteristics["violation_type"]
            st.markdown(f"""
            <div class="metric-card">
                <strong>Điểm:</strong> {vt['score']}/6<br>
                <strong>Mô tả:</strong> {vt['description']}<br>
                <strong>Chi tiết:</strong> {vt['details']}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### Vai Trò Khách Hàng")
        if "customer_role" in characteristics:
            cr = characteristics["customer_role"]
            st.markdown(f"""
            <div class="metric-card">
                <strong>Điểm:</strong> {cr['score']}/3<br>
                <strong>Mô tả:</strong> {cr['description']}<br>
                <strong>Chi tiết:</strong> {cr['details']}
            </div>
            """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown("### Tình Trạng Pháp Lý")
        if "legal_status" in characteristics:
            ls = characteristics["legal_status"]
            st.markdown(f"""
            <div class="metric-card">
                <strong>Điểm:</strong> {ls['score']}/3<br>
                <strong>Mô tả:</strong> {ls['description']}<br>
                <strong>Chi tiết:</strong> {ls['details']}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### Nguồn Tin")
        if "source_level" in characteristics:
            sl = characteristics["source_level"]
            st.markdown(f"""
            <div class="metric-card">
                <strong>Điểm:</strong> {sl['score']}/1<br>
                <strong>Mô tả:</strong> {sl['description']}<br>
                <strong>Chi tiết:</strong> {sl['details']}
            </div>
            """, unsafe_allow_html=True)

# Main application
def main():
    # Header
    st.markdown('<h1 class="main-header">🏦 VP Bank - Hệ Thống Phân Tích Rủi Ro Cá Nhân</h1>', unsafe_allow_html=True)
    
    # Check API health
    if not check_api_health():
        st.error("⚠️ API Server không khả dụng. Vui lòng khởi động backend trước.")
        st.info("Chạy lệnh: `cd agents && python app.py`")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cài Đặt")
        
        # Mode selection
        mode = st.selectbox(
            "Chọn chế độ:",
            ["Truy vấn tự nhiên", "Tìm kiếm trực tiếp", "Test LLM Name Extraction", "API Documentation"]
        )
        
        st.markdown("---")
        st.markdown("### 📋 Hướng Dẫn Sử Dụng")
        st.info("""
        **Truy vấn tự nhiên:**
        - "cho tôi thông tin về [Tên]"
        - "tìm kiếm thông tin [Tên]"
        - "ông/bà [Tên] có vi phạm gì không?"
        
        **Ví dụ:**
        - cho tôi thông tin về Trương Mỹ Lan
        - tìm kiếm thông tin Nguyễn Văn A
        """)
        
        st.markdown("---")
        api_status = "🟢 Kết nối" if check_api_health() else "🔴 Mất kết nối"
        st.markdown(f"**Trạng thái API:** {api_status}")
    
    # Main content area
    if mode == "Truy vấn tự nhiên":
        st.header("💬 Truy Vấn Bằng Tiếng Việt")
        
        # Query input
        query = st.text_input(
            "Nhập câu hỏi của bạn:",
            placeholder="cho tôi thông tin về Trương Mỹ Lan",
            help="Sử dụng tiếng Việt tự nhiên để hỏi về thông tin rủi ro của một người"
        )
        
        if st.button("🔍 Phân Tích", type="primary"):
            if query.strip():
                with st.spinner("Đang xử lý truy vấn..."):
                    success, result = call_api("/query", {"query": query}, "POST")
                
                if success:
                    if result.get("success"):
                        st.markdown('<div class="success-message">✅ Phân tích hoàn tất!</div>', unsafe_allow_html=True)
                        
                        # Display extracted person name
                        if result.get("person_name"):
                            st.info(f"🏷️ Tên người được trích xuất: **{result['person_name']}**")
                        
                        # Display response
                        st.markdown("### 📋 Kết Quả Phân Tích")
                        st.markdown(result["response"])
                        
                        # Option to get detailed analysis
                        if result.get("person_name"):
                            if st.button("📊 Xem Phân Tích Chi Tiết"):
                                with st.spinner("Đang tải phân tích chi tiết..."):
                                    detailed_success, detailed_result = call_api(
                                        "/analyze", 
                                        {"person_name": result["person_name"]}, 
                                        "POST"
                                    )
                                
                                if detailed_success and detailed_result.get("success"):
                                    risk_analysis = detailed_result.get("risk_analysis", {})
                                    
                                    if "error" not in risk_analysis:
                                        # Display risk level
                                        risk_summary = risk_analysis.get("risk_summary", {})
                                        if risk_summary:
                                            risk_html = format_risk_level(
                                                risk_summary.get("risk_level", ""),
                                                risk_summary.get("total_score", 0)
                                            )
                                            st.markdown(risk_html, unsafe_allow_html=True)
                                        
                                        # Display characteristic scores
                                        characteristics = risk_analysis.get("characteristics", {})
                                        display_characteristic_scores(characteristics)
                                        
                                        # Display raw data option
                                        with st.expander("📄 Dữ Liệu JSON Chi Tiết"):
                                            st.json(risk_analysis)
                    else:
                        st.markdown(f'<div class="error-message">❌ {result.get("error", "Lỗi không xác định")}</div>', unsafe_allow_html=True)
                else:
                    st.error(f"Lỗi API: {result}")
            else:
                st.warning("Vui lòng nhập truy vấn!")
    
    elif mode == "Tìm kiếm trực tiếp":
        st.header("🎯 Tìm Kiếm Trực Tiếp")
        
        # Direct person name input
        person_name = st.text_input(
            "Nhập tên người cần phân tích:",
            placeholder="Trương Mỹ Lan",
            help="Nhập chính xác tên người cần tra cứu"
        )
        
        if st.button("📊 Phân Tích Rủi Ro", type="primary"):
            if person_name.strip():
                with st.spinner("Đang phân tích..."):
                    success, result = call_api("/analyze", {"person_name": person_name}, "POST")
                
                if success:
                    if result.get("success"):
                        st.markdown('<div class="success-message">✅ Phân tích hoàn tất!</div>', unsafe_allow_html=True)
                        
                        # Display formatted response
                        st.markdown("### 📋 Báo Cáo Phân Tích")
                        st.markdown(result.get("formatted_response", ""))
                        
                        # Display detailed analysis
                        risk_analysis = result.get("risk_analysis", {})
                        if "error" not in risk_analysis:
                            # Risk level
                            risk_summary = risk_analysis.get("risk_summary", {})
                            if risk_summary:
                                risk_html = format_risk_level(
                                    risk_summary.get("risk_level", ""),
                                    risk_summary.get("total_score", 0)
                                )
                                st.markdown(risk_html, unsafe_allow_html=True)
                            
                            # Characteristic scores
                            characteristics = risk_analysis.get("characteristics", {})
                            display_characteristic_scores(characteristics)
                            
                            # Raw data
                            with st.expander("📄 Dữ Liệu Tra Cứu Gốc"):
                                lookup_result = result.get("lookup_result", {})
                                if lookup_result:
                                    st.json(lookup_result)
                    else:
                        st.markdown(f'<div class="error-message">❌ {result.get("error", "Lỗi không xác định")}</div>', unsafe_allow_html=True)
                else:
                    st.error(f"Lỗi API: {result}")
            else:
                st.warning("Vui lòng nhập tên người!")
    
    elif mode == "API Documentation":
        st.header("📚 API Documentation")
        
        # Get API docs
        success, docs = call_api("/api-docs")
        
        if success:
            st.json(docs)
            
            st.markdown("### 🧪 Test API Endpoints")
            
            # Test health endpoint
            if st.button("Test Health Endpoint"):
                health_success, health_result = call_api("/health")
                if health_success:
                    st.success("✅ API is healthy!")
                    st.json(health_result)
                else:
                    st.error(f"❌ Health check failed: {health_result}")
            
            # Test extract name endpoint
            st.markdown("#### Test Name Extraction")
            test_query = st.text_input("Test query:", "cho tôi thông tin về Trương Mỹ Lan")
            if st.button("Test Extract Name"):
                extract_success, extract_result = call_api("/extract-name", {"query": test_query}, "POST")
                if extract_success:
                    st.success("✅ Name extraction successful!")
                    st.json(extract_result)
                else:
                    st.error(f"❌ Name extraction failed: {extract_result}")
        else:
                                st.error("Không thể tải API documentation")
     
    
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 1rem;">
            💡 <strong>VP Bank Person Risk Analysis System</strong><br>
            Powered by AWS Bedrock Claude • DynamoDB • FastAPI • Streamlit
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main() 
# VP Bank Person Risk Analysis System

Hệ thống phân tích rủi ro cá nhân thông minh sử dụng AI và DynamoDB cho VP Bank.

## 🚀 Tổng Quan

Hệ thống phân tích rủi ro cá nhân tích hợp đầy đủ với khả năng:
- **Xử lý tiếng Việt tự nhiên** sử dụng LLM (AWS Bedrock Claude)
- **API Backend** với FastAPI
- **Giao diện người dùng** với Streamlit
- **Phân tích rủi ro thông minh** dựa trên 4 đặc tính chính
- **Kết nối DynamoDB** real-time

## 🏗️ Kiến Trúc Hệ Thống

### Core Components

| Component | Description | Technology |
|-----------|-------------|------------|
| **PersonRiskAgent** | Main agent với LLM integration | Python, AWS Bedrock |
| **FastAPI Backend** | REST API endpoints | FastAPI, Uvicorn |
| **Streamlit UI** | Web interface | Streamlit |
| **PersonLookupDynamoDB** | Database layer | AWS DynamoDB |
| **RiskAnalyzer** | Scoring engine | Python |
| **BedrockModelManager** | LLM interface | AWS Bedrock Claude |

## 🧠 LLM-Powered Features

### Smart Name Extraction
- **Hybrid Approach**: Regex đầu tiên, LLM backup cho câu phức tạp
- **Claude 3 Haiku**: Xử lý các truy vấn như "Võ Tấn Hoàng Văn là ai vậy?"
- **Fallback Strategy**: Đảm bảo luôn có kết quả tốt nhất

### Supported Query Examples
```vietnamese
✅ "Võ Tấn Hoàng Văn là ai vậy, cho tôi một vài thông tin đi"
✅ "Hãy cho tôi biết về bà Trương Mỹ Lan"
✅ "Ông Nguyễn Văn A có vi phạm gì không?"
✅ "Tìm kiếm thông tin liên quan đến Lê Thị B"
✅ "Phân tích rủi ro của CEO công ty XYZ - ông Pham Van C"
```

## 📊 Risk Scoring System

### 4-Characteristic Analysis

| Characteristic | Max Points | Description |
|----------------|------------|-------------|
| **violation_type** | 6 | Loại hình vi phạm |
| **customer_role** | 3 | Vai trò trong vụ việc |
| **legal_status** | 3 | Tình trạng pháp lý |
| **source_level** | 1 | Độ tin cậy nguồn |

### Risk Levels

| Score Range | Level | Action Required |
|-------------|-------|-----------------|
| 10-15 | 🔴 Rất Cao | Từ chối giao dịch |
| 7-9 | 🟠 Cao | Thẩm định đặc biệt |
| 4-6 | 🟡 Trung Bình | Giám sát tăng cường |
| 1-3 | 🟢 Thấp | Theo dõi thường xuyên |
| 0 | ⚪ Không Rủi Ro | Giao dịch bình thường |

## 🛠️ Setup & Installation

### 1. Environment Setup
```bash
# Clone và di chuyển vào thư mục agents
cd agents/

# Install dependencies
pip install fastapi uvicorn streamlit boto3 python-dotenv requests

# Setup environment variables
cp .env.example .env
# Edit .env với AWS credentials
```

### 2. Environment Variables
```env
# AWS Configuration
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
AWS_REGION=ap-southeast-1

# Optional: Bedrock Model Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

### 3. DynamoDB Tables
Đảm bảo có các bảng DynamoDB:
- `personal_info`
- `personal2media` 
- `organization_info`
- `org2media`
- `adverse_media`

## 🚀 Quick Start

### Option 1: FastAPI + Streamlit (Recommended)

```bash
# Terminal 1: Start FastAPI Backend
cd agents/
python app.py
# API runs on http://localhost:8000

# Terminal 2: Start Streamlit UI  
cd agents/
streamlit run streamlit_app.py
# UI runs on http://localhost:8501
```

### Option 2: Direct Agent Usage

```bash
# Interactive mode
python person_risk_agent.py

# Single query
python test_agent.py
```

## 📡 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/query` | POST | Process Vietnamese query |
| `/analyze` | POST | Direct person analysis |
| `/extract-name` | POST | Name extraction (hybrid) |
| `/extract-name-llm-only` | POST | LLM-only extraction |

### Example API Usage

```bash
# Test name extraction
curl -X POST "http://localhost:8000/extract-name" \
  -H "Content-Type: application/json" \
  -d '{"query": "Võ Tấn Hoàng Văn là ai vậy?"}'

# Process full query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "cho tôi thông tin về Trương Mỹ Lan"}'
```

## 🖥️ Streamlit UI Features

### 1. Truy Vấn Tự Nhiên
- Input tiếng Việt tự nhiên
- Real-time name extraction feedback
- Comprehensive risk analysis display

### 2. Tìm Kiếm Trực Tiếp
- Direct person name input
- Detailed characteristic scoring
- Risk level visualization

### 3. Test LLM Name Extraction
- Compare regex vs LLM results
- Performance monitoring
- Method comparison

### 4. API Documentation
- Interactive endpoint testing
- Live API status monitoring
- Usage examples

## 🧪 Testing & Validation

### Test Scripts

```bash
# Test basic agent functionality
python test_agent.py

# Test person lookup only
python test_person_lookup.py

# Test LLM integration
python -c "
from person_risk_agent import PersonRiskAgent
agent = PersonRiskAgent()
result = agent.extract_person_name_with_llm('Võ Tấn Hoàng Văn là ai vậy?')
print(f'LLM Result: {result}')
"
```

### Performance Monitoring

```bash
# API health check
curl http://localhost:8000/health

# Check LLM status
curl -X POST "http://localhost:8000/extract-name-llm-only" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

## 🔧 Advanced Configuration

### LLM Model Selection

```python
# Initialize with specific model
agent = PersonRiskAgent()
agent.bedrock_manager.default_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
```

### Custom Risk Rules

```python
# Modify scoring in risk_analyzer.py
# Add new violation types, adjust weights, etc.
```

### Database Optimization

```python
# Configure DynamoDB connection pooling
# Implement caching strategies
# Add read replicas for better performance
```

## 📈 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Name Extraction** | ~200ms | Regex: 10ms, LLM: 1-3s |
| **Database Lookup** | ~500ms | Varies by data size |
| **Risk Analysis** | ~50ms | Pure computation |
| **Total Response** | ~1-4s | End-to-end |

## 🔒 Security & Compliance

### Data Protection
- AWS IAM role-based access
- Environment variable encryption
- No sensitive data logging

### Audit Trail
- All queries logged with timestamps
- Risk decisions tracked
- Compliance reporting ready

## 🤝 Development Guidelines

### Code Style
```python
# Vietnamese comments for business logic
# English for technical comments
# Comprehensive error handling
# Type hints for all functions
```

### Testing Requirements
```python
# Unit tests for each component
# Integration tests for full workflow
# Performance benchmarks
# Vietnamese language test cases
```

### Deployment Checklist
- [ ] Environment variables configured
- [ ] DynamoDB permissions set
- [ ] Bedrock access enabled
- [ ] API documentation updated
- [ ] Performance tests passed

## 📚 API Documentation

Comprehensive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Custom Docs**: http://localhost:8000/api-docs

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| LLM not working | Check AWS Bedrock permissions |
| DynamoDB timeout | Verify network/credentials |
| UI not loading | Ensure backend is running |
| Name extraction fails | Try LLM-only endpoint |

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python app.py

# Test individual components
python -m pytest tests/ -v
```

## 📞 Support

For technical support:
- Check logs: `tail -f *.log`
- API status: http://localhost:8000/health
- Test endpoints: Use Streamlit test interface

## 🎯 Roadmap

### Phase 1 (Current)
- ✅ LLM-powered name extraction
- ✅ FastAPI backend
- ✅ Streamlit UI
- ✅ Hybrid extraction strategy

### Phase 2 (Planned)
- [ ] Multi-language support
- [ ] Advanced caching
- [ ] Real-time notifications
- [ ] Mobile-responsive UI

### Phase 3 (Future)
- [ ] Machine learning risk models
- [ ] Automated decision making
- [ ] Integration with banking systems
- [ ] Advanced analytics dashboard

---

**Powered by**: AWS Bedrock • DynamoDB • FastAPI • Streamlit • Claude 3  
**Developed for**: VP Bank Hackathon 2024 
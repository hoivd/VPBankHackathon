# VP Bank Person Risk Analysis System

## 🚀 Tổng Quan

Hệ thống phân tích rủi ro cá nhân thông minh sử dụng AI và DynamoDB cho VP Bank.

- **Xử lý tiếng Việt tự nhiên** sử dụng LLM (AWS Bedrock Claude)
- **API Backend** với FastAPI
- **Giao diện người dùng** với Streamlit
- **Phân tích rủi ro thông minh** dựa trên 4 đặc tính chính
- **Kết nối DynamoDB** real-time
- **Tự động tạo blacklist từ dữ liệu báo chí (crawled news)**
- **Phân tích và gán nhãn rủi ro bằng mô hình AI**
- **So khớp theo tên người/tổ chức, truy vấn adverse media**
- **Giao diện trực quan để kiểm tra thông tin và điểm rủi ro**

---

## 🏗️ Kiến Trúc Hệ Thống

### Core Components

| Component                | Description                        | Technology                |
|--------------------------|------------------------------------|---------------------------|
| **PersonRiskAgent**      | Main agent với LLM integration     | Python, AWS Bedrock       |
| **FastAPI Backend**      | REST API endpoints                 | FastAPI, Uvicorn          |
| **Streamlit UI**         | Web interface                      | Streamlit                 |
| **PersonLookupDynamoDB** | Database layer                     | AWS DynamoDB              |
| **RiskAnalyzer**         | Scoring engine                     | Python                    |
| **BedrockModelManager**  | LLM interface                      | AWS Bedrock Claude        |

---

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

---

## 📊 Risk Scoring System

### 4-Characteristic Analysis
| Characteristic     | Max Points | Description           |
|--------------------|------------|----------------------|
| **violation_type** | 6          | Loại hình vi phạm    |
| **customer_role**  | 3          | Vai trò trong vụ việc|
| **legal_status**   | 3          | Tình trạng pháp lý   |
| **source_level**   | 1          | Độ tin cậy nguồn     |

### Risk Levels
| Score Range | Level      | Action Required         |
|-------------|------------|------------------------|
| 10-15       | 🔴 Rất Cao | Từ chối giao dịch      |
| 7-9         | 🟠 Cao     | Thẩm định đặc biệt     |
| 4-6         | 🟡 Trung Bình | Giám sát tăng cường |
| 1-3         | 🟢 Thấp    | Theo dõi thường xuyên  |
| 0           | ⚪ Không Rủi Ro | Giao dịch bình thường|

---

## 📁 Cấu trúc thư mục

```
.
├── requirements.txt             # Thư viện Python
├── config.py                   # Thiết lập chung
├── .env                        # (tuỳ chọn) biến môi trường
├── blacklist_builder/          # Tạo blacklist từ dữ liệu báo chí
│   └── blacklist_builder_app.py
│   └── builder/
├── llm_model/                  # Gọi và sử dụng mô hình LLM
├── utils/                      # Tiện ích dùng chung
├── dynamodb/                   # Tương tác với DynamoDB
├── mongodb/                    # Tương tác với MongoDB
├── agent/                      # Backend API agent để truy vấn
│   └── app.py
├── Frontend/                   # Giao diện người dùng
    ├── package.json
    └── ...
```

---

## 🛠️ Yêu cầu hệ thống
- Python >= 3.10
- pip
- Node.js + npm
- `virtualenv` (khuyên dùng)
- Tài khoản AWS (nếu dùng Bedrock hoặc DynamoDB)

---

## 🧪 Thiết lập môi trường Python
```bash
# Tạo môi trường ảo
python -m venv venv
# Kích hoạt
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
# Cài đặt thư viện
pip install -r requirements.txt
```

---

## ⚙️ Thiết lập biến môi trường (tuỳ chọn)
Tạo file `.env` hoặc export thủ công:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

---

## 🧱 Các bước chạy hệ thống
### Bước 1️⃣: Build Blacklist từ bài báo
```bash
python -m blacklist_builder.blacklist_builder_app
```
- Sử dụng các mô hình LLM để trích xuất thông tin tiêu cực
- Gán nhãn rủi ro và lưu dữ liệu vào MongoDB hoặc DynamoDB

### Bước 2️⃣: Chạy Agent Backend để truy vấn rủi ro
```bash
cd agents
python app.py
```
- Backend API xử lý truy vấn tên cá nhân/tổ chức
- So khớp thông tin với blacklist
- Trả về thông tin rủi ro liên quan

### Bước 3️⃣: Khởi chạy Frontend Web App
```bash
cd Frontend
npm install
npm run dev
```
- Giao diện đơn giản, dễ sử dụng để kiểm tra kết quả truy vấn

---

## 💡 Ví dụ sử dụng
1. Người dùng nhập tên cá nhân hoặc tổ chức vào frontend.
2. Agent backend nhận truy vấn, tìm kiếm thông tin khớp.
3. Hệ thống trả lại dữ liệu liên quan đến adverse media, cùng với risk score và gợi ý phân loại.

---

## 🧠 LLM-Powered Features (Chi tiết)
- Hybrid name extraction: Regex + LLM fallback
- Claude 3 Haiku for Vietnamese queries
- Fallback strategy for best results

---

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

---

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

---

## 📈 Performance Characteristics
| Metric | Value | Notes |
|--------|-------|-------|
| **Name Extraction** | ~200ms | Regex: 10ms, LLM: 1-3s |
| **Database Lookup** | ~500ms | Varies by data size |
| **Risk Analysis** | ~50ms | Pure computation |
| **Total Response** | ~1-4s | End-to-end |

---

## 🔒 Security & Compliance
### Data Protection
- AWS IAM role-based access
- Environment variable encryption
- No sensitive data logging
### Audit Trail
- All queries logged with timestamps
- Risk decisions tracked
- Compliance reporting ready

---

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

---

## 📚 API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Custom Docs**: http://localhost:8000/api-docs

---

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

---

## 📞 Support
For technical support:
- Check logs: `tail -f *.log`
- API status: http://localhost:8000/health
- Test endpoints: Use Streamlit test interface

---

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
# Person Risk Analysis Agent

Vietnamese-language agent for comprehensive person risk analysis using DynamoDB lookup and characteristic scoring.

## Features

🤖 **Vietnamese Language Support**: Native Vietnamese query processing and response generation  
🔍 **DynamoDB Integration**: Direct connection to AWS DynamoDB for real-time data lookup  
📊 **Risk Analysis**: Automated scoring based on 4 key characteristics  
🎯 **Comprehensive Reporting**: Detailed risk assessment with recommendations  
⚡ **Real-time Processing**: Fast query processing and analysis  

## System Components

### 1. PersonLookupDynamoDB (`person_lookup_dynamodb.py`)
- Connects to AWS DynamoDB tables
- Performs relational queries across multiple tables
- Extracts person information, personal2media, org2media, and adverse media data
- Supports fuzzy name matching and suggestions

### 2. RiskAnalyzer (`risk_analyzer.py`)
- Implements scoring rules from VP Bank requirements
- Analyzes 4 key characteristics:
  - **violation_type**: Loại hình vi phạm (0-6 points)
  - **customer_role**: Vai trò trong vụ việc (0-3 points)
  - **legal_status**: Tình trạng pháp lý (0-3 points)
  - **source_level**: Độ tin cậy của nguồn (0-1 points)
- Calculates overall risk scores and levels

### 3. PersonRiskAgent (`person_risk_agent.py`)
- Main agent interface
- Vietnamese query processing
- Combines lookup and analysis
- Generates comprehensive Vietnamese responses

## Scoring Rules

### 1️⃣ Violation Type (Loại hình vi phạm)
**Individual violations:**
- Rửa tiền, Tài trợ khủng bố: **+6 points**
- Lừa đảo, chiếm đoạt tài sản, tham nhũng, hối lộ: **+4 points**
- Vi phạm dân sự, hành chính, tranh chấp nhỏ: **+2 points**
- Không có hành vi phạm được đề cập: **0 points**

**Organization violations:**
- Đưa vào danh sách trừng phạt: **+5 points**
- Cấm vận kinh tế tài chính: **+5 points**
- Trừng phạt ngành lĩnh vực: **+4 points**

### 2️⃣ Customer Role (Vai trò trong vụ việc)
- Chủ mưu, cầm đầu, tổ chức thực hiện: **+3 points**
- Tham gia, đồng phạm, giúp sức: **+2 points**
- Bên liên quan bị động: **+1 point**
- Không có liên quan rõ ràng: **0 points**

### 3️⃣ Legal Status (Tình trạng pháp lý)
- Đã kết án: **+3 points**
- Đang trong quá trình điều tra: **+2 points**
- Tin chưa rõ ràng: **+1 point**
- Được minh oan: **0 points** (resets other scores)

### 4️⃣ Source Level (Độ tin cậy của nguồn)
- Tuổi Trẻ, Dân Trí, Thanh Niên, VNExpress, Chính phủ: **+1 point**
- Các nguồn khác: **0 points**

## Risk Level Classification

| Total Score | Risk Level | Description |
|-------------|------------|-------------|
| 10-15 | Rất Cao 🔴 | Extremely High Risk |
| 7-9 | Cao 🟠 | High Risk |
| 4-6 | Trung Bình 🟡 | Medium Risk |
| 1-3 | Thấp 🟢 | Low Risk |
| 0 | Không Có Rủi Ro ⚪ | No Risk |

## Setup and Configuration

### Prerequisites
```bash
pip install boto3 python-dotenv
```

### Environment Variables
Create a `.env` file with:
```env
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
AWS_REGION=ap-southeast-1
```

### DynamoDB Tables Required
- `personal_info`: Personal information
- `personal2media`: Person-to-media relationships
- `organization_info`: Organization information
- `org2media`: Organization-to-media relationships
- `adverse_media`: Media/news articles

## Usage Examples

### 1. Command Line Usage
```bash
# Single query
python person_risk_agent.py --query "cho tôi thông tin về Trương Mỹ Lan"

# Interactive mode
python person_risk_agent.py --interactive

# Save detailed analysis to JSON
python person_risk_agent.py --query "cho tôi thông tin về Trương Mỹ Lan" --output-json result.json
```

### 2. Python Code Usage
```python
from agents.person_risk_agent import PersonRiskAgent

# Initialize agent
agent = PersonRiskAgent()

# Process Vietnamese query
query = "cho tôi thông tin về Trương Mỹ Lan"
response = agent.process_query(query)
print(response)
```

### 3. Test Script
```bash
python agents/test_agent.py
```

## Example Input/Output

### Input:
```
"cho tôi thông tin về Trương Mỹ Lan"
```

### Output:
```
Đây là thông tin về Trương Mỹ Lan mà hệ thống tìm được:

📊 PHÂN TÍCH RỦI RO CHO: Trương Mỹ Lan
================================================================================

👤 THÔNG TIN CÁ NHÂN:
• Họ tên: Trương Mỹ Lan
• Giới tính: Female
• Chức vụ: Chủ tịch Tập đoàn Vạn Thịnh Phát
• Tổ chức: Tập đoàn Vạn Thịnh Phát

🚨 ĐÁNH GIÁ RỦI RO TỔNG THỂ:
• Mức độ rủi ro: Cao
• Điểm rủi ro cao nhất: 8/15
• Điểm rủi ro trung bình: 6.57/15
• Tổng số mục phân tích: 7
• Số mục có rủi ro cao: 1

📋 PHÂN TÍCH RỦI RO CÁ NHÂN:

1. Mục p2m_id_1752384042694560:
   • Loại vi phạm: Tham ô tài sản/Đưa hối lộ/Vi phạm quy định cho vay (Điểm: 4)
   • Vai trò: Chủ mưu/Cầm đầu (Điểm: 3)
   • Tình trạng pháp lý: Đã kết án (Điểm: 3)
   • Mức độ nguồn: Other (Điểm: 0)
   • 🎯 TỔNG ĐIỂM RỦI RO: 10/15 - Rất Cao

🏢 PHÂN TÍCH RỦI RO TỔ CHỨC:
[... detailed organization analysis ...]

💼 KHUYẾN NGHỊ:
🔴 RỦI RO RẤT CAO - Cần thực hiện các biện pháp sau:
• Từ chối giao dịch hoặc ngưng hợp tác ngay lập tức
• Báo cáo lên cấp quản lý cao nhất
• Xem xét báo cáo lên cơ quan chức năng
[... more recommendations ...]
```

## System Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Vietnamese Query  │───▶│  PersonRiskAgent     │───▶│   Risk Analysis     │
│ "thông tin về..."   │    │  - Query Processing  │    │   - Scoring         │
└─────────────────────┘    │  - Name Extraction   │    │   - Classification  │
                           └──────────┬───────────┘    │   - Recommendations │
                                      │                └─────────────────────┘
                                      ▼
                           ┌──────────────────────┐
                           │ PersonLookupDynamoDB │
                           │  - Table Queries     │
                           │  - Data Aggregation  │
                           │  - Relationship Join │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │    AWS DynamoDB      │
                           │  - personal_info     │
                           │  - personal2media    │
                           │  - org2media         │
                           │  - organization_info │
                           │  - adverse_media     │
                           └──────────────────────┘
```

## Error Handling

The agent handles various error scenarios:
- **Person not found**: Provides suggestions for similar names
- **AWS connection issues**: Clear error messages with troubleshooting
- **Invalid queries**: Helpful guidance on query format
- **Data inconsistencies**: Graceful handling with partial results

## Performance Considerations

- **Caching**: Consider implementing caching for frequently accessed data
- **Pagination**: Handles DynamoDB pagination automatically
- **Connection pooling**: Reuses DynamoDB connections efficiently
- **Error retry**: Implements exponential backoff for transient errors

## Contributing

1. Follow Vietnamese naming conventions in comments and outputs
2. Maintain scoring rule accuracy according to VP Bank requirements
3. Add comprehensive error handling
4. Include unit tests for new features
5. Update documentation for any API changes

## License

This project is proprietary to VP Bank Hackathon. 
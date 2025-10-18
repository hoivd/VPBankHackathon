# 📖 Repository Overview: VPBankHackathon

## 🎯 What is this Repository About?

This repository contains an **Intelligent Risk Analyzer for AML (Anti-Money Laundering) Case Review** system developed for VPBank Hackathon. It's a comprehensive AI-powered platform designed to help financial institutions automatically collect, analyze, and query negative information from open sources (adverse media) to build a blacklist of individuals and organizations with potential money laundering risks.

---

## 🏗️ System Purpose

The system helps financial compliance officers to:
- **Detect Risk**: Automatically identify high-risk individuals and organizations from news articles and public sources
- **Assess Threat Level**: Analyze and score risk levels using AI/LLM models based on VP Bank's specific criteria
- **Make Decisions**: Provide quick, accurate, and comprehensive risk assessments to support decision-making
- **Compliance**: Support AML (Anti-Money Laundering) compliance requirements

---

## 🔑 Core Technologies

- **AI/LLM**: Large Language Models (Claude 3.5/3.7 via AWS Bedrock, DeepSeek) for intelligent analysis
- **Vector Search**: FAISS for efficient similarity search and matching
- **Databases**: 
  - DynamoDB (AWS) for structured data storage
  - MongoDB for document storage
  - Elasticsearch for advanced querying
- **Frontend**: React + Vite web interface
- **Backend**: Python-based agents and services
- **Cloud**: AWS (S3, Bedrock, DynamoDB)

---

## 🎨 Key Features

### 1. 🔎 Blacklist Builder
- Automatically processes news articles (crawled data)
- Extracts entities (persons and organizations) from media content
- Uses LLM to analyze and assign risk labels
- Stores structured data in DynamoDB/MongoDB

### 2. 🧠 AI-Powered Risk Analysis
The system analyzes **4 key risk characteristics** according to VP Bank requirements:

#### For Individuals:
- **Violation Type (Loại hình vi phạm)**: 0-6 points
  - Money laundering, terrorism financing: +6 points
  - Fraud, embezzlement, corruption, bribery: +4 points
  - Civil/administrative violations: +2 points
  
- **Customer Role (Vai trò)**: 0-3 points
  - Mastermind/leader: +3 points
  - Accomplice/participant: +2 points
  - Passive involvement: +1 point

- **Legal Status (Tình trạng pháp lý)**: 0-3 points
  - Convicted: +3 points
  - Under investigation: +2 points
  - Unclear information: +1 point

- **Source Level (Độ tin cậy nguồn)**: 0-1 points
  - Trusted sources (Tuổi Trẻ, Dân Trí, VNExpress, etc.): +1 point

#### Risk Level Classification:
| Score | Risk Level | Action |
|-------|------------|--------|
| 10-15 | Very High 🔴 | Reject transaction immediately |
| 7-9 | High 🟠 | Enhanced due diligence required |
| 4-6 | Medium 🟡 | Standard monitoring |
| 1-3 | Low 🟢 | Normal process |
| 0 | No Risk ⚪ | Proceed |

### 3. 🤖 Backend Agent System
- Vietnamese language query processing
- Real-time DynamoDB lookups
- Intelligent name matching and suggestions
- Comprehensive risk scoring and reporting

### 4. 🌐 Web Interface
- User-friendly React-based frontend
- Query individuals or organizations by name
- Visual risk assessment display
- Detailed breakdown of risk factors

---

## 📊 Database Schema

The system uses a relational data model in DynamoDB:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  personal_info  │────▶│  personal2media  │────▶│  adverse_media  │
│  (Person data)  │     │  (Relationships) │     │  (News articles)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           ▲
┌─────────────────┐     ┌──────────────────┐              │
│organization_info│────▶│   org2media      │──────────────┘
│  (Org data)     │     │  (Relationships) │
└─────────────────┘     └──────────────────┘
```

**Core Tables:**
- `personal_info`: Individual person records with risk assessments
- `organization_info`: Organization records
- `adverse_media`: News articles and media content
- `personal2media`: Links persons to media articles (many-to-many)
- `org2media`: Links organizations to media articles (many-to-many)
- Various embedding tables for vector search capabilities

---

## 🚀 How It Works

### Workflow:

1. **Data Collection** 📥
   - News articles are crawled from various Vietnamese news sources
   - Stored in S3 bucket and processed

2. **Blacklist Building** 🔨
   ```bash
   python -m blacklist_builder.blacklist_builder_app
   ```
   - LLM extracts entities (persons, organizations) from articles
   - Analyzes risk factors using AI models
   - Stores structured data in DynamoDB

3. **Backend Agent Service** 🤖
   ```bash
   cd agents
   python app.py
   ```
   - Provides API endpoints for queries
   - Performs person/organization lookup
   - Calculates risk scores in real-time
   - Returns comprehensive analysis

4. **Frontend Interface** 💻
   ```bash
   cd Frontend
   npm install
   npm run dev
   ```
   - User enters person/organization name
   - System queries backend agent
   - Displays risk assessment results
   - Shows detailed breakdown and recommendations

---

## 🔧 System Components

### Main Directories:

- **`blacklist_builder/`**: Processes news data and builds blacklist
- **`agents/`**: Backend API agent for risk queries (Vietnamese language support)
- **`Frontend/`**: React web application
- **`dynamodb/`**: DynamoDB interaction utilities and explorers
- **`mongodb/`**: MongoDB integration
- **`elasticsearch_manager/`**: Elasticsearch integration
- **`llm_model/`**: LLM model integration (AWS Bedrock)
- **`faiss_manager/`**: FAISS vector search integration
- **`embedder/`**: Text embedding utilities
- **`matching/`**: Entity matching algorithms
- **`utils/`**: Common utilities

---

## 🎯 Use Cases

### Example Query Flow:

**User Input**: "cho tôi thông tin về Trương Mỹ Lan" (Vietnamese: "give me information about Trương Mỹ Lan")

**System Output**:
```
📊 PHÂN TÍCH RỦI RO CHO: Trương Mỹ Lan

👤 THÔNG TIN CÁ NHÂN:
• Họ tên: Trương Mỹ Lan
• Giới tính: Female
• Chức vụ: Chủ tịch Tập đoàn Vạn Thịnh Phát

🚨 ĐÁNH GIÁ RỦI RO TỔNG THỂ:
• Mức độ rủi ro: Rất Cao 🔴
• Điểm rủi ro: 10/15

📋 CHI TIẾT PHÂN TÍCH:
• Loại vi phạm: Tham ô, hối lộ (+4 điểm)
• Vai trò: Chủ mưu (+3 điểm)
• Tình trạng pháp lý: Đã kết án (+3 điểm)

💼 KHUYẾN NGHỊ:
🔴 Từ chối giao dịch ngay lập tức
🔴 Báo cáo lên cấp quản lý
🔴 Xem xét báo cáo cơ quan chức năng
```

---

## 🛠️ Technology Stack

### Backend:
- **Python 3.10+**
- **AWS Bedrock** (Claude 3.5 Haiku, Claude 3.7 Sonnet, DeepSeek)
- **boto3** (AWS SDK)
- **FAISS** (Vector similarity search)
- **MongoDB** (Document storage)
- **DynamoDB** (Structured data)
- **Elasticsearch** (Search engine)

### Frontend:
- **React** (UI framework)
- **Vite** (Build tool)
- **Node.js + npm**

### Infrastructure:
- **AWS S3** (File storage)
- **AWS DynamoDB** (Database)
- **AWS Bedrock** (LLM inference)

---

## 🌟 Key Innovations

1. **Vietnamese Language First**: Native Vietnamese processing for local compliance needs
2. **Multi-Source Intelligence**: Combines data from multiple news sources and databases
3. **AI-Powered Scoring**: Uses state-of-the-art LLMs for intelligent risk assessment
4. **Real-Time Analysis**: Fast query processing with vector search optimization
5. **Comprehensive Reporting**: Detailed risk breakdowns with actionable recommendations
6. **Scalable Architecture**: Cloud-based infrastructure ready for production use

---

## 📋 Target Users

- **AML Compliance Officers**: Monitor and assess money laundering risks
- **Risk Analysts**: Evaluate customer risk profiles
- **Bank Managers**: Make informed decisions on high-risk clients
- **Compliance Teams**: Support regulatory reporting requirements

---

## 🎓 Business Value

### For VP Bank:
- **Automation**: Reduces manual research time from hours to seconds
- **Accuracy**: AI-powered analysis ensures consistent risk assessment
- **Compliance**: Helps meet AML regulatory requirements
- **Risk Mitigation**: Early detection of high-risk customers
- **Cost Savings**: Reduces compliance team workload
- **Audit Trail**: Complete documentation of risk assessments

---

## 🔐 Security & Privacy

- AWS IAM-based access control
- Secure credential management
- Data encryption at rest and in transit
- Compliance with banking security standards

---

## 📝 Summary

This repository is a **sophisticated AML compliance platform** that leverages cutting-edge AI technology to help Vietnamese banks (specifically VP Bank) automatically detect, analyze, and assess money laundering risks from adverse media. It combines web scraping, natural language processing, vector search, and large language models to provide real-time risk intelligence in Vietnamese language, helping compliance officers make faster and more accurate decisions about customer relationships.

The system represents a modern approach to financial compliance, replacing manual research processes with automated, AI-driven intelligence gathering and risk assessment.

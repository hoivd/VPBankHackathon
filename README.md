
# 🧠 Intelligent Risk Analyzer for AML Case Review

Hệ thống hỗ trợ tự động thu thập, phân tích và truy vấn thông tin tiêu cực từ các nguồn mở (adverse media) nhằm xây dựng danh sách cá nhân/tổ chức tiềm ẩn rủi ro rửa tiền (AML). Giải pháp này ứng dụng AI/LLM, FAISS, MongoDB, DynamoDB và giao diện Web để hỗ trợ chuyên viên đánh giá và ra quyết định nhanh chóng, chính xác.

---

## 🚀 Tính năng chính

- 🔎 Tự động tạo blacklist từ dữ liệu báo chí (crawled news)
- 🧠 Phân tích và gán nhãn rủi ro bằng mô hình AI
- 🤖 Agent backend truy vấn và so khớp theo tên người/tổ chức
- 🌐 Giao diện trực quan để kiểm tra thông tin và điểm rủi ro

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

---

### Bước 2️⃣: Chạy Agent Backend để truy vấn rủi ro

```bash
cd agents
python app.py
```

- Backend API xử lý truy vấn tên cá nhân/tổ chức
- So khớp thông tin với blacklist
- Trả về thông tin rủi ro liên quan

---

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

## 📌 Lưu ý

- Đảm bảo đã tạo blacklist (bước 1) trước khi truy vấn backend/frontend.
- Nếu gọi Bedrock hoặc sử dụng DynamoDB, bạn cần thiết lập AWS credentials trước.


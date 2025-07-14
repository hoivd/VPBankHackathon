# 📦 INTELLIGENT RISK ANALYZER FOR AML CASE REVIEW
```bash
B1: Xây dựng Blacklist
B2: Xây dựng Agent Matching Blacklist
B3: Huấn luyện mô hình chấm điểm risk aml
B4: Inference

```
---

## 📁 Cấu trúc thư mục

```bash
.
├── requirements.txt
├── README.md
├── config.py
├── utils/
├── dynamodb/
├── mongodb/
├── llm_model/
├── blacklist_builder/
    ├── builder
```

---

## 🛠️ Yêu cầu hệ thống

* Python 3.13 hoặc mới hơn
* pip
* `virtualenv` (tùy chọn nhưng khuyên dùng)

---

## 🧪 Thiết lập môi trường ảo

```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

---

## 📥 Cài đặt thư viện

```bash
pip install -r requirements.txt
```


## ⚙️ Thiết lập biến môi trường (tuỳ chọn)

Tạo file `.env` hoặc xuất thủ công:

```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

---

## 🚀 Chạy tạo blacklist

```bash
python -m blacklist_builder.multiarticle_risk_processor
```

Hoặc chạy module cụ thể:

```bash
python -m llm_model.bedrock_manager
```

---


## 📌 Ghi chú

* Đảm bảo thiết lập env AWS credential trước khi gọi Bedrock/DynamoDB

---



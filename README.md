📦 Project Title

Mô tả ngắn gọn về dự án. Ví dụ:
Pipeline xử lý dữ liệu, phân tích thông tin nguy cơ từ bài báo, sử dụng Python, MongoDB, AWS Bedrock.

📁 Cấu trúc thư mục

.
├── requirements.txt
├── README.md
├── main.py
├── config.py
├── utils/
├── dynamodb/
├── mongodb/
├── llm_model/
├── blacklist_builder/

🛠️ Yêu cầu hệ thống

Python 3.10 hoặc mới hơn

pip

virtualenv (tùy chọn nhưng khuyên dùng)

AWS credentials (nếu dùng Bedrock hoặc DynamoDB)

🧪 Thiết lập môi trường ảo

# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

📥 Cài đặt thư viện

pip install -r requirements.txt

Nếu chưa có file requirements.txt, có thể tạo bằng:

pip freeze > requirements.txt

⚙️ Thiết lập biến môi trường (tuỳ chọn)

Tạo file .env hoặc xuất thủ công:

export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-southeast-1

🚀 Chạy dự án

python main.py

Hoặc chạy module cụ thể:

python -m llm_model.bedrock_manager

🧪 Test nhanh chức năng

Tạo file test:

from llm_model.bedrock_manager import BedrockModelManager

bm = BedrockModelManager()
result = bm.generate("Xin chào!")
print(result)

📌 Ghi chú

Đảm bảo thiết lập AWS credentials trước khi gọi Bedrock/DynamoDB

Nếu gặp lỗi JSON, kiểm tra encoding hoặc trường thiếu trong dữ liệu


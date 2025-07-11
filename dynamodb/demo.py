import boto3

# Kết nối DynamoDB (sử dụng credentials đã cấu hình)
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')

# Truy cập bảng
table = dynamodb.Table('blacklist')

# Dữ liệu muốn thêm (phải chứa partition key)
item = {
    'user': 'u12345',                # partition key
    'action': 'login',
    'timestamp': '2025-07-10T22:00:00Z',
    'ip_address': '192.168.1.10'
}

# Thêm dữ liệu
response = table.put_item(Item=item)

# Kiểm tra phản hồi
print("✅ Đã thêm item:", response)
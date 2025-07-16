import boto3
import io
import pandas as pd
import json

class S3DataFetcher:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, region_name="ap-southeast-1"):
        """
        Khởi tạo kết nối S3. Nếu bạn đã cấu hình qua AWS CLI, có thể bỏ qua key/secret.
        """
        self.s3 = boto3.client(
            "s3",
            region_name=region_name
        )

    def read_file(self, bucket_name: str, object_key: str, file_type: str = "csv"):
        """
        Tải nội dung file từ S3 và xử lý theo định dạng.
        
        :param bucket_name: tên bucket S3
        :param object_key: đường dẫn đầy đủ tới file (key)
        :param file_type: "csv", "json", hoặc "text"
        :return: DataFrame, dict/list, hoặc str tùy loại file
        """
        try:
            response = self.s3.get_object(Bucket=bucket_name, Key=object_key)
            content = response["Body"].read().decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"Không thể tải file từ S3: {e}")

        if file_type == "csv":
            return pd.read_csv(io.StringIO(content))
        elif file_type == "json":
            return json.loads(content)
        elif file_type == "text":
            return content
        else:
            raise ValueError("file_type phải là 'csv', 'json', hoặc 'text'.")

    def list_files(self, bucket_name: str, prefix: str = ""):
        """
        Liệt kê tất cả file trong bucket hoặc một "thư mục con" (prefix)

        :param bucket_name: tên bucket
        :param prefix: đường dẫn thư mục con, ví dụ '2025/july/'
        :return: list các key (đường dẫn file)
        """
        try:
            response = self.s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            if "Contents" not in response:
                return []
            return [obj["Key"] for obj in response["Contents"]]
        except Exception as e:
            raise RuntimeError(f"Lỗi khi liệt kê file: {e}")

if __name__ == "__main__":
    # Thông tin cấu hình
    bucket = "team253"
    key = "models/catboost_aml_model.pkl"  # ví dụ: "data/test.csv"
    file_type = "json"  # hoặc "json", "text"

    # Khởi tạo fetcher (dùng credentials đã cấu hình sẵn)
    fetcher = S3DataFetcher()

    # Đọc file
    try:
        result = fetcher.read_file(bucket_name=bucket, object_key=key, file_type=file_type)

        # In kết quả
        print("✅ File đọc thành công.")
        if file_type == "csv":
            print(result.head())
        elif file_type == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")

    # Liệt kê các file trong thư mục (tuỳ chọn test)
    try:
        files = fetcher.list_files(bucket_name=bucket, prefix="data/")
        print(f"📁 Có {len(files)} file:")
        for f in files:
            print("-", f)
    except Exception as e:
        print(f"❌ Lỗi khi liệt kê file: {e}")
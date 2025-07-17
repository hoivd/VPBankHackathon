import pandas as pd
import json
from S3.s3_connector import S3Connector
import io
import config
import os

class S3DataFetcher:
    def __init__(self, s3_client):
        """
        :param s3_client: đối tượng boto3.client đã được khởi tạo từ S3Connector
        """
        self.s3 = s3_client

    def read_file(self, bucket_name: str, object_key: str, file_type: str = "csv"):
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
        try:
            response = self.s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            if "Contents" not in response:
                return []
            return [obj["Key"] for obj in response["Contents"]]
        except Exception as e:
            raise RuntimeError(f"Lỗi khi liệt kê file: {e}")


if __name__ == "__main__":
    # Thông tin cấu hình
    bucket = "team253vpbank"
    key = "models/catboost_aml_model.pkl"  # ví dụ: "data/test.csv"
    file_type = "json"  # hoặc "json", "text"

    # Khởi tạo fetcher (dùng credentials đã cấu hình sẵn)
    fetcher = S3DataFetcher()

    # Đọc file
    try:
        result = fetcher.read_file(bucket_name=bucket, object_key=key, file_type=file_type)
        print("✅ File đọc thành công.")
        if file_type == "csv":
            print(result.head())
        elif file_type == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")

    try:
        files = fetcher.list_files(bucket_name=bucket, prefix="data/")
        print(f"📁 Có {len(files)} file:")
        for f in files:
            print("-", f)
    except Exception as e:
        print(f"❌ Lỗi khi liệt kê file: {e}")
import pandas as pd
from S3.s3_connector import S3Connector
import config
import json
import io
import os
from dotenv import load_dotenv

load_dotenv()
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
        
    def fetch_json_from_s3(self, bucket: str, key: str):
        """
        Tải và parse file JSON từ S3.
        """
        
        return self.s3.read_file(self, bucket_name=bucket, object_key=key, file_type="json")

    def fetch_csv_from_s3(self, bucket: str, key: str):
        """
        Tải file CSV từ S3 và trả về dưới dạng DataFrame.
        """
        return self.s3.read_file(bucket_name=bucket, object_key=key, file_type="csv")

    def fetch_text_from_s3(self, bucket: str, key: str):
        """
        Tải file text từ S3 và trả về dưới dạng chuỗi.
        """
        return self.s3.read_file(bucket_name=bucket, object_key=key, file_type="text")
        
    def download_file(self, bucket_name: str, object_key: str, local_path: str):
        """
        Tải một file duy nhất từ S3 về máy cục bộ.

        :param bucket_name: Tên bucket S3
        :param object_key: Key (đường dẫn) file trên S3
        :param local_path: Đường dẫn đầy đủ để lưu file về máy cục bộ
        """
        try:
            # Tạo thư mục đích nếu chưa tồn tại
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Tải file từ S3
            self.s3.download_file(Bucket=bucket_name, Key=object_key, Filename=local_path)
            print(f"✅ Đã tải file: {object_key} → {local_path}")
        except Exception as e:
            raise RuntimeError(f"Không thể tải file từ S3 về: {e}")
        
    def download_folder(self, bucket_name: str, s3_folder_prefix: str, local_dir: str):
        """
        Tải toàn bộ thư mục từ S3 về máy cục bộ.

        :param bucket_name: Tên bucket S3
        :param s3_folder_prefix: Prefix của "thư mục" trên S3 (ví dụ: 'data/2023/')
        :param local_dir: Thư mục đích trên máy cục bộ để lưu file
        """
        try:
            # Đảm bảo local_dir tồn tại
            os.makedirs(local_dir, exist_ok=True)

            # Danh sách object keys
            object_keys = self.list_files(bucket_name, prefix=s3_folder_prefix)

            if not object_keys:
                print(f"📂 Không tìm thấy file nào trong thư mục S3: {s3_folder_prefix}")
                return

            for key in object_keys:
                # Loại bỏ các object là 'folder' rỗng (kết thúc bằng '/')
                if key.endswith("/"):
                    continue

                # Tạo đường dẫn local tương ứng
                relative_path = os.path.relpath(key, s3_folder_prefix)
                local_path = os.path.join(local_dir, relative_path)

                # Tạo thư mục cha nếu chưa có
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Tải file
                self.s3.download_file(Bucket=bucket_name, Key=key, Filename=local_path)
                print(f"✅ Đã tải: {key} → {local_path}")

        except Exception as e:
            raise RuntimeError(f"Lỗi khi tải thư mục từ S3: {e}")


def main():
    bucket = "team253vpbank"
    
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

    REGION = config.AWS_REGION

    s3_client = S3Connector(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION
    ).get_client()
    fetcher = S3DataFetcher(s3_client)

    # 📌 Tải 1 file cụ thể
    try:
        key = "faiss_indexes/personal_faiss_index/metadata.json"
        local_path = "./downloads/metadata.json"
        fetcher.download_file(bucket_name=bucket, object_key=key, local_path=local_path)
        print("✅ Đã tải file thành công.")
    except Exception as e:
        print(f"❌ Lỗi khi tải file: {e}")

    # 📌 Tải toàn bộ thư mục
    try:
        folder_prefix = "faiss_indexe/"
        local_dir = "./downloads/faiss_indexe"
        fetcher.download_folder(bucket_name=bucket, s3_folder_prefix=folder_prefix, local_dir=local_dir)
        print("📁 Đã tải toàn bộ thư mục.")
    except Exception as e:
        print(f"❌ Lỗi khi tải thư mục: {e}")

    # bucket_name = "team253vpbank"
    # key = "adverse_media_data/case1.json"

if __name__ == "__main__":
    main()
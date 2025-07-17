import boto3
from botocore.exceptions import ClientError
from S3.s3_connector import S3Connector
import config
import os
from dotenv import load_dotenv

# Load từ file .env (mặc định ở thư mục hiện tại)
load_dotenv()


class S3Uploader:
    def __init__(self, s3_client):
        """
        :param s3_client: boto3.client đã khởi tạo từ S3Connector
        """
        self.s3 = s3_client

    def upload_file(self, file_path: str, bucket_name: str, object_key: str, content_type: str = None):
        """
        Upload một file từ máy local lên S3.
        
        :param file_path: đường dẫn file local
        :param bucket_name: tên bucket S3
        :param object_key: đường dẫn đích trên S3
        :param content_type: tuỳ chọn, định dạng MIME (e.g. 'text/csv', 'application/json')
        :return: True nếu thành công, False nếu lỗi
        """
        try:
            extra_args = {"ContentType": content_type} if content_type else {}
            self.s3.upload_file(Filename=file_path, Bucket=bucket_name, Key=object_key, ExtraArgs=extra_args)
            print(f"✅ Đã upload thành công: {file_path} → s3://{bucket_name}/{object_key}")
            return True
        except ClientError as e:
            print(f"❌ Upload thất bại: {e}")
            return False

    def upload_folder(self, folder_path: str, bucket_name: str, object_key_prefix: str = ""):
        """
        Upload toàn bộ thư mục (bao gồm subfolder) lên S3.

        :param folder_path: đường dẫn thư mục local
        :param bucket_name: tên bucket S3
        :param object_key_prefix: tiền tố object key (ví dụ: 'mydata/' → file sẽ lưu tại 'mydata/filename.ext')
        :return: None
        """
        folder_path = os.path.abspath(folder_path)
        for root, _, files in os.walk(folder_path):
            for file_name in files:
                local_file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(local_file_path, folder_path)
                s3_object_key = os.path.join(object_key_prefix, relative_path).replace("\\", "/")
                self.upload_file(local_file_path, bucket_name, s3_object_key)


# ====== Ví dụ sử dụng ======
if __name__ == "__main__":
    AWS_ACCESS_KEY = os.getenv("NEW_AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("NEW_AWS_SECRET_KEY")
    REGION = config.AWS_REGION
    print(f"AWS_ACCESS_KEY: {AWS_ACCESS_KEY}")
    print(f"AWS_SECRET_KEY: {AWS_SECRET_KEY}")
    print(f"REGION: {REGION}")

    # Tạo kết nối và fetcher
    connector = S3Connector(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION
    )
    uploader = S3Uploader(connector.get_client())

    # file_path ="data/test.txt"
    # bucket_name = "team253vpbank"
    # object_key = "upload_test/test.txt"

    # uploader.upload_file(file_path=file_path, bucket_name=bucket_name, object_key=object_key)

    folder_path = "faiss_indexes/2025-07-17_16-36-59"
    bucket_name = "team253vpbank"
    object_key_prefix = "faiss_indexes"

    uploader.upload_folder(folder_path=folder_path, bucket_name=bucket_name, object_key_prefix=object_key_prefix)
import boto3

class S3Connector:
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name):
        """
        Tạo kết nối với AWS S3. Nếu bạn đã cấu hình sẵn bằng AWS CLI hoặc IAM role, có thể bỏ qua key/secret.
        """
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )

    def get_client(self):
        return self.s3_client
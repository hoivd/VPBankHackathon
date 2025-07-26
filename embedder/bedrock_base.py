import boto3

class BedrockBaseClient:
    def __init__(self, access_key: str, secret_key: str, region_name: str = "us-east-1", session_token: str = None):
        if not access_key or not secret_key:
            raise ValueError("AWS access_key and secret_key are required.")

        session_params = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region_name
        }

        if session_token:
            session_params["aws_session_token"] = session_token

        self.client = boto3.client("bedrock-runtime", **session_params)

    def get_client(self):
        return self.client
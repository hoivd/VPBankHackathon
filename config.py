import logging

LOG_LEVEL = logging.DEBUG  # Mức độ log mặc định
AWS_REGION = "ap-southeast-1"  # Khu vực AWS mặc định
S3_BUCKET_NAME = "team253vpbank"  # Tên bucket S3 mặc định
PROMPT_EXTRACTOR_FILE = "prompts/prompt_extractor.txt"  # Đường dẫn tới file prompt extractor
PROMPT_COMPARE_INFO_FILE = "./prompts/promt_compare_info.txt"  # Đường dẫn tới file prompt so sánh thông tin
TABLE_CONFIG = {
        'media_config': {"adverse_media": "media_id"},
        'person_config': {"personal_info": "per_id"},
        'organization_config': {"organization_info": "org_id"},
        'p2m_config': {"personal2media": "p2m_id"},
        'o2m_config': {"org2media": "o2m_id"}
    }

# TABLE_CONFIG = {
#         'media_config': {"adverse_media_demo": "media_id"},
#         'person_config': {"personal_info_demo": "per_id"},
#         'organization_config': {"organization_info_demo": "org_id"},
#         'p2m_config': {"personal2media_demo": "p2m_id"},
#         'o2m_config': {"org2media_demo": "o2m_id"}
#     }

AWS_VIRGINA_REGION = 'us-east-1'
DEEPSEEK_MODEL_VIRGINA_ID = "arn:aws:bedrock:us-east-1:048013208071:inference-profile/us.deepseek.r1-v1:0"
CLAUDE_35_CROSS_REGION_HAIKU_MODEL_ID = 'arn:aws:bedrock:us-east-1:048013208071:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0'

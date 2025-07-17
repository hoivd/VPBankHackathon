RELATION_TABLES = """
THESE ARE RELATIONS BETWEEN TABLES IN MONGODB
RELATIONSHIP SUMMARY
============================================================

adverse_media:
   • Shares key 'media_id' with personal2media
   • Links to personal_info via personal2media
   • Links to organization_info via org2media

org2media:
   • Junction table: Links org ↔ media
   • References adverse_media
   • References organization_info
   • References personal2media

organization_info:
   • Links to adverse_media via org2media

personal2media:
   • Junction table: Links personal ↔ media
   • References adverse_media
   • References org2media
   • References personal_info

personal_info:
   • Links to adverse_media via personal2media
"""


COLLECTION_STRUCTURE = """
MONGGODB Collections Structure
============================================================

1. adverse_media
   - Status: ACTIVE
   - Items: 4
   - Size: 20,350 bytes
   - Partition Key: media_id (String)
   - Fields: content, created_at, media_id, news_sentiment_type, recency, source_credibility

2. org2media
   - Status: ACTIVE
   - Items: 63
   - Size: 23,224 bytes
   - Partition Key: o2m_id (String)
   - Fields: created_at, customer_role, entity_name, is_individual, legal_status, media_id, o2m_id, org_id, role_in_event, source_level, violation_type

3. organization_info
   - Status: ACTIVE
   - Items: 79
   - Size: 17,982 bytes
   - Partition Key: org_id (String)
   - Fields: birth_year_or_age, created_at, full_name, gender, hometown_or_residence, occupation_or_position, org_id, organization, personal_relationships

4. personal2media
   - Status: ACTIVE
   - Items: 25
   - Size: 8,636 bytes
   - Partition Key: p2m_id (String)
   - Schema Attributes: media_id (String), p2m_id (String)
   - Global Secondary Index: media_id-index (Partition Key: media_id, Projection: ALL)
   - Fields: created_at, customer_role, entity_name, is_individual, legal_status, media_id, p2m_id, per_id, role_in_event, source_level, violation_type

5. personal_info
   - Status: ACTIVE
   - Items: 35
   - Size: 8,308 bytes
   - Partition Key: per_id (String)
   - Fields: birth_year_or_age, created_at, full_name, gender, hometown_or_residence, occupation_or_position, organization, per_id, personal_relationships
"""
DYNAMODB_SCHEMA = """
MongoDB Schema Definitions 
============================================================

1. adverse_media:
{{
  "media_id": str,  # Partition Key
  "content": str,   # Full article content in Vietnamese
  "created_at": str,  # Timestamp
  "news_sentiment_type": str,  # "Positive", "Negative", "Neutral"
  "recency": str,   # "recent", "old"
  "source_credibility": str  # "High", "Medium", "Low"
}}

2. personal_info:
{{
  "per_id": str,  # Partition Key
  "birth_year_or_age": str,
  "created_at": str,
  "full_name": str,  # Vietnamese names like "Trương Mỹ Lan"
  "gender": str,  # "Male", "Female"
  "hometown_or_residence": str,  # Vietnamese locations
  "occupation_or_position": str,  # Job titles in Vietnamese
  "organization": str,  # Organization names in Vietnamese
  "personal_relationships": str  # Relationship descriptions
}}

3. organization_info:
{{
  "org_id": str,  # Partition Key
  "birth_year_or_age": str,
  "created_at": str,
  "full_name": str,  # Organization names in Vietnamese
  "gender": str,
  "hometown_or_residence": str,
  "occupation_or_position": str,
  "organization": str,
  "personal_relationships": str
}}

4. personal2media (Junction Table):
{{
  "p2m_id": str,  # Partition Key
  "per_id": str,  # Foreign Key to personal_info
  "media_id": str,  # Foreign Key to adverse_media
  "created_at": str,
  "customer_role": str,  # "Chủ mưu", "Tham gia", etc.
  "entity_name": str,  # Person name
  "is_individual": bool,  # true for persons
  "legal_status": str,  # "Đã kết án", "Đang điều tra", etc.
  "role_in_event": str,  # "Bị cáo", "Nhân chứng", etc.
  "source_level": str,  # News source level
  "violation_type": str  # "Tham ô tài sản", "Lừa đảo", etc.
}}

5. org2media (Junction Table):
{{
  "o2m_id": str,  # Partition Key
  "org_id": str,  # Foreign Key to organization_info
  "media_id": str,  # Foreign Key to adverse_media
  "created_at": str,
  "customer_role": str,  # Organization role
  "entity_name": str,  # Organization name
  "is_individual": bool,  # false for organizations
  "legal_status": str,  # Legal status in Vietnamese
  "role_in_event": str,  # Role in the event
  "source_level": str,  # News source level
  "violation_type": str  # Type of violation
}}

Global Secondary Indexes:
- personal2media: media_id-index (Partition Key: media_id, Projection: ALL)
"""

SAMPLE_DOCUMENTS = """
Sample DynamoDB Documents 
============================================================

1. adverse_media Sample:
{{
  "media_id": "media_id_1752384078640333",
  "content": "Phó chủ nhiệm Ủy ban Pháp luật và Tư pháp của Quốc hội Nguyễn Phương Thủy giải đáp câu hỏi bà Trương Mỹ Lan có được chuyển từ án tử hình xuống chung thân. Trưa 27-6, tổng thư ký Quốc hội tổ chức họp báo công bố kết quả kỳ họp thứ 9, Quốc hội khóa XV...",
  "created_at": "1752384078640333",
  "news_sentiment_type": "Negative",
  "recency": "recent",
  "source_credibility": "High"
}}

2. personal_info Sample:
{{
  "per_id": "per_id_1752384018355865",
  "birth_year_or_age": null,
  "created_at": "1752384018355853",
  "full_name": "Võ Tấn Hoàng Văn",
  "gender": "Male",
  "hometown_or_residence": null,
  "occupation_or_position": null,
  "organization": "Ngân hàng SCB",
  "personal_relationships": "Bị cáo, thực hiện rút tiền SCB theo chỉ đạo của Trương Mỹ Lan"
}}

3. organization_info Sample:
{{
  "org_id": "org_id_1752383993651339",
  "birth_year_or_age": null,
  "created_at": "1752383993651329",
  "full_name": "Tập đoàn Vạn Thịnh Phát",
  "gender": null,
  "hometown_or_residence": null,
  "occupation_or_position": "Tập đoàn kinh doanh",
  "organization": null,
  "personal_relationships": "Có Trương Mỹ Lan là Chủ tịch"
}}

4. personal2media Sample:
{{
  "p2m_id": "p2m_id_1752383993651713",
  "per_id": "per_id_1752383993651203",
  "media_id": "media_id_1752383993651068",
  "created_at": "1752383993651710",
  "customer_role": "Bên liên quan bị động",
  "entity_name": "Trương Mỹ Lan",
  "is_individual": true,
  "legal_status": "Tin chưa rõ ràng",
  "role_in_event": "Nhà tài trợ, doanh nhân",
  "source_level": "Other",
  "violation_type": "Không có hành vi phạm được đề cập"
}}

5. org2media Sample:
{{
  "o2m_id": "o2m_id_1752383993652057",
  "org_id": "org_id_1752383993651331",
  "media_id": "media_id_1752383993651068",
  "created_at": "1752383993652054",
  "customer_role": "Không có liên quan rõ ràng trong bài báo",
  "entity_name": "Ban Dân tộc TP Hồ Chí Minh",
  "is_individual": false,
  "legal_status": "Tin chưa rõ ràng",
  "role_in_event": "Cơ quan quản lý",
  "source_level": "Other",
  "violation_type": "Không có hành vi phạm được đề cập"
}}
"""

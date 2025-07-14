RELATION_TABLES ="""
THESE IS REALTIONS BETWEEN TABLES IN DYNAMODB
🔗 RELATIONSHIP SUMMARY
============================================================

📋 adverse_media:
   • 🔗 Shares key 'media_id' with adverse_media_demo
   • 🔗 Shares key 'media_id' with personal2media
   • 🔗 Links to personal_info via personal2media
   • 🔗 Links to organization_info via org2media

📋 adverse_media_demo:
   • 🔗 Shares key 'media_id' with adverse_media
   • 🔗 Shares key 'media_id' with personal2media

📋 org2media:
   • 🔗 Junction table: Links org ↔ media
   • 🔗 References adverse_media
   • 🔗 References adverse_media_demo
   • 🔗 References org2media_demo
   • 🔗 References org2media_demo
   • 🔗 References organization_info
   • 🔗 References organization_info_demo
   • 🔗 References personal2media
   • 🔗 References personal2media_demo
   • 🔗 Shares key 'o2m_id' with org2media_demo

📋 org2media_demo:
   • 🔗 Junction table: Links org ↔ media_demo
   • 🔗 References adverse_media_demo
   • 🔗 References org2media
   • 🔗 References organization_info
   • 🔗 References organization_info_demo
   • 🔗 References personal2media_demo
   • 🔗 Shares key 'o2m_id' with org2media

📋 organization_info:
   • 🔗 Shares key 'org_id' with organization_info_demo
   • 🔗 Links to adverse_media via org2media

📋 organization_info_demo:
   • 🔗 Shares key 'org_id' with organization_info

📋 personal2media:
   • 🔗 Junction table: Links personal ↔ media
   • 🔗 References adverse_media
   • 🔗 References adverse_media_demo
   • 🔗 References org2media
   • 🔗 References org2media_demo
   • 🔗 References personal2media_demo
   • 🔗 References personal2media_demo
   • 🔗 References personal_info
   • 🔗 References personal_info_demo
   • 🔗 Shares key 'p2m_id' with personal2media_demo

📋 personal2media_demo:
   • 🔗 Junction table: Links personal ↔ media_demo
   • 🔗 References adverse_media_demo
   • 🔗 References org2media_demo
   • 🔗 References personal2media
   • 🔗 References personal_info
   • 🔗 References personal_info_demo
   • 🔗 Shares key 'p2m_id' with personal2media

📋 personal_info:
   • 🔗 Shares key 'per_id' with personal_info_demo
   • 🔗 Links to adverse_media via personal2media

📋 personal_info_demo:
   • 🔗 Shares key 'per_id' with personal_info

"""
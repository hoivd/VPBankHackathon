# Person Lookup Script

This script connects to MongoDB and performs relational queries to find information about a person based on their full name.

## 🎯 **What it does:**

Given a person's full name, the script returns:

1. **Personal2Media Info**: 
   - `legal_status`
   - `role_in_event` 
   - `source_level`
   - `violation_type`
   - `media_id`
   - `customer_role`

2. **Org2Media Info** (organizations the person is associated with):
   - `legal_status`
   - `media_id`
   - `o2m_id`
   - `org_id`
   - `role_in_event`
   - `source_level`
   - `violation_type`
   - `organization_name`
   - `organization_type`

3. **Media Details** for all related articles
4. **Person Info** from personal_info collection

## 📋 **Requirements:**

```bash
pip install pymongo python-dotenv
```

## 🔧 **Setup:**

1. Set your MongoDB URI in environment variable:
```bash
export MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/"
```

Or create a `.env` file:
```
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

## 🚀 **Usage:**

### **1. Command Line Usage:**

```bash
# Basic lookup
python person_lookup.py --name "Trương Mỹ Lan"

# Save result to JSON file
python person_lookup.py --name "Trương Mỹ Lan" --output-json result.json

# Specify different MongoDB database
python person_lookup.py --name "Trương Mỹ Lan" --mongo-db "my_database"
```

### **2. Interactive Mode:**

```bash
python test_person_lookup.py --mode interactive
```

### **3. Quick Lookup:**

```bash
python test_person_lookup.py --mode quick --name "Trương Mỹ Lan"
```

### **4. Test Mode:**

```bash
python test_person_lookup.py --mode test
```

## 📊 **Sample Output:**

```
🔍 Looking up information for: Trương Mỹ Lan
✅ Found person: Trương Mỹ Lan (ID: per_id_1752383993651203)
📋 Found 2 personal2media entries
🏢 Found 1 org2media entries

================================================================================
👤 PERSON INFORMATION
================================================================================
Per Id: per_id_1752383993651203
Full Name: Trương Mỹ Lan
Gender: Female
Organization: Tập đoàn Vạn Thịnh Phát
Personal Relationships: Chủ tịch Tập đoàn Vạn Thịnh Phát

================================================================================
📋 PERSONAL2MEDIA INFORMATION
================================================================================

1. Entry ID: p2m_id_1752383993651713
   Legal Status: Tin chưa rõ ràng
   Role in Event: Nhà tài trợ, doanh nhân
   Source Level: Other
   Violation Type: Không có hành vi phạm được đề cập
   Media ID: media_id_1752383993651068
   Customer Role: Bên liên quan bị động

================================================================================
🏢 ORG2MEDIA INFORMATION
================================================================================

1. Entry ID: o2m_id_1752383993652057
   Organization: Tập đoàn Vạn Thịnh Phát (Tập đoàn kinh doanh)
   Legal Status: Tin chưa rõ ràng
   Role in Event: Cơ quan quản lý
   Source Level: Other
   Violation Type: Không có hành vi phạm được đề cập
   Media ID: media_id_1752383993651068
   Org ID: org_id_1752383993651339

================================================================================
📰 MEDIA DETAILS
================================================================================

Media ID: media_id_1752383993651068
   Sentiment: Negative
   Recency: recent
   Credibility: High
   Content Preview: Phó chủ nhiệm Ủy ban Pháp luật và Tư pháp của Quốc hội...

================================================================================
📊 SUMMARY
================================================================================
Total Personal2Media Entries: 2
Total Org2Media Entries: 1
Total Media Articles: 1
Unique Media IDs: media_id_1752383993651068
```

## 🔍 **How it works:**

1. **Person Search**: Searches `personal_info` collection for exact, case-insensitive, or partial name matches
2. **Personal2Media Query**: Uses `per_id` to find all entries in `personal2media` collection
3. **Org2Media Query**: Searches `organization_info` for organizations mentioning the person, then finds related `org2media` entries
4. **Media Details**: Retrieves full media information for all related `media_id`s
5. **Comprehensive Result**: Combines all information with media details and summary statistics

## 🎯 **Key Features:**

- **Smart Name Matching**: Exact, case-insensitive, and partial matching
- **Relational Queries**: Automatically follows relationships between collections
- **Vietnamese Support**: Full UTF-8 support for Vietnamese names and content
- **Error Handling**: Graceful handling of missing data and connection issues
- **Suggestions**: Provides similar names when exact match not found
- **JSON Export**: Save results to JSON files for further processing
- **Interactive Mode**: User-friendly interactive interface

## 🛠️ **API Usage:**

```python
from person_lookup import PersonLookup

# Initialize
lookup = PersonLookup(mongo_uri="your_mongo_uri")

# Perform lookup
result = lookup.lookup_person_comprehensive("Trương Mỹ Lan")

# Access specific data
personal2media_info = result["personal2media_info"]
org2media_info = result["org2media_info"]
media_details = result["media_details"]

# Close connection
lookup.close()
```

## 📝 **Sample Names to Test:**

Based on your database schema, try these names:
- `Trương Mỹ Lan` (main person from Vạn Thịnh Phát case)
- `Võ Tấn Hoàng Văn` (person from sample data)
- `Nguyễn Phương Thủy` (mentioned in content)

## 🔧 **Troubleshooting:**

1. **Connection Issues**: Ensure MongoDB URI is correct and accessible
2. **No Results**: Check if person exists in `personal_info` collection
3. **Encoding Issues**: Ensure terminal supports UTF-8 for Vietnamese characters
4. **Permission Issues**: Verify MongoDB user has read permissions

## 📚 **Files:**

- `person_lookup.py` - Main lookup script
- `test_person_lookup.py` - Test and interactive scripts
- `PERSON_LOOKUP_README.md` - This documentation 
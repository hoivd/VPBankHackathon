from pymongo import MongoClient
from utils import Utils

# Thay URI bằng URI kết nối MongoDB Atlas của bạn
mongo_uri = Utils.load_api_key_from_env("MONGO_URI")

# Tên database và các collections cần xoá
db_name = "blacklist"
collections_to_clear = ["adverse_media", "customer2media", "customer_info"]

# Kết nối tới MongoDB
client = MongoClient(mongo_uri)
db = client[db_name]

# Xoá tất cả documents trong từng collection
for collection_name in collections_to_clear:
    result = db[collection_name].delete_many({})
    print(f"Đã xoá {result.deleted_count} documents từ collection: {collection_name}")
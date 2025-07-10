from pymongo import MongoClient
from bson import ObjectId
import time
import copy
from utils import Utils
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class MongoPusher:
    def __init__(self, mongo_uri: str, db_name: str):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]

    def insert(self, collection_name: str, data, add_unix_id: bool = False):
        """
        Hàm chính để insert 1 dict hoặc list[dict]
        """
        if isinstance(data, list):
            self.insert_many_dicts(collection_name, data, add_unix_id=add_unix_id)
        elif isinstance(data, dict):
            self.insert_one_dict(collection_name, data, add_unix_id=add_unix_id)
        else:
            raise TypeError("Data phải là dict hoặc list[dict]")

    def insert_one_dict(self, collection_name: str, data_dict: dict, add_unix_id: bool = False):
        """
        Chèn một document vào MongoDB
        """
        collection = self.db[collection_name]
        to_insert = copy.deepcopy(data_dict)

        if "_id" not in to_insert:
            to_insert["_id"] = ObjectId()

        if add_unix_id:
            to_insert["_unix_id"] = int(time.time() * 1000)

        collection.insert_one(to_insert)

    def insert_many_dicts(self, collection_name: str, data_list: list[dict], add_unix_id: bool = False):
        """
        Chèn nhiều documents vào MongoDB
        """
        collection = self.db[collection_name]
        for item in data_list:
            to_insert = copy.deepcopy(item)
            if add_unix_id:
                to_insert["_unix_id"] = int(time.time() * 1000)
            collection.insert_one(to_insert)

    def close(self):
        self.client.close()


if __name__ == "__main__":
    json =  [{
        "personal_id": "P007",
        "full_name": "Đỗ Phước Trung",
        "birth_year_or_age": "null",
        "gender": "Male",
        "occupation_or_position": "Đại diện Viện Kiểm sát",
        "organization": "Viện Kiểm sát nhân dân cấp cao tại TP.HCM",
        "hometown_or_residence": "null",
        "personal_relationships": "null"
    },
    {
        "personal_id": "P007",
        "full_name": "Đỗ Phước Trung",
        "birth_year_or_age": "null",
        "gender": "Male",
        "occupation_or_position": "Đại diện Viện Kiểm sát",
        "organization": "Viện Kiểm sát nhân dân cấp cao tại TP.HCM",
        "hometown_or_residence": "null",
        "personal_relationships": "null"
    }
    ]

    mongo_uri = Utils.load_api_key_from_env("MONGO_URI")
    db_name = "demo"
    collection_name = "test"

    pusher = MongoPusher(mongo_uri=mongo_uri, db_name=db_name)
    pusher.insert_many_dicts(collection_name, json)
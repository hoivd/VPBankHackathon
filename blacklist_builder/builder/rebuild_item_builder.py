from utils import Utils
import copy
import json
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)
class RebuildItemBuilder:
    @staticmethod
    def create_rebuild_organization_items(organization_duplicated: list, partition_key: str):
        """
        Tái tạo lại tổ chức nhưng giữ nguyên org_id cũ để chèn đè vào DynamoDB.
        
        :param organization_duplicated: List tổ chức đã có, mỗi item chứa org_id cũ
        :param partition_key: Partition key chính (vd: 'org_id')
        :return: Danh sách tổ chức đã rebuild
        """
        rebuilt_items = []
        current_time = Utils.get_current_unix_time()
        
        org_ids = []
        org_id_gen_to_org_id = {}
        for item in organization_duplicated:
            item_copy = copy.deepcopy(item)

            # Đảm bảo có org_id (partition key)
            logger.debug(f"Tien hanh kiem tra partition_key")
            if partition_key not in item_copy or not item_copy[partition_key]:
                logger.error(f"Thiếu {partition_key} trong item, không thể tái tạo.")
                continue

            # Ghi đè/thiết lập lại created_at
            item_copy["created_at"] = current_time

            # (Tùy chọn) xóa organizer_id nếu không dùng nữa
            if "organizer_id" in item_copy:
                org_id_gen_to_org_id[item_copy["organizer_id"]] = item_copy[partition_key]
                item_copy.pop("organizer_id", None)

            org_ids.append(item_copy[partition_key])
            rebuilt_items.append(item_copy)

        return rebuilt_items, org_id_gen_to_org_id, org_ids
    
    @staticmethod
    def create_rebuild_personal_items(personal_duplicated: list, partition_key: str):
        """
        Tái tạo lại danh sách cá nhân nhưng giữ nguyên per_id cũ để chèn đè vào DynamoDB.

        :param personal_duplicated: List cá nhân đã có, mỗi item chứa per_id cũ
        :param partition_key: Partition key chính (vd: 'per_id')
        :return: Tuple (danh sách cá nhân đã rebuild, mapping từ personal_id → per_id)
        """
        rebuilt_items = []
        current_time = Utils.get_current_unix_time()

        per_id_gen_to_per_id = {}
        per_ids = []

        for item in personal_duplicated:
            item_copy = copy.deepcopy(item)

            logger.debug(f"Tien hanh kiem tra partition_key")
            # Đảm bảo có per_id (partition key)
            if partition_key not in item_copy or not item_copy[partition_key]:
                logger.error(f"Thiếu {partition_key} trong item, không thể tái tạo.")
                continue

            # Ghi lại thời gian tái tạo
            item_copy["created_at"] = current_time

            # Nếu có personal_id, giữ lại để map và xóa đi
            if "personal_id" in item_copy:
                per_id_gen_to_per_id[item_copy["personal_id"]] = item_copy[partition_key]
                item_copy.pop("personal_id", None)

            per_ids.append(item_copy[partition_key])
            rebuilt_items.append(item_copy)

        return rebuilt_items, per_id_gen_to_per_id, per_ids
    

    
if __name__ == "__main__":
    # Dữ liệu tổ chức cần rebuild
    organization_duplicated = Utils.load_json('prepare_data/org_duplicated.json')
    print(Utils.json_to_str(organization_duplicated))
    # Khởi tạo builder
    builder = RebuildItemBuilder

    # Gọi hàm rebuild
    org_rebuilt_items, org_id_gen_to_org_id, org_ids = builder.create_rebuild_organization_items(organization_duplicated, partition_key="org_id")

    # In kết quả ra console
    print("✅ Rebuilt Organization Items:")
    print(json.dumps(org_rebuilt_items, indent=2, ensure_ascii=False))
    print(Utils.json_to_str(org_id_gen_to_org_id))

    personal_duplicated = Utils.load_json('prepare_data/personal_duplicated.json')
    print(Utils.json_to_str(personal_duplicated))
    # Khởi tạo builder

    # Gọi hàm rebuild
    per_rebuilt_items, per_id_gen_to_per_id, per_ids = builder.create_rebuild_personal_items(personal_duplicated, partition_key="per_id")

    # In kết quả ra console
    print("✅ Rebuilt Personal Items:")
    print(json.dumps(per_rebuilt_items, indent=2, ensure_ascii=False))
    print(Utils.json_to_str(per_id_gen_to_per_id))


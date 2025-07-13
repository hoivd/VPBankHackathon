import copy
from utils import Utils

class NewItemBuilder:
    @staticmethod
    def create_adverse_media_item(risk_info: dict, partition_key: str, context: str): 
        risk_info_copy = copy.deepcopy(risk_info)

        unix_time = Utils.get_current_unix_time()
        item = {k: v for k, v in risk_info_copy.items() if k not in ["list_personal_risks", "list_organizer_risks"]}  
        item[partition_key] = partition_key + "_" + str(unix_time)
        item['content'] = context
        item["created_at"] = unix_time

        return item, item[partition_key]
    
    @staticmethod
    def create_personal2media_items(risk_info: dict, partition_key: str, per_id_gen_to_per_id: dict, media_id: str):
        risk_info_copy = copy.deepcopy(risk_info)

        personal2media = risk_info_copy.get("list_personal_risks", [])
        personal2media_copy = copy.deepcopy(personal2media)

        batch_unix_time = Utils.get_current_unix_time()
        final_personal2media_items = []

        for item in personal2media_copy:
            item[partition_key] = partition_key + "_" + str(Utils.get_current_unix_time())
            item["media_id"] = media_id
            item["created_at"] = batch_unix_time
            item["per_id"] = per_id_gen_to_per_id.get(item["entity_id"], None)
            if item['per_id']:
                final_personal2media_items.append(item)
            item.pop("entity_id", None)

        return final_personal2media_items
    
    @staticmethod
    def create_org2media_items(risk_info: dict, partition_key: str, org_id_gen_to_org_id: dict, media_id: str):
        """
        Tạo danh sách org2media từ risk_info, giữ thông tin mapping org_id.
        
        :param risk_info: dict chứa list_organizer_risks
        :param partition_key: tên khóa partition cho org2media (vd: 'o2m_id')
        :param org_id_gen_to_org_id: mapping từ entity_id → org_id (giữ nguyên)
        :param media_id: media_id của bài báo gốc
        :return: danh sách org2media item đã chuẩn hóa
        """
        risk_info_copy = copy.deepcopy(risk_info)
        org2media = risk_info_copy.get("list_organizer_risks", [])
        org2media_copy = copy.deepcopy(org2media)

        batch_unix_time = Utils.get_current_unix_time()
        final_org2media_items = []

        for item in org2media_copy:
            item[partition_key] = partition_key + "_" + str(Utils.get_current_unix_time())
            item["media_id"] = media_id
            item["created_at"] = batch_unix_time
            item["org_id"] = org_id_gen_to_org_id.get(item["entity_id"], None)

            if item["org_id"]:  # Chỉ thêm nếu có mapping đúng
                final_org2media_items.append(item)

            item.pop("entity_id", None)

        return final_org2media_items
    

if __name__ == "__main__":
    builder = NewItemBuilder()

    risk_info = Utils.load_json('prepare_data/risk_info.json')
    print(Utils.json_to_str(risk_info))
    adverse_media_item, media_id = builder.create_adverse_media_item(risk_info=risk_info, partition_key='media_id', context='test')
    print(Utils.json_to_str(adverse_media_item))
    print(media_id)

    per_id_gen_to_per_id = Utils.load_json('prepare_data/per_id_gen_to_per_id.json')
    print(Utils.json_to_str(per_id_gen_to_per_id))

    personal2media_items = builder.create_personal2media_items(risk_info=risk_info, partition_key='p2m_id', per_id_gen_to_per_id=per_id_gen_to_per_id, media_id=media_id)

    print(Utils.json_to_str(personal2media_items))


    org_id_gen_to_org_id = Utils.load_json('prepare_data/org_id_gen_to_org_id.json')
    print(Utils.json_to_str(org_id_gen_to_org_id))

    org2media_items = builder.create_org2media_items(risk_info=risk_info, partition_key='o2m_id', org_id_gen_to_org_id=org_id_gen_to_org_id, media_id=media_id)

    print(Utils.json_to_str(org2media_items))


import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np
from logger import _setup_logger
import config
import os
import time
from pathlib import Path



logger = _setup_logger(__name__, config.LOG_LEVEL)

class ModelEmbedder:
    def __init__(self, model_name="vinai/phobert-base", device=None):
        self.tokenizer = AutoTokenizer.from_pretrained(Path(model_name))
        self.model = AutoModel.from_pretrained(Path(model_name), use_safetensors=True)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"KHOI TAO MO HINH EMBEDDER THANH CONG {model_name}. SU DUNG DEVICE {self.device}")

    def mean_pooling(self, model_output, attention_mask):
        # Lấy embedding ra, tính trung bình theo attention_mask
        token_embeddings = model_output[0]  # (batch_size, seq_len, hidden_size)
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, dim=1) / \
               torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)

    def encode(self, texts, return_numpy=True):
        if isinstance(texts, str):
            texts = [texts]

        encoded_input = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors='pt'
        ).to(self.device)
        
        start = time.time()
        with torch.no_grad():
            model_output = self.model(**encoded_input)
        end = time.time()

        logger.info(f"Thoi gian embedd {end - start:.2f} giay")
        embeddings = self.mean_pooling(model_output, encoded_input['attention_mask'])
        logger.info(f"Encode THANH CONG")

        if return_numpy:
            return embeddings.cpu().numpy()
        return embeddings
    
    def save_model_local(self, save_dir="./phobert_local"):
        os.makedirs(save_dir, exist_ok=True)
        self.tokenizer.save_pretrained(save_dir)
        self.model.save_pretrained(save_dir)
        logger.info(f"Model and tokenizer saved to {save_dir}")
    
if __name__ == "__main__":
    embedder = ModelEmbedder(model_name="./embedder/models/phobert_base_v2_local")

    texts = [
        '''
        Bắt nhóm nghi can trộm cắp tài sản tại Đồng Nai
        Ngày 4/2, Công an tỉnh Đồng Nai cho biết, Công an huyện Long Thành đã bắt giữ nhóm đối tượng đột nhập văn phòng, trộm cắp tài sản của một công ty, với trị giá hơn 430 triệu đồng trong ngày mồng 2 Tết.
        Thứ Ba, ngày 04/02/2025 - 17:42
        Lực lượng Công an huyện Long Thành thu giữ 13 máy hàn tại phòng trọ của Tân.
        Trước đó, theo thông tin người dân trình báo, rạng sáng 30/1 (mồng 2 Tết), tại Phòng giao dịch của Công ty trách nhiệm hữu hạn AUTOWEL VINA, xã Long An, huyện Long Thành, chuyên kinh doanh mua bán thiết bị hàn công nghiệp bị mất trộm nhiều tài sản có giá trị lớn.
        Thời điểm này, lợi dụng công ty không có bảo vệ trông coi, một nam thanh niên bịt mặt, trùm đầu, mặc áo khoác đã đột nhập vào văn phòng cạy két sắt lấy trộm tài sản nhưng không thành. Sau đó, đối tượng này đã lấy trộm 13 máy hàn và 1 cuộn dây điện, với trị giá hơn 430 triệu đồng.
        Sau khi tiếp nhận thông tin, bằng nhiều biện pháp nghiệp vụ, đến chiều 2/2, lực lượng Công an huyện Long Thành xác định được đối tượng gây ra vụ trộm là Đinh Quang Tân (27 tuổi, ngụ tỉnh Bà Rịa-Vũng Tàu) nên tiến hành truy bắt tại xã Bàu Cạn.
        Hơn 120 chiếc đồng hồ đeo tay là tài sản mà các đối tượng thực hiện trong một vụ trộm cắp khác được phát hiện tại phòng trọ của Tân.
        Ngoài bắt giữ Tân để điều tra về tội trộm cắp tài sản, Công an huyện Long Thành còn bắt giữ nghi can Hoàng Quốc Việt (41 tuổi, quê tỉnh Quảng Nam) và Phạm Văn Ngọc (27 tuổi, ngụ tỉnh Bà Rịa-Vũng Tàu) để điều tra về hành vi che giấu hành vi phạm tội. Trong đó, Việt được xác định là đối tượng ở cùng dãy trọ đã báo cho Tân biết để tìm cách bỏ trốn; còn Ngọc là người chở Tân đi trốn.
        Khám xét phòng trọ của Việt, Công an huyện Long Thành thu giữ giữ 13 máy hàn. Ngoài ra, phát hiện hơn 120 đồng hồ đeo tay các loại, máy tính cùng nhiều tài sản khác. Số tài sản này được các đối tượng lấy trộm trong một vụ đột nhập trộm cắp tài sản khác tại địa bàn huyện Nhơn Trạch vào giữa tháng 1/2025.
        Hiện, vụ việc đang được Công an huyện Long Thành mở rộng điều tra.
        THIÊN VƯƠNG
        ''',
        "Trí tuệ nhân tạo đang phát triển nhanh chóng."
    ]

    embeddings = embedder.encode(texts)

    logger.info(f"Shape: {embeddings.shape}")         # (2, 768)
    logger.info(f"Embedding 1: {embeddings[0][:10]}") # In 10 giá trị đầu tiên

    # Lưu model local
    embedder.save_model_local("./embedder/models/phobert_base_v2_local")



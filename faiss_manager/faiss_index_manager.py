import faiss
import numpy as np
import json
import os
from logger import _setup_logger
import config

logger = _setup_logger(__name__, config.LOG_LEVEL)

class FaissIndexManager:
    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))
        self.embedding_map = {}   # ID → vector
        self.next_id = 100000     # ID tự động tăng

    def add(self, vectors: np.ndarray) -> list[int]:
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        elif vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(f"Dữ liệu đầu vào phải có shape (n, {self.dim})")

        vectors = vectors.astype('float32')
        n = vectors.shape[0]
        ids = np.arange(self.next_id, self.next_id + n, dtype=np.int64)
        self.next_id += n

        self.index.add_with_ids(vectors, ids)
        for i in range(n):
            self.embedding_map[int(ids[i])] = vectors[i]
        return ids.tolist()

    def search(self, query_vector: np.ndarray, top_k=3):
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        query_vector = query_vector.astype('float32')
        D, I = self.index.search(query_vector, top_k)
        return [(int(id_), float(dist)) for id_, dist in zip(I[0], D[0])]

    def remove_by_ids(self, ids_to_remove: list[int]):
        if not ids_to_remove:
            return  # Không làm gì nếu danh sách rỗng

        id_array = np.array(ids_to_remove, dtype='int64')  # FAISS yêu cầu int64
        self.index.remove_ids(faiss.IDSelectorBatch(id_array))

        for id_ in ids_to_remove:
            self.embedding_map.pop(id_, None)

        logger.info(f"Đã xóa {len(ids_to_remove)} vector khỏi FAISS index và embedding map.")

    def reset(self):
        self.index.reset()
        self.embedding_map.clear()
        self.next_id = 100000

    def get_embedding_by_id(self, id_: int):
        return self.embedding_map.get(id_)

    def get_total(self):
        return self.index.ntotal

    def save_index(self, directory: str):
        """
        Lưu FAISS index và metadata vào thư mục chỉ định.
        - index.faiss: FAISS index
        - index.meta.json: metadata (next_id, ntotal, dim)
        """
        os.makedirs(directory, exist_ok=True)

        index_path = os.path.join(directory, "index.faiss")
        metadata_path = os.path.join(directory, "metadata.json")

        faiss.write_index(self.index, index_path)

        metadata = {
            "next_id": self.next_id,
            "ntotal": self.index.ntotal,
            "dim": self.dim,
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

    @classmethod
    def load_index(cls, directory: str):
        """
        Tải FAISS index và metadata từ thư mục.
        """
        index_path = os.path.join(directory, "index.faiss")
        metadata_path = os.path.join(directory, "metadata.json")

        # Đọc index trực tiếp, không cần bọc lại bằng IndexIDMap nếu đã lưu từ đó
        index = faiss.read_index(index_path)

        dim = index.d
        manager = cls(dim=dim)
        manager.index = index  # dùng trực tiếp, không wrapped

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                meta = json.load(f)
                manager.next_id = meta.get("next_id", 100000)

        return manager


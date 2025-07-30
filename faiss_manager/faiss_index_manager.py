import faiss
import numpy as np
import json
import os
# from logging import _setup_logging
import config
import logging
# logging = _setup_logging(__name__, config.LOG_LEVEL)
import logging
class FaissIndexManager:
    def __init__(self, dim: int, metric_type: str = 'ip'):
        """
        metric_type: 'ip' (inner product) hoặc 'l2' (euclidean distance)
        """
        self.dim = dim
        self.metric_type = metric_type.lower()
        self.index = self._create_index()
        self.embedding_map = {}
        self.next_id = 100000

    def _create_index(self):
        if self.metric_type == 'ip':
            return faiss.IndexIDMap(faiss.IndexFlatIP(self.dim))
        elif self.metric_type == 'l2':
            return faiss.IndexIDMap(faiss.IndexFlatL2(self.dim))
        else:
            raise ValueError("metric_type phải là 'ip' hoặc 'l2'")

    def _normalize(self, vecs: np.ndarray) -> np.ndarray:
        """
        Chỉ normalize nếu dùng Inner Product để mô phỏng cosine similarity.
        """
        if self.metric_type == 'ip':
            return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs

    def add(self, vectors) -> list[int]:
        if isinstance(vectors, list):
            vectors = np.array(vectors)

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        elif vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(f"Dữ liệu đầu vào phải có shape (n, {self.dim})")

        vectors = vectors.astype('float32')
        vectors = self._normalize(vectors)

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
        query_vector = self._normalize(query_vector)

        D, I = self.index.search(query_vector, top_k)
        return [(int(id_), float(dist)) for id_, dist in zip(I[0], D[0])]

    def remove_by_ids(self, ids_to_remove: list[int]):
        if not ids_to_remove:
            return

        id_array = np.array(ids_to_remove, dtype='int64')
        self.index.remove_ids(faiss.IDSelectorBatch(id_array))

        for id_ in ids_to_remove:
            self.embedding_map.pop(id_, None)

        logging.info(f"Đã xóa {len(ids_to_remove)} vector khỏi FAISS index và embedding map.")

    def reset(self):
        self.index = self._create_index()
        self.embedding_map.clear()
        self.next_id = 100000

    def get_embedding_by_id(self, id_: int):
        return self.embedding_map.get(id_)

    def get_total(self):
        return self.index.ntotal

    def save_index(self, directory: str):
        os.makedirs(directory, exist_ok=True)

        index_path = os.path.join(directory, "index.faiss")
        metadata_path = os.path.join(directory, "metadata.json")

        faiss.write_index(self.index, index_path)

        metadata = {
            "next_id": self.next_id,
            "ntotal": self.index.ntotal,
            "dim": self.dim,
            "metric_type": self.metric_type,
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

    @classmethod
    def load_index(cls, directory: str):
        index_path = os.path.join(directory, "index.faiss")
        metadata_path = os.path.join(directory, "metadata.json")

        index = faiss.read_index(index_path)

        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Không tìm thấy metadata tại {metadata_path}")

        with open(metadata_path, "r") as f:
            meta = json.load(f)

        dim = meta.get("dim")
        metric_type = meta.get("metric_type", "ip")

        manager = cls(dim=dim, metric_type=metric_type)
        manager.index = index
        manager.next_id = meta.get("next_id", 100000)

        return manager


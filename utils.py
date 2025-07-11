import json
from typing import List, Dict, Union
from logger import _setup_logger
import pandas as pd
import config
from dotenv import load_dotenv
import os


logger = _setup_logger(__name__, config.LOG_LEVEL)

class Utils:
    @staticmethod
    def load_json(file_path: str) -> dict:
        """Đọc file .json và trả về dữ liệu dưới dạng dict hoặc list."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Load FILE JSON {file_path} thành công")
                return data
        except Exception as e:
            logger.debug(f"Load FILE JSON {file_path} thất bại")
            raise Exception(e)

    @staticmethod
    def load_jsonl(file_path: str) -> List[Dict]:
        """Đọc file .jsonl và trả về list chứa các dict (mỗi dòng là một JSON).
    
        Args:
            file_path (str): Đường dẫn tới file .jsonl
            logger: Logger đã được cấu hình sẵn (thường dùng logging.getLogger(...))
    
        Returns:
            List[Dict]: Danh sách các dòng JSON đã parse thành dict
        """
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if line:
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            logger.debug(f"Lỗi JSON ở dòng {line_num}: {e}")
        except FileNotFoundError:
            logger.debug(f"Không tìm thấy file: {file_path}")
        except Exception as e:
            logger.debug(f"Lỗi khi đọc file '{file_path}': {e}")
        return data

    @staticmethod
    def write_csv(data: List[Dict], file_path: str, encoding: str = "utf-8", index: bool = False) -> None:
        """
        Ghi list[dict] hoặc pandas.DataFrame ra file CSV.
    
        Args:
            data (List[Dict] or pd.DataFrame): Dữ liệu cần ghi.
            file_path (str): Đường dẫn file CSV đầu ra.
            encoding (str): Kiểu mã hóa (mặc định: "utf-8").
            index (bool): Có ghi chỉ số dòng (index) hay không (mặc định: False).
        """
        try:
            if isinstance(data, pd.DataFrame):
                df = data
            else:
                df = pd.DataFrame(data)
    
            df.to_csv(file_path, index=index, encoding=encoding)
            logger.debug(f"[write_csv] ✅ Đã ghi {len(df)} dòng vào '{file_path}'")
    
        except Exception as e:
            logger.debug(f"[write_csv] ❌ Lỗi khi ghi CSV: {e}")

    @staticmethod
    def load_api_key_from_env(key_name: str, env_path: str = ".env") -> str:
        """
        Load API key từ biến môi trường, tự động đọc từ file .env nếu chưa có.

        Args:
            key_name (str): Tên biến môi trường (ví dụ: "GEMINI_API_KEY").
            env_path (str): Đường dẫn tới file .env (mặc định là cùng thư mục).

        Returns:
            str: Giá trị API key

        Raises:
            EnvironmentError: Nếu không tìm thấy key trong môi trường
        """
        load_dotenv(dotenv_path=env_path)
        api_key = os.getenv(key_name)

        if not api_key:
            raise EnvironmentError(f"⚠️ Không tìm thấy biến môi trường: {key_name}")
        
        logger.debug(f"[load_api_key_from_env] ✅ Đã load key '{key_name}' từ môi trường")
        return api_key
    
    @staticmethod
    def save_json(data: Union[Dict, List], file_path: str, ensure_ascii: bool = False, indent: int = 2) -> None:
        """
        Ghi dữ liệu (dict hoặc list) vào file JSON.

        Args:
            data (Union[Dict, List]): Dữ liệu cần ghi.
            file_path (str): Đường dẫn tới file JSON đầu ra.
            ensure_ascii (bool): Nếu True, các ký tự không ASCII sẽ được escape. Mặc định là False để giữ tiếng Việt.
            indent (int): Số khoảng trắng thụt dòng cho JSON đẹp.

        Raises:
            Exception: Nếu ghi file thất bại.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
            logger.debug(f"[save_json] ✅ Đã ghi JSON vào '{file_path}'")
        except Exception as e:
            logger.debug(f"[save_json] ❌ Lỗi khi ghi JSON: {e}")
            raise Exception(e)
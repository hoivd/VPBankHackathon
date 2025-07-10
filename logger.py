import logging

def _setup_logger(name: str, level=logging.INFO, log_file=None) -> logging.Logger:
    '''
         Hàm khởi tạo và trả về logger đã cấu hình
    '''
    formatter = logging.Formatter('<%(levelname)s-%(name)s> - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Tránh nhân bản handler
    if not logger.handlers:
        logger.addHandler(handler)

        # Nếu muốn ghi vào file log
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger

if __name__ == "main":
    logger = _setup_logger("main", log_file="main.log")
    logger.debug("Debug message")
    logger.info("Info message")
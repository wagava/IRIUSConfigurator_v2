import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s", level=logging.INFO
)


def get_logger(name: str) -> logging.Logger:
    """Функция создания экземпляра логгера."""
    stream_handler = logging.StreamHandler()
    logger = logging.getLogger(name)
    logger.addHandler(stream_handler)
    return logger

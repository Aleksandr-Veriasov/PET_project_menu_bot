import logging
import sys
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


# Настраиваем root-логгер
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Удаляем старые хендлеры (если уже был basicConfig или др.)
root_logger.handlers = []

# Новый handler с JSON-форматером
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(JSONFormatter())
root_logger.addHandler(stream_handler)

# (опционально) Экспортировать заранее полученный логгер
logger = logging.getLogger(__name__)

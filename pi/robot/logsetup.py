"""Send log messages to both the screen and a log file."""
import logging
from logging.handlers import RotatingFileHandler

from robot.config import PI_DIR


def setup_logging(config: dict) -> None:
    log_cfg = config.get("logging", {})
    log_file = PI_DIR / log_cfg.get("file", "logs/robot.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    # Keep up to 5 files of 1 MB each so the SD card never fills up.
    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    file_handler.setFormatter(fmt)
    screen_handler = logging.StreamHandler()
    screen_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(log_cfg.get("level", "INFO"))
    root.handlers = [file_handler, screen_handler]

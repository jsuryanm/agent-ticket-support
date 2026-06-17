import logging
import shutil
from pathlib import Path

from solution.logging_config import configure_logging


def test_configure_logging_writes_to_logs_directory():
    log_dir = Path(".test-logs")
    if log_dir.exists():
        shutil.rmtree(log_dir)

    try:
        log_file = configure_logging(log_dir=log_dir, log_file="test.log")
        logging.getLogger("udahub.test").info("file logging works")

        assert log_file == log_dir / "test.log"
        assert log_file.exists()
        text = log_file.read_text(encoding="utf-8")
        assert "INFO udahub.test: file logging works" in text
        assert text[:4].isdigit()
    finally:
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
        if log_dir.exists():
            shutil.rmtree(log_dir)

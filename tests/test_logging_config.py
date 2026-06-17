import json
import logging
import shutil
from pathlib import Path

from solution.logging_config import configure_logging, log_event


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


def test_configure_logging_writes_structured_jsonl_events():
    log_dir = Path(".test-logs")
    if log_dir.exists():
        shutil.rmtree(log_dir)

    try:
        configure_logging(log_dir=log_dir, log_file="test.log")
        log_event(
            logging.getLogger("udahub.test"),
            "finalized",
            ticket_id="ticket-123",
            agent="finalize",
            final_status="resolved",
        )

        jsonl_file = log_dir / "udahub.jsonl"
        assert jsonl_file.exists()
        records = [
            json.loads(line)
            for line in jsonl_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert records[-1]["ticket_id"] == "ticket-123"
        assert records[-1]["agent"] == "finalize"
        assert records[-1]["event"] == "finalized"
        assert records[-1]["final_status"] == "resolved"
        assert records[-1]["logger"] == "udahub.test"
        assert records[-1]["level"] == "INFO"
        assert "timestamp" in records[-1]
    finally:
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
        if log_dir.exists():
            shutil.rmtree(log_dir)

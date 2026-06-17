import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
STRUCTURED_LOG_ATTR = "structured_event"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StructuredEventFilter(logging.Filter):
    """Only write records emitted through log_event to the JSONL handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        return hasattr(record, STRUCTURED_LOG_ATTR)


class JsonlEventFormatter(logging.Formatter):
    """Serialize workflow evidence logs as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        fields = getattr(record, STRUCTURED_LOG_ATTR, {}) or {}
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        payload.update(fields)
        return json.dumps(payload, default=str, sort_keys=True)


def configure_logging(
    level: int = logging.INFO,
    *,
    log_dir: Path | str | None = None,
    log_file: str = "udahub.log",
    structured_log_file: str | None = "udahub.jsonl",
    structured: bool = True,
) -> Path:
    """Configure timestamped console and file logs for CLI, notebooks, and tests."""
    target_dir = Path(log_dir) if log_dir is not None else PROJECT_ROOT / "logs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / log_file

    formatter = logging.Formatter(LOG_FORMAT)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(target_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    handlers: list[logging.Handler] = [console_handler, file_handler]

    if structured and structured_log_file is not None:
        structured_handler = logging.FileHandler(target_dir / structured_log_file, encoding="utf-8")
        structured_handler.setFormatter(JsonlEventFormatter())
        structured_handler.addFilter(StructuredEventFilter())
        handlers.append(structured_handler)

    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )
    return target_file


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit a structured workflow event without changing readable text logs."""
    payload = {"event": event}
    payload.update({key: value for key, value in fields.items() if value is not None})
    logger.log(level, event, extra={STRUCTURED_LOG_ATTR: payload})

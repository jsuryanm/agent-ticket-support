import logging
from pathlib import Path


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def configure_logging(
    level: int = logging.INFO,
    *,
    log_dir: Path | str | None = None,
    log_file: str = "udahub.log",
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

    logging.basicConfig(
        level=level,
        handlers=[console_handler, file_handler],
        force=True,
    )
    return target_file

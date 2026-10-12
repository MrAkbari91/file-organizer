"""Unit tests for logger configuration."""

from pathlib import Path
from file_organizer.core.logger import setup_logger


def test_logger_file_creation(temp_dir: Path):
    log_file = temp_dir / "custom.log"
    logger = setup_logger(log_file=log_file)

    logger.info("Test message for file organizer log")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test message for file organizer log" in content


def test_logger_gui_callback(temp_dir: Path):
    received = []
    logger = setup_logger(gui_callback=lambda msg: received.append(msg))

    logger.info("Real-time message")

    assert any("Real-time message" in m for m in received)

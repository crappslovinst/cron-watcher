import json
import pytest
import tempfile
import os

from cron_watcher.config import load_config, Config, AlertConfig


@pytest.fixture
def minimal_config_file():
    data = {"jobs": [{"name": "backup", "schedule": "0 2 * * *"}]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def full_config_file():
    data = {
        "log_file": "/tmp/cron-watcher.log",
        "db_path": "/tmp/jobs.db",
        "check_interval": 30,
        "alert": {
            "webhook_url": "https://hooks.example.com/notify",
            "email_to": ["admin@example.com"],
            "email_from": "watcher@example.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
        },
        "jobs": [{"name": "cleanup", "schedule": "@daily"}],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        yield f.name
    os.unlink(f.name)


def test_load_minimal_config(minimal_config_file):
    cfg = load_config(minimal_config_file)
    assert isinstance(cfg, Config)
    assert cfg.log_file == "/var/log/cron-watcher.log"
    assert cfg.check_interval == 60
    assert len(cfg.jobs) == 1
    assert cfg.jobs[0]["name"] == "backup"


def test_load_full_config(full_config_file):
    cfg = load_config(full_config_file)
    assert cfg.log_file == "/tmp/cron-watcher.log"
    assert cfg.check_interval == 30
    assert cfg.alert.webhook_url == "https://hooks.example.com/notify"
    assert cfg.alert.smtp_port == 587
    assert "admin@example.com" in cfg.alert.email_to


def test_missing_config_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.json")


def test_default_alert_config():
    alert = AlertConfig()
    assert alert.webhook_url is None
    assert alert.email_to == []
    assert alert.smtp_host == "localhost"
    assert alert.smtp_port == 25

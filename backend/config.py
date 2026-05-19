"""
配置模块
"""
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


def load_yaml_config() -> Dict[str, Any]:
    config_path = BASE_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    app_name: str = "多市场量化分析与策略回测"
    app_version: str = "1.0.0"
    debug: bool = True
    db_type: str = "sqlite"
    db_path: str = str(BASE_DIR / "data" / "stocks.db")
    server_host: str = "0.0.0.0"
    server_port: int = 8777


@lru_cache()
def get_settings() -> Settings:
    yaml_config = load_yaml_config()
    app_config = yaml_config.get("app", {})
    db_config = yaml_config.get("database", {})
    server_config = yaml_config.get("server", {})
    return Settings(
        app_name=app_config.get("name", "多市场量化分析与策略回测"),
        app_version=app_config.get("version", "1.0.0"),
        debug=app_config.get("debug", True),
        db_type=db_config.get("type", "sqlite"),
        db_path=db_config.get("path", str(BASE_DIR / "data" / "stocks.db")),
        server_host=server_config.get("host", "0.0.0.0"),
        server_port=server_config.get("port", 8777),
    )


def get_backtest_config() -> Dict[str, Any]:
    yaml_config = load_yaml_config()
    return yaml_config.get("backtest", {})


def get_crawler_config() -> Dict[str, Any]:
    yaml_config = load_yaml_config()
    return yaml_config.get("crawler", {})


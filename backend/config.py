                 """
配置模块
"""
import os
from pathlib import Path
from typing import Dict, Any
import yaml
from pydantic_settings import BaseSettings
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent


def load_yaml_config() -> Dict[str, Any]:
    config_path = BASE_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


class Settings(BaseSettings):
    app_name: str = "US Stock Quant System"
    app_version: str = "1.0.0"
    debug: bool = True
    db_type: str = "sqlite"
    db_path: str = str(BASE_DIR / "data" / "us_stocks.db")
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    yaml_config = load_yaml_config()
    app_config = yaml_config.get("app", {})
    db_config = yaml_config.get("database", {})
    server_config = yaml_config.get("server", {})
    return Settings(
        app_name=app_config.get("name", "US Stock Quant System"),
        app_version=app_config.get("version", "1.0.0"),
        debug=app_config.get("debug", True),
        db_type=db_config.get("type", "sqlite"),
        db_path=db_config.get("path", str(BASE_DIR / "data" / "us_stocks.db")),
        server_host=server_config.get("host", "0.0.0.0"),
        server_port=server_config.get("port", 8000),
    )


def get_backtest_config() -> Dict[str, Any]:
    yaml_config = load_yaml_config()
    return yaml_config.get("backtest", {})


def get_crawler_config() -> Dict[str, Any]:
    yaml_config = load_yaml_config()
    return yaml_config.get("crawler", {})

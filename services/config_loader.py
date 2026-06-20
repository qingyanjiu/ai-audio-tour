"""
配置加载模块
从 config.yaml 读取 LLM、服务、图片等配置，提供统一的配置访问入口。
"""

import os
from pathlib import Path
from typing import Any

import yaml

_config: dict[str, Any] | None = None


def _find_config() -> Path:
    """从项目根目录查找 config.yaml"""
    candidates = [
        Path.cwd() / "config.yaml",
        Path(__file__).resolve().parent.parent / "config.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "config.yaml not found. Looked in: " + ", ".join(str(c) for c in candidates)
    )


def load_config(reload: bool = False) -> dict[str, Any]:
    """加载并缓存配置（单例）"""
    global _config
    if _config is not None and not reload:
        return _config

    path = _find_config()
    with open(path, encoding="utf-8") as f:
        _config = yaml.safe_load(f)

    # 环境变量覆盖（便于部署时免修改配置文件）
    if env_url := os.getenv("LLM_BASE_URL"):
        _config.setdefault("llm", {})["base_url"] = env_url
    if env_key := os.getenv("LLM_API_KEY"):
        _config.setdefault("llm", {})["api_key"] = env_key
    if env_model := os.getenv("LLM_MODEL"):
        _config.setdefault("llm", {})["model"] = env_model

    return _config


def get_llm_config() -> dict[str, Any]:
    """快捷获取 LLM 配置"""
    return load_config().get("llm", {})


def get_server_config() -> dict[str, Any]:
    """快捷获取服务配置"""
    return load_config().get("server", {})


def get_image_config() -> dict[str, Any]:
    """快捷获取图片处理配置"""
    return load_config().get("image", {})


def get_screenshot_config() -> dict[str, Any]:
    """快捷获取截图配置"""
    return load_config().get("screenshot", {})

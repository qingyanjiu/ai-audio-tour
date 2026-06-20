"""
图片处理模块
支持：压缩、转 base64、data URI 格式转换、URL 下载。
"""

import base64
import io
from pathlib import Path

import requests
from PIL import Image

from .config_loader import get_image_config


def resize_image(img: Image.Image, size: int | None = None, quality: int | None = None) -> str:
    """压缩 PIL Image，返回 base64 编码的 JPEG 字符串"""
    cfg = get_image_config()
    size = size or cfg.get("max_size", 1024)
    quality = quality or cfg.get("quality", 85)

    img = img.copy()
    img.thumbnail((size, size))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)

    return base64.b64encode(buf.getvalue()).decode()


def image_to_data_uri(img: Image.Image, **kwargs) -> str:
    """PIL Image → data:image/jpeg;base64,..."""
    b64 = resize_image(img, **kwargs)
    return f"data:image/jpeg;base64,{b64}"


def from_bytes(data: bytes) -> Image.Image:
    """字节数据 → PIL Image"""
    return Image.open(io.BytesIO(data))


def from_path(path: str | Path) -> Image.Image:
    """本地文件路径 → PIL Image"""
    return Image.open(path)


def from_url(url: str) -> Image.Image:
    """远程 URL → PIL Image"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content))


def normalize_to_data_uri(source: str | bytes | Image.Image) -> str:
    """统一入口：接收路径 / URL / bytes / PIL Image，返回 data URI"""
    if isinstance(source, Image.Image):
        return image_to_data_uri(source)

    if isinstance(source, bytes):
        img = from_bytes(source)
        return image_to_data_uri(img)

    s = str(source)
    if s.startswith(("http://", "https://")):
        img = from_url(s)
    else:
        img = from_path(s)
    return image_to_data_uri(img)


def save_upload(file_bytes: bytes, filename: str) -> Path:
    """保存上传的图片到本地"""
    dest_dir = Path.cwd() / "screenshots"
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / filename
    dest.write_bytes(file_bytes)
    return dest

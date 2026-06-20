# -*- coding: utf-8 -*-
"""
CDP 截图服务模块

通过 Chrome DevTools Protocol 截图，供 API 和 CLI 共同使用。
"""

import asyncio
import base64
import json
from pathlib import Path

import websockets

from .config_loader import get_screenshot_config


def _get_page_url(menu_name: str | None = None) -> str | None:
    """根据菜单名称从配置中查找对应的页面 URL"""
    cfg = get_screenshot_config()
    urls = cfg.get("urls", [])
    if menu_name:
        for item in urls:
            if item["name"] == menu_name:
                return item["url"]
    if urls:
        return urls[0]["url"]
    return None


async def capture_page(
    ws_url: str = "ws://127.0.0.1:9222/devtools/browser",
    url_filter: str | None = None,
) -> bytes:
    """通过 CDP 截图，返回 JPEG 字节"""
    async with websockets.connect(ws_url) as ws:
        # 1. 获取所有标签页
        await ws.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
        resp = json.loads(await ws.recv())
        targets = resp.get("result", {}).get("targetInfos", [])

        # 2. 找目标页面（优先匹配 url_filter，否则取第一个页面）
        tid = None
        for t in targets:
            if t.get("type") == "page":
                if url_filter and url_filter in t.get("url", ""):
                    tid = t["targetId"]
                    break
                if tid is None:
                    tid = t["targetId"]

        if not tid:
            raise RuntimeError("没有可用页面。请确认 Chrome 已打开大屏页面")

        # 3. 附加到目标页面
        await ws.send(json.dumps({
            "id": 2, "method": "Target.attachToTarget",
            "params": {"targetId": tid, "flatten": True},
        }))
        sess = json.loads(await ws.recv()).get("result", {}).get("sessionId")

        # 4. 截图
        await ws.send(json.dumps({
            "id": 3, "sessionId": sess,
            "method": "Page.captureScreenshot",
            "params": {"format": "jpeg", "quality": 85},
        }))
        b64 = json.loads(await ws.recv()).get("result", {}).get("data", "")
        return base64.b64decode(b64)


async def capture_and_save(
    menu_name: str | None = None,
    timestamp: str | None = None,
    output_dir: str | Path | None = None,
) -> tuple[bytes, str, str]:
    """
    截取大屏页面 → 保存到文件 → 返回 (jpeg_bytes, 文件名, 时间戳)。

    参数:
        menu_name: 菜单专题名称（按名称匹配 config.yaml 中的 URL）
        timestamp: 自定义时间戳，不传则自动生成
        output_dir: 截图保存目录，不传则使用配置中的 output_dir

    返回:
        (jpeg_bytes, filename, timestamp)
    """
    cfg = get_screenshot_config()
    page_url = _get_page_url(menu_name)
    ws_url = f"ws://{cfg.get('cdp_host', '127.0.0.1')}:{cfg.get('cdp_port', 9222)}/devtools/browser"

    if timestamp is None:
        timestamp = str(int(asyncio.get_event_loop().time()))

    # 截图
    jpeg_bytes = await capture_page(ws_url=ws_url, url_filter=page_url)

    # 保存
    out_dir = Path(output_dir or cfg.get("output_dir", "./screenshots"))
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{timestamp}.jpg"
    (out_dir / filename).write_bytes(jpeg_bytes)

    return jpeg_bytes, filename, timestamp

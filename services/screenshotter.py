# -*- coding: utf-8 -*-
"""
CDP 截图服务模块

通过 Chrome DevTools Protocol 截图，供 API 和 CLI 共同使用。
"""

import asyncio
import base64
import http.client
import json
import time
from pathlib import Path

import websockets
from .config_loader import get_screenshot_config


def _fetch_json(host: str, port: int, path: str) -> list | dict:
    """通过 HTTP 获取 CDP 控制端点 JSON"""
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode()
        return json.loads(body)
    finally:
        conn.close()


async def _get_browser_ws_url(host: str, port: int) -> str:
    """从 CDP HTTP 端点获取浏览器级 WebSocket URL（含 UUID）"""
    info = await asyncio.get_running_loop().run_in_executor(
        None, _fetch_json, host, port, "/json/version"
    )
    if isinstance(info, dict) and "webSocketDebuggerUrl" in info:
        return info["webSocketDebuggerUrl"]
    raise RuntimeError(
        f"CDP 端点未返回 webSocketDebuggerUrl。"
        f"请确认 Chrome 已用 --remote-debugging-port={port} 启动"
    )

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
    host: str = "127.0.0.1",
    port: int = 9222,
    url_filter: str | None = None,
) -> bytes:
    """通过 CDP 截图，返回 JPEG 字节"""
    # 1. 从 HTTP 端点获取所有标签页，直接取目标页面的 WebSocket URL
    targets = await asyncio.get_running_loop().run_in_executor(
        None, _fetch_json, host, port, "/json"
    )
    if not isinstance(targets, list):
        raise RuntimeError(f"CDP /json 返回非列表: {targets}")

    # 2. 找目标页面
    page = None
    for t in targets:
        if t.get("type") != "page":
            continue
        if url_filter and url_filter in t.get("url", ""):
            page = t
            break
        if page is None:
            page = t

    if not page:
        raise RuntimeError(
            "没有可用页面。请确认 Chrome 已打开大屏页面\n"
            f"可用 targets: {[(t.get('type'), t.get('url','')[:60]) for t in targets]}"
        )

    # 3. 直接连到目标页面的 WebSocket（页面级，免 session 管理）
    page_ws = page["webSocketDebuggerUrl"]
    if not page_ws:
        raise RuntimeError(f"页面没有 WebSocket 地址: {page}")

    async with websockets.connect(page_ws) as ws:
        # 4. 启用 Page 域（某些 Chrome 版本需要）
        await ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
        r = json.loads(await ws.recv())
        if "error" in r:
            # Page.enable 失败不致命，继续尝试截图
            pass

        # 5. 截图
        await ws.send(json.dumps({
            "id": 2,
            "method": "Page.captureScreenshot",
            "params": {"format": "jpeg", "quality": 85},
        }))
        msg = json.loads(await ws.recv())
        if "error" in msg:
            raise RuntimeError(f"截图失败: {msg['error']}")
        b64 = msg.get("result", {}).get("data", "")
        if not b64:
            raise RuntimeError(
                f"截图数据为空，响应: {json.dumps(msg, ensure_ascii=False)[:500]}"
            )
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
    host = cfg.get("cdp_host", "127.0.0.1")
    port = cfg.get("cdp_port", 9222)
    page_url = _get_page_url(menu_name)

    if timestamp is None:
        timestamp = str(int(time.time()))

    # 截图
    jpeg_bytes = await capture_page(host=host, port=port, url_filter=page_url)

    # 保存
    out_dir = Path(output_dir or cfg.get("output_dir", "./screenshots"))
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{timestamp}.jpg"
    (out_dir / filename).write_bytes(jpeg_bytes)

    return jpeg_bytes, filename, timestamp

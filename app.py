# -*- coding: utf-8 -*-
"""
AI 大屏讲解员 - Web API 服务

单 POST 接口：传入 timestamp + menu_name → 服务端 CDP 截图 → 压缩 → LLM 识别 → 返回讲解词。
"""

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.config_loader import get_server_config
from services.image_processor import normalize_to_data_uri
from services.llm_client import describe_page_with_image
from services.screenshotter import capture_and_save


# ── 应用初始化 ────────────────────────────────────────────

app = FastAPI(
    title="AI 大屏讲解员",
    description="园区数字孪生驾驶舱大屏智能讲解 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 数据模型 ──────────────────────────────────────────────

class DescribeResponse(BaseModel):
    code: int = 0
    data: dict
    message: str = "ok"


class DescribeBody(BaseModel):
    menu_name: str | None = None
    timestamp: str | None = None  # 可选，不传则自动生成


# ── 接口：POST /api/v1/describe ──────────────────────────

@app.post("/api/v1/describe", response_model=DescribeResponse)
async def describe(body: DescribeBody):
    """
    传入菜单名称 → 服务端自动截取大屏页面 → 识别 → 返回讲解词。

    ```json
    {
      "menu_name": "智慧安防",
      "timestamp": "1740389422"
    }
    ```

    timestamp 可选，不传则服务端自动生成。
    """
    ts = body.timestamp or str(int(time.time()))

    # 1. CDP 截图 + 保存到 screenshots/{ts}.jpg
    jpeg_bytes, filename, _ = await capture_and_save(
        menu_name=body.menu_name,
        timestamp=ts,
    )

    # 2. 压缩 → base64 data URI
    data_uri = normalize_to_data_uri(jpeg_bytes)

    # 3. LLM 识别
    result = describe_page_with_image(data_uri, body.menu_name)

    # 4. 补充文件信息
    result["timestamp"] = ts
    result["filename"] = filename

    return DescribeResponse(data=result)


# ── 静态文件 ──────────────────────────────────────────────

@app.get("/ai-guide.js")
async def serve_guide_js():
    return FileResponse(
        Path(__file__).resolve().parent / "ai-guide.js",
        media_type="application/javascript",
    )

_here = Path(__file__).resolve().parent
_ss_dir = _here / "screenshots"
_ss_dir.mkdir(exist_ok=True)
app.mount("/screenshots", StaticFiles(directory=str(_ss_dir)), name="screenshots")


# ── 健康检查 ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── 启动入口 ──────────────────────────────────────────────

def main():
    cfg = get_server_config()
    import uvicorn
    uvicorn.run(
        "app:app",
        host=cfg.get("host", "0.0.0.0"),
        port=cfg.get("port", 8000),
        reload=True,
    )


if __name__ == "__main__":
    main()

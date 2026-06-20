# -*- coding: utf-8 -*-
"""
CDP 截图 + 智能识别工具（CLI 版）

用法:
  1. Chrome 以调试模式启动（或用 start_chrome.py）
  2. python capture.py --menu 智慧安防
"""

import argparse
import asyncio

from services.image_processor import normalize_to_data_uri
from services.llm_client import describe_page_with_image
from services.screenshotter import capture_and_save


async def main():
    parser = argparse.ArgumentParser(description="CDP 截图 → 压缩 → LLM 识别 → 讲解词")
    parser.add_argument("--menu", default="", help="当前专题名称（如：智慧安防）")
    parser.add_argument("--save", default=None, help="截图保存路径（默认存到 screenshots/ 目录）")
    args = parser.parse_args()

    print("正在通过 CDP 截图...")
    jpeg_bytes, filename, ts = await capture_and_save(
        menu_name=args.menu,
        timestamp=None,
        output_dir=args.save,
    )
    print(f"截图已保存: {filename}")

    print("正在压缩图片...")
    data_uri = normalize_to_data_uri(jpeg_bytes)

    print("正在生成讲解词...")
    result = describe_page_with_image(data_uri, args.menu)

    print(f"\n{result.get('description', '')}")


if __name__ == "__main__":
    asyncio.run(main())

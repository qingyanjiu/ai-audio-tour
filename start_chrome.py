# -*- coding: utf-8 -*-
"""
一键启动 Chrome（调试模式）+ 打开大屏页面。

自动识别 Windows / macOS / Linux。

用法:
    python start_chrome.py                  # 打开配置中第一个页面
    python start_chrome.py --name 智慧安防   # 按名称匹配
    python start_chrome.py --url http://... # 自定义地址
    python start_chrome.py --port 9222      # 自定义调试端口
"""

import argparse
import platform
import subprocess
import sys
from pathlib import Path

from services.config_loader import get_screenshot_config


def find_chrome() -> str:
    """自动查找 Chrome 可执行文件路径"""
    system = platform.system()

    if system == "Windows":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            # 用户安装路径
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path.home() / "AppData" / "Local" / "Chrome" / "Application" / "chrome.exe",
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            Path.home() / "Applications" / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome",
        ]
    else:  # Linux
        candidates = [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        ]

    for c in candidates:
        c = str(c)
        try:
            if system == "Windows":
                if Path(c).exists():
                    return c
            else:
                subprocess.run([c, "--version"], capture_output=True, timeout=5)
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    raise FileNotFoundError(
        "找不到 Chrome，请手动指定路径。"
        if system == "Windows"
        else "找不到 Chrome，请确认已安装。"
    )


def get_default_url() -> str:
    """从配置文件获取第一个大屏地址"""
    cfg = get_screenshot_config()
    urls = cfg.get("urls", [])
    if urls:
        return urls[0]["url"]
    return "about:blank"


def main():
    parser = argparse.ArgumentParser(description="一键启动 Chrome 调试模式 + 大屏")
    parser.add_argument("--url", default=None, help="大屏页面地址")
    parser.add_argument("--name", default=None, help="按 config.yaml 中的名称匹配页面地址")
    parser.add_argument("--port", default="9222", help="调试端口（默认 9222）")
    parser.add_argument("--data-dir", default=None, help="用户数据目录")
    args = parser.parse_args()

    # 确定 URL
    url = args.url
    if not url and args.name:
        cfg = get_screenshot_config()
        for item in cfg.get("urls", []):
            if item["name"] == args.name:
                url = item["url"]
                break
        if not url:
            print(f"配置中未找到名称 '{args.name}'")
            sys.exit(1)
    if not url:
        url = get_default_url()

    # 自动处理数据目录
    system = platform.system()
    if args.data_dir:
        data_dir = args.data_dir
    else:
        # 用项目下的 .chrome-data 目录，避免干扰正常 Chrome
        data_dir = str(Path(__file__).resolve().parent / ".chrome-data")

    Path(data_dir).mkdir(parents=True, exist_ok=True)

    # 查找 Chrome
    chrome = find_chrome()

    # 构建命令
    cmd = [
        chrome,
        f"--remote-debugging-port={args.port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={data_dir}",
        url,
    ]

    print(f"🚀 启动 Chrome: {chrome}")
    print(f"   调试端口: {args.port}")
    print(f"   数据目录: {data_dir}")
    print(f"   打开页面: {url}")
    print()

    # Windows 用 CREATE_NEW_CONSOLE 避免占用终端
    kwargs = {}
    if system == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(cmd, **kwargs)
    print("✅ Chrome 已启动，可以关闭本窗口。")
    print()
    print("验证方法（新终端执行）：")
    print(f"  curl http://127.0.0.1:{args.port}/json/version")
    print(f"  curl http://127.0.0.1:{args.port}/json")


if __name__ == "__main__":
    main()

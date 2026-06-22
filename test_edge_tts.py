#!/usr/bin/env python3
"""
Edge-TTS 文本转语音 CLI 工具

用法:
  python test_edge_tts.py --text "您现在看到的是智慧安防专题"
  python test_edge_tts.py --text "您好" --voice zh-CN-YunxiNeural --rate +20%%
  python test_edge_tts.py --text "您好" --filename output_name     # 指定文件名
  python test_edge_tts.py --list-voices           # 列出所有中文语音
  python test_edge_tts.py --list-voices zh         # 列出中文语音
"""

import argparse
import asyncio
import sys
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # 中文女声（推荐）
OUT_DIR = Path(__file__).resolve().parent


def list_voices(lang: str | None = None):
    """列出可用语音"""
    import json
    voices = asyncio.run(edge_tts.list_voices())

    if lang:
        voices = [v for v in voices if lang in v.get("Locale", "")]

    print(f"\n可用语音 ({len(voices)} 个)：\n")
    for v in voices:
        name = v["ShortName"]
        locale = v.get("Locale", "")
        gender = v.get("Gender", "")
        status = "Neural" if "Neural" in name else "     "
        print(f"  [{status}] {name:<35} {locale:<12} {gender}")

    print(f"\n推荐中文语音：")
    print(f"  zh-CN-XiaoxiaoNeural    女声（自然亲和，推荐展厅）")
    print(f"  zh-CN-YunxiNeural       男声（阳光活力）")
    print(f"  zh-CN-YunjianNeural     男声（沉稳专业）")
    print(f"  zh-CN-XiaoyiNeural      女声（热情）")


async def synthesize(text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%",
                     output: str | None = None) -> str:
    """将文本合成为语音文件"""
    if output is None:
        safe = "".join(c for c in text[:10] if c.isalnum() or c in "_-")
        output = str(OUT_DIR / f"tts_{safe or 'speech'}.mp3")

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output)

    file_size = Path(output).stat().st_size
    print(f"\n语音已保存 -> {output}")
    print(f"文件大小: {file_size / 1024:.1f} KB")
    print(f"语音: {voice}  |  语速: {rate}")
    return output


def main():
    parser = argparse.ArgumentParser(description="Edge-TTS 文本转语音")
    parser.add_argument("--text", "-t", default=None, help="待朗读文本")
    parser.add_argument("--filename", "-f", default=None,
                        help="输出文件名(不含路径和 .mp3, 默认自动从文本生成)")
    parser.add_argument("--voice", default=DEFAULT_VOICE,
                        help=f"语音名称(默认 {DEFAULT_VOICE})")
    parser.add_argument("--rate", default="+0%",
                        help="语速调整(如 +20%% / -10%%, 默认 +0%%)")
    parser.add_argument("--output", default=None,
                        help="输出文件完整路径(优先级高于 --filename)")
    parser.add_argument("--list-voices", nargs="?", const="zh", default=None,
                        metavar="LANG", help="列出语音(可指定语言过滤, 默认 zh)")
    args = parser.parse_args()

    text = args.text

    if args.list_voices:
        list_voices(args.list_voices if args.list_voices != "zh" else None)
        return

    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        parser.print_help()
        print("\n请提供待朗读文本, 如: --text \"您看到的是...\"")
        sys.exit(1)

    # 输出路径优先级: --output > --filename > 自动生成
    output = args.output
    if not output and args.filename:
        output = str(OUT_DIR / f"{args.filename}.mp3")

    asyncio.run(synthesize(text, args.voice, args.rate, output))


if __name__ == "__main__":
    main()

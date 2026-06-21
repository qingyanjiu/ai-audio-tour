#!/usr/bin/env python3
"""
Kokoro TTS 音色测试工具

用法:
  python test_kokoro.py                          # 列出所有可用音色
  python test_kokoro.py --voice zf_xiaobei        # 测试指定音色
  python test_kokoro.py --voice zf_xiaobei --text "自定义文本"
  python test_kokoro.py --voice all               # 逐个测试所有音色
  python test_kokoro.py --service                # 测试 TTSService 封装

第一次运行会自动从 HuggingFace 下载音色文件，需要联网。
"""

import argparse
import time
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from huggingface_hub import list_repo_files
from kokoro import KPipeline

# ── 复用服务模块的拆句函数 ──────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from services.tts_service import split_sentences

REPO_ID = "hexgrad/Kokoro-82M"
DEFAULT_TEXT = (
    "您现在看到的是智慧安防专题，该专题主要包含园区安防监控、人员车辆出入管理"
    "以及突发事件应急处置等内容。目前园区总体安全态势平稳。"
    "大屏左侧显示的是园区各主要出入口的人车流量统计，从数据来看，"
    "今日入园车辆为两千三百辆，人员为六千八百人次，较昨日环比上升了百分之十二。"
    "右侧是重点区域视频监控画面，覆盖了园区所有关键点位。"
    "中间大图展示的是园区三维数字孪生地图，各安防设备状态一目了然。"
)
OUT_DIR = Path(__file__).resolve().parent


def list_voices():
    """从 HuggingFace 拉取所有可用音色列表"""
    files = list_repo_files(REPO_ID)
    voices = sorted(f for f in files if f.startswith("voices/"))

    print(f"\nKokoro 共有 {len(voices)} 个音色文件：\n")
    for v in voices:
        name = v.replace("voices/", "").replace(".pt", "")
        lang = name[:2]
        label = {"af": "🇺🇸 美式女声", "am": "🇺🇸 美式男声",
                 "bf": "🇬🇧 英式女声", "bm": "🇬🇧 英式男声",
                 "jf": "🇯🇵 日语女声", "jm": "🇯🇵 日语男声",
                 "zf": "🇨🇳 中文女声", "zm": "🇨🇳 中文男声"}.get(lang, f"其它({lang})")
        print(f"  {name:<20}  {label}")

    print("\n推荐展厅讲解音色：")
    print("  🇨🇳 zf_xiaobei, zf_xiaotong  (中文女声)")
    print("  🇨🇳 zm_yunxi, zm_yunjian      (中文男声)")


def test_voice(voice: str, text: str = None):
    """测试单个音色，按标点拆句 + 自动拼接"""
    if text is None:
        text = DEFAULT_TEXT

    sentences = split_sentences(text)
    print(f"\n文本已拆分为 {len(sentences)} 句：")
    for i, s in enumerate(sentences):
        print(f"  ({i+1}) {s}")

    prefix = voice[:2]
    lang_map = {"af": "a", "am": "a", "bf": "b", "bm": "b",
                "jf": "j", "jm": "j", "zf": "z", "zm": "z"}
    lang_code = lang_map.get(prefix, "a")

    print(f"\n正在加载 {voice} (lang={lang_code})...")
    t0 = time.perf_counter()
    pipeline = KPipeline(lang_code=lang_code)
    load_time = time.perf_counter() - t0

    print(f"正在生成语音（共 {len(sentences)} 句, {len(text)} 字）...")
    gen_t0 = time.perf_counter()
    all_audio = []
    for i, sentence in enumerate(sentences):
        for gs, ps, audio in pipeline(sentence, voice=voice, speed=1):
            all_audio.append(audio)
        silence = np.zeros(int(24000 * 0.3), dtype=np.float32)
        all_audio.append(silence)
        print(f"  句 {i+1} 完成")
    gen_time = time.perf_counter() - gen_t0

    if not all_audio:
        print(f"❌ {voice}: 未生成任何音频")
        return

    full_audio = np.concatenate(all_audio)
    out_path = OUT_DIR / f"test_{voice}.wav"
    sf.write(str(out_path), full_audio, 24000)
    duration = len(full_audio) / 24000
    audio_seconds = len(full_audio) / 24000
    rtf = gen_time / audio_seconds if audio_seconds > 0 else 0
    print(f"\n✅ {voice} → {out_path.name}")
    print(f"   模型加载: {load_time:.2f}s  |  生成耗时: {gen_time:.2f}s  |  音频时长: {audio_seconds:.1f}s")
    print(f"   实时倍率: {rtf:.2f}x  ({'快' if rtf < 1 else '慢'})")


def test_service():
    """使用 TTSService 封装来测试"""
    print(f"\n使用 TTSService 测试...\n")
    from services.tts_service import TTSService
    t0 = time.perf_counter()

    tts = TTSService()

    print(f"当前配置：voice={tts.voice_name}, speed={tts.speed}, "
          f"silence={tts.silence_sec}s\n")

    # 女声
    text = "您现在看到的是智慧安防专题，该专题主要包含园区安防监控、人员车辆出入管理等内容。"
    out = tts.synthesize_to_file(text, OUT_DIR / "tts_female.wav")
    female_time = time.perf_counter()
    print(f"✅ 女声 → {out}  ({female_time - t0:.2f}s)")

    # 切成男声
    tts.set_voice("male")
    out = tts.synthesize_to_file(text, OUT_DIR / "tts_male.wav")
    male_time = time.perf_counter()
    print(f"✅ 男声 → {out}  ({male_time - female_time:.2f}s)")

    # 恢复默认
    tts.close()
    total_time = time.perf_counter() - t0
    print(f"\n  总耗时: {total_time:.2f}s")


def test_all():
    """逐个测试所有音色（每个生成一个 wav 文件）"""
    t0 = time.perf_counter()
    files = list_repo_files(REPO_ID)
    voices = sorted(f.replace("voices/", "").replace(".pt", "")
                    for f in files if f.startswith("voices/"))
    for v in voices:
        try:
            test_voice(v, text=DEFAULT_TEXT)
        except Exception as e:
            print(f"❌ {v}: {e}")
    total = time.perf_counter() - t0
    print(f"\n{'='*50}")
    print(f"全部 {len(voices)} 个音色测试完成，总耗时 {total:.2f}s ({total/60:.1f}min)")


def main():
    parser = argparse.ArgumentParser(description="Kokoro TTS 音色测试")
    parser.add_argument("--voice", default=None,
                        help="要测试的音色名（如 zf_xiaobei），留空则列出所有音色")
    parser.add_argument("--text", default=None,
                        help="自定义朗读文本，默认使用讲解示例文本")
    parser.add_argument("--service", action="store_true",
                        help="测试 TTSService 封装")
    args = parser.parse_args()

    if args.service:
        test_service()
        return

    if not args.voice:
        list_voices()
        print("\n试听某个音色：")
        print(f"  python {Path(__file__).name} --voice zf_xiaobei")
        print(f"  python {Path(__file__).name} --voice zm_yunjian")
        print(f"  python {Path(__file__).name} --voice all")
        print(f"  python {Path(__file__).name} --service")
        return

    if args.voice == "all":
        test_all()
    else:
        test_voice(args.voice, text=args.text)


if __name__ == "__main__":
    main()

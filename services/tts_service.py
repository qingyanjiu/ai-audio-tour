# -*- coding: utf-8 -*-
"""
TTS 语音合成服务模块

封装 Kokoro-TTS，提供统一的文本转语音接口。
支持男声 / 女声切换，自动按标点拆句 + 句间静音间隔。

配置项（config.yaml）：
```yaml
tts:
  enabled: true
  provider: kokoro
  voice: female          # female / male
  speed: 1.0
  sample_rate: 24000
  silence_sec: 0.3       # 句间静音间隔（秒）
```
"""

import re
from pathlib import Path

import numpy as np
import soundfile as sf
from typing import Generator

from .config_loader import load_config

# ── 标点拆句 ──────────────────────────────────────────────


def split_sentences(text: str, max_len: int = 30) -> list[str]:
    """
    按中文标点将文本拆分为句子列表。

    拆分规则：
      1. 按句尾标点（。！？）拆，保留标点在句末
      2. 超过 max_len 字的子句，按分号（；）进一步拆分

    Args:
        text: 原始文本
        max_len: 按分号二次拆分的字数阈值

    Returns:
        句子列表
    """
    parts = re.split(r'(?<=[。！？])', text)
    parts = [p.strip() for p in parts if p.strip()]

    result = []
    for part in parts:
        if len(part) > max_len and '；' in part:
            sub = re.split(r'(?<=；)', part)
            result.extend(s.strip() for s in sub if s.strip())
        else:
            result.append(part)

    return result


# ── 配置映射 ──────────────────────────────────────────────

# 预定义音色映射（voice 配置项 → 实际 Kokoro 音色名）
DEFAULT_VOICES = {
    "female": "zf_xiaobei",
    "male": "zm_yunxi",
}

# lang_code 映射
_LANG_MAP = {
    "af": "a", "am": "a", "bf": "b", "bm": "b",
    "jf": "j", "jm": "j", "zf": "z", "zm": "z",
}


def _voice_name(cfg_voice: str) -> str:
    """从配置的 voice 值解析出实际音色名"""
    # 1. 如果是预定义的 male / female
    if cfg_voice.lower() in DEFAULT_VOICES:
        return DEFAULT_VOICES[cfg_voice.lower()]

    # 2. 如果已经是完整音色名（如 zf_xiaobei），直接返回
    if cfg_voice.startswith(("af_", "am_", "bf_", "bm_", "jf_", "jm_", "zf_", "zm_")):
        return cfg_voice

    # 3. 兜底
    return DEFAULT_VOICES["female"]


def _lang_code(voice: str) -> str:
    """从音色名推断语言代码"""
    prefix = voice[:2]
    return _LANG_MAP.get(prefix, "a")


# ── TTS 服务类 ────────────────────────────────────────────


class TTSService:
    """Kokoro-TTS 语音合成服务"""

    def __init__(self, config: dict | None = None):
        """
        初始化 TTS 服务。

        Args:
            config: 配置字典，不传则从 config.yaml 加载
        """
        if config is None:
            config = load_config().get("tts", {})

        self.enabled = config.get("enabled", True)
        self.provider = config.get("provider", "kokoro")
        self.speed = config.get("speed", 1.0)
        self.sample_rate = config.get("sample_rate", 24000)
        self.silence_sec = config.get("silence_sec", 0.3)
        self.device = config.get("device", "auto")

        # 解析音色
        voice_cfg = config.get("voice", "female")
        self.voice_name = _voice_name(voice_cfg)
        self.lang_code = _lang_code(self.voice_name)

        # 懒加载：首次使用时才初始化 pipeline
        self._pipeline = None

    @property
    def pipeline(self):
        """获取或初始化 KPipeline（懒加载）"""
        if self._pipeline is None:
            if not self.enabled:
                raise RuntimeError("TTS 未启用（tts.enabled = false）")
            from kokoro import KPipeline
            _device = None if self.device == "auto" else self.device
            self._pipeline = KPipeline(lang_code=self.lang_code, device=_device)
        return self._pipeline

    def set_voice(self, voice: str):
        """动态切换音色"""
        self.voice_name = _voice_name(voice)
        self.lang_code = _lang_code(self.voice_name)
        # 语言改变时需要重建 pipeline
        self._pipeline = None

    def synthesize(self, text: str, voice: str | None = None) -> tuple[np.ndarray, int]:
        """
        将文本合成为音频。

        Args:
            text: 待朗读文本
            voice: 可选，覆盖当前音色

        Returns:
            (audio_array, sample_rate)
            audio_array 为 np.float32 数组
        """
        if voice:
            self.set_voice(voice)

        # 拆句
        sentences = split_sentences(text)

        # 逐句生成
        all_audio = []
        for sentence in sentences:
            for _, _, audio in self.pipeline(sentence, voice=self.voice_name, speed=self.speed):
                all_audio.append(audio)
            # 句间加静音
            silence = np.zeros(int(self.sample_rate * self.silence_sec), dtype=np.float32)
            all_audio.append(silence)

        if not all_audio:
            return np.array([], dtype=np.float32), self.sample_rate

        return np.concatenate(all_audio), self.sample_rate

    def synthesize_stream(self, text: str, voice: str | None = None
                          ) -> Generator[np.ndarray, None, None]:
        """流式合成：逐句生成并 yield 音频块，边合成边播放。

        Args:
            text: 待朗读文本
            voice: 可选，覆盖当前音色

        Yields:
            每句合成音频 + 句间静音的 np.float32 数组
        """
        if voice:
            self.set_voice(voice)
        sentences = split_sentences(text)
        for sentence in sentences:
            for _, _, audio in self.pipeline(
                sentence, voice=self.voice_name, speed=self.speed
            ):
                yield audio
            yield np.zeros(int(self.sample_rate * self.silence_sec), dtype=np.float32)

    def synthesize_to_file(self, text: str, output_path: str | Path,
                           voice: str | None = None) -> str:
        """
        合成音频并保存到文件。

        Args:
            text: 待朗读文本
            output_path: 输出文件路径（支持 wav 格式）
            voice: 可选，覆盖当前音色

        Returns:
            输出文件路径
        """
        audio, sr = self.synthesize(text, voice=voice)
        sf.write(str(output_path), audio, sr)
        return str(output_path)

    def close(self):
        """释放资源"""
        self._pipeline = None

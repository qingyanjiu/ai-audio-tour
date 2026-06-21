import importlib
import sys as _sys

# ── 懒加载：按需导入 ──

_LAZY_MODULES = {
    "load_config": ".config_loader",
    "get_llm_config": ".config_loader",
    "get_server_config": ".config_loader",
    "get_image_config": ".config_loader",
    "get_screenshot_config": ".config_loader",
    "normalize_to_data_uri": ".image_processor",
    "save_upload": ".image_processor",
    "describe_page_with_image": ".llm_client",
    "capture_page": ".screenshotter",
    "capture_and_save": ".screenshotter",
    "TTSService": ".tts_service",
    "split_sentences": ".tts_service",
}


def __getattr__(name):
    if name in _LAZY_MODULES:
        module = importlib.import_module(_LAZY_MODULES[name], package=__package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(_LAZY_MODULES.keys())

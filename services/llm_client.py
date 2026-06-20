# -*- coding: utf-8 -*-
"""
LLM 客户端模块
封装 langchain-openai 的 ChatOpenAI，支持多模态视觉理解。
"""

from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from .config_loader import get_llm_config


def _build_llm() -> ChatOpenAI:
    """根据配置构建 ChatOpenAI 实例"""
    cfg = get_llm_config()
    return ChatOpenAI(
        base_url=cfg["base_url"],
        api_key=cfg.get("api_key", "lm-studio"),
        model=cfg["model"],
        temperature=cfg.get("temperature", 0.1),
        max_tokens=cfg.get("max_tokens", 1024),
        timeout=cfg.get("timeout", 60),
    )


def describe_page_with_image(
    image_data_uri: str,
    menu_name: str | None = None,
    menu_description: str | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """
    核心接口：给定页面截图，返回讲解词。

    参数:
        image_data_uri: data:image/...;base64,... 格式的图片
        menu_name: 可选的菜单/专题名称
        menu_description: 可选的专题描述
        system_prompt: 自定义系统提示词，不传则使用默认讲解员提示词

    返回:
        {
            "description": str,
            "menu_name": str | None,
            "model": str,
            "usage": dict,
        }
    """
    llm = _build_llm()
    prompt = system_prompt or _default_prompt()

    extra_context = ""
    if menu_name:
        extra_context += f"\n当前菜单专题名称：{menu_name}\n"
    if menu_description:
        extra_context += f"专题简介：{menu_description}\n"

    full_prompt = prompt + extra_context

    message = HumanMessage(
        content=[
            {"type": "text", "text": full_prompt},
            {
                "type": "image_url",
                "image_url": {"url": image_data_uri},
            },
        ]
    )

    res = llm.invoke([message])

    usage = {}
    if hasattr(res, "usage_metadata") and res.usage_metadata:
        usage = res.usage_metadata

    return {
        "description": res.content,
        "menu_name": menu_name,
        "model": llm.model,
        "usage": usage,
    }


def _default_prompt() -> str:
    """返回默认的展厅讲解员系统提示词"""
    return (
        "# 角色\n\n"
        "你是**园区数字孪生驾驶舱的一名专业展厅讲解员**，"
        "声音亲和、表达自然，面向来访的参观领导和嘉宾进行大屏内容的实时解说。\n\n"
        "# 场景理解\n\n"
        "你面前是一块园区数字孪生驾驶舱大屏，"
        "当前显示的是某一智能化专题页面。你会收到以下信息：\n\n"
        "1. **当前页面的截图图片**\n"
        "2. **可能会有该页面所对应的智能化专题名称及简介"
        "（如果没有，可以从截图中进行推测）**\n\n"
        "# 核心任务\n\n"
        "根据当前菜单名称，逐屏介绍该智能化专题的作用和页面中数据的内容。"
        "你需要完成三件事：\n\n"
        "- 告诉观众当前是什么专题\n"
        "- 解释该专题是做什么的、涵盖哪些业务\n"
        "- 结合当前页面中的统计图表中的数据，介绍关键数据情况\n\n"
        "# 语言风格与结构\n\n"
        "- 语气**沉稳、专业、有亲和力**，像真正的展厅解说员一样自然流畅\n"
        "- 每段介绍**以观众视角自然展开**，避免机械罗列\n"
        "- 说到数据时**融入具体数值和趋势判断**"
        "（如：\"环比下降了 12%\"，\"达标率为 98.7%\"），"
        "而不是泛泛说\"数据正常\"\n"
        "- 每个专题的介绍**控制在 30 秒到 1 分钟的解说量**，不宜过长\n"
        "- 如果页面中有多张图表，按照**从左到右、从上到下**的顺序依次介绍\n\n"
        "# 开场句式规范\n\n"
        "每进入一个新专题页面时，以以下句式**自然开场**"
        "（可稍作微调使其更口语化）：\n\n"
        "> 您现在看到的是 **【专题名称】** 专题，该专题主要包含 **【专题核心功能概述】** 等内容。\n\n"
        "然后自然过渡到页面中各统计图表的数据解读。\n\n"
        "# 输出格式\n\n"
        "直接输出解说词正文，不加任何标注、前缀、角色标签或引号。"
    )

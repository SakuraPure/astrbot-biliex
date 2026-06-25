"""AI 总结服务。

定义 :class:`Summarizer` 协议，便于未来替换为其它后端（如本地模型 / 第三方接口）。
默认实现 :class:`LLMSummarizer` 走 AstrBot 配置的 LLM Provider（``text_chat``）。
总结依据为视频**标题**列表（按需求），不抓取视频正文，轻量且稳定。
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol

from ..config import PluginConfig
from ..errors import LlmUnavailableError
from ..models import VideoInfo

ProviderResolver = Callable[[str], Awaitable[Any]]


class Summarizer(Protocol):
    """总结后端协议。"""

    async def summarize(self, videos: list[VideoInfo], umo: str) -> str: ...


class LLMSummarizer:
    """默认总结后端：调用 AstrBot LLM Provider。"""

    def __init__(self, config: PluginConfig, provider_resolver: ProviderResolver) -> None:
        self._config = config
        self._resolve = provider_resolver

    def _build_prompt(self, videos: list[VideoInfo]) -> str:
        max_n = self._config.summary_max_videos
        items = videos[:max_n]
        lines = [f"{i}. {v.title}" for i, v in enumerate(items, 1)]
        return (
            "以下是一位 B 站 UP 主近期投稿视频的标题列表：\n"
            + "\n".join(lines)
            + "\n\n请基于这些标题，用中文归纳这位 UP 主近期创作内容的主题与方向，"
            "提炼 3~5 个要点，并简要给出内容概览。不要逐条罗列标题。"
        )

    async def summarize(self, videos: list[VideoInfo], umo: str) -> str:
        if not videos:
            return "暂无视频可总结。"
        provider = await self._resolve(umo)
        if provider is None:
            raise LlmUnavailableError(
                "未配置可用的 LLM Provider，无法进行 AI 总结。请在 AstrBot WebUI 的「配置 → AI」中接入大模型后再试。"
            )
        prompt = self._build_prompt(videos)
        system_prompt = (
            f"你是一名善于归纳总结的内容分析助手，请用{self._config.summary_language}输出简洁有条理的总结。"
        )
        resp = await provider.text_chat(prompt=prompt, system_prompt=system_prompt)
        # LLMResponse 对象：取文本内容（兼容 .completion / .content / 直接 str）
        return _extract_text(resp)


def _extract_text(resp: Any) -> str:
    """从 LLMResponse 中兼容地取文本。"""
    if resp is None:
        return ""
    for attr in ("completion_text", "completion", "content", "text"):
        val = getattr(resp, attr, None)
        if val:
            return str(val)
    # 某些实现直接返回字符串
    if isinstance(resp, str):
        return resp
    return str(resp)

"""消息渲染：把归一化模型渲染为 AstrBot 消息。

提供两种出口：
- ``MessageChain``（主动推送路径，经 ``context.send_message`` 发送）；
- 组件列表 / 纯文本（指令回复路径，经 ``event.make_result().chain`` 或 ``event.plain_result`` 回复）。

这是「模型 → 平台消息」的接缝点；改推送样式或适配其它平台消息段，集中改本文件。
"""

from __future__ import annotations

from typing import Any

from .models import VideoInfo


def _new_chain():
    """延迟导入并构造一个空 MessageChain。"""
    from astrbot.api.event import MessageChain

    return MessageChain()


def video_components(video: VideoInfo, include_cover: bool = True) -> list[Any]:
    """构造单条视频的消息组件列表：[Plain(标题+链接), Image(封面)?]。

    供指令回复路径用（``event.make_result().chain = ...``）。
    """
    import astrbot.api.message_components as Comp

    comps: list[Any] = [Comp.Plain(text=f"🎬 {video.title}\n🔗 {video.url}")]
    if include_cover and video.cover:
        comps.append(Comp.Image(file=video.cover))
    return comps


def build_text_chain(text: str):
    """构造纯文本 MessageChain。"""
    chain = _new_chain()
    chain.message(text)
    return chain


def build_video_chain(video: VideoInfo, include_cover: bool = True):
    """构造单条视频的 MessageChain（标题+链接+封面）。"""
    chain = _new_chain()
    chain.message(f"🎬 {video.title}\n🔗 {video.url}")
    if include_cover and video.cover:
        try:
            chain.image(video.cover)
        except AttributeError:
            # 兜底：极旧版本 MessageChain 无 .image()，直接追加组件
            chain.chain.extend(video_components(video, include_cover)[1:])  # type: ignore[attr-defined]
    return chain


def videos_list_text(videos: list[VideoInfo], header: str = "") -> str:
    """把视频列表渲染为纯文本（供 plain_result 回复）。"""
    if not videos:
        return f"{header}暂无视频。".strip()
    lines = [header] if header else []
    for idx, v in enumerate(videos, 1):
        lines.append(f"{idx}. {v.title}\n   {v.url}")
    return "\n".join(lines)

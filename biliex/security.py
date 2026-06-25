"""安全：撤回含 Cookie 的消息以防泄露。

仅 aiocqhttp（OneBot v11）支持撤回；其它平台静默跳过。
通过 ``event.bot.api.call_action('delete_msg', message_id=...)`` 调用协议端 API。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent  # noqa: F401


async def recall_message(event: "Any", message_id: str | int | None) -> bool:
    """撤回指定消息。成功或平台不支持都返回 bool，绝不抛异常。

    :param event: AstrMessageEvent
    :param message_id: 要撤回的消息 id
    :return: 是否实际撤回成功
    """
    if not message_id:
        return False
    try:
        platform = event.get_platform_name()
    except Exception:
        platform = ""
    if platform != "aiocqhttp":
        return False
    try:
        client = event.bot  # aiocqhttp 适配器暴露的 OneBot 客户端
        await client.api.call_action("delete_msg", message_id=message_id)
        return True
    except Exception:
        # 撤回失败（无权限 / 消息过旧 / 协议端不支持）不阻断流程
        return False

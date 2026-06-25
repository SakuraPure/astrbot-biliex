"""astrbot_plugin_biliex — 哔哩哔哩账户绑定与视频推送插件。

分层结构：
- ``biliex.bili``      : bilibili-api 隔离层（唯一触碰 ``bilibili_api`` 的地方）。
- ``biliex.services``  : 业务服务（订阅 / 视频 / 推送 / 总结）。
- ``biliex.storage``   : 基于 AstrBot KV 的持久化。
- ``biliex.scheduler`` : 后台定时推送循环。
- ``biliex.messaging`` / ``biliex.security`` : 消息渲染与安全（撤回凭据消息）。
- ``biliex.config`` / ``biliex.models`` / ``biliex.errors`` : 配置、归一化模型、错误层级。

对外只暴露插件入口 ``main.py`` 中的 ``BiliExPlugin``。
"""

__version__ = "0.1.0"

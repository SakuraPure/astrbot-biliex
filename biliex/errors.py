"""插件错误层级。

handler 统一捕获 :class:`BiliExError` 并转换为友好的纯文本回复；
未预期异常交由上层兜底并记日志，避免单个错误导致插件崩溃。
"""

from __future__ import annotations


class BiliExError(Exception):
    """所有插件业务错误的基类。message 即面向用户的提示。"""


class ConfigError(BiliExError):
    """配置非法或缺失。"""


class CredentialError(BiliExError):
    """Cookie 解析失败或凭据无效。"""


class BindError(BiliExError):
    """绑定流程失败（如凭据无法验证、账号已绑定等）。"""


class NoActiveBindingError(BiliExError):
    """当前没有可用的「激活绑定」。"""


class BindingNotFoundError(BiliExError):
    """按标识找不到对应绑定。"""


class ApiError(BiliExError):
    """调用 bilibili 接口失败（网络、风控、返回异常等）。"""


class LlmUnavailableError(BiliExError):
    """未配置可用的 LLM Provider，无法执行 AI 总结。"""

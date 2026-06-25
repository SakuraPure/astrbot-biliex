"""bilibili-api 封装层（插件内**唯一** import ``bilibili_api`` 的地方）。

对外只返回归一化模型 :class:`UserInfo` / :class:`VideoInfo`，并统一把底层异常
转换为 :class:`ApiError` / :class:`CredentialError`，使业务层无需感知库细节。

若 ``bilibili-api`` 库签名变更，仅需调整本文件对应方法。
"""

from __future__ import annotations

import asyncio
from typing import Any

from ..errors import ApiError, CredentialError
from ..models import CredentialInfo, UserInfo, VideoInfo
from . import parser

# 延迟导入 bilibili_api：仅在真正调用时加载，且若库未安装也能让插件加载阶段不崩
# （指令调用时会给出清晰报错，而非插件整体加载失败）。
def _import_bili():
    try:
        from bilibili_api import user as bili_user  # noqa: F401
        from bilibili_api import Credential  # noqa: F401
        return bili_user, Credential
    except ImportError as e:  # pragma: no cover - 依赖缺失场景
        raise ApiError(
            "未安装 bilibili-api 依赖，请在插件目录执行 pip install bilibili-api-python，或在 AstrBot 中重装本插件以自动安装依赖。"
        ) from e


class BilibiliClient:
    """对 bilibili-api 的薄封装，返回归一化模型。"""

    def __init__(self, timeout: int = 15, proxy: str = "") -> None:
        self._timeout = max(3, timeout)
        self._proxy = proxy.strip()

    # --- 凭据构建 ---
    def _build_credential(self, cred: CredentialInfo) -> Any:
        _, Credential = _import_bili()
        try:
            return Credential(
                sessdata=cred.sessdata or None,
                bili_jct=cred.bili_jct or None,
                buvid3=cred.buvid3 or None,
                dedeuserid=cred.dedeuserid or None,
            )
        except Exception as e:
            raise CredentialError(f"凭据构建失败：{e}") from e

    async def _call(self, coro):
        """带超时与异常归一化的协程执行器。"""
        try:
            return await asyncio.wait_for(coro, timeout=self._timeout)
        except asyncio.TimeoutError:
            raise ApiError(f"调用 B 站接口超时（{self._timeout}s）")
        except Exception as e:
            # bilibili_api 的业务异常通常是 ResponseCodeException / NetworkError 等，
            # 这里统一归类，凭据类错误（-101 / 未登录）单独识别。
            msg = str(e)
            if any(k in msg for k in ("登录", "未登录", "-101", " credential", "Credential", "SESSDATA")):
                raise CredentialError(f"凭据无效或已失效：{msg}") from e
            raise ApiError(f"调用 B 站接口失败：{msg}") from e

    # --- 对外能力 ---
    async def get_self_account(self, cred: CredentialInfo) -> UserInfo:
        """用凭据反查自身账号信息（uid + 名称）。

        优先用 ``user.get_self_info``；若签名不符或失败，回退到「从 Cookie 取 DedeUserID
        → User.get_user_info」。两条路都不行则报 :class:`CredentialError`。
        """
        bili_user, _ = _import_bili()
        credential = self._build_credential(cred)

        # 路径 1：get_self_info
        try:
            data = await self._call(self._safe_call(bili_user.get_self_info, credential=credential))
            info = parser.parse_user_info(data)
            if info.uid:
                return info
        except CredentialError:
            raise
        except Exception:
            pass  # 回退到路径 2

        # 路径 2：DedeUserID + User.get_user_info
        if cred.dedeuserid:
            try:
                u = bili_user.User(uid=int(cred.dedeuserid), credential=credential)
                data = await self._call(u.get_user_info())
                info = parser.parse_user_info(data)
                if info.uid:
                    return info
            except CredentialError:
                raise
            except Exception:
                pass

        raise CredentialError("凭据无效或无法获取账号信息，请检查 Cookie 是否完整且未失效。")

    async def get_videos(self, uid: str, cred: CredentialInfo, count: int = 10) -> list[VideoInfo]:
        """获取指定 uid 的主页投稿视频（最新 count 条，按发布时间倒序）。"""
        if not uid:
            raise ApiError("uid 为空，无法获取视频")
        bili_user, _ = _import_bili()
        credential = self._build_credential(cred) if not cred.is_empty() else None
        try:
            u = bili_user.User(uid=int(uid), credential=credential)
            data = await self._call(u.get_videos(pn=1, ps=max(1, min(50, count))))
        except (CredentialError, ApiError):
            raise
        return parser.parse_video_list(data, owner_uid=uid)

    async def _safe_call(self, fn, **kwargs):
        """兼容 get_self_info 可能的两种签名：``get_self_info()`` 或 ``get_self_info(credential=...)``。"""
        import inspect

        sig = inspect.signature(fn)
        if "credential" in sig.parameters:
            return await fn(credential=kwargs.get("credential"))
        # 不接受 credential 参数时，靠全局/环境凭据；这里尽力调用
        try:
            return await fn()
        except TypeError:
            return await fn(kwargs.get("credential"))

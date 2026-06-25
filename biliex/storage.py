"""基于 AstrBot KV 的持久化存储。

绑定/归属者数据落到 AstrBot 的 per-plugin KV 存储（自动位于 ``data/`` 目录，
插件更新/重装不丢失）。为可测试性与解耦，存储层通过注入的 ``KvBackend`` 抽象访问 KV，
``main.py`` 负责把 Star 实例的 ``put_kv_data`` 等方法适配为该接口。

数据键设计：
- ``owner:<owner_key>``  → Owner（dict）
- ``binding:<binding_id>`` → Binding（dict）
- ``index:bindings``     → [binding_id, ...]（供调度器枚举所有绑定）
"""

from __future__ import annotations

from typing import Any, Protocol

from .models import Binding, Owner


class KvBackend(Protocol):
    """KV 后端抽象（Star 实例适配后注入）。"""

    async def get(self, key: str, default: Any = None) -> Any: ...
    async def put(self, key: str, value: Any) -> None: ...
    async def delete(self, key: str) -> None: ...


_KEY_OWNER = "owner:{owner_key}"
_KEY_BINDING = "binding:{binding_id}"
_KEY_INDEX = "index:bindings"


class Storage:
    def __init__(self, kv: KvBackend) -> None:
        self._kv = kv

    # --- Owner ---
    async def get_owner(self, owner_key: str) -> Owner | None:
        data = await self._kv.get(_KEY_OWNER.format(owner_key=owner_key))
        return Owner.from_dict(data) if isinstance(data, dict) else None

    async def upsert_owner(self, owner: Owner) -> None:
        await self._kv.put(_KEY_OWNER.format(owner_key=owner.owner_key), owner.to_dict())

    async def delete_owner(self, owner_key: str) -> None:
        await self._kv.delete(_KEY_OWNER.format(owner_key=owner_key))

    # --- Binding ---
    async def get_binding(self, binding_id: str) -> Binding | None:
        data = await self._kv.get(_KEY_BINDING.format(binding_id=binding_id))
        return Binding.from_dict(data) if isinstance(data, dict) else None

    async def upsert_binding(self, binding: Binding) -> None:
        await self._kv.put(_KEY_BINDING.format(binding_id=binding.binding_id), binding.to_dict())

    async def delete_binding(self, binding_id: str) -> None:
        await self._kv.delete(_KEY_BINDING.format(binding_id=binding_id))

    # --- 索引（binding 列表，供调度器枚举）---
    async def _get_index(self) -> list[str]:
        data = await self._kv.get(_KEY_INDEX, [])
        return list(data) if isinstance(data, list) else []

    async def _set_index(self, ids: list[str]) -> None:
        await self._kv.put(_KEY_INDEX, ids)

    async def add_to_index(self, binding_id: str) -> None:
        ids = await self._get_index()
        if binding_id not in ids:
            ids.append(binding_id)
            await self._set_index(ids)

    async def remove_from_index(self, binding_id: str) -> None:
        ids = await self._get_index()
        if binding_id in ids:
            ids.remove(binding_id)
            await self._set_index(ids)

    # --- 组合操作 ---
    async def list_bindings_for_owner(self, owner_key: str) -> list[Binding]:
        owner = await self.get_owner(owner_key)
        if not owner:
            return []
        results: list[Binding] = []
        for bid in owner.binding_ids:
            b = await self.get_binding(bid)
            if b:
                results.append(b)
        return results

    async def iter_all_bindings(self) -> list[Binding]:
        """枚举所有绑定（调度器用）。已自动剔除索引中存在但记录丢失的脏数据。"""
        ids = await self._get_index()
        results: list[Binding] = []
        stale: list[str] = []
        for bid in ids:
            b = await self.get_binding(bid)
            if b:
                results.append(b)
            else:
                stale.append(bid)
        if stale:
            ids = [i for i in ids if i not in stale]
            await self._set_index(ids)
        return results

    async def save_new_binding(self, owner: Owner, binding: Binding) -> None:
        """原子地保存绑定、更新归属者、维护索引。"""
        if binding.binding_id not in owner.binding_ids:
            owner.binding_ids.append(binding.binding_id)
        if not owner.active_binding_id:
            owner.active_binding_id = binding.binding_id
        await self.upsert_binding(binding)
        await self.upsert_owner(owner)
        await self.add_to_index(binding.binding_id)

    async def remove_binding(self, owner: Owner, binding_id: str) -> None:
        """删除绑定、更新归属者激活态与索引。返回更新后的 owner（已持久化）。"""
        if binding_id in owner.binding_ids:
            owner.binding_ids.remove(binding_id)
        if owner.active_binding_id == binding_id:
            # 激活绑定被删，回退到第一个，或置空
            owner.active_binding_id = owner.binding_ids[0] if owner.binding_ids else ""
        await self.delete_binding(binding_id)
        await self.remove_from_index(binding_id)
        if owner.binding_ids:
            await self.upsert_owner(owner)
        else:
            # 没有绑定了，顺带清掉 owner 记录
            await self.delete_owner(owner.owner_key)

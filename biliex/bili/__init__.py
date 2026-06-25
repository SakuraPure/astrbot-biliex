"""bilibili-api 隔离层。

本子包是插件中**唯一**引用 ``bilibili_api`` 的地方：
- :mod:`biliex.bili.client`  封装库调用，返回归一化模型；
- :mod:`biliex.bili.parser`  把原始返回 dict 防御式地映射为模型；
- :mod:`biliex.bili.credential` 解析 Cookie 字符串为凭据。

B 站接口字段或 ``bilibili-api`` 库签名变更时，通常只需改动本子包，业务层不受影响。
"""

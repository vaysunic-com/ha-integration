"""云端网关的异步 HTTP 客户端。

只做两件事：取电站/设备清单(/stations)、拉实时数据(/devices)。
网关响应统一 {"code":200,"data":...}；401 抛 InvalidAuth，其余网络/解析错误抛 CannotConnect。
"""
from __future__ import annotations

import logging

import aiohttp

from .const import CODE_UNAUTHORIZED, HEADER_TOKEN

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """无法连接网关/响应异常。"""


class InvalidAuth(Exception):
    """令牌无效或已禁用(401)。"""


class VaysunicApiClient:
    """极简只读客户端。"""

    def __init__(self, session: aiohttp.ClientSession, host: str, token: str) -> None:
        # 去掉末尾斜杠，避免拼出 //stations
        self._base = host.rstrip("/")
        self._token = token
        self._session = session

    async def _get(self, path: str) -> list | dict:
        """GET {base}{path}，带令牌头，解析 {code,data}。"""
        url = f"{self._base}{path}"
        headers = {HEADER_TOKEN: self._token}
        try:
            async with self._session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == CODE_UNAUTHORIZED:
                    raise InvalidAuth
                body = await resp.json(content_type=None)
        except InvalidAuth:
            raise
        except aiohttp.ClientError as err:
            raise CannotConnect(f"Request to {url} failed: {err}") from err
        except Exception as err:  # noqa: BLE001  解析等其它异常统一归为连接失败
            raise CannotConnect(f"Could not parse the response from {url}: {err}") from err

        code = body.get("code")
        if code == CODE_UNAUTHORIZED:
            raise InvalidAuth
        if code is not None and code != 200:
            raise CannotConnect(f"{url} returned code={code} msg={body.get('msg')}")
        return body.get("data") or []

    async def async_get_stations(self) -> list:
        """电站 + 设备清单。"""
        data = await self._get("/stations")
        return data if isinstance(data, list) else []

    async def async_get_devices(self) -> list:
        """全部可见设备实时数据(points)。"""
        data = await self._get("/devices")
        return data if isinstance(data, list) else []

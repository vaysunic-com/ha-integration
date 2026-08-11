"""DataUpdateCoordinator：定时轮询，聚合 stations(元信息) + devices(实时值)。

data 结构:
{
  "device_meta": { sn: {name, model, type, station_id, station_name} },   # 来自 /stations
  "devices":     { sn: {online, points:[...]} },                          # 来自 /devices
}
sensor 平台据此发现实体并刷 state。

两个接口刷新频率不同:
  /devices   每 UPDATE_INTERVAL(2 分钟)  —— 设备约 3 分钟上报一次
  /stations  每 STATIONS_INTERVAL(10 分钟) —— 清单几个月才变一次, 缓存复用
所以稳态下每轮只打 1 个请求, 只有每 5 轮才多打一个。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, VaysunicApiClient
from .const import (
    CONF_HOST,
    CONF_TOKEN,
    DOMAIN,
    STATIONS_INTERVAL,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class VaysunicCoordinator(DataUpdateCoordinator):
    """协调器。"""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        session = async_get_clientsession(hass)
        self.client = VaysunicApiClient(
            session, entry.data[CONF_HOST], entry.data[CONF_TOKEN]
        )
        # 电站/设备清单单独降频, 这里缓存上一次的结果与取回时间
        self._device_meta: dict[str, dict] = {}
        self._meta_fetched_at: datetime | None = None

    def _meta_is_stale(self) -> bool:
        """清单是否该重新拉了(首次、或超过 STATIONS_INTERVAL)。"""
        if self._meta_fetched_at is None:
            return True
        return datetime.now(timezone.utc) - self._meta_fetched_at >= STATIONS_INTERVAL

    async def _async_update_data(self) -> dict:
        try:
            # 清单几个月才变一次, 不跟实时数据同频; 未到期就复用上一次的结果
            if self._meta_is_stale():
                self._device_meta = self._build_meta(
                    await self.client.async_get_stations()
                )
                self._meta_fetched_at = datetime.now(timezone.utc)
            devices = await self.client.async_get_devices()
        except InvalidAuth as err:
            # 触发 HA 重新认证(令牌被禁用/失效)
            raise ConfigEntryAuthFailed("The access token is invalid or has been disabled") from err
        except CannotConnect as err:
            raise UpdateFailed(str(err)) from err

        device_rt: dict[str, dict] = {}
        for d in devices:
            sn = d.get("sn")
            if sn:
                device_rt[sn] = d

        return {"device_meta": self._device_meta, "devices": device_rt}

    @staticmethod
    def _build_meta(stations: list[dict]) -> dict[str, dict]:
        """把 /stations 的嵌套结构摊平成 sn → 元信息。"""
        device_meta: dict[str, dict] = {}
        for st in stations:
            station_id = st.get("stationId")
            station_name = st.get("stationName")
            for d in st.get("devices", []):
                sn = d.get("sn")
                if not sn:
                    continue
                device_meta[sn] = {
                    "name": d.get("name") or sn,
                    "model": d.get("model"),
                    "type": d.get("type"),
                    "station_id": station_id,
                    "station_name": station_name,
                }
        return device_meta

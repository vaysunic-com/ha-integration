"""传感器平台：每个设备的每个数值测点 → 一个 sensor。

动态发现：首刷建实体，之后协调器每次更新若出现新 sn/测点则追加。
"""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VaysunicCoordinator
from .entity import build_device_info, normalize_unit

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VaysunicCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _discover() -> None:
        new: list[VaysunicSensor] = []
        devices = (coordinator.data or {}).get("devices", {})
        for sn, dev in devices.items():
            for point in dev.get("points", []):
                key = point.get("key")
                if key is None:
                    continue
                # 只为数值测点建 sensor(非数值点位无 HA 展示价值)
                if not isinstance(point.get("value"), (int, float)):
                    continue
                uid = f"{sn}-{key}"
                if uid in known:
                    continue
                known.add(uid)
                new.append(VaysunicSensor(coordinator, sn, key))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


# 归入「诊断」类的测点。
#
# 这些是设备自身的工况与铭牌参数, 不是用户日常关心的发电数据。标成 DIAGNOSTIC 后, HA 会
# 把它们折叠进设备页单独的「诊断」区, 不与发电量/功率混在一起, 也不会被自动加进仪表板。
# 实体本身照常工作, 历史、自动化、模板都不受影响。
#
# ⚠️ entity_category 写在实体注册表里, **只在实体首次注册时生效** —— 发布后再调整
# 对已装用户不追溯。所以这个集合必须在正式发布前定好。
_DIAGNOSTIC_KEYS = frozenset({
    "rssi",         # 信号强度
    "temp",         # 机内温度
    "freq",         # 电网频率
    "rate power",   # 额定功率(铭牌参数, 恒定; dataflag 本身带空格)
})


class VaysunicSensor(CoordinatorEntity[VaysunicCoordinator], SensorEntity):
    """单个测点传感器。"""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VaysunicCoordinator, sn: str, key: str) -> None:
        super().__init__(coordinator)
        self._sn = sn
        self._key = key
        self._attr_unique_id = f"{sn}-{key}"
        self._attr_name = key
        self._attr_device_info = build_device_info(coordinator, sn)
        if key in _DIAGNOSTIC_KEYS:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _point(self) -> dict | None:
        """从最新快照取本测点。"""
        dev = (self.coordinator.data or {}).get("devices", {}).get(self._sn)
        if not dev:
            return None
        for p in dev.get("points", []):
            if p.get("key") == self._key:
                return p
        return None

    @property
    def available(self) -> bool:
        # last_update_success 不能省: 只看设备的 online 标志的话, 网关不可达或令牌被撤时
        # 协调器停止刷新, 实体却仍是 available, 永远停在最后一次拉到的读数上 ——
        # 用户看到的是一个"活着的"数字, 实际上早就断了(实测停更 10 分钟仍显示 16.0 W)。
        if not self.coordinator.last_update_success:
            return False
        dev = (self.coordinator.data or {}).get("devices", {}).get(self._sn)
        return bool(dev and dev.get("online"))

    @property
    def native_value(self):
        p = self._point()
        return p.get("value") if p else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        p = self._point()
        return normalize_unit(p.get("unit")) if p else None

    @property
    def device_class(self) -> SensorDeviceClass | None:
        p = self._point()
        raw = p.get("deviceClass") if p else None
        if not raw:
            return None
        try:
            return SensorDeviceClass(raw)
        except ValueError:
            return None

    @property
    def state_class(self) -> SensorStateClass | None:
        p = self._point()
        raw = p.get("stateClass") if p else None
        if not raw:
            return None
        try:
            return SensorStateClass(raw)
        except ValueError:
            return None

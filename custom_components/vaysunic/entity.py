"""实体公共部分：设备信息 + 单位/device_class 规范化。"""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import VaysunicCoordinator

# 网关返回的单位 → HA 合法单位(device_class 对单位有强校验，不匹配会告警)
_UNIT_MAP = {
    "℃": "°C",
    "°c": "°C",
    "kwh": "kWh",
    "wh": "Wh",
    "var": "var",   # 无功，HA 要小写 var
    "va": "VA",
    "dbm": "dBm",
}


def normalize_unit(unit: str | None) -> str | None:
    """把网关返回的单位对齐到 HA 认可的写法。"""
    if not unit:
        return None
    return _UNIT_MAP.get(unit.strip().lower(), unit.strip())


def build_device_info(coordinator: VaysunicCoordinator, sn: str) -> DeviceInfo:
    """按 sn 归组设备(HA 设备卡)，附电站名与型号。

    **name 用 sn 而不是平台上的设备名** —— HA 拿设备名去拼 entity_id
    (has_entity_name=True 时格式为 区域_设备_测点), 而平台上的设备名是用户
    自己起的、**不保证唯一**: 实测同一账号下三台微逆都叫 "VMP2", HA 只能
    生成 ..._vmp2_energy 和 ..._vmp2_energy_2 靠后缀区分, 用户在能源面板
    下拉框里根本认不出哪个对应哪台。sn 全局唯一且不随改名而变。

    想要好认的名字, 用户可以在 HA 里直接改设备名 —— HA 把它存成
    name_by_user, **不会**牵动已生成的 entity_id, 这正是 HA 的设计意图。
    """
    meta = (coordinator.data or {}).get("device_meta", {}).get(sn, {})
    return DeviceInfo(
        identifiers={(DOMAIN, sn)},
        name=sn,
        model=meta.get("model"),
        manufacturer="VAYSUNIC",
        serial_number=sn,
        suggested_area=meta.get("station_name"),
    )

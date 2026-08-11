"""配置流程：用户填 网关地址 + 令牌，校验后建条目。"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, VaysunicApiClient
from .const import CONF_HOST, CONF_TOKEN, DEFAULT_HOST, DOMAIN


class VaysunicConfigFlow(ConfigFlow, domain=DOMAIN):
    """填 token 的单步配置流程 + 令牌失效重新认证。"""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            token = user_input[CONF_TOKEN].strip()
            session = async_get_clientsession(self.hass)
            client = VaysunicApiClient(session, host, token)
            try:
                # 用 /stations 试连校验令牌
                await client.async_get_stations()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                # 同一令牌只允许配一次
                await self.async_set_unique_id(token)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="VAYSUNIC Solar",
                    data={CONF_HOST: host, CONF_TOKEN: token},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_TOKEN): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """令牌失效(被禁用)后由 coordinator 触发，进入重填令牌。"""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """校验新令牌并原地更新条目(网关地址沿用旧值)。"""
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if user_input is not None and entry is not None:
            host = entry.data[CONF_HOST]
            token = user_input[CONF_TOKEN].strip()
            session = async_get_clientsession(self.hass)
            client = VaysunicApiClient(session, host, token)
            try:
                await client.async_get_stations()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_TOKEN: token}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

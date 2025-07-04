from __future__ import annotations

"""
    * SPDX-FileCopyrightText: Copyright 2024 LG Electronics Inc.
    * SPDX-License-Identifier: Apache-2.0
"""
from typing import Any

from ..thinq_api import ThinQApi
from .connect_device import READABILITY, WRITABILITY, ConnectBaseDevice, ConnectDeviceProfile
from .const import Property, Resource


class WaterHeaterProfile(ConnectDeviceProfile):
    def __init__(self, profile: dict[str, Any]):
        super().__init__(
            profile=profile,
            resource_map={
                "waterHeaterJobMode": Resource.WATER_HEATER_JOB_MODE,
                "operation": Resource.OPERATION,
                "temperatureInUnits": Resource.TEMPERATURE,
            },
            profile_map={
                "waterHeaterJobMode": {"currentJobMode": Property.CURRENT_JOB_MODE},
                "operation": {"waterHeaterOperationMode": Property.WATER_HEATER_OPERATION_MODE},
                "temperatureInUnits": {
                    "currentTemperatureC": Property.CURRENT_TEMPERATURE_C,
                    "currentTemperatureF": Property.CURRENT_TEMPERATURE_F,
                    "targetTemperatureC": Property.TARGET_TEMPERATURE_C,
                    "targetTemperatureF": Property.TARGET_TEMPERATURE_F,
                    "unit": Property.TEMPERATURE_UNIT,
                },
            },
            custom_resources=["temperatureInUnits"],
        )

    def check_attribute_writable(self, prop_attr: Property) -> bool:
        return prop_attr == Property.TEMPERATURE_UNIT or self._get_prop_attr(prop_attr)[WRITABILITY]

    def _get_attribute_payload(self, attribute: Property, value: str | int) -> dict:
        for resource, props in self._PROFILE.items():
            for prop_key, prop_attr in props.items():
                if prop_attr == attribute:
                    return (
                        {resource: {prop_key: value}}
                        if prop_key[-1:] not in ["C", "F"]
                        else {resource: {prop_key[:-1]: value}}
                    )

    def _generate_custom_resource_properties(
        self, resource_key: str, resource_property: dict | list, props: dict[str, str]
    ) -> tuple[list[str], list[str]]:
        # pylint: disable=unused-argument
        readable_props = []
        writable_props = []

        if resource_key not in self._CUSTOM_RESOURCES:
            return readable_props, writable_props

        units = []

        for temperatures in resource_property:
            unit = temperatures["unit"]
            for prop_key, prop_attr in props.items():
                if prop_key[-1:] != unit:
                    continue
                prop = self._get_properties(temperatures, prop_key[:-1])
                if prop[READABILITY]:
                    readable_props.append(str(prop_attr))
                if prop[WRITABILITY]:
                    writable_props.append(str(prop_attr))
                self._set_prop_attr(prop_attr, prop)
            units.append(unit)

        prop_attr = props.get("unit")
        prop = self._get_readonly_enum_property(units)
        if prop[READABILITY]:
            readable_props.append(str(prop_attr))
        if prop[WRITABILITY]:
            writable_props.append(str(prop_attr))
        self._set_prop_attr(prop_attr, prop)

        return readable_props, writable_props


class WaterHeaterDevice(ConnectBaseDevice):
    """WaterHeater Property."""

    def __init__(
        self,
        thinq_api: ThinQApi,
        device_id: str,
        device_type: str,
        model_name: str,
        alias: str,
        reportable: bool,
        profile: dict[str, Any],
    ):
        super().__init__(
            thinq_api=thinq_api,
            device_id=device_id,
            device_type=device_type,
            model_name=model_name,
            alias=alias,
            reportable=reportable,
            profiles=WaterHeaterProfile(profile=profile),
        )

    @property
    def profiles(self) -> WaterHeaterProfile:
        return self._profiles

    def _set_custom_resources(
        self,
        prop_key: str,
        attribute: str,
        resource_status: dict[str, str] | list[dict[str, str]],
        is_updated: bool = False,
    ) -> bool:
        for temperature_status in resource_status:
            unit = temperature_status.get("unit")
            if attribute is Property.TEMPERATURE_UNIT:
                if unit == "C":
                    self._set_status_attr(attribute, unit)
            elif attribute[-1:].upper() == unit:
                temperature_map = self.profiles._PROFILE["temperatureInUnits"]
                _prop_key = None

                if attribute in temperature_map.values():
                    _prop_key = list(temperature_map.keys())[list(temperature_map.values()).index(attribute)]

                if not _prop_key:
                    _attribute_value = None
                elif _prop_key[:-1] not in temperature_status and is_updated:
                    continue
                else:
                    _attribute_value = temperature_status.get(_prop_key[:-1])
                self._set_status_attr(attribute, _attribute_value)
        return True

    async def set_current_job_mode(self, mode: str) -> dict | None:
        return await self.do_enum_attribute_command(Property.CURRENT_JOB_MODE, mode)

    async def _set_target_temperature(self, temperature: int | float, unit: str) -> dict | None:
        property_map = {
            "C": Property.TARGET_TEMPERATURE_C,
            "F": Property.TARGET_TEMPERATURE_F,
        }
        return await self.do_multi_attribute_command(
            {
                property_map[unit]: temperature,
                Property.TEMPERATURE_UNIT: unit,
            }
        )

    async def set_target_temperature_c(self, temperature: int | float) -> dict | None:
        return await self._set_target_temperature(temperature, "C")

    async def set_target_temperature_f(self, temperature: int | float) -> dict | None:
        return await self._set_target_temperature(temperature, "F")

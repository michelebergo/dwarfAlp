from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ConnectivityState:
    sta_ip: Optional[str] = None
    last_error: Optional[str] = None
    mode: str = "unknown"
    wifi_credentials: dict[str, str] = field(default_factory=dict)
    last_device_address: Optional[str] = None
    timezone_name: Optional[str] = None
    site_latitude: Optional[float] = None
    site_longitude: Optional[float] = None
    site_elevation: Optional[float] = None


@dataclass
class StateStore:
    path: Path
    state: ConnectivityState = field(default_factory=ConnectivityState)

    def load(self) -> ConnectivityState:
        if not self.path.exists():
            return self.state

        try:
            with self.path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except json.JSONDecodeError:
            return self.state

        if not isinstance(data, dict):
            return self.state

        data.setdefault("sta_ip", None)
        data.setdefault("last_error", None)
        data.setdefault("mode", "unknown")
        data.setdefault("last_device_address", None)
        data.setdefault("timezone_name", None)
        # drop legacy timezone offset if present
        data.pop("timezone_offset_hours", None)
        raw_credentials = data.get("wifi_credentials", {})
        if isinstance(raw_credentials, dict):
            sanitized_credentials: dict[str, str] = {}
            for ssid, password in raw_credentials.items():
                if isinstance(ssid, str) and isinstance(password, str) and password:
                    sanitized_credentials[ssid] = password
            data["wifi_credentials"] = sanitized_credentials
        else:
            data["wifi_credentials"] = {}

        raw_tz_name = data.get("timezone_name")
        if isinstance(raw_tz_name, str):
            sanitized_name = raw_tz_name.strip()
            data["timezone_name"] = sanitized_name or None
        else:
            data["timezone_name"] = None

        if not isinstance(data.get("last_device_address"), str):
            data["last_device_address"] = None

        for coord_key in ("site_latitude", "site_longitude", "site_elevation"):
            raw = data.get(coord_key)
            if isinstance(raw, (int, float)):
                data[coord_key] = float(raw)
            else:
                data.setdefault(coord_key, None)

        self.state = ConnectivityState(**data)
        return self.state

    def save(self, state: ConnectivityState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        sanitized = ConnectivityState(
            sta_ip=state.sta_ip,
            last_error=state.last_error,
            mode=state.mode,
            wifi_credentials={
                ssid: password
                for ssid, password in state.wifi_credentials.items()
                if isinstance(ssid, str) and isinstance(password, str) and password
            },
            last_device_address=state.last_device_address if isinstance(state.last_device_address, str) else None,
            timezone_name=(
                state.timezone_name.strip()
                if isinstance(state.timezone_name, str) and state.timezone_name.strip()
                else None
            ),
            site_latitude=float(state.site_latitude) if isinstance(state.site_latitude, (int, float)) else None,
            site_longitude=float(state.site_longitude) if isinstance(state.site_longitude, (int, float)) else None,
            site_elevation=float(state.site_elevation) if isinstance(state.site_elevation, (int, float)) else None,
        )
        with self.path.open("w", encoding="utf-8") as stream:
            json.dump(sanitized.__dict__, stream, indent=2)
        self.state = sanitized

    def record_error(self, message: str) -> ConnectivityState:
        self.state.last_error = message
        self.save(self.state)
        return self.state

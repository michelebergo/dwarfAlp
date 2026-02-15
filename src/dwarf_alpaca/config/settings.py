from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


_REMOTE_TIMEOUT_MULTIPLIERS: dict[str, float] = {
    "http_timeout_seconds": 3.0,
    "ftp_timeout_seconds": 3.0,
    "ftp_poll_interval_seconds": 3.0,
    "ws_ping_interval_seconds": 3.0,
    "goto_command_timeout_seconds": 2.67,
    "go_live_timeout_seconds": 3.0,
    "dark_check_timeout_seconds": 3.0,
    "calibration_timeout_seconds": 2.0,
}


class Settings(BaseSettings):
    """Runtime configuration for the DWARF Alpaca server."""

    model_config = SettingsConfigDict(env_prefix="DWARF_ALPACA_", env_file=".env", extra="allow")

    http_host: str = "0.0.0.0"
    http_port: int = 11111
    http_scheme: str = "http"
    enable_https: bool = False
    tls_certfile: Optional[Path] = None
    tls_keyfile: Optional[Path] = None
    http_advertise_host: Optional[str] = None

    # Authentication
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"

    discovery_enabled: bool = True
    discovery_interface: str = "0.0.0.0"
    discovery_port: int = 32227

    state_directory: Path = Path("var")
    profiles_path: Optional[Path] = None

    timezone_name: Optional[str] = None

    # Observatory site coordinates (persisted in var/connectivity.json)
    site_latitude: Optional[float] = None
    site_longitude: Optional[float] = None
    site_elevation: Optional[float] = None

    dwarf_ap_ip: str = "192.168.88.1"
    dwarf_http_port: int = 8082
    dwarf_jpeg_port: int = 8092
    dwarf_ws_port: int = 9900
    dwarf_rtsp_port: int = 554
    dwarf_ftp_port: int = 21
    dwarf_ws_client_id: str = "0000DAF3-0000-1000-8000-00805F9B34FB"

    http_timeout_seconds: float = 5.0
    http_retries: int = 3
    stream_buffer_seconds: float = 1.5
    ftp_timeout_seconds: float = 10.0
    ftp_poll_interval_seconds: float = 1.0
    ws_ping_interval_seconds: float = 5.0
    temperature_refresh_interval_seconds: float = 5.0
    temperature_stale_after_seconds: float = 20.0
    goto_command_timeout_seconds: float = 45.0
    camera_gain_command_timeout_seconds: float = 2.0
    camera_disconnect_timeout_seconds: float = 5.0
    go_live_before_exposure: bool = True
    go_live_timeout_seconds: float = 5.0
    allow_continue_without_darks: bool = True
    dark_check_timeout_seconds: float = 5.0
    goto_valid_seconds: float = 300.0
    calibration_valid_seconds: float = 900.0
    calibration_timeout_seconds: float = 60.0
    calibration_wait_for_slew_seconds: float = 10.0
    auto_calibrate_on_slew: bool = False
    focuser_target_tolerance_steps: int = 5

    ble_adapter: Optional[str] = None
    ble_password: Optional[str] = None
    ble_response_timeout_seconds: float = 15.0
    provisioning_timeout_seconds: float = 120.0

    # WebSocket reconnection
    ws_reconnect_enabled: bool = True
    ws_reconnect_max_retries: int = 10
    ws_reconnect_base_delay: float = 1.0
    ws_reconnect_max_delay: float = 30.0

    # Latency profile: "local" (default) or "remote" (relaxed timeouts)
    latency_profile: str = "local"

    force_simulation: bool = False
    network_mode: str = "ap"

    def with_timezone_name(self, tz_name: Optional[str]) -> "Settings":
        data = self.model_dump()
        data["timezone_name"] = tz_name
        return type(self).model_validate(data)

    def with_latency_profile_applied(self) -> "Settings":
        """Return a copy with timeouts adjusted for the configured latency profile.

        When ``latency_profile`` is ``"remote"``, timeout fields that were not
        explicitly overridden via environment variables are scaled up by
        pre-defined multipliers to tolerate higher network latency.
        """
        if self.latency_profile != "remote":
            return self
        data = self.model_dump()
        for field_name, multiplier in _REMOTE_TIMEOUT_MULTIPLIERS.items():
            default = type(self).model_fields[field_name].default
            if data.get(field_name) == default:
                data[field_name] = round(default * multiplier, 1)
        return type(self).model_validate(data)


def load_settings(config_path: Optional[str]) -> Settings:
    """Load settings optionally layering a YAML profile file."""
    settings = Settings()
    if config_path:
        from .yaml_loader import load_yaml_settings

        settings = load_yaml_settings(settings, config_path)
    return settings.with_latency_profile_applied()

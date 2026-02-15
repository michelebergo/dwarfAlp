from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from ..devices.utils import alpaca_response, bind_request_context
from ..discovery import DEVICE_LIST
from ..dwarf.session import get_session

SERVER_DESCRIPTION = {
    "ServerName": "DWARF 3 Alpaca Server",
    "Manufacturer": "Astro Tools",
    "ManufacturerVersion": "0.1.0",
    "Location": "Observatory",
}

_start_time = time.monotonic()

router = APIRouter(dependencies=[Depends(bind_request_context)])


@router.get("/health")
async def healthcheck() -> dict:
    """Health endpoint for remote monitoring.  Excluded from API-key auth."""
    session = await get_session()
    ws_connected = session._ws_client.connected if not session.simulation else True
    return {
        "status": "ok" if ws_connected else "degraded",
        "simulation": session.simulation,
        "ws_connected": ws_connected,
        "master_lock": session.has_master_lock,
        "latency_profile": session.settings.latency_profile,
        "auth_enabled": session.settings.api_key is not None,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
    }


@router.get("/apiversions")
def get_api_versions():
    return alpaca_response(value=[1])


@router.get("/v1/description")
def get_description():
    return alpaca_response(value=SERVER_DESCRIPTION)


@router.get("/v1/configureddevices")
def get_configured_devices():
    devices = [dict(device) for device in DEVICE_LIST]
    return alpaca_response(value=devices)


@router.get("/v1/devicelist")
def get_device_list():
    return alpaca_response(value=DEVICE_LIST)

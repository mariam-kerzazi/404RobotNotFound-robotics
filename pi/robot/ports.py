"""Find the serial port the ESP32 is plugged into."""
import logging
from typing import Optional

from serial.tools import list_ports

log = logging.getLogger(__name__)

CH340_VID = 0x1A86  # the ESP32 board's USB chip (WCH CH340)


def find_esp32_port(configured: Optional[str] = None) -> Optional[str]:
    """Return the port to use.

    1. The configured port, if that port exists right now.
    2. Otherwise the first CH340 USB-serial port (works on Windows "COM5" and Pi "/dev/ttyUSB0").
    3. Otherwise None.
    """
    ports = list(list_ports.comports())
    names = {p.device for p in ports}
    if configured and configured in names:
        return configured
    for p in ports:
        if p.vid == CH340_VID:
            if configured:
                log.info("Configured port %s not found; using ESP32 on %s", configured, p.device)
            return p.device
    # by-id paths (/dev/serial/by-id/...) are symlinks and don't show up in comports().
    return configured

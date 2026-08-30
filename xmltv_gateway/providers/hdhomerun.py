"""SiliconDust HDHomeRun.

Config:
    HDHOMERUN_HOST  address of the tuner
"""

import json
import os
import urllib.parse
import urllib.request

XMLTV_URL = "https://api.hdhomerun.com/api/xmltv"
DISCOVER_TIMEOUT = 15
FETCH_TIMEOUT = 120


def fetch() -> bytes:
    host = os.environ.get("HDHOMERUN_HOST", "").rstrip("/")
    if not host:
        raise RuntimeError("HDHOMERUN_HOST must be set for the hdhomerun provider")
    if "://" not in host:
        host = f"http://{host}"

    # Discover DeviceAuth every fetch in case it's rotated
    with urllib.request.urlopen(
        f"{host}/discover.json", timeout=DISCOVER_TIMEOUT
    ) as response:
        discover = json.load(response)

    auth = discover.get("DeviceAuth")
    if not auth:
        raise RuntimeError(f"no DeviceAuth in discover.json from {host}")

    query = urllib.parse.urlencode({"DeviceAuth": auth})
    with urllib.request.urlopen(
        f"{XMLTV_URL}?{query}", timeout=FETCH_TIMEOUT
    ) as response:
        return response.read()

"""Target Wi-Fi information feature. Replaceable at runtime."""

import json
import client_service

FEATURE = {"name": "wifi", "title": "Wi-Fi", "version": 1, "actions": ["info"]}


def run():
    return FEATURE


def build_wifi_code():
    return '''import json
from com.chaquo.python import Python
from android.content import Context
from android.net.wifi import WifiManager
from android.text.format import Formatter

appctx = Python.getPlatform().getApplication()
wm = appctx.getSystemService(Context.WIFI_SERVICE)
wi = wm.getConnectionInfo()
ssid = wi.getSSID()
if ssid:
    ssid = ssid.strip('"')
r = json.dumps({"ok": True, "wifi": {
    "ssid": ssid,
    "bssid": str(wi.getBSSID()) if wi.getBSSID() else None,
    "rssi": wi.getRssi(),
    "link_speed": wi.getLinkSpeed(),
    "frequency": wi.getFrequency(),
    "ip": Formatter.formatIpAddress(wi.getIpAddress()),
    "mac": str(wi.getMacAddress()) if wi.getMacAddress() else None,
}}, ensure_ascii=False)
'''


def info():
    result = client_service.rpc(build_wifi_code())
    return json.dumps(client_service.parse_json_result(result), ensure_ascii=False)

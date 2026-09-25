"""Target Wi-Fi information feature. Replaceable at runtime."""

import client_service

FEATURE = {"name": "wifi", "version": 1, "actions": ["info"]}


def run():
    return FEATURE


def info():
    return client_service.parse_json_result(client_service.rpc(client_service.build_wifi_code()))

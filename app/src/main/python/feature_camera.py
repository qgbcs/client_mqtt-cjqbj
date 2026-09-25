"""In-memory remote camera feature. Replaceable at runtime."""

import client_service

FEATURE = {"name": "camera", "title": "Camera", "version": 1, "actions": ["capture"]}


def run():
    return FEATURE


def capture(facing=0):
    result = client_service.rpc(client_service.build_photo_code(int(facing)))
    return client_service.parse_json_result(result)

"""Remote filesystem feature. Replaceable at runtime."""

import client_service
import json

FEATURE = {"name": "files", "title": "Files", "version": 1, "actions": ["scan", "upload"]}


def run():
    return FEATURE


def scan(root, offset=0, limit=100):
    return client_service.scan_remote(root, offset, limit)


def upload(remote_path):
    return json.dumps(client_service.upload_remote(remote_path), ensure_ascii=False)

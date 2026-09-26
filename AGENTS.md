# Client MQTT 项目协作指南

## 工作范围
- 只修改当前 Client MQTT 项目；不要修改工作区级的 `../multi_mqtt/` 或 `../Xime_rpc/`。
- `app/src/main/python/multi_mqtt/` 是由 `debug_build_secexp.sh` 从 `.gitmodules` 指定的源码同步生成的副本，不要手工编辑。默认源码位于相邻的 `../multi_mqtt/`。
- MQTT 依赖的平铺模块会被放入同名目录；客户端通过 `client_service.py` 兼容加载。修复应放在项目自己的桥接层，不要改生成副本。
- Chaquopy APK 不保证保留 `.py` 源文件；三个内置 feature 必须由 `bootstrap.py` 静态登记，不能只靠 `os.listdir` 扫描。

## 产品边界
- MQTT 只承载 RPC 控制代码和少量 JSON 元数据。
- 远程浏览通过目标设备上的 RPC 执行 `os.walk` 和 `os.stat`。
- 文件和照片字节通过目标端 `aliyun_git` 上传，再由客户端通过 HTTP 下载。
- 拍照数据必须保留在内存中，不得在目标设备写入照片文件。
- 不要输出 Aliyun token、私钥或 RPC 生成的密钥。
- 每个 `request_topic` 对应带稳定 ID 的独立目标配置；topic、远程根目录、Aliyun JSON、私钥、超时和验签回退选项保存在脚本根目录的 `client_mqtt.json`。目标页修改后自动保存，并轮询感知外部文件变更；Android 本机应用设置仍单独管理。
- 拍照目标端代码和 `capture` 入口集中在 `feature_camera.py`；Compose 页面只负责选择相机并调用 feature。
- 首次使用外部脚本目录时，可通过设置页的 Python 下载器安装缺失的 files、camera、wifi 脚本。下载要有超时、备用地址和重试，并在界面日志区显示逐步结果。

## 开发与文档维护
- 保持 Compose UI、Python 桥接、RPC 代码生成和传输适配器职责清晰。
- 新增运行时脚本遵循 `FEATURE_DEVELOPMENT.md`；不要把新的脚本专属 Compose 页面继续堆入主 Activity。
- 每个 feature 自己负责领域代码生成和 RPC 动作；`client_service` 只提供通用 RPC、JSON、配置和传输桥接，不新增 `build_wifi_code`、`scan_remote` 这类 feature 专属 helper。
- Feature 返回结构化 JSON；普通信息由 Compose 展示，照片等媒体通过 feature 返回的短 URL/元数据交给 Compose 下载和预览，不能把媒体字节经 MQTT 返回。
- RPC 结果使用明确 JSON，不要为新协议依赖 Python 的 repr 输出。
- 递归扫描必须限制分页大小并返回 `has_more`、`next_offset`；拒绝路径穿越、符号链接逃逸和无界递归。
- 扩大改动前先添加或更新针对性测试。
- 每完成一个可验证里程碑，更新 `PROGRESS.md`；RPC 请求或响应契约变化时更新 `PROTOCOL.md`。
- 架构、构建流程、feature API 或剩余工作发生变化时，分别同步 `ARCHITECTURE.md`、`BUILD.md`、`FEATURE_DEVELOPMENT.md` 或 `TODO.md`；不要把未验证事项写成已完成。

## 验证顺序
1. `bash -n debug_build_secexp.sh`
2. `python3 -m unittest discover -s tests`
3. `git diff --check`
4. 构建后按需比较 `.gitmodules` 指定源码与 `app/src/main/python/multi_mqtt/`，不要手改生成副本。
5. Android SDK 可用时运行 `./debug_build_secexp.sh`，并确认 APK 签名和包信息。
6. 目标设备在线时再运行设备 RPC 验证；未执行的相机、传输、权限等设备测试必须记录在 `PROGRESS.md`，不能声称已通过。

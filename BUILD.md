# Build

在项目根目录运行：

```sh
./debug_build_secexp.sh
```

脚本从 `.gitmodules` 读取 MQTT 源目录并同步到 `app/src/main/python/multi_mqtt/`，查找 Android SDK，构建 debug APK，规范化归档后使用 secexp 签名。默认输出目录为 `out/`，默认产物为 `out/com.qgb.client-20260916-arm64-v8a.apk`。

当前脚本默认值：

- `APPLICATION_ID=com.qgb.client`
- `VERSION_CODE=20260916`
- `BUILD_ABIS=arm64-v8a`
- `SECEXP=1`
- `OUT_DIR=$PROJECT_DIR/out`

脚本会清除 `APPLICATION_ID`、`VERSION_CODE`、`VERSION_NAME`、`APP_NAME` 和 `BUILD_ABIS` 的继承环境值，因此这些值不能通过环境变量覆盖。可用的常见环境设置包括 `SECEXP`、`OUT_DIR` 和 `ANDROID_HOME`。SDK 需要 Android 36 平台及可用的 `aapt`、`apksigner` 和 Gradle 环境。

Chaquopy 使用 Python 3.12；只有在本地具备匹配解释器时才调整版本。构建同步会覆盖生成目录中的 MQTT 副本，不要直接编辑该目录。

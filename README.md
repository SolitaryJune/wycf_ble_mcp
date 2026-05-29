# TryFun CTF BLE/MCP 本地控制器

目标：不依赖官方 App，直接通过本机 BLE 与玩具 GATT 交互，并提供 MCP tools 让 Codex/Claude 调用。

当前状态：

- 已静态确认 Unity 侧 `TFGTC.dll` 通过 `tfgtc://...` 桥接命令调用 Flutter/Dart。
- 已静态提取产品 ID、状态字段、OTA UUID、普通控制 UUID 候选。
- 已动态确认 Black Hole Max 伸缩控制：`ffac` service、`ffb7` write、`ffb8` notify。
- macOS 本机已通过独立 `artifacts/BleMcpPython.app` 绕过 Homebrew shell Python 的 Bluetooth TCC 崩溃。
- 当前实测目标：`TF-BHMAX`，macOS CoreBluetooth UUID `32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0`。
- 已封装 `telescopic` / `heating` / `set-level` / MCP tools，并新增单文件 Web Bluetooth 控制台。

## 安装依赖

```bash
cd /Users/a24
python -m pip install -r /Users/a24/ble_mcp/requirements.txt
```

## CLI 用法

打印 APK/DLL 静态结论：

```bash
python -m ble_mcp.cli known
```

扫描疑似 TryFun 设备：

```bash
python -m ble_mcp.cli scan --duration 8
```

发现 GATT：

```bash
python -m ble_mcp.cli discover "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0"
```

订阅通知：

```bash
python -m ble_mcp.cli notify "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" 0000ffb8-0000-1000-8000-00805f9b34fb --seconds 10
```

写入已确认 payload：

```bash
python -m ble_mcp.cli write "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" 0000ffb7-0000-1000-8000-00805f9b34fb "01020304"
```

默认拒绝写 OTA 特征 `0000ae01-...`；只有明确需要固件升级通道时才加 `--allow-ota`。

设置 Black Hole Max 伸缩强度：

```bash
python -m ble_mcp.cli build-level 0x0c 74 --seq 8
python -m ble_mcp.cli telescopic "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" 74
python -m ble_mcp.cli telescopic "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" 0
```

随机自动模式：

```bash
python -m ble_mcp.cli build-random --min-level 10 --max-level 90
python -m ble_mcp.cli random "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" --min-level 10 --max-level 90
python -m ble_mcp.cli random-loop "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" --count 20 --interval-ms 500 --min-level 10 --max-level 90 --stop-after
```

开关加热：

```bash
python -m ble_mcp.cli heating "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" --on
python -m ble_mcp.cli heating "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" --off
```

注意：Android 日志里的 `5C:65:E7:3A:9E:D6` 是手机看到的 BLE MAC；macOS/ CoreBluetooth 要使用扫描得到的 UUID。

## 单文件 HTML 控制台

文件：

```text
/Users/a24/ble_mcp/web/index.html
```

启动本地静态服务后用 Chrome/Edge 打开：

```bash
cd /Users/a24/ble_mcp
python3 -m http.server 8000
```

然后访问：

```text
http://localhost:8000/web/index.html
```

页面功能：

- Web Bluetooth 连接 `TF-BHMAX`
- 伸缩滑杆：`ffb7 + command_id 0x0c`
- 加热开关：`ffb5 + command_id 0x05`
- 自动随机模式：按配置间隔在最小/最大强度内随机发送伸缩强度
- 音频联动：可选内置/外置麦克风，或浏览器支持时捕获屏幕/系统音频，按实时音量映射伸缩强度；放大倍数支持 `-100x..100x`；“休息”会停止声音读取但保持 BLE 连接
- 订阅 `ffb8` notify 并显示状态/ack
- raw hex 发送和命令帧生成

读取当前系统音量设置：

```bash
python -m ble_mcp.cli system-volume
```

这个 CLI/MCP 工具读的是当前系统音量设置；真正“随着声音变化”的实时响度检测在 HTML 页面里完成。

## 解析 patched APK 日志

已存在日志补丁 APK：

```bash
adb install -r /path/to/tryfun-ble-log-signed.apk
adb logcat | rg "TFBLEWrite|writeCharacteristic"
```

把日志保存后解析：

```bash
python -m ble_mcp.cli parse-log --file /Users/a24/ble_mcp/artifacts/tfble_write_20260529.log
```

需要从日志中拿到这三个字段：

- `service_uuid`
- `characteristic_uuid`
- `payload_hex`

拿到以后即可用本工具 raw write 复现，再封装 `set_vibration` / `set_telescopic` / `set_rotation` / `stop`。

## MCP server

MCP stdio 启动命令：

```bash
cd /Users/a24
/Users/a24/ble_mcp/.venv/bin/python -m ble_mcp.server
```

完整 MCP 文档见：

```text
/Users/a24/ble_mcp/docs/MCP.md
```

MCP 自检：

```bash
cd /Users/a24
/Users/a24/ble_mcp/.venv/bin/python /Users/a24/ble_mcp/scripts/test_mcp.py
```

主要 tools：

- `known_facts`
- `read_system_audio_volume`
- `controller_profile`
- `scan_devices`
- `discover_gatt`
- `write_raw_hex`
- `collect_notifications`
- `parse_tfblewrite_log`
- `build_control_level_frame`
- `build_named_control_frame`
- `build_telescopic_frame`
- `build_random_telescopic_frame`
- `build_random_telescopic_sequence`
- `build_heating_frame`
- `decode_control_notify`
- `map_audio_to_level`
- `build_audio_level_frame`
- `set_telescopic_level`
- `set_random_telescopic_level`
- `run_random_telescopic_sequence`
- `stop_telescopic`
- `set_heating`
- `set_control_level`
- `emergency_stop`
- `set_telescopic_from_audio_level`
- `set_telescopic_from_system_volume`
- `build_tfgtc_bridge_command`

音频相关说明：

- HTML 用 Web Audio 读取实时响度，支持内置/外置麦克风和 Chrome 支持的系统/标签页音频捕获。
- MCP 的 `read_system_audio_volume` 读 OS 音量设置。
- MCP 的 `map_audio_to_level` / `build_audio_level_frame` / `set_telescopic_from_audio_level` 支持阈值、增益、放大倍数 `multiplier` 和上限 `max_level`。`multiplier` 范围为 `-100..100`；负值表示反向映射：超过阈值后音量越大强度越低，低于阈值仍归零。

## 已确认静态信息

### OTA UUID

- Service: `0000ae00-0000-1000-8000-00805f9b34fb`
- Write: `0000ae01-0000-1000-8000-00805f9b34fb`
- Notify: `0000ae02-0000-1000-8000-00805f9b34fb`

### 普通控制 UUID 候选

来自 `E:\Code\wycf\apktool_out\lib\arm64-v8a\libapp.so`：

- `0000ff00-0000-1000-8000-00805f9b34fb`
- `0000ff01-0000-1000-8000-00805f9b34fb`
- `0000ff10-0000-1000-8000-00805f9b34fb`
- `0000ff12-0000-1000-8000-00805f9b34fb`
- `0000ff14-0000-1000-8000-00805f9b34fb`
- `0000ffac-0000-1000-8000-00805f9b34fb`
- `0000ffb4-0000-1000-8000-00805f9b34fb`
- `0000ffb5-0000-1000-8000-00805f9b34fb`
- `0000ffb7-0000-1000-8000-00805f9b34fb`
- `0000ffb8-0000-1000-8000-00805f9b34fb`
- `0000fff1-0000-1000-8000-00805f9b34fb`

### Unity TFGTC 桥接命令

这些不是 BLE 帧，而是 Unity -> Flutter 的高级命令：

- `tfgtc://create_session`
- `tfgtc://disconnect?id={session_id}`
- `tfgtc://reconnect?id={session_id}`
- `tfgtc://change_heartbeat_period?id={session_id}&period={seconds}`
- `tfgtc://stop?id={session_id}&with_response={True|False}`
- `tfgtc://pause?id={session_id}`
- `tfgtc://resume?id={session_id}`
- `tfgtc://execute?id={session_id}&with_response={True|False}&commands={cmd1|cmd2}`
- `tfgtc://get_accessory_id?id={session_id}`
- `tfgtc://get_score_calculation_req_data?id={session_id}&complete={True|False}`
- `tfgtc://get_state?id={session_id}`
- `tfgtc://select_product_to_play_with?id={session_id}&connected_product_id={product_id}&limited_product_ids={id1|id2}`

## 产品 ID

见 `ble_mcp/known.py`。这些来自 `E:\Code\wycf\extracted_yoo_dlls\TFConstant.dll` 的 enum description。

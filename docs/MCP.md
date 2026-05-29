# TryFun BLE MCP Server

本服务通过 MCP 暴露 TryFun / TF-BHMAX 的本地 BLE 控制、协议帧生成、通知解析、音频音量映射和 Web 控制台信息。

## 启动

从仓库父目录启动：

```bash
cd /Users/a24
/Users/a24/ble_mcp/.venv/bin/python -m ble_mcp.server
```

如果已用 editable 模式安装：

```bash
tryfun-ble-mcp-server
```

## 自检

```bash
cd /Users/a24
/Users/a24/ble_mcp/.venv/bin/python /Users/a24/ble_mcp/scripts/test_mcp.py
```

自检会启动 stdio MCP server，检查核心 tools 是否存在，并调用构帧、音频映射和 notify 解码工具。

## Codex / Claude MCP 配置示例

```json
{
  "mcpServers": {
    "tryfun-ble": {
      "command": "/Users/a24/ble_mcp/.venv/bin/python",
      "args": ["-m", "ble_mcp.server"],
      "cwd": "/Users/a24"
    }
  }
}
```

> macOS 直连 BLE 时，代码会自动通过 `artifacts/BleMcpPython.app` helper 启动 CoreBluetooth，避免 shell Python 被 TCC 杀掉。

## 已确认目标

```text
Device name              TF-BHMAX
Android BLE MAC          5C:65:E7:3A:9E:D6
macOS CoreBluetooth UUID 32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0
service                  0000ffac-0000-1000-8000-00805f9b34fb
telescopic write          0000ffb7-0000-1000-8000-00805f9b34fb
heating write             0000ffb5-0000-1000-8000-00805f9b34fb
notify                    0000ffb8-0000-1000-8000-00805f9b34fb
```

## Tool 清单

### 信息/发现

- `known_facts()`
  - 返回产品 ID、确认 UUID、命令、Unity `tfgtc://` 桥接命令。
- `controller_profile()`
  - 返回本地目标、UUID、Web 控制台路径和 URL。
- `scan_devices(duration=5.0, name_prefix=None, include_all=False)`
  - BLE 扫描。
- `discover_gatt(address, timeout=20.0)`
  - 连接并列出 GATT 服务/特征。
- `read_system_audio_volume()`
  - 读取当前 OS 音量设置。注意这不是实时响度；实时响度联动在 HTML 用 Web Audio 做。

### 原始 BLE

- `write_raw_hex(address, characteristic_uuid, payload_hex, response=False, timeout=20.0, allow_ota=False)`
  - 写 raw hex。默认拒绝 OTA。
- `collect_notifications(address, characteristic_uuid, seconds=10.0, timeout=20.0)`
  - 短时间订阅 notify。

### 协议解析/构帧

- `parse_tfblewrite_log(log_text)`
  - 解析 patched APK 的 `TFBLEWrite` logcat。
- `build_control_level_frame(command_id, level, seq=None)`
  - 通用 level 帧。
- `build_named_control_frame(name, level, seq=None)`
  - 名称构帧：`telescopic` / `伸缩` / `heating` / `heat` / `加热`。
- `build_telescopic_frame(level, seq=None)`
  - 构造伸缩帧，写入 `ffb7`。
- `build_random_telescopic_frame(min_level=0, max_level=100, seq=None)`
  - 在范围内随机取一个伸缩强度，并构造单个 `ffb7` 帧。
- `build_random_telescopic_sequence(count=10, min_level=0, max_level=100, interval_ms=500, seq=None)`
  - 构造有限随机自动模式帧序列。`count` 会限制在 `1..1000`，`interval_ms` 会限制在 `50..60000`。
- `build_heating_frame(on, seq=None)`
  - 构造加热开关帧，写入 `ffb5`。
- `decode_control_notify(payload_hex)`
  - 解码 `ffb8` 的 ack/status notify。

### 控制

- `set_telescopic_level(address, level, seq=None, response=False, timeout=20.0)`
  - 设置伸缩强度 `0..100`。
- `set_random_telescopic_level(address, min_level=0, max_level=100, seq=None, timeout=20.0)`
  - 随机取一个伸缩强度并立即发送。
- `run_random_telescopic_sequence(address, count=10, min_level=0, max_level=100, interval_ms=500, stop_after=True, seq=None, timeout=20.0)`
  - 在一次 BLE 连接内运行有限随机自动模式；默认结束后追加一次归零帧。
- `stop_telescopic(address, seq=None, timeout=20.0)`
  - 伸缩归零。
- `set_heating(address, on, seq=None, timeout=20.0)`
  - 加热开关。
- `set_control_level(address, command_id, level, seq=None, response=False, timeout=20.0)`
  - 通用命令写入 `ffb7`。
- `emergency_stop(address, stop_heating=False, seq=None, timeout=20.0)`
  - 伸缩归零，可选关闭加热。

### 音频映射

- `map_audio_to_level(volume_percent, threshold_percent=1.0, gain=8.0, multiplier=1.0, max_level=100)`
  - 将 `0..100` 音量/响度映射为伸缩强度。`multiplier` 支持 `-100..100`；负值表示反向映射：超过阈值后音量越大强度越低，低于阈值仍归零。
- `build_audio_level_frame(volume_percent, threshold_percent=1.0, gain=8.0, multiplier=1.0, max_level=100, seq=None)`
  - 音量映射后构造伸缩帧。
- `set_telescopic_from_audio_level(address, volume_percent, threshold_percent=1.0, gain=8.0, multiplier=1.0, max_level=100, seq=None, timeout=20.0)`
  - 传入音量值，映射并直接发 BLE。
- `set_telescopic_from_system_volume(address, source="output_volume", threshold_percent=1.0, gain=8.0, multiplier=1.0, max_level=100, seq=None, timeout=20.0)`
  - 读取 OS 音量设置，再映射发送。`source` 常用 `output_volume` 或 `input_volume`。

HTML 页面支持真正的实时音频联动：

```text
/Users/a24/ble_mcp/web/index.html
http://localhost:8000/web/index.html
```

HTML 的“休息（停采集）”只停止麦克风/屏幕音频读取，保持 BLE 连接不断开，之后可直接重新开始联动。

## 示例调用意图

### 伸缩到 30

```text
set_telescopic_level(
  address="32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0",
  level=30
)
```

### 伸缩归零

```text
stop_telescopic(address="32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0")
```

### 随机自动模式

构造单个随机帧：

```text
build_random_telescopic_frame(
  min_level=10,
  max_level=90
)
```

运行 20 次随机自动模式，每 500ms 一次，结束后归零：

```text
run_random_telescopic_sequence(
  address="32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0",
  count=20,
  min_level=10,
  max_level=90,
  interval_ms=500,
  stop_after=true
)
```

### 打开加热

```text
set_heating(
  address="32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0",
  on=true
)
```

### 按 100 倍放大映射音量

```text
build_audio_level_frame(
  volume_percent=3.0,
  threshold_percent=1.0,
  gain=8.0,
  multiplier=100.0,
  max_level=100
)
```

### 按负倍数反向映射音量

```text
build_audio_level_frame(
  volume_percent=3.0,
  threshold_percent=1.0,
  gain=8.0,
  multiplier=-1.0,
  max_level=100
)
```

### 解码 notify

```text
decode_control_notify(payload_hex="010700030501fa")
```

## 安全边界

- 默认不会写 OTA 特征 `0000ae01-...`。
- `emergency_stop` 只写普通控制特征。
- macOS 地址必须使用 CoreBluetooth UUID，不是 Android MAC。

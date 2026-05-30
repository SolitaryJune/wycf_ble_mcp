# TryFun BLE 本地控制器

不依赖官方 App，通过浏览器或 AI 助手直接控制 TryFun 玩具。

## 它能做什么

- **手动控制** — 滑杆拖动伸缩强度 0-100%，加热开关
- **自动随机模式** — 设定范围和间隔，自动随机发送强度变化
- **音频联动** — 麦克风或屏幕音频实时驱动伸缩，支持鼓点律动和音量包络两种模式
- **多模式并行** — 音频联动、自动随机、手动控制可同时运行
- **MCP 接入** — Claude / Codex 等 AI 助手可通过 MCP 协议直接控制设备

## 支持设备

已实测：**Black Hole Max** (`TF-BHMAX`)

协议逆向自官方 App，理论上支持所有使用相同 GATT 协议的 TryFun 产品线（Black Hole 系列、吮吸系列、震动蛋系列等）。

## 快速开始

### Web 控制台（推荐）

```bash
cd /Users/a24/ble_mcp
python3 -m http.server 8000
```

用 Chrome/Edge 打开 `http://localhost:8000/web/index.html`，点击"连接 TF-BHMAX"即可。

### MCP（AI 助手接入）

在 MCP 配置中添加：

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

AI 助手即可通过自然语言控制设备，例如"把伸缩强度设到 50"、"开启加热"、"开始音频联动"。

### CLI

```bash
# 扫描设备
python -m ble_mcp.cli scan --duration 8

# 设置伸缩强度
python -m ble_mcp.cli telescopic "设备UUID" 50

# 加热开关
python -m ble_mcp.cli heating "设备UUID" --on
python -m ble_mcp.cli heating "设备UUID" --off

# 随机自动模式
python -m ble_mcp.cli random-loop "设备UUID" --count 20 --interval-ms 500 --min-level 10 --max-level 90
```

## 控制模式

### 手动控制

拖动滑杆设定伸缩强度，支持"拖动实时发送"开关。加热独立控制。

### 自动随机模式

设定最小/最大强度和发送间隔，系统在范围内随机取值并持续发送。适合解放双手。

### 音频联动

将声音实时转化为伸缩动作。两种驱动方式：

**律动/节拍模式**（默认，推荐）
- 只用 70-260Hz 鼓点突增触发，输出短脉冲
- 人声（300-3400Hz）只参与抑制，不会触发
- 自适应底噪门，过滤持续环境声
- 适合音乐节拍跟随

**音量包络模式**
- 按整体响度映射强度
- 关闭所有过滤后等同原始响度模式
- 适合语音/环境声驱动

音频来源可选：
- 内置/外置麦克风
- 屏幕/系统音频捕获（Chrome 支持）

**参数实时可调**：阈值、增益、放大倍数、上限等参数在联动运行时修改即时生效，无需重启。

**休息模式**：暂停音频采集但保持 BLE 连接，点击"继续"恢复，不需重新选择音频设备。

**放大倍数**：支持 `-100x..100x`。负值表示反向映射 — 声音越大强度越低。

## 多模式并行

所有控制模式互不排斥：

- 开启音频联动后，仍可启动自动随机模式
- 手动拖动滑杆随时可用
- 多个模式同时写入时命令交错发送到设备

## MCP 工具列表

| 工具 | 说明 |
|------|------|
| `scan_devices` | 扫描 BLE 设备 |
| `discover_gatt` | 连接并列出 GATT 特征 |
| `set_telescopic_level` | 设置伸缩强度 |
| `stop_telescopic` | 伸缩归零 |
| `set_heating` | 加热开关 |
| `emergency_stop` | 紧急停止（可选关闭加热） |
| `run_random_telescopic_sequence` | 运行随机自动模式 |
| `set_telescopic_from_audio_level` | 音量映射并发送 |
| `set_telescopic_from_audio_beat` | 鼓点映射并发送 |
| `build_*_frame` | 构造协议帧（不发送） |
| `decode_control_notify` | 解码设备状态通知 |
| `write_raw_hex` | 写入原始 hex |
| `known_facts` | 查看已知协议信息 |

完整 MCP 文档见 `docs/MCP.md`。

## 安装

```bash
pip install -r requirements.txt
```

依赖：`bleak`（BLE）、`mcp`（MCP server）。

## 技术细节

### BLE 协议

```
Service:    0000ffac-0000-1000-8000-00805f9b34fb
伸缩写入:    0000ffb7 (write without response)
加热写入:    0000ffb5 (write with response)
状态通知:    0000ffb8 (notify)
```

伸缩帧格式：`[seq, 0x02, 0x00, 0x03, 0x0c, level, checksum]`

加热帧格式：`[seq, 0x02, 0x00, 0x03, 0x05, 1/0, checksum]`

### macOS 注意事项

- macOS 使用 CoreBluetooth UUID（如 `32D7BA9B-...`），不是 Android 的 BLE MAC
- 代码自动通过 `BleMcpPython.app` 绕过 shell Python 的 Bluetooth TCC 限制

### 项目结构

```
ble_mcp/
  server.py          # MCP server
  protocol.py        # 协议帧构建和音频映射
  ble.py             # BLE 通信层
  cli.py             # 命令行工具
  known.py           # 静态提取的产品/UUID 信息
  audio_level.py     # OS 音量读取
  web/index.html     # 单文件 Web 控制台
  docs/MCP.md        # MCP 完整文档
```

## 解析 APK 日志

如需为其他产品确认协议，可用 patched APK 抓取 BLE 写入日志：

```bash
adb install -r tryfun-ble-log-signed.apk
adb logcat | rg "TFBLEWrite|writeCharacteristic"
python -m ble_mcp.cli parse-log --file log.txt
```

## 友情链接

[Linux do](https://linux.do))。

## 许可证

Business Source License

# 协议还原摘要

## 当前结论

普通控制链路分两层：

1. Unity 游戏/控制层发 `tfgtc://...` 高级命令给 Flutter/Dart。
2. Dart AOT 内的 `TFProtocol*` / BLE 逻辑把高级命令转为 GATT 写入。

Java/Android 层只看到 `flutter_blue_plus` 一类通用 BLE 插件；真正的协议和 UUID 选择在 `libapp.so`。

## 已确认的 Unity -> Flutter bridge

证据文件：

- `E:\Code\wycf\extracted_yoo_dlls\TFGTC.dll`
- 反汇工具：`E:\Code\wycf\DumpDnlib.exe`

关键命令：

```text
tfgtc://create_session
tfgtc://disconnect?id={session_id}
tfgtc://reconnect?id={session_id}
tfgtc://change_heartbeat_period?id={session_id}&period={seconds}
tfgtc://stop?id={session_id}&with_response={True|False}
tfgtc://pause?id={session_id}
tfgtc://resume?id={session_id}
tfgtc://execute?id={session_id}&with_response={True|False}&commands={cmd1|cmd2}
tfgtc://get_accessory_id?id={session_id}
tfgtc://get_score_calculation_req_data?id={session_id}&complete={True|False}
tfgtc://get_state?id={session_id}
tfgtc://select_product_to_play_with?id={session_id}&connected_product_id={product_id}&limited_product_ids={id1|id2}
```

## 已确认状态字段/能力字段

来自 `TFGTCState`：

```text
vibrationLevel
telescopicLevel
rotationLevel
suctionLevel
switchMode
gyroSwitch
gamePadModeVibrationLevel
gamePadModeTelescopicLevel
gamePadModeRotationLevel
gamePadButtonVibrationTap
gamePadButtonTelescopicTap
gamePadButtonRotationTap
gamePadButtonStopTap
```

## 已确认产品 ID

来自 `E:\Code\wycf\extracted_yoo_dlls\TFConstant.dll` enum description：

```text
YXL01   tf-mastrb8-yxl01
BBW01   tf-clitsuck-bbw01
LC01    tf-vibroegg-lc01
BHMINI  tf-mastrb8-bhmp01
BHPRO   tf-mastrb8-bhp02
PTPRO   tf-mastrb8-hqm01
YL02    tf-mastrb8-yxl02
ROSE    tf-vibrowand-rose01
CX02    tf-vibroegg-spr01
BHPLUS  tf-mastrb8-bhp03
SOULMT  tf-mastrb8-hqm02
YL02SE  tf-mastrb8-yxl03
ICEPOP  tf-vibrowand-ice01
BHMAX   tf-mastrb8-bhmx01
BHSE    tf-mastrb8-bhse01
```

## BLE UUID

OTA 已确认，不应作为普通控制优先通道：

```text
OTA service  0000ae00-0000-1000-8000-00805f9b34fb
OTA write    0000ae01-0000-1000-8000-00805f9b34fb
OTA notify   0000ae02-0000-1000-8000-00805f9b34fb
```

普通控制候选来自 `E:\Code\wycf\apktool_out\lib\arm64-v8a\libapp.so`：

```text
0000ff00-0000-1000-8000-00805f9b34fb
0000ff01-0000-1000-8000-00805f9b34fb
0000ff10-0000-1000-8000-00805f9b34fb
0000ff12-0000-1000-8000-00805f9b34fb
0000ff14-0000-1000-8000-00805f9b34fb
0000ffac-0000-1000-8000-00805f9b34fb
0000ffb4-0000-1000-8000-00805f9b34fb
0000ffb5-0000-1000-8000-00805f9b34fb
0000ffb7-0000-1000-8000-00805f9b34fb
0000ffb8-0000-1000-8000-00805f9b34fb
0000fff1-0000-1000-8000-00805f9b34fb
```

Black Hole Max 伸缩控制已动态确认：

```text
service 0000ffac-0000-1000-8000-00805f9b34fb
write   0000ffb7-0000-1000-8000-00805f9b34fb
notify  0000ffb8-0000-1000-8000-00805f9b34fb
```

本机实测目标：

```text
Android BLE MAC             5C:65:E7:3A:9E:D6
macOS CoreBluetooth UUID    32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0
advertised name             TF-BHMAX
```

伸缩帧：

```text
[seq, 0x02, 0x00, 0x03, 0x0c, level, checksum]
checksum = -(0x0c + level) & 0xff
```

动态日志样本：

```text
050200030c03f1  # level 3
080200030c4aaa  # level 74
0a0200030c00f4  # level 0
```

本地生成/发送：

```bash
python -m ble_mcp.cli build-level 0x0c 74 --seq 8
python -m ble_mcp.cli telescopic "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" 74
python -m ble_mcp.cli telescopic "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" 0
```

加热开关写入目标特征是 `ffb5` 而非 `ffb7`：

```text
characteristic 0000ffb5-0000-1000-8000-00805f9b34fb
on payload    010200030501fa
off payload   <seq>0200030500fb
frame         [seq, 0x02, 0x00, 0x03, command_id=0x05, level=1/0, checksum]
```

它会让 19 字节 notify 状态中的 `0x05` 字段在 `0/1` 间切换。

本地发送：

```bash
python -m ble_mcp.cli heating "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" --on
python -m ble_mcp.cli heating "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0" --off
```

单文件 HTML 控制台：

```text
/Users/a24/ble_mcp/web/index.html
```

HTML 还包含音频联动模式：

- 麦克风输入：通过 `enumerateDevices()` 选择内置/外置 `audioinput`。
- 屏幕/系统音频：通过 `getDisplayMedia({ audio: true })` 捕获，是否能取到系统声取决于浏览器和系统权限。
- 音频算法：Web Audio `AnalyserNode` 同时读取 time-domain PCM 和频谱。默认“律动/节拍 + 只认鼓点/低频”模式只用约 `70-260Hz` 的鼓点突增计算谱通量并输出短脉冲；“音量包络”模式仍可按响度映射到 `0..100` 伸缩强度，关闭过滤后等同原始响度模式。
- 过滤选项：人声过滤压低约 `300-3400Hz`，并在人声能量主导时抑制触发；底噪/杂音过滤忽略低频轰鸣、高频嘶声，并用自适应噪声门减少持续环境声触发。

MCP/CLI 的 `read_system_audio_volume` / `system-volume` 读取的是 OS 音量设置，不是实时响度；实时联动优先用 HTML。
MCP 另有状态化鼓点工具：`reset_audio_beat_state`、`map_audio_beat_to_level`、`build_audio_beat_frame`、`set_telescopic_from_audio_beat`。调用方传入外部分析得到的低频鼓点能量/通量和人声能量，MCP 维护噪声门、通量历史、释放包络并输出短脉冲 level。

## 仍缺的关键证据

震动、旋转、吸吮、加热等功能仍需各抓一条动态写入来实锤：

- `service_uuid`
- `characteristic_uuid`
- `command_id`
- `write_type`
- `payload_hex`

推荐路径：

```bash
adb install -r E:\Code\wycf\tryfun-ble-log-signed.apk
adb logcat | rg "TFBLEWrite|writeCharacteristic"
```

然后：

```bash
python -m ble_mcp.cli parse-log --file E:\Code\wycf\tfble.log
python -m ble_mcp.cli write "AA:BB:CC:DD:EE:FF" "<characteristic_uuid>" "<payload_hex>"
```

## blutter 状态

当前 Windows blutter 未完成：

- MinGW 构建会碰到 Dart 3.8 Windows 源码兼容问题，例如 `interface` 宏、`__asm`、`ThreadEntry` static/extern。
- MSVC 可用，但需要 `tools\blutter\external` 下 ICU/capstone 依赖；`init_env_win.py` 下载曾卡住，已停止。
- 不阻塞主路径；动态 BLE 日志比继续修 blutter 更快得到可复现控制帧。

# Microduck 复现开发日志

本仓库记录 Microduck（kissqy/Microduck-kissqy）复现过程中的开发日志与自研脚本。

- [开发日志](开发日志.md)
- 语音控制：`voice_pc.py`（PC 收音+识别）、`cmd_relay.py`（Zero 命令转发）
- 其它自研脚本见根目录

## 目录

| 文件 | 说明 |
|---|---|
| `开发日志.md` | 完整开发记录 |
| `cmd_relay.py` | Zero 端 TCP→robotd 命令转发 |
| `cmd-relay.service` | 转发服务 systemd 单元 |
| `voice_pc.py` | PC 端收音 + Vosk 识别 + 意图 + TCP 下发 |
| `voice_ptt_client.py` | 旧 PTT 客户端（已弃用） |
| `voice_control_vosk.py` | Zero 本地 Vosk 旧方案（已弃用） |
| `vosk_server.py` / `asr_server_whisper.py` | 早期 HTTP ASR 服务器（已弃用） |
| `imu_check.py` | IMU ID 200 总线检测脚本 |
| `run_voice.sh` / `voice-client.service` | 旧 tmux 常驻方案（已弃用） |

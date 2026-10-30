import argparse
import json
import socket
import subprocess
import sys
import threading
import time

import requests

WAKE_WORDS = ("小鸭", "小鸭子", "鸭鸭", "你好")


class Robot:
    def __init__(self, path="/run/robotd.sock"):
        self.path = path
        self.sock = None
        self.reader = None
        self.ident = 0
        self.lock = threading.Lock()
        self.timer = None
        self.watchdog = None

    def connect(self):
        if self.sock is not None:
            return
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect(self.path)
        self.reader = self.sock.makefile("rb")

    def call(self, method, params=None):
        with self.lock:
            self.connect()
            self.ident += 1
            msg = {"jsonrpc": "2.0", "id": self.ident, "method": method,
                   "params": params or {}}
            self.sock.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))
            for _ in range(8):
                line = self.reader.readline(262145)
                if not line:
                    raise RuntimeError("robotd IPC 已断开")
                row = json.loads(line)
                if row.get("id") != self.ident:
                    continue
                if row.get("error"):
                    raise RuntimeError(str(row["error"]))
                result = row.get("result")
                if isinstance(result, dict) and result.get("accepted") is False:
                    raise RuntimeError(result.get("reason", "robotd 拒绝动作"))
                return result
            raise RuntimeError("robotd 回执编号不一致")

    def sound(self, tag="chirp"):
        try:
            self.call("robot.sound", {"tag": tag})
        except Exception as exc:
            print("sound:", exc)

    def cancel_timer(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def arm_watchdog(self, seconds=2.0):
        if self.watchdog is not None:
            self.watchdog.cancel()
        self.watchdog = threading.Timer(seconds, self.zero)
        self.watchdog.daemon = True
        self.watchdog.start()

    def cancel_watchdog(self):
        if self.watchdog is not None:
            self.watchdog.cancel()
            self.watchdog = None

    def zero(self):
        self.cancel_timer()
        try:
            self.call("robot.move", {"vx": 0.0, "vy": 0.0, "vyaw": 0.0})
        except Exception as exc:
            print("stop:", exc)

    def move(self, vx=0.0, vy=0.0, vyaw=0.0, duration=0.8):
        self.cancel_timer()
        self.call("robot.move", {"vx": vx, "vy": vy, "vyaw": vyaw})
        self.timer = threading.Timer(duration, self.zero)
        self.timer.daemon = True
        self.timer.start()

    def head(self, **params):
        self.call("robot.head", params)

    def mouth(self, value):
        self.call("robot.mouth", {"open": value})

    def home(self):
        self.zero()
        self.call("robot.init")

    def relax(self):
        self.zero()
        self.call("robot.relax")

    def close(self):
        self.cancel_timer()
        self.cancel_watchdog()
        if self.reader is not None:
            self.reader.close()
        if self.sock is not None:
            self.sock.close()
        self.sock = self.reader = None


def handle(text, robot, awake_until, no_wake):
    now = time.time()
    stripped = text.replace(" ", "")
    for word in WAKE_WORDS:
        if word in stripped:
            stripped = stripped.replace(word, "")
            awake_until = now + 5.0
            print("wake:", word, "->", stripped or "(等待命令)")
            if robot is not None:
                robot.sound()
            break

    if any(w in stripped for w in ("停止", "停下", "别动", "停")):
        if robot is not None:
            robot.zero()
        return awake_until, "stop"

    if any(w in stripped for w in ("卸力", "放松", "趴下")):
        if robot is not None:
            robot.relax()
        return awake_until, "relax"

    if now > awake_until and not no_wake:
        return awake_until, None

    if any(w in stripped for w in ("回家", "回位", "站好")):
        if robot is not None:
            robot.home()
        return awake_until, "home"

    if any(w in stripped for w in ("前进", "向前", "往前走")):
        if robot is not None:
            robot.move(vx=0.15, duration=4.5)
        return awake_until, "forward"

    if any(w in stripped for w in ("后退", "向后", "往后")):
        if robot is not None:
            robot.move(vx=-0.12, duration=0.8)
        return awake_until, "back"

    if any(w in stripped for w in ("左转", "向左转")):
        if robot is not None:
            robot.move(vyaw=0.6, duration=3.0)
        return awake_until, "turn_left"

    if any(w in stripped for w in ("右转", "向右转")):
        if robot is not None:
            robot.move(vyaw=-0.6, duration=3.0)
        return awake_until, "turn_right"

    if any(w in stripped for w in ("左移", "向左移")):
        if robot is not None:
            robot.move(vy=0.12, duration=0.6)
        return awake_until, "strafe_left"

    if any(w in stripped for w in ("右移", "向右移")):
        if robot is not None:
            robot.move(vy=-0.12, duration=0.6)
        return awake_until, "strafe_right"

    if "点头" in stripped:
        if robot is not None:
            robot.head(head_pitch=0.20)
            threading.Timer(1.4, lambda: robot.head(head_pitch=0.0)).start()
        return awake_until, "nod"

    if "摇头" in stripped:
        if robot is not None:
            robot.head(head_yaw=0.25)
            threading.Timer(0.35, lambda: robot.head(head_yaw=0.0)).start()
        return awake_until, "shake"

    if any(w in stripped for w in ("张嘴", "开口")):
        if robot is not None:
            robot.mouth(1.0)
        return awake_until, "mouth_open"

    if any(w in stripped for w in ("闭嘴", "合嘴")):
        if robot is not None:
            robot.mouth(0.0)
        return awake_until, "mouth_close"

    return awake_until, None


def record(path, device, seconds):
    command = [
        "arecord", "-q", "-D", device, "-f", "S16_LE",
        "-r", "16000", "-c", "1", "-d", str(seconds), path,
    ]
    return subprocess.run(command).returncode == 0


def transcribe(server, path):
    with open(path, "rb") as wav:
        response = requests.post(
            server,
            files={"file": ("cmd.wav", wav, "audio/wav")},
            timeout=20,
        )
    response.raise_for_status()
    return response.json().get("text", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://192.168.1.100:8000/asr")
    parser.add_argument("--device", default="plughw:1,0")
    parser.add_argument("--seconds", type=int, default=2)
    parser.add_argument("--socket", default="/run/robotd.sock")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    robot = None if args.dry_run else Robot(args.socket)
    print("server:", args.server)
    print("回车录音，说命令；Ctrl+C 退出。")

    try:
        while True:
            try:
                input("> ")
            except (EOFError, KeyboardInterrupt):
                break
            path = "/tmp/vosk_cmd.wav"
            if not record(path, args.device, args.seconds):
                print("arecord 失败")
                continue
            try:
                text = transcribe(args.server, path)
            except Exception as exc:
                print("ASR 请求失败:", exc)
                continue
            text = text.strip()
            if not text:
                print("(未识别)")
                continue
            print("heard:", text)
            try:
                _, action = handle(text, robot, float("inf"), True)
                print("action:", action)
                if robot is not None:
                    robot.arm_watchdog(6.0)
            except Exception as exc:
                print("action error:", exc)
    finally:
        if robot is not None:
            robot.zero()
            robot.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

import argparse
import json
import socket
import threading
import time
import sys

import pyaudio
import vosk

WAKE_WORDS = ("小鸭", "小鸭子", "鸭鸭", "你好")


class Robot:
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.sock = None
        self.ident = 0
        self.lock = threading.Lock()
        self.timer = None
        self.watchdog = None

    def connect(self):
        if self.sock is not None:
            return
        self.sock = socket.create_connection((self.host, self.port), timeout=5)

    def call(self, method, params=None):
        with self.lock:
            self.connect()
            self.ident += 1
            msg = {"jsonrpc": "2.0", "id": self.ident, "method": method,
                   "params": params or {}}
            self.sock.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))
            buf = b""
            while not buf.endswith(b"\n"):
                chunk = self.sock.recv(1)
                if not chunk:
                    raise RuntimeError("relay 连接断开")
                buf += chunk
        row = json.loads(buf)
        if row.get("error"):
            raise RuntimeError(str(row["error"]))
        result = row.get("result")
        if isinstance(result, dict) and result.get("accepted") is False:
            raise RuntimeError(result.get("reason", "robotd 拒绝动作"))
        return result

    def sound(self, tag="chirp"):
        try:
            self.call("robot.sound", {"tag": tag})
        except Exception:
            pass

    def cancel_timer(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def arm_watchdog(self, seconds=6.0):
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
        if self.sock is not None:
            self.sock.close()
            self.sock = None


def handle(text, robot, awake_until, no_wake):
    now = time.time()
    stripped = text.replace(" ", "")
    for word in WAKE_WORDS:
        if word in stripped:
            stripped = stripped.replace(word, "")
            awake_until = now + 5.0
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


def record(seconds, mic_index=None, rate=16000):
    audio = pyaudio.PyAudio()
    kwargs = {
        "format": pyaudio.paInt16,
        "channels": 1,
        "rate": rate,
        "input": True,
        "frames_per_buffer": 1024,
    }
    if mic_index is not None:
        kwargs["input_device_index"] = mic_index
    stream = audio.open(**kwargs)
    frames = []
    for _ in range(int(rate / 1024 * seconds)):
        frames.append(stream.read(1024))
    stream.stop_stream()
    stream.close()
    audio.terminate()
    return b"".join(frames)


def transcribe(model, pcm, rate=16000):
    rec = vosk.KaldiRecognizer(model, rate)
    rec.AcceptWaveform(pcm)
    return json.loads(rec.FinalResult()).get("text", "").strip()


def stream_loop(model, robot, mic_index, no_wake):
    audio = pyaudio.PyAudio()
    kwargs = {
        "format": pyaudio.paInt16,
        "channels": 1,
        "rate": 16000,
        "input": True,
        "frames_per_buffer": 1024,
    }
    if mic_index is not None:
        kwargs["input_device_index"] = mic_index
    stream = audio.open(**kwargs)
    rec = vosk.KaldiRecognizer(model, 16000)
    awake_until = float("-inf")
    mute_until = 0.0
    print("持续监听中... 唤醒词：小鸭/你好；说命令；Ctrl+C 退出。")
    try:
        while True:
            data = stream.read(1024, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text", "").replace(" ", "")
                if text and time.time() >= mute_until:
                    try:
                        awake_until, action = handle(text, robot, awake_until, no_wake)
                        print("heard:", text, "action:", action)
                        if action is not None:
                            mute_until = time.time() + 1.0
                            if robot is not None:
                                robot.arm_watchdog(6.0)
                    except Exception as exc:
                        print("action error:", exc)
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot", default="192.168.8.25:8098")
    parser.add_argument("--model", default=r"C:\Users\27994\models\vosk-model-small-cn-0.22")
    parser.add_argument("--seconds", type=int, default=2)
    parser.add_argument("--mic-index", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ptt", action="store_true")
    parser.add_argument("--no-wake", action="store_true")
    args = parser.parse_args()

    host, _, port = args.robot.partition(":")
    robot = None if args.dry_run else Robot(host, int(port))
    model = vosk.Model(args.model)

    if args.ptt:
        print("回车录音，说命令；Ctrl+C 退出。")
        try:
            while True:
                try:
                    input("> ")
                except (EOFError, KeyboardInterrupt):
                    break
                pcm = record(args.seconds, args.mic_index)
                text = transcribe(model, pcm)
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
    else:
        stream_loop(model, robot, args.mic_index, args.no_wake)
        if robot is not None:
            robot.zero()
            robot.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

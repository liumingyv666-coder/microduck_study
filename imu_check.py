#!/usr/bin/env python3
"""FT6 IMU (ID 200) bench check on the Radxa /dev/ttyS2.

Stop robotd first, otherwise the serial port is busy:
    sudo systemctl stop robotd
    sudo python3 imu_check.py
    sudo systemctl start robotd

The IMU is a Feetech Sync Read device at 1 Mbps:
    ID 200, address 56, length 15.
"""
import struct
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyS2"
BAUD = 1_000_000
IMU_ID = 200
ADDR = 56
LEN = 15


def sync_read_request(ids):
    params = bytes([ADDR, LEN, *ids])
    body = bytes([0xFE, len(params) + 2, 0x82]) + params
    return b"\xff\xff" + body + bytes([(~sum(body)) & 0xFF])


def parse_reply(frame):
    if len(frame) != 21:
        return None
    if frame[0:2] != b"\xff\xff" or frame[2] != IMU_ID:
        return None
    if frame[3] + 4 != 21:
        return None
    if (sum(frame[2:21]) & 0xFF) != 0xFF:
        return None

    payload = frame[5:20]
    gyro = struct.unpack("<3h", payload[0:6])
    qx, qy, qz = struct.unpack("<3e", payload[6:12])
    w2 = 1.0 - (qx * qx + qy * qy + qz * qz)
    quat = (w2 ** 0.5 if w2 > 0.0 else 0.0, qx, qy, qz)
    return gyro, quat, payload[12], payload[13]


def status_text(value):
    flags = []
    if value & 0x01:
        flags.append("NOT_READY")
    if value & 0x02:
        flags.append("STALE")
    if value & 0x04:
        flags.append("ERROR")
    if value & 0x08:
        flags.append("FRESH")
    return "|".join(flags) if flags else "OK"


def main():
    request = sync_read_request([IMU_ID])
    print("TX:", request.hex(" "))
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.05)
    except Exception as exc:
        print(f"open {PORT} failed: {exc}")
        return 1

    with ser:
        for i in range(20):
            ser.reset_input_buffer()
            ser.write(request)
            ser.flush()
            data = ser.read(64)
            start = data.find(b"\xff\xff\xc8")
            parsed = parse_reply(data[start:start + 21]) if start >= 0 else None
            if parsed:
                gyro, quat, seq, status = parsed
                q = tuple(round(v, 3) for v in quat)
                print(f"{i:02d} gyro={gyro} quat(wxyz)={q} "
                      f"seq={seq} status=0x{status:02x} {status_text(status)}")
            else:
                print(f"{i:02d} no valid reply: {data.hex(' ')}")
            time.sleep(0.2)

    print("Tilt/rotate the IMU: gyro and quat should change; seq should increase.")
    print("If there is no reply: check 5-8.4V on J1.2, 3.3V on U4, FT6 firmware, J1 wiring.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

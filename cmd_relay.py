import json
import socket
import socketserver

ROBOTD = "/run/robotd.sock"
ALLOWED = {
    "robot.move", "robot.head", "robot.mouth", "robot.init",
    "robot.relax", "robot.sound", "robot.busStatus", "robot.enable",
}


def forward(req):
    method = req.get("method")
    if method not in ALLOWED:
        raise ValueError("method not allowed")
    params = req.get("params") or {}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(ROBOTD)
        s.sendall((json.dumps({"jsonrpc": "2.0", "id": 1,
                               "method": method, "params": params}) + "\n").encode("utf-8"))
        with s.makefile("rb") as reader:
            line = reader.readline(262145)
    if not line.endswith(b"\n") or len(line) > 262144:
        raise ValueError("bad robotd reply")
    return json.loads(line)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            line = self.rfile.readline()
            if not line:
                break
            req = {}
            try:
                req = json.loads(line)
                reply = forward(req)
            except Exception as exc:
                reply = {"jsonrpc": "2.0", "id": req.get("id"),
                         "error": {"message": str(exc)}}
            self.wfile.write((json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8"))
            self.wfile.flush()


def main():
    host = "0.0.0.0"
    port = 8098
    with socketserver.ThreadingTCPServer((host, port), Handler) as server:
        server.allow_reuse_address = True
        server.serve_forever()


if __name__ == "__main__":
    main()

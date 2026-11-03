#!/usr/bin/env python3
import json
import os
import queue
import socket
import struct
import sys
import threading
import traceback

HOST = "127.0.0.1"
PORT = 47221
NATIVE_LIMIT = 1024 * 1024

ready = threading.Event()
commands = queue.Queue()
responses = queue.Queue()


def die_on_thread_error(args):
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=sys.stderr)
    os._exit(1)


def read_exact(size):
    buffer = bytearray()
    while len(buffer) < size:
        chunk = sys.stdin.buffer.read(size - len(buffer))
        if not chunk:
            return None
        buffer.extend(chunk)
    return bytes(buffer)


def read_native():
    raw_length = read_exact(4)
    if raw_length is None:
        return None
    length = struct.unpack("<I", raw_length)[0]
    if length == 0 or length >= NATIVE_LIMIT:
        os._exit(1)
    data = read_exact(length)
    if data is None:
        return None
    return json.loads(data.decode("utf-8"))


def write_native(encoded):
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def stdin_loop():
    while True:
        message = read_native()
        if message is None:
            os._exit(0)
        if isinstance(message, dict) and message.get("type") == "ready":
            ready.set()
            continue
        responses.put(message)


def worker():
    while True:
        payload, done, box = commands.get()
        ready.wait()
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(encoded) >= NATIVE_LIMIT:
            response = {
                "ok": False,
                "error": "native messaging limit exceeded",
                "size": len(encoded),
            }
            if "id" in payload:
                response["id"] = payload["id"]
            box["response"] = response
            done.set()
            continue
        write_native(encoded)
        box["response"] = responses.get()
        done.set()


def write_line(conn, payload):
    conn.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")


def handle_line(conn, line):
    try:
        payload = json.loads(line.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        write_line(conn, {"ok": False, "error": "invalid json"})
        return
    if not isinstance(payload, dict):
        write_line(conn, {"ok": False, "error": "request must be a json object"})
        return
    done = threading.Event()
    box = {}
    commands.put((payload, done, box))
    done.wait()
    write_line(conn, box["response"])


def client_loop(conn):
    buffer = bytearray()
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            return
        buffer.extend(chunk)
        while b"\n" in buffer:
            line, _, rest = buffer.partition(b"\n")
            buffer = bytearray(rest)
            handle_line(conn, bytes(line))


def client_thread(conn):
    try:
        client_loop(conn)
    except ConnectionError:
        pass
    try:
        conn.close()
    except ConnectionError:
        pass


def serve():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    sys.stderr.write(f"listening on {HOST}:{PORT}\n")
    sys.stderr.flush()
    while True:
        conn, _addr = server.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        threading.Thread(target=client_thread, args=(conn,), daemon=True).start()


def main():
    threading.excepthook = die_on_thread_error
    threading.Thread(target=stdin_loop, daemon=True).start()
    threading.Thread(target=worker, daemon=True).start()
    serve()


if __name__ == "__main__":
    main()

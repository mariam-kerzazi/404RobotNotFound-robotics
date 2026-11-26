"""A pretend ESP32 for testing the Pi code on a laptop, with no hardware.

It looks like a pyserial port (write / readline / close) and answers the
same way the real firmware does.
"""
import queue
import threading


class FakeEsp32:
    def __init__(self, send_ready=True, answer=True, distance_cm=50):
        self.answer = answer            # set False to simulate a dead / unplugged ESP32
        self.distance_cm = distance_cm
        self.received = []              # every line the Pi sent, in order
        self.closed = False
        self._out = queue.Queue()
        self._lock = threading.Lock()
        if send_ready:
            self._reply("READY robot_body fake")

    # --- pyserial-like interface used by SerialLink ---

    def write(self, data: bytes) -> int:
        line = data.decode("ascii").strip()
        with self._lock:
            self.received.append(line)
        if not self.answer:
            return len(data)
        cmd = line.split(" ")[0]
        if cmd == "PING":
            self._reply("PONG")
        elif cmd in ("MOVE", "STOP"):
            self._reply(f"ACK {cmd}")
        else:
            self._reply(f"ERR unknown_cmd {cmd}")
        return len(data)

    def readline(self) -> bytes:
        try:
            return self._out.get(timeout=0.05)
        except queue.Empty:
            # Like the real ESP32, keep sending distance readings when idle.
            if self.answer and not self.closed:
                return f"DIST {self.distance_cm}\n".encode("ascii")
            return b""

    def close(self) -> None:
        self.closed = True

    # --- helpers ---

    def _reply(self, line: str) -> None:
        self._out.put((line + "\n").encode("ascii"))

    def sent(self, prefix: str):
        with self._lock:
            return [l for l in self.received if l.startswith(prefix)]

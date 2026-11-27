"""A pretend ESP32 for testing the Pi code on a laptop, with no hardware.

It looks like a pyserial port (write / readline / close) and answers the
same way the real firmware does.
"""
import queue
import threading


class FakeEsp32:
    def __init__(self, send_ready=True, answer=True, distance_cm=50, lock_reason=""):
        self.answer = answer            # set False to simulate a dead / unplugged ESP32
        self.distance_cm = distance_cm
        self.lock_reason = lock_reason  # "" = unlocked, or "warmup" / "person"
        self.light_level = 0
        self.received = []              # every line the Pi sent, in order
        self.closed = False
        self._out = queue.Queue()
        self._lock = threading.Lock()
        if send_ready:
            self._reply("READY robot_body fake")
        self._send_state()

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
        elif cmd == "MOVE" and self.lock_reason:
            self._reply(f"ERR locked {self.lock_reason}")
        elif cmd == "LIGHT":
            level = int(line.split(" ")[1])
            if level > 0 and self.lock_reason:
                self.light_level = 0
                self._reply(f"ERR locked {self.lock_reason}")
            else:
                self.light_level = level
                self._reply("ACK LIGHT")
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

    def see_person(self):
        """Simulate the PIR firing: lock, lights off, report it."""
        self.lock_reason = "person"
        self.light_level = 0
        self._send_state(pir=1)

    def clear(self):
        """Simulate 30 s without motion: unlocked."""
        self.lock_reason = ""
        self._send_state(pir=0)

    def _send_state(self, pir=0):
        self._reply(f"PIR {pir}")
        self._reply(f"LOCK 1 {self.lock_reason}" if self.lock_reason else "LOCK 0")

    def _reply(self, line: str) -> None:
        self._out.put((line + "\n").encode("ascii"))

    def sent(self, prefix: str):
        with self._lock:
            return [l for l in self.received if l.startswith(prefix)]

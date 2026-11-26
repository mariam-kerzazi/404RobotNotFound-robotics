"""SSH connection from the laptop to the Raspberry Pi.

How we log in, in order:
  1. The laptop's SSH key (~/.ssh/id_ed25519). No password needed.
  2. The password typed into the panel, if the key doesn't work.

The password is only kept in this program's memory. It is never written to
disk, never logged, and never sent back to the browser. Closing the panel
(or pressing "Forget") throws it away.
"""
import threading
from typing import Callable, Optional, Tuple, Union

import paramiko


class PiConnection:
    def __init__(self, host: str = "robot1.local", user: str = "pi"):
        self.host = host
        self.user = user
        self.auth_method: Optional[str] = None  # "SSH key" or "password"
        self.last_error: Optional[str] = None
        self._password: Optional[str] = None
        self._client: Optional[paramiko.SSHClient] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Password (memory only)
    # ------------------------------------------------------------------

    @property
    def has_password(self) -> bool:
        return self._password is not None

    def set_password(self, password: Optional[str]) -> None:
        self._password = password or None

    def forget_password(self) -> None:
        self._password = None

    # ------------------------------------------------------------------
    # Connect
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        transport = self._client.get_transport() if self._client else None
        return bool(transport and transport.is_active())

    @staticmethod
    def _new_client() -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.load_system_host_keys()  # ~/.ssh/known_hosts
        # First time we see a robot, remember it (fine on a home/school network).
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    def connect(self, host: Optional[str] = None, user: Optional[str] = None) -> None:
        """Connect (or reconnect). Raises an exception with a readable message on failure."""
        with self._lock:
            if host:
                self.host = host.strip()
            if user:
                self.user = user.strip()
            self._close_locked()

            client = self._new_client()
            try:
                client.connect(self.host, username=self.user, timeout=8,
                               look_for_keys=True, allow_agent=True)
                self.auth_method = "SSH key"
            except paramiko.SSHException:
                # Key login didn't work. Try the password, if we have one.
                client.close()
                if not self._password:
                    self.last_error = "SSH key not accepted. Enter the Pi password and connect again."
                    raise RuntimeError(self.last_error)
                client = self._new_client()
                try:
                    client.connect(self.host, username=self.user, password=self._password,
                                   timeout=8, look_for_keys=False, allow_agent=False)
                except paramiko.AuthenticationException:
                    client.close()
                    self.last_error = "Wrong password."
                    raise RuntimeError(self.last_error)
                self.auth_method = "password"
            except OSError as e:  # host not found, network down, timeout
                client.close()
                self.last_error = f"Can't reach {self.host}: {e}"
                raise RuntimeError(self.last_error)

            client.get_transport().set_keepalive(15)
            self._client = client
            self.last_error = None

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    def _close_locked(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self.auth_method = None

    def _ensure(self) -> None:
        if not self.is_connected():
            self.connect()

    # ------------------------------------------------------------------
    # Run commands
    # ------------------------------------------------------------------

    def run(self, command: str, stdin_data: Optional[str] = None, timeout: float = 30,
            binary: bool = False) -> Tuple[int, Union[str, bytes], str]:
        """Run a command on the Pi and wait for it. Returns (exit code, stdout, stderr)."""
        self._ensure()
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        if stdin_data is not None:
            stdin.write(stdin_data)
            stdin.channel.shutdown_write()
        out = stdout.read()
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        return code, (out if binary else out.decode(errors="replace")), err

    def stream(self, command: str, on_line: Callable[[str], None], timeout: float = 600) -> int:
        """Run a command and call on_line() for each line of output as it arrives.
        Returns the exit code."""
        self._ensure()
        channel = self._client.get_transport().open_session()
        channel.set_combine_stderr(True)  # errors and normal output in one stream
        channel.settimeout(timeout)
        channel.exec_command(command)
        for line in channel.makefile("r"):
            on_line(line.rstrip("\n"))
        return channel.recv_exit_status()

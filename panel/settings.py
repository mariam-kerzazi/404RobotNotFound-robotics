"""Settings for the control panel. Change these if your robot is set up differently."""
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
PI_CODE_DIR = REPO_DIR / "pi"           # the robot's Python code (also used for laptop tests)

DEFAULT_HOST = "robot1.local"
DEFAULT_USER = "pi"

# Where things live on the Pi (see README "Pi" setup).
REMOTE_REPO = "~/404RobotNotFound-robotics"
REMOTE_PYTHON = "~/.venvs/robot404/bin/python"

# The panel only listens on this laptop. Other computers can't open it,
# which matters because it can run commands on the robot.
PANEL_HOST = "127.0.0.1"
PANEL_PORT = 5050

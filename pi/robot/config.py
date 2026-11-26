"""Load pi/config.yaml."""
from pathlib import Path

import yaml

PI_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PI_DIR / "config.yaml"


def load_config(path=DEFAULT_CONFIG) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

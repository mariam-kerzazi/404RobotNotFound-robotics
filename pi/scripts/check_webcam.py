#!/usr/bin/env python3
"""Check that a USB webcam works: resolution, real frame rate, one snapshot.

Works on the laptop and on the Pi.
  Laptop:  python pi/scripts/check_webcam.py --show
  Pi:      python3 scripts/check_webcam.py          (needs: sudo apt install python3-opencv)

Options:
  --index N    which camera (0 = first one). On a laptop, 0 is usually the
               built-in camera and 1 the USB webcam.
  --show       open a live preview window (press q to quit).
  --seconds S  how long to measure the frame rate (default 5).

PASS if: it prints a resolution and an FPS above ~10, and the snapshot
(pi/logs/webcam_snapshot.jpg) looks right.
"""
import argparse
import platform
import sys
import time
from pathlib import Path

import cv2

PI_DIR = Path(__file__).resolve().parents[1]


def open_camera(index: int):
    # On Windows, the DirectShow backend opens cameras much faster.
    backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        return None
    # Ask for 1280x720 in MJPG. Cheap webcams only reach full speed at
    # 720p/1080p when sending MJPG instead of raw frames.
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    cap = open_camera(args.index)
    if cap is None:
        print(f"FAIL: could not open camera {args.index}. Is it plugged in? Try --index 1.")
        return 1

    ok, frame = cap.read()
    if not ok:
        print("FAIL: camera opened but returned no image.")
        cap.release()
        return 1
    h, w = frame.shape[:2]
    print(f"Camera {args.index}: {w}x{h}")

    frames = 0
    start = time.monotonic()
    while time.monotonic() - start < args.seconds:
        ok, frame = cap.read()
        if not ok:
            print("FAIL: camera stopped sending images.")
            cap.release()
            return 1
        frames += 1
        if args.show:
            cv2.imshow("webcam check (q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    fps = frames / (time.monotonic() - start)
    print(f"Measured {fps:.1f} frames per second")

    snapshot = PI_DIR / "logs" / "webcam_snapshot.jpg"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(snapshot), frame)
    print(f"Snapshot saved to {snapshot}")

    cap.release()
    cv2.destroyAllWindows()
    print("PASS" if fps >= 10 else "WARNING: low frame rate (bad lighting or USB bandwidth?)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

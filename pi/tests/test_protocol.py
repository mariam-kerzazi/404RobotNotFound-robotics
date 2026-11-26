"""Run on any computer:  cd pi && python -m pytest"""
import pytest

from robot import protocol


def test_move_format():
    assert protocol.encode_move(0.3, 0, -0.25) == b"MOVE 0.30 0.00 -0.25\n"


def test_move_is_clamped_to_safe_range():
    assert protocol.encode_move(5, -5, 0) == b"MOVE 1.00 -1.00 0.00\n"


def test_move_never_sends_negative_zero():
    assert protocol.encode_move(-0.001, 0, 0) == b"MOVE 0.00 0.00 0.00\n"


def test_move_rejects_nan():
    with pytest.raises(ValueError):
        protocol.encode_move(float("nan"), 0, 0)


def test_lines_fit_in_esp32_buffer():
    assert len(protocol.encode_move(-1, -1, -1)) <= protocol.MAX_LINE_LEN


def test_servo_range_checked():
    assert protocol.encode_servo(2, 90) == b"SERVO 2 90\n"
    with pytest.raises(ValueError):
        protocol.encode_servo(2, 200)


@pytest.mark.parametrize(
    "line, expected",
    [
        ("PONG\r\n", protocol.Message("PONG")),
        ("WDT\n", protocol.Message("WDT")),
        ("DIST 42\n", protocol.Message("DIST", value=42)),
        ("DIST -1\n", protocol.Message("DIST", value=-1)),
        ("ACK MOVE\n", protocol.Message("ACK", text="MOVE")),
        ("ERR bad_args MOVE\n", protocol.Message("ERR", text="bad_args MOVE")),
        ("READY robot_body 0.1.0\n", protocol.Message("READY", text="robot_body 0.1.0")),
        ("DIST abc\n", protocol.Message("UNKNOWN", text="DIST abc")),
        ("\x00\xffets Jun  8 2016\n", protocol.Message("UNKNOWN", text="\x00\xffets Jun  8 2016")),
    ],
)
def test_parse(line, expected):
    assert protocol.parse_line(line) == expected

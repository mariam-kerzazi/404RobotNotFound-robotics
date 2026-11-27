"""Tests for SerialLink against the fake ESP32. No hardware needed."""
import time

import pytest

from robot.serial_link import LinkError, SerialLink
from tests.fake_esp32 import FakeEsp32


def make_link(fake, **kwargs):
    kwargs.setdefault("ready_timeout_s", 1.0)
    return SerialLink("fake", serial_factory=lambda: fake, **kwargs)


def test_connects_on_ready():
    fake = FakeEsp32()
    with make_link(fake) as link:
        assert link.firmware_version == "robot_body fake"
        assert link.is_alive()


def test_connects_by_ping_if_no_ready():
    fake = FakeEsp32(send_ready=False)
    with make_link(fake) as link:
        assert link.is_alive()
    assert fake.sent("PING")


def test_open_fails_if_esp32_is_silent():
    fake = FakeEsp32(send_ready=False, answer=False)
    with pytest.raises(LinkError):
        make_link(fake, ready_timeout_s=0.6).open()


def test_move_for_repeats_move_then_stops():
    fake = FakeEsp32()
    with make_link(fake, move_rate_hz=10) as link:
        link.move_for(0.3, 0, 0, seconds=0.5)
        moves = fake.sent("MOVE")
        # ~5 MOVEs in 0.5 s at 10 Hz; every one well inside the 300 ms watchdog.
        assert 4 <= len(moves) <= 7
        assert all(m == "MOVE 0.30 0.00 0.00" for m in moves)
        assert fake.received[-1] == "STOP"


def test_closing_sends_stop():
    fake = FakeEsp32()
    with make_link(fake) as link:
        link.move(0.3, 0, 0)
    assert fake.received[-1] == "STOP"
    assert fake.closed


def test_move_refused_when_esp32_goes_silent():
    fake = FakeEsp32()
    with make_link(fake, link_timeout_s=0.3) as link:
        fake.answer = False  # cable pulled
        time.sleep(0.5)
        assert not link.is_alive()
        with pytest.raises(LinkError):
            link.move(0.3, 0, 0)


def test_distance_and_ping():
    fake = FakeEsp32(distance_cm=37)
    with make_link(fake) as link:
        time.sleep(0.2)
        cm, age = link.distance()
        assert cm == 37 and age < 0.5
        assert link.ping() is not None


def test_pir_and_lock_state_are_tracked():
    fake = FakeEsp32()
    with make_link(fake) as link:
        time.sleep(0.2)
        assert link.pir() == 0 and not link.is_locked()
        fake.see_person()
        time.sleep(0.2)
        assert link.pir() == 1
        assert link.is_locked() and link.lock_reason() == "person"
        fake.clear()
        time.sleep(0.2)
        assert not link.is_locked()


def test_locked_esp32_refuses_lights():
    fake = FakeEsp32(lock_reason="warmup")
    with make_link(fake) as link:
        time.sleep(0.2)
        assert link.is_locked()
        link.light(200)
        time.sleep(0.2)
        assert fake.light_level == 0
        assert link.last_error == "locked warmup"


def test_lights_on_when_unlocked():
    fake = FakeEsp32()
    with make_link(fake) as link:
        link.light(120)
        time.sleep(0.2)
        assert fake.light_level == 120

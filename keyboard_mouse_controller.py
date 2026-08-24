from __future__ import annotations

import ctypes
import logging
import threading
import time

import pyautogui

ARROW_MOVE_PIXELS = 12
MOVE_INTERVAL = 0.025
SCROLL_AMOUNT = 3
SCROLL_INTERVAL = 0.12

DOUBLE_PRESS_WINDOW = 0.35
TAP_MAX_DURATION = 0.22
HOLD_START_DELAY = 0.25

VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_RCONTROL = 0xA3

user32 = ctypes.windll.user32


def key_down(vk_code: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk_code) & 0x8000)


class KeyboardMouseController:
    """Keyboard-only mouse controller.

    Single/held arrows move the cursor.
    Double LEFT arrow press = left click.
    Double RIGHT arrow press = right click.
    Right Ctrl + Up = scroll up.
    Right Ctrl + Down = scroll down.
    """

    ARROWS = {
        "left": VK_LEFT,
        "right": VK_RIGHT,
        "up": VK_UP,
        "down": VK_DOWN,
    }

    def __init__(self):
        self.log = logging.getLogger("keyboard_mouse")
        self.running = False
        self.thread = None

        pyautogui.PAUSE = 0.0
        pyautogui.FAILSAFE = True

        self.previous = {name: False for name in self.ARROWS}
        self.press_started = {name: 0.0 for name in self.ARROWS}
        self.last_tap = {name: 0.0 for name in self.ARROWS}
        self.hold_moving = {name: False for name in self.ARROWS}

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._loop,
            name="KeyboardMouseController",
            daemon=True,
        )
        self.thread.start()

        print("==============================")
        print("KEYBOARD MOUSE CONTROL")
        print("==============================")
        print("Arrow keys -> move cursor")
        print("Double LEFT arrow  -> LEFT CLICK")
        print("Double RIGHT arrow -> RIGHT CLICK")
        print("Right Ctrl + UP    -> SCROLL UP")
        print("Right Ctrl + DOWN  -> SCROLL DOWN")
        print("Ctrl+C -> stop")
        print("==============================")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        self.thread = None

    def _new_press(self, direction, now):
        previous_tap = self.last_tap[direction]

        if (
            previous_tap
            and now - previous_tap <= DOUBLE_PRESS_WINDOW
            and direction == "left"
        ):
            pyautogui.click(button="left")
            self.last_tap[direction] = 0.0
            return

        if (
            previous_tap
            and now - previous_tap <= DOUBLE_PRESS_WINDOW
            and direction == "right"
        ):
            pyautogui.click(button="right")
            self.last_tap[direction] = 0.0
            return

        self.press_started[direction] = now
        self.hold_moving[direction] = False

    def _release(self, direction, now):
        started = self.press_started[direction]
        if not started:
            return

        duration = now - started
        if duration <= TAP_MAX_DURATION and not self.hold_moving[direction]:
            self.last_tap[direction] = now

        self.press_started[direction] = 0.0
        self.hold_moving[direction] = False

    def _move(self, direction):
        if direction == "left":
            pyautogui.moveRel(-ARROW_MOVE_PIXELS, 0)
        elif direction == "right":
            pyautogui.moveRel(ARROW_MOVE_PIXELS, 0)
        elif direction == "up":
            pyautogui.moveRel(0, -ARROW_MOVE_PIXELS)
        elif direction == "down":
            pyautogui.moveRel(0, ARROW_MOVE_PIXELS)

    def _loop(self):
        last_scroll_up = 0.0
        last_scroll_down = 0.0

        while self.running:
            now = time.monotonic()

            for direction, vk in self.ARROWS.items():
                current = key_down(vk)
                was_down = self.previous[direction]

                if current and not was_down:
                    self._new_press(direction, now)

                if current:
                    started = self.press_started[direction]
                    if started and now - started >= HOLD_START_DELAY:
                        self._move(direction)
                        self.hold_moving[direction] = True

                if not current and was_down:
                    self._release(direction, now)

                self.previous[direction] = current

            if key_down(VK_RCONTROL) and key_down(VK_UP):
                if now - last_scroll_up >= SCROLL_INTERVAL:
                    pyautogui.scroll(SCROLL_AMOUNT)
                    last_scroll_up = now

            if key_down(VK_RCONTROL) and key_down(VK_DOWN):
                if now - last_scroll_down >= SCROLL_INTERVAL:
                    pyautogui.scroll(-SCROLL_AMOUNT)
                    last_scroll_down = now

            time.sleep(MOVE_INTERVAL)


if __name__ == "__main__":
    controller = KeyboardMouseController()
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
        print("Keyboard mouse controller stopped.")

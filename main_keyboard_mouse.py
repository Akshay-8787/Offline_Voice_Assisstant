from __future__ import annotations

import time

from keyboard_mouse_controller import KeyboardMouseController


def main():
    controller = KeyboardMouseController()
    controller.start()

    print("Mouse is controlled ONLY by physical keyboard keys.")
    print("Arrow keys -> move cursor")
    print("Double LEFT arrow -> LEFT CLICK")
    print("Double RIGHT arrow -> RIGHT CLICK")
    print("Right Ctrl + Up -> scroll up")
    print("Right Ctrl + Down -> scroll down")
    print("Ctrl+C -> stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        controller.stop()


if __name__ == "__main__":
    main()

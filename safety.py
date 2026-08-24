from __future__ import annotations

from dataclasses import dataclass
import logging
from datetime import datetime
from pathlib import Path

import pyautogui

from app_launcher import AppLauncher


@dataclass(frozen=True)
class ExecutionResult:
    message: str
    speak: bool = True


class SafetyManager:
    """Safety boundary for voice assistant commands."""

    ALLOWED_ACTIONS = {
        # Application control
        "open_app",
        "close_window",
        "minimize_window",
        "maximize_window",
        "switch_window",

        # System control
        "volume_up",
        "volume_down",
        "volume_mute",
        "screenshot",

        # Conversation
        "greeting",
        "how_are_you",
        "thanks",
        "capabilities",
        "identity",
        "presence",
        "good_morning",
        "good_night",
    }

    def __init__(self) -> None:
        self.log = logging.getLogger("safety")
        self.launcher = AppLauncher()

    def execute(self, command) -> ExecutionResult:

        if command.action not in self.ALLOWED_ACTIONS:
            return ExecutionResult(
                "I can't perform that command.",
                speak=False,
            )

        # =====================================================
        # CONVERSATION
        # =====================================================

        if command.action == "greeting":
            return ExecutionResult(
                "Hey! I'm here. What do you need?",
                speak=True,
            )

        if command.action == "how_are_you":
            return ExecutionResult(
                "I'm doing great. Ready to help you.",
                speak=True,
            )

        if command.action == "thanks":
            return ExecutionResult(
                "You're welcome.",
                speak=True,
            )

        if command.action == "capabilities":
            return ExecutionResult(
                "I can open applications, control windows, "
                "use the phone controller, and respond to your voice commands.",
                speak=True,
            )

        if command.action == "identity":
            return ExecutionResult(
                "I'm your offline voice assistant. "
                "I run locally on your PC and use Whisper for speech recognition.",
                speak=True,
            )

        if command.action == "presence":
            return ExecutionResult(
                "Yes, I'm here. I'm listening.",
                speak=True,
            )

        if command.action == "good_morning":
            return ExecutionResult(
                "Good morning! I'm ready whenever you are.",
                speak=True,
            )

        if command.action == "good_night":
            return ExecutionResult(
                "Good night! Take care.",
                speak=True,
            )

        # =====================================================
        # SYSTEM VOLUME CONTROL
        # =====================================================

        if command.action == "volume_up":
            pyautogui.press("volumeup")

            self.log.info(
                "Volume increased."
            )

            return ExecutionResult(
                "Volume increased.",
                speak=True,
            )

        if command.action == "volume_down":
            pyautogui.press("volumedown")

            self.log.info(
                "Volume decreased."
            )

            return ExecutionResult(
                "Volume decreased.",
                speak=True,
            )

        if command.action == "volume_mute":
            pyautogui.press("volumemute")

            self.log.info(
                "Volume mute toggled."
            )

            return ExecutionResult(
                "Volume mute toggled.",
                speak=True,
            )

        # =====================================================
        # SCREENSHOT
        # =====================================================

        if command.action == "screenshot":

            screenshot_dir = (
                Path.home()
                / "Pictures"
                / "VoiceAssistant"
            )

            screenshot_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            timestamp = datetime.now().strftime(
                "%Y-%m-%d_%H-%M-%S"
            )

            screenshot_path = (
                screenshot_dir
                / f"screenshot_{timestamp}.png"
            )

            try:
                pyautogui.screenshot(
                    str(screenshot_path)
                )

                self.log.info(
                    "Screenshot saved: %s",
                    screenshot_path,
                )

                return ExecutionResult(
                    "Screenshot saved.",
                    speak=True,
                )

            except Exception:
                self.log.exception(
                    "Screenshot failed."
                )

                return ExecutionResult(
                    "I couldn't take the screenshot.",
                    speak=True,
                )

        # =====================================================
        # OPEN APPLICATION
        # =====================================================

        if command.action == "open_app":

            target = (
                command.target or ""
            ).strip()

            if not target:
                return ExecutionResult(
                    "Please tell me which application to open.",
                    speak=True,
                )

            success, message = (
                self.launcher.open_application(
                    target
                )
            )

            self.log.info(
                "Open application '%s': %s",
                target,
                message,
            )

            return ExecutionResult(
                message,
                speak=True,
            )

        # =====================================================
        # CLOSE WINDOW
        # =====================================================

        if command.action == "close_window":

            target = (
                command.target or ""
            ).strip()

            if not target:
                return ExecutionResult(
                    "Please tell me which window to close.",
                    speak=True,
                )

            success, message = (
                self.launcher.close_window(
                    target
                )
            )

            self.log.info(
                "Close window '%s': %s",
                target,
                message,
            )

            return ExecutionResult(
                message,
                speak=True,
            )

        # =====================================================
        # MINIMIZE WINDOW
        # =====================================================

        if command.action == "minimize_window":

            target = (
                command.target or ""
            ).strip()

            if not target:
                return ExecutionResult(
                    "Please tell me which window to minimize.",
                    speak=True,
                )

            success, message = (
                self.launcher.minimize_window(
                    target
                )
            )

            self.log.info(
                "Minimize window '%s': %s",
                target,
                message,
            )

            return ExecutionResult(
                message,
                speak=True,
            )

        # =====================================================
        # MAXIMIZE WINDOW
        # =====================================================

        if command.action == "maximize_window":

            target = (
                command.target or ""
            ).strip()

            if not target:
                return ExecutionResult(
                    "Please tell me which window to maximize.",
                    speak=True,
                )

            success, message = (
                self.launcher.maximize_window(
                    target
                )
            )

            self.log.info(
                "Maximize window '%s': %s",
                target,
                message,
            )

            return ExecutionResult(
                message,
                speak=True,
            )

        # =====================================================
        # SWITCH WINDOW
        # =====================================================

        if command.action == "switch_window":

            target = (
                command.target or ""
            ).strip()

            if not target:
                return ExecutionResult(
                    "Please tell me which window to switch to.",
                    speak=True,
                )

            success, message = (
                self.launcher.switch_window(
                    target
                )
            )

            self.log.info(
                "Switch window '%s': %s",
                target,
                message,
            )

            return ExecutionResult(
                message,
                speak=True,
            )

        # =====================================================
        # FALLBACK
        # =====================================================

        return ExecutionResult(
            "Command blocked.",
            speak=False,
        )
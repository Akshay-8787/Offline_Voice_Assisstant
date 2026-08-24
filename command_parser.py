from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Command:
    action: str
    amount: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    raw_text: str = ""
    target: Optional[str] = None


class CommandParser:
    """Convert speech into single, explicit assistant commands."""

    def __init__(self, safety) -> None:
        self.safety = safety

    @staticmethod
    def _clean(text: str) -> str:
        text = text.lower().strip()

        text = re.sub(
            r"[^a-z0-9\s-]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    # =========================================================
    # SINGLE COMMAND PARSER
    # =========================================================

    def _parse_single(
        self,
        text: str,
        raw: str,
    ) -> Command:

        # =====================================================
        # STOP
        # =====================================================

        if text in {
            "stop assistant",
            "stop",
            "exit assistant",
            "quit assistant",
            "shutdown assistant",
        }:
            return Command(
                "stop",
                raw_text=raw,
            )

        # =====================================================
        # GREETINGS
        # =====================================================

        if text in {
            "hello",
            "hi",
            "hey",
            "hello assistant",
            "hi assistant",
            "hey assistant",
        }:
            return Command(
                "greeting",
                raw_text=raw,
            )

        # =====================================================
        # CONVERSATION
        # =====================================================

        if text in {
            "how are you",
            "how are you doing",
            "how are you today",
        }:
            return Command(
                "how_are_you",
                raw_text=raw,
            )

        if text in {
            "thank you",
            "thanks",
            "thanks assistant",
            "thank you assistant",
        }:
            return Command(
                "thanks",
                raw_text=raw,
            )

        if text in {
            "what can you do",
            "what can you do for me",
            "what are your features",
            "what can you help me with",
        }:
            return Command(
                "capabilities",
                raw_text=raw,
            )

        if text in {
            "who are you",
            "what are you",
            "tell me about yourself",
        }:
            return Command(
                "identity",
                raw_text=raw,
            )

        if text in {
            "are you there",
            "assistant are you there",
            "you there",
        }:
            return Command(
                "presence",
                raw_text=raw,
            )

        if text in {
            "good morning",
            "morning",
        }:
            return Command(
                "good_morning",
                raw_text=raw,
            )

        if text in {
            "good night",
            "goodnight",
        }:
            return Command(
                "good_night",
                raw_text=raw,
            )

        # =====================================================
        # VOLUME UP
        # =====================================================

        if (
            text in {
                "volume up",
                "increase volume",
                "increase the volume",
                "turn volume up",
                "turn up volume",
                "turn up the volume",
                "make volume louder",
                "make the volume louder",
                "make it louder",
                "louder",
                "raise volume",
                "raise the volume",
            }
            or re.search(
                r"\b(increase|raise|turn up|boost)\b.*\b(volume|sound)\b",
                text,
            )
        ):
            return Command(
                "volume_up",
                raw_text=raw,
            )

        # =====================================================
        # VOLUME DOWN
        # =====================================================

        if (
            text in {
                "volume down",
                "decrease volume",
                "decrease the volume",
                "turn volume down",
                "turn down volume",
                "turn down the volume",
                "make volume lower",
                "make the volume lower",
                "make it quieter",
                "lower volume",
                "lower the volume",
                "quieter",
            }
            or re.search(
                r"\b(decrease|lower|turn down|reduce)\b.*\b(volume|sound)\b",
                text,
            )
        ):
            return Command(
                "volume_down",
                raw_text=raw,
            )

        # =====================================================
        # MUTE
        # =====================================================

        if (
            text in {
                "mute",
                "mute volume",
                "mute the volume",
                "turn off volume",
                "turn the volume off",
                "silence",
                "silence volume",
                "turn off sound",
                "mute sound",
            }
            or re.search(
                r"\b(mute|silence)\b.*\b(volume|sound)?\b",
                text,
            )
        ):
            return Command(
                "volume_mute",
                raw_text=raw,
            )

        # =====================================================
        # SCREENSHOT
        # =====================================================

        if text in {
            "screen shot",
            "take screen shot",
            "take a screen shot",
            "take screen shot",
            "screen shot",
            "capture screen",
            "capture the screen",
            "capture my screen",
            "capture the entire screen",
            "take a screen capture",
            "screen capture",
        }:
            return Command(
                "screenshot",
                raw_text=raw,
            )

        # =====================================================
        # WINDOW CONTROL
        # =====================================================

        close_match = re.match(
            r"^(?:close|exit)\s+(?:the\s+)?(.+?)$",
            text,
        )

        if close_match:
            target = close_match.group(1).strip()

            if target and len(target) <= 80:
                return Command(
                    "close_window",
                    target=target,
                    raw_text=raw,
                )

        minimize_match = re.match(
            r"^(?:minimize|minimise)\s+(?:the\s+)?(.+?)$",
            text,
        )

        if minimize_match:
            target = minimize_match.group(1).strip()

            if target and len(target) <= 80:
                return Command(
                    "minimize_window",
                    target=target,
                    raw_text=raw,
                )

        maximize_match = re.match(
            r"^(?:maximize|maximise)\s+(?:the\s+)?(.+?)$",
            text,
        )

        if maximize_match:
            target = maximize_match.group(1).strip()

            if target and len(target) <= 80:
                return Command(
                    "maximize_window",
                    target=target,
                    raw_text=raw,
                )

        switch_match = re.match(
            r"^(?:switch\s+to|focus\s+on|go\s+to)\s+(?:the\s+)?(.+?)$",
            text,
        )

        if switch_match:
            target = switch_match.group(1).strip()

            if target and len(target) <= 80:
                return Command(
                    "switch_window",
                    target=target,
                    raw_text=raw,
                )

        # =====================================================
        # OPEN APPLICATION
        # =====================================================

        open_match = re.match(
            r"^(?:open|start|launch|run)\s+(?:the\s+)?(.+?)$",
            text,
        )

        if open_match:
            target = open_match.group(1).strip()

            if target and len(target) <= 80:
                return Command(
                    "open_app",
                    target=target,
                    raw_text=raw,
                )

        # =====================================================
        # UNKNOWN
        # =====================================================

        return Command(
            "unknown",
            raw_text=raw,
        )

    # =========================================================
    # MAIN PARSER
    # =========================================================

    def parse(
        self,
        text: str,
    ) -> Command:

        raw = text

        cleaned = self._clean(
            text
        )

        if not cleaned:
            return Command(
                "unknown",
                raw_text=raw,
            )

        return self._parse_single(
            cleaned,
            raw,
        )
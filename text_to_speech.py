from __future__ import annotations

import logging

import pyttsx3

from config import TTS_RATE, TTS_VOLUME


class OfflineTTS:
    """Windows offline TTS through SAPI5."""

    FEMALE_HINTS = (
        "zira",
        "hazel",
        "heera",
        "kalpana",
        "female",
        "susan",
        "eva",
        "aria",
        "jenny",
    )

    def __init__(self) -> None:
        self.log = logging.getLogger("tts")
        self.engine = None
        self.voice_id = None
        self.voice_name = "Unknown"

        # Find the best available female voice once.
        self._find_voice()

    def _find_voice(self) -> None:
        try:
            engine = pyttsx3.init("sapi5")
            voices = engine.getProperty("voices")

            if not voices:
                self.log.warning("No SAPI voices found.")
                engine.stop()
                return

            # Prefer known female voices.
            for voice in voices:
                name = str(
                    getattr(voice, "name", "")
                ).lower()

                voice_id = str(
                    getattr(voice, "id", "")
                ).lower()

                if any(
                    hint in name or hint in voice_id
                    for hint in self.FEMALE_HINTS
                ):
                    self.voice_id = voice.id
                    self.voice_name = str(
                        getattr(
                            voice,
                            "name",
                            voice.id,
                        )
                    )

                    self.log.info(
                        "Selected female voice: %s",
                        self.voice_name,
                    )

                    engine.stop()
                    return

            # Fallback.
            self.voice_id = voices[0].id
            self.voice_name = str(
                getattr(
                    voices[0],
                    "name",
                    voices[0].id,
                )
            )

            self.log.warning(
                "Female voice not found. Using: %s",
                self.voice_name,
            )

            engine.stop()

        except Exception:
            self.log.exception(
                "Could not initialize SAPI voice."
            )

    def _create_engine(self):
        """Create a fresh SAPI engine for each response."""

        engine = pyttsx3.init("sapi5")

        engine.setProperty(
            "rate",
            TTS_RATE,
        )

        engine.setProperty(
            "volume",
            TTS_VOLUME,
        )

        if self.voice_id:
            engine.setProperty(
                "voice",
                self.voice_id,
            )

        return engine

    def say(self, text: str) -> None:
        if not text:
            return

        text = str(text).strip()

        if not text:
            return

        self.log.info(
            "Speaking: %s",
            text,
        )

        engine = None

        try:
            # Fresh engine every time.
            engine = self._create_engine()

            engine.say(text)

            engine.runAndWait()

            # Explicitly stop after completion.
            engine.stop()

        except Exception:
            self.log.exception(
                "TTS playback failed."
            )

        finally:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass

                del engine

    def stop(self) -> None:
        if self.engine is not None:
            try:
                self.engine.stop()
            except Exception:
                pass

            self.engine = None
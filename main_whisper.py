from __future__ import annotations

import logging
import sys
import subprocess
import time
from pathlib import Path

from command_parser import CommandParser
from config import LOG_FILE
from safety import SafetyManager
from text_to_speech import OfflineTTS
from whisper_speech import WhisperSpeechRecognizer


PHONE_SERVER = Path(__file__).parent / "phone_server.py"


def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def start_phone_controller():
    """Start the phone controller automatically."""

    if not PHONE_SERVER.exists():
        print()
        print("WARNING: phone_server.py not found.")
        print("Phone controller will not start.")
        return None

    print()
    print("==============================")
    print("STARTING PHONE CONTROLLER")
    print("==============================")

    try:
        process = subprocess.Popen(
            [sys.executable, str(PHONE_SERVER)],
            cwd=str(PHONE_SERVER.parent),
        )

        # Give Flask a moment to start.
        time.sleep(1)

        print("Phone controller started.")
        print("Open http://<PC-IP>:5000 on your phone.")
        print("PIN: akshaykumar")
        print()

        return process

    except Exception as exc:
        print("Could not start phone controller:")
        print(exc)
        return None


def stop_phone_controller(process):
    """Stop the phone controller when assistant exits."""

    if process is None:
        return

    try:
        if process.poll() is None:
            print()
            print("Stopping phone controller...")
            process.terminate()

            try:
                process.wait(timeout=3)

            except subprocess.TimeoutExpired:
                process.kill()

            print("Phone controller stopped.")

    except Exception as exc:
        print("Could not stop phone controller:")
        print(exc)


def speak_safely(
    recognizer: WhisperSpeechRecognizer,
    tts: OfflineTTS,
    message: str,
):
    """
    Speak without allowing Whisper to hear the assistant's own voice.
    """

    if not message:
        return

    # Pause microphone capture BEFORE TTS starts.
    recognizer.pause_capture()

    try:
        tts.say(message)

    finally:
        # Clear any audio captured around the transition,
        # then resume microphone listening.
        recognizer.resume_capture()


def main():

    setup_logging()

    log = logging.getLogger("assistant")

    phone_process = None
    recognizer = None
    tts = None

    print()
    print("==============================")
    print("OFFLINE WHISPER VOICE ASSISTANT")
    print("==============================")
    print("STT: Whisper (local CPU)")
    print("TTS: Offline")
    print("PC Control: Applications only")
    print("Mouse Voice Control: DISABLED")
    print("Phone Controller: ENABLED")
    print("Safety: explicit allowlist")
    print()

    try:

        # --------------------------
        # START PHONE CONTROLLER
        # --------------------------

        phone_process = start_phone_controller()

        # --------------------------
        # INITIALIZE VOICE SYSTEM
        # --------------------------

        tts = OfflineTTS()

        safety = SafetyManager()

        parser = CommandParser(
            safety=safety
        )

        recognizer = WhisperSpeechRecognizer()

    except Exception as exc:

        log.exception("Startup failed")

        print()
        print("STARTUP ERROR:")
        print(exc)

        stop_phone_controller(
            phone_process
        )

        sys.exit(1)

    print()
    print("==============================")
    print("ASSISTANT READY")
    print("==============================")

    print()
    print("Voice Commands:")
    print()

    print("  Open Chrome")
    print("  Open WhatsApp")
    print("  Open File Manager")
    print()

    print("  Start Chrome")
    print("  Launch Chrome")
    print("  Start WhatsApp")
    print("  Launch WhatsApp")
    print()

    print("  Hello")
    print("  How are you")
    print("  Thank you")
    print("  What can you do")
    print()

    print("  Stop Assistant")
    print()

    print("Phone Controller: ACTIVE")
    print("Listening...")
    print()

    try:

        for text in recognizer.listen_forever():

            if not text:
                continue

            print()
            print("You:", text)

            log.info(
                "Recognized speech: %s",
                text,
            )

            command = parser.parse(text)

            print(
                "Action:",
                command.action,
            )

            # --------------------------
            # STOP ASSISTANT
            # --------------------------

            if command.action == "stop":

                message = "Stopping assistant."

                print(
                    "Assistant:",
                    message,
                )

                speak_safely(
                    recognizer,
                    tts,
                    message,
                )

                break

            # --------------------------
            # UNKNOWN COMMAND
            # --------------------------

            if command.action == "unknown":

                message = (
                    "Sorry, I didn't "
                    "understand that command."
                )

                print(
                    "Assistant:",
                    message,
                )

                speak_safely(
                    recognizer,
                    tts,
                    message,
                )

                continue

            # --------------------------
            # EXECUTE SAFE COMMAND
            # --------------------------

            result = safety.execute(
                command
            )

            if result.message:

                print(
                    "Assistant:",
                    result.message,
                )

            if result.speak:

                speak_safely(
                    recognizer,
                    tts,
                    result.message,
                )

    except KeyboardInterrupt:

        print()
        print("Stopping assistant...")

    except Exception as exc:

        log.exception(
            "Runtime error"
        )

        print()
        print("RUNTIME ERROR:")
        print(exc)

    finally:

        # --------------------------
        # CLOSE WHISPER
        # --------------------------

        if recognizer is not None:

            try:
                recognizer.close()

            except Exception:
                pass

        # --------------------------
        # STOP TTS
        # --------------------------

        if tts is not None:

            try:
                tts.stop()

            except Exception:
                pass

        # --------------------------
        # STOP PHONE SERVER
        # --------------------------

        stop_phone_controller(
            phone_process
        )

        log.info(
            "Assistant stopped."
        )

        print()
        print("==============================")
        print("ASSISTANT STOPPED")
        print("==============================")


if __name__ == "__main__":
    main()
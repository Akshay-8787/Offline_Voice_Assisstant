from __future__ import annotations

import logging
import queue
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from config import SAMPLE_RATE


MODEL_NAME = "base.en"
DEVICE = 1
CHANNELS = 1

BLOCK_DURATION = 0.08
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)

# Audio tuning
SILENCE_DURATION = 0.65
MAX_RECORDING_SECONDS = 8.0
MIN_RECORDING_SECONDS = 0.25
PRE_ROLL_BLOCKS = 4

# Microphone threshold
MIN_THRESHOLD = 250.0
THRESHOLD_MULTIPLIER = 3.3


class WhisperSpeechRecognizer:
    """
    Offline microphone -> voice activity detection -> Whisper text.

    The microphone can temporarily be paused while the assistant
    is speaking so that the assistant does not recognize its own voice.
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        device: int = DEVICE,
    ):
        self.log = logging.getLogger("whisper")

        self.device = device

        self.audio_queue: queue.Queue[np.ndarray] = queue.Queue()

        self.model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )

        self.threshold = MIN_THRESHOLD
        self.stream = None

        # IMPORTANT:
        # True while TTS is speaking.
        # Incoming microphone audio will be ignored.
        self.capture_paused = False

        self._calibrate_threshold()

    # =========================================================
    # MICROPHONE CALLBACK
    # =========================================================

    def _callback(
        self,
        indata,
        frames,
        time_info,
        status,
    ):
        if status:
            self.log.warning(
                "Audio status: %s",
                status,
            )

        # Do not capture audio while assistant is speaking.
        if self.capture_paused:
            return

        self.audio_queue.put(
            indata.copy()
        )

    # =========================================================
    # AUDIO ENERGY
    # =========================================================

    @staticmethod
    def _energy(
        audio: np.ndarray,
    ) -> float:

        data = audio.astype(
            np.float32
        )

        if data.size == 0:
            return 0.0

        return float(
            np.sqrt(
                np.mean(
                    data * data
                )
            )
        )

    # =========================================================
    # QUEUE
    # =========================================================

    def _clear_queue(self):
        """Remove any old microphone audio."""

        while True:
            try:
                self.audio_queue.get_nowait()

            except queue.Empty:
                break

    # =========================================================
    # PAUSE / RESUME MICROPHONE
    # =========================================================

    def pause_capture(self):
        """
        Temporarily stop accepting microphone audio.

        Called immediately before TTS starts speaking.
        """

        self.capture_paused = True

        # Remove audio that may already be waiting.
        self._clear_queue()

        self.log.info(
            "Microphone capture paused."
        )

    def resume_capture(self):
        """
        Resume microphone capture after TTS finishes.
        """

        # First remove anything that may have arrived
        # around the transition.
        self._clear_queue()

        self.capture_paused = False

        self.log.info(
            "Microphone capture resumed."
        )

    # =========================================================
    # CALIBRATION
    # =========================================================

    def _calibrate_threshold(self):
        """
        Measure room noise for one second and
        choose an adaptive threshold.
        """

        samples = []

        print(
            "Calibrating microphone noise..."
            " please stay quiet for 1 second."
        )

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=CHANNELS,
            dtype="int16",
            device=self.device,
        ) as stream:

            end = (
                time.monotonic()
                + 1.0
            )

            while time.monotonic() < end:

                data, _ = stream.read(
                    BLOCK_SIZE
                )

                samples.append(
                    data.copy()
                )

        if samples:

            energies = [
                self._energy(x)
                for x in samples
            ]

            noise_floor = float(
                np.percentile(
                    energies,
                    80,
                )
            )

            self.threshold = max(
                MIN_THRESHOLD,
                noise_floor
                * THRESHOLD_MULTIPLIER,
            )

        print(
            f"Microphone threshold: "
            f"{self.threshold:.0f}"
        )

    # =========================================================
    # LISTEN FOREVER
    # =========================================================

    def listen_forever(self):
        """
        Continuously listen and yield
        one recognized command at a time.
        """

        self._clear_queue()

        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=CHANNELS,
            dtype="int16",
            device=self.device,
            callback=self._callback,
        )

        self.stream.start()

        try:

            while True:

                # If TTS has paused capture,
                # don't try to process old audio.
                if self.capture_paused:

                    self._clear_queue()

                    time.sleep(
                        0.05
                    )

                    continue

                audio = (
                    self._record_command()
                )

                if audio is None:
                    continue

                text = self._transcribe(
                    audio
                )

                if text:
                    yield text

        finally:
            self.close()

    # =========================================================
    # RECORD ONE COMMAND
    # =========================================================

    def _record_command(self):

        frames = []

        pre_roll = deque(
            maxlen=PRE_ROLL_BLOCKS
        )

        speaking = False

        silence_time = 0.0

        start_time = None

        while True:

            # If assistant started speaking while
            # we were waiting for input, stop immediately.
            if self.capture_paused:

                self._clear_queue()

                return None

            audio = (
                self.audio_queue.get()
            )

            # Check again after receiving audio.
            if self.capture_paused:

                self._clear_queue()

                return None

            energy = self._energy(
                audio
            )

            if not speaking:

                pre_roll.append(
                    audio
                )

                if energy >= self.threshold:

                    speaking = True

                    start_time = (
                        time.monotonic()
                    )

                    frames.extend(
                        pre_roll
                    )

                    pre_roll.clear()

                    print(
                        ">>> SPEECH DETECTED <<<"
                    )

                continue

            frames.append(
                audio
            )

            if energy < self.threshold:

                silence_time += (
                    BLOCK_DURATION
                )

            else:

                silence_time = 0.0

            elapsed = (
                time.monotonic()
                - start_time
            )

            if (
                silence_time
                >= SILENCE_DURATION
                and elapsed
                >= MIN_RECORDING_SECONDS
            ):

                break

            if (
                elapsed
                >= MAX_RECORDING_SECONDS
            ):

                break

        if not frames:
            return None

        return np.concatenate(
            frames,
            axis=0,
        )

    # =========================================================
    # WHISPER TRANSCRIPTION
    # =========================================================

    def _transcribe(
        self,
        audio: np.ndarray,
    ) -> str:

        # Do not transcribe if TTS started.
        if self.capture_paused:
            return ""

        temp_file = Path(
            "_whisper_command.wav"
        )

        with wave.open(
            str(temp_file),
            "wb",
        ) as file:

            file.setnchannels(
                CHANNELS
            )

            file.setsampwidth(2)

            file.setframerate(
                SAMPLE_RATE
            )

            file.writeframes(
                audio.astype(
                    np.int16
                ).tobytes()
            )

        # If TTS starts while the WAV is being
        # prepared, don't send it to Whisper.
        if self.capture_paused:

            try:
                temp_file.unlink()

            except OSError:
                pass

            return ""

        segments, _ = (
            self.model.transcribe(
                str(temp_file),
                language="en",
                beam_size=5,
                best_of=5,
                temperature=0.0,
                vad_filter=True,
                condition_on_previous_text=False,
            )
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        ).strip()

        try:
            temp_file.unlink()

        except OSError:
            pass

        # Never return assistant-generated
        # audio captured during TTS.
        if self.capture_paused:
            return ""

        return text.lower()

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        self.capture_paused = True

        if self.stream is not None:

            try:
                self.stream.stop()

            except Exception:
                pass

            try:
                self.stream.close()

            except Exception:
                pass

            self.stream = None

        self._clear_queue()

        self.log.info(
            "Whisper microphone closed."
        )
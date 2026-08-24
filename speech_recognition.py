from __future__ import annotations

import json
import logging
import queue
from pathlib import Path
from typing import Generator

import sounddevice as sd
from vosk import KaldiRecognizer, Model

from config import BLOCKSIZE, CHANNELS, SAMPLE_RATE


class OfflineSpeechRecognizer:
    """Streaming microphone -> Vosk speech recognition.

    Audio is processed locally. No network request is made by this class.
    """

    def __init__(self, model_path: Path) -> None:
        self.log = logging.getLogger("speech")
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Vosk model directory does not exist: {self.model_path}"
            )

        self.audio_queue: queue.Queue[bytes] = queue.Queue()
        self.model = Model(str(self.model_path))
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.recognizer.SetWords(False)
        self.stream = None
        self.running = False

    def _callback(self, indata, frames, time, status) -> None:
        if status:
            self.log.warning("Audio status: %s", status)
        self.audio_queue.put(bytes(indata))

    def _clear_queue(self) -> None:
        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                return

    def listen_forever(self) -> Generator[str, None, None]:
        self.running = True
        self._clear_queue()

        self.stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            dtype="int16",
            channels=CHANNELS,
            callback=self._callback,
        )

        self.stream.start()
        self.log.info("Microphone stream started.")

        try:
            while self.running:
                data = self.audio_queue.get()

                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip().lower()
                    if text:
                        yield text

        finally:
            self.close()

    def close(self) -> None:
        self.running = False

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
        self.log.info("Microphone stream closed.")

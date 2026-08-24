import json
import queue
import sys

import sounddevice as sd
from vosk import Model, KaldiRecognizer


MODEL_PATH = "models/vosk-model-small-en-in-0.4"
SAMPLE_RATE = 16000
DEVICE = 1

audio_queue = queue.Queue()


def audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status, file=sys.stderr)

    audio_queue.put(bytes(indata))


print("==============================")
print("LIVE VOSK SPEECH TEST")
print("==============================")
print("Loading offline Vosk model...")

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

print("Model loaded.")
print()
print("Microphone: Realtek Audio")
print("Speak now.")
print("Press Ctrl+C to stop.")
print()
print("--------------------------------")

try:
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=8000,
        device=DEVICE,
        dtype="int16",
        channels=1,
        callback=audio_callback,
    ):
        while True:
            data = audio_queue.get()

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()

                if text:
                    print("You:", text)

except KeyboardInterrupt:
    print()
    print("Live speech test stopped.")

except Exception as error:
    print()
    print("ERROR:", error)
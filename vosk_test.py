import json
import wave
from pathlib import Path

from vosk import Model, KaldiRecognizer


MODEL_PATH = Path("models/vosk-model-small-en-in-0.4")
AUDIO_FILE = Path("mic_test.wav")


print("==============================")
print("VOSK SPEECH RECOGNITION TEST")
print("==============================")

if not MODEL_PATH.exists():
    print("ERROR: Vosk model not found.")
    print("Expected:", MODEL_PATH)
    raise SystemExit(1)

if not AUDIO_FILE.exists():
    print("ERROR: mic_test.wav not found.")
    raise SystemExit(1)

print("Loading Vosk model...")
model = Model(str(MODEL_PATH))

print("Opening recorded audio...")
with wave.open(str(AUDIO_FILE), "rb") as audio:

    if audio.getnchannels() != 1:
        print("ERROR: Audio must be mono.")
        raise SystemExit(1)

    sample_rate = audio.getframerate()

    recognizer = KaldiRecognizer(model, sample_rate)

    print("Recognizing speech...")

    while True:
        data = audio.readframes(4000)

        if not data:
            break

        recognizer.AcceptWaveform(data)

    result = json.loads(recognizer.FinalResult())

print()
print("==============================")
print("RECOGNIZED TEXT:")
print(result.get("text", ""))
print("==============================")
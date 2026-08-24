from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Put the extracted Vosk model directory here.
# Example:
# models/vosk-model-small-en-in-0.4/
MODEL_PATH = BASE_DIR / "models" / "vosk-model-small-en-in-0.4"

# Microphone / audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 8000

# Mouse sensitivity
# "move right" / "move a little right" uses this many pixels.
DEFAULT_MOVE_PIXELS = 12

# Safety
CONFIRMATION_TIMEOUT_SECONDS = 8

# TTS
TTS_RATE = 175
TTS_VOLUME = 1.0

LOG_FILE = BASE_DIR / "assistant.log"

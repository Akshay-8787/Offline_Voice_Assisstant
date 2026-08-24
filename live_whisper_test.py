from __future__ import annotations

import queue
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


# ==============================
# SETTINGS
# ==============================

MODEL_NAME = "base.en"

SAMPLE_RATE = 16000
CHANNELS = 1
DEVICE = 1

BLOCK_DURATION = 0.1
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)

# How loud speech must be to start recording.
# Lower = more sensitive.
ENERGY_THRESHOLD = 700

# How long silence must continue before we stop recording.
SILENCE_DURATION = 1

# Maximum length of one command.
MAX_RECORDING_SECONDS = 8


# ==============================
# LOAD WHISPER
# ==============================

print("==============================")
print("LIVE OFFLINE WHISPER TEST")
print("==============================")
print()

print("Loading Whisper model...")

model = WhisperModel(
    MODEL_NAME,
    device="cpu",
    compute_type="int8",
)

print("Whisper model loaded.")
print()
print("Microphone device:", DEVICE)
print("Listening...")
print("Speak a command.")
print("Press Ctrl+C to stop.")
print()


# ==============================
# AUDIO QUEUE
# ==============================

audio_queue = queue.Queue()


def audio_callback(indata, frames, time_info, status):
    if status:
        print("Audio:", status)

    audio_queue.put(indata.copy())


# ==============================
# AUDIO ENERGY
# ==============================

def get_energy(audio):
    audio = audio.astype(np.float32)

    if audio.size == 0:
        return 0

    return float(np.sqrt(np.mean(audio ** 2)))


# ==============================
# RECORD ONE COMMAND
# ==============================

def record_command(stream):

    frames = []

    speaking = False
    silence_time = 0.0
    start_time = None

    while True:

        audio = audio_queue.get()

        energy = get_energy(audio)

        # --------------------------
        # Waiting for speech
        # --------------------------

        if not speaking:

            if energy > ENERGY_THRESHOLD:

                speaking = True
                start_time = time.time()

                print()
                print(">>> SPEECH DETECTED <<<")

                frames.append(audio)

            continue

        # --------------------------
        # Currently recording
        # --------------------------

        frames.append(audio)

        if energy < ENERGY_THRESHOLD:

            silence_time += BLOCK_DURATION

        else:

            silence_time = 0.0

        # Stop after enough silence
        if silence_time >= SILENCE_DURATION:

            break

        # Safety limit
        if time.time() - start_time >= MAX_RECORDING_SECONDS:

            break

    if not frames:
        return None

    audio_data = np.concatenate(frames, axis=0)

    return audio_data


# ==============================
# TRANSCRIBE
# ==============================

def transcribe(audio_data):

    temporary_file = Path("whisper_command.wav")

    with wave.open(str(temporary_file), "wb") as file:

        file.setnchannels(CHANNELS)
        file.setsampwidth(2)
        file.setframerate(SAMPLE_RATE)

        file.writeframes(
            audio_data.astype(np.int16).tobytes()
        )

    segments, info = model.transcribe(
        str(temporary_file),

        language="en",

        beam_size=5,

        vad_filter=True,

        condition_on_previous_text=False,
    )

    text_parts = []

    for segment in segments:

        text = segment.text.strip()

        if text:
            text_parts.append(text)

    return " ".join(text_parts).strip()


# ==============================
# MAIN LOOP
# ==============================

try:

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        channels=CHANNELS,
        dtype="int16",
        device=DEVICE,
        callback=audio_callback,
    ):

        while True:

            audio = record_command(None)

            if audio is None:
                continue

            print(">>> SPEECH ENDED <<<")
            print("Recognizing...")

            text = transcribe(audio)

            if text:

                print()
                print("YOU SAID:")
                print(text)

                print()
                print("------------------------------")

            else:

                print("No speech recognized.")

            print()
            print("Listening again...")


except KeyboardInterrupt:

    print()
    print("Live Whisper test stopped.")
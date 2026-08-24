import sounddevice as sd
import wave
import traceback

SAMPLE_RATE = 16000
DURATION = 5
DEVICE = 1
OUTPUT_FILE = "mic_test.wav"

print("==============================")
print("MICROPHONE TEST")
print("==============================")
print("Microphone device:", DEVICE)
print("Recording will start NOW.")
print("Speak clearly for 5 seconds!")
print()

try:
    print(">>> RECORDING STARTED <<<", flush=True)

    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device=DEVICE,
        blocking=True,
    )

    print(">>> RECORDING FINISHED <<<", flush=True)

    with wave.open(OUTPUT_FILE, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(SAMPLE_RATE)
        file.writeframes(audio.tobytes())

    print()
    print("SUCCESS!")
    print("File created:", OUTPUT_FILE)

except Exception as error:
    print()
    print("MICROPHONE ERROR:")
    print(error)
    print()
    traceback.print_exc()
from faster_whisper import WhisperModel

AUDIO_FILE = "mic_test.wav"

print("==============================")
print("OFFLINE WHISPER TEST")
print("==============================")
print("Loading Whisper model...")
print("First run may take some time.")

model = WhisperModel(
    "base.en",
    device="cpu",
    compute_type="int8",
)

print("Model loaded.")
print("Transcribing mic_test.wav...")

segments, info = model.transcribe(
    AUDIO_FILE,
    beam_size=5,
    vad_filter=True,
)

print()
print("==============================")
print("RECOGNIZED TEXT:")
print("==============================")

text_parts = []

for segment in segments:
    text = segment.text.strip()

    if text:
        print(text)
        text_parts.append(text)

print("==============================")
print("FINAL:")
print(" ".join(text_parts))
print("==============================")
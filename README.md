# Offline Voice-Controlled PC Assistant

A Windows 10/11 Python assistant that performs a small, explicit set of mouse actions from locally recognized speech.

## Privacy

Core operation is offline:

Microphone -> sounddevice -> Vosk model -> local command parser -> PyAutoGUI / local Windows SAPI5 TTS

The project does not send microphone audio or recognized commands to OpenAI, Google Cloud, Azure, ElevenLabs, or another cloud API.

## Recommended stack

- Python 3.9 x64 for the first version. The official Vosk installation page currently documents Python 3.5-3.9 support.
- Vosk for offline streaming speech recognition.
- sounddevice for microphone capture.
- PyAutoGUI for mouse control.
- pyttsx3 + Windows SAPI5 for offline TTS.

## Project structure

```text
offline_voice_assistant/
├── main.py
├── config.py
├── speech_recognition.py
├── command_parser.py
├── mouse_controller.py
├── text_to_speech.py
├── safety.py
├── requirements.txt
├── README.md
├── assistant.log          # created automatically
└── models/
    └── vosk-model-small-en-in-0.4/
```

## 1. Install Python

Install Python 3.9 64-bit on Windows.

Then open PowerShell in this folder.

Create a virtual environment:

```powershell
py -3.9 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the Python executable directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

## 2. Install Python packages

With the environment activated:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `vosk` refuses to install under your current Python version, use Python 3.9 for this project rather than changing the code.

## 3. Download an offline Vosk model

For an Indian-English voice, start with:

`vosk-model-small-en-in-0.4`

It is a small Indian-English model and is suitable for desktop/mobile-style use.

Download it from the official Vosk models page:

https://alphacephei.com/vosk/models

Extract the downloaded archive into:

```text
offline_voice_assistant/
└── models/
    └── vosk-model-small-en-in-0.4/
```

The extracted directory should contain Vosk model files/directories inside it.

You can also use another Vosk model. If you do, change `MODEL_PATH` in `config.py`.

## 4. Test the microphone

Run:

```powershell
python -c "import sounddevice as sd; print(sd.query_devices())"
```

You should see your microphone in the list.

If there are multiple microphones and the default one is wrong, set the desired input device in `speech_recognition.py` by adding:

```python
device=YOUR_DEVICE_INDEX,
```

to `sd.RawInputStream(...)`.

## 5. Run the assistant

```powershell
python main.py
```

Expected startup:

```text
Offline Voice Assistant
-----------------------
Everything in this version is local/offline.
Say: move right, left click, right click, double click, move to center
Say 'stop assistant' to exit.

Assistant ready.
```

The assistant then continuously waits for recognized speech.

## Supported commands

### Relative movement

- "move right" -> right by the configured default amount
- "move left" -> left by the configured default amount
- "move up" -> up by the configured default amount
- "move down" -> down by the configured default amount
- "move a little right" -> right by the configured default amount
- "go a little to the right" -> right by the configured default amount
- "move the mouse slightly left" -> left by the configured default amount
- "cursor down" -> down by the configured default amount

### Pixel movement

- "move right 50 pixels" -> +50 X
- "move 50 pixels to the left" -> -50 X
- "move up 50 pixels" -> -50 Y
- "move down 100 pixels" -> +100 Y
- "move the pointer 30 pixels to the left" -> -30 X

### Clicks

- "left click"
- "click here"
- "right click"
- "double click"

### Center

- "move to the center"
- "move mouse to center"
- "cursor to center"

### Absolute coordinates

The first version supports:

- "move cursor to 500 300"

Coordinates are interpreted as primary-screen pixels from the top-left corner.

Voice-only absolute positioning has limitations: speech recognition can confuse digits, and humans cannot reliably specify a precise pixel coordinate by voice. For accurate targeting, a future version should support a screen grid, OCR/vision target selection, or named UI targets.

### Emergency stop

Say:

- "stop assistant"

The main loop stops listening and exits.

## Cursor sensitivity

Open `config.py` and change:

```python
DEFAULT_MOVE_PIXELS = 12
```

Examples:

```python
DEFAULT_MOVE_PIXELS = 10
```

for smaller steps, or:

```python
DEFAULT_MOVE_PIXELS = 15
```

for larger steps.

Explicit pixel commands are still capped at 1000 pixels per command in `mouse_controller.py` to avoid accidental giant movements.

## Safety design

Speech is never executed as a command line.

For example, saying:

```text
open powershell and run something
```

does not execute anything.

Only actions explicitly recognized by `CommandParser` and listed in `SafetyManager.ALLOWED_ACTIONS` can reach the mouse controller.

When future destructive actions are added, use a separate confirmation state such as:

```text
"shut down computer"
-> "Are you sure?"
-> "confirm shutdown"
```

Do not add destructive actions directly to the allowlist.

## Troubleshooting

### `ModuleNotFoundError: No module named vosk`

Activate the virtual environment and reinstall:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Vosk model not found

Check that the folder is exactly:

```text
models\vosk-model-small-en-in-0.4
```

and that the model files are inside that directory.

### Microphone not working

Check Windows:

Settings -> Privacy & security -> Microphone

Make sure microphone access is enabled for desktop applications.

Then run:

```powershell
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Wrong microphone

Use the device index shown by `sd.query_devices()` and set `device=<index>` in `speech_recognition.py`.

### Recognition is poor

Try:
1. Move the microphone closer.
2. Reduce background noise.
3. Speak short commands.
4. Use the Indian-English model for Indian English speech.
5. For a later high-accuracy version, try the larger Indian-English model from the official Vosk model page.

### TTS does not speak

Test:

```powershell
python -c "import pyttsx3; e=pyttsx3.init('sapi5'); e.say('Hello, I am offline'); e.runAndWait()"
```

Check Windows speech/voice settings.

### TTS voice is not female

`text_to_speech.py` searches installed SAPI5 voices for common female-voice names. If none is installed, it falls back to the first Windows SAPI voice.

The TTS layer is deliberately isolated, so it can later be replaced by a local neural TTS engine without changing the STT/parser/mouse architecture.

### Mouse does not move

Test PyAutoGUI:

```powershell
python -c "import pyautogui; print(pyautogui.position()); pyautogui.moveRel(20, 0)"
```

PyAutoGUI's fail-safe is enabled. Moving the mouse to a screen corner can trigger its emergency fail-safe behavior.

## Extending the project

Good next stages:

1. Wake-word detection such as "Jarvis".
2. Keyboard commands: type text, press Enter, Tab, Escape, etc.
3. Scroll commands.
4. Media/volume controls.
5. Application launching using a fixed allowlist.
6. Window switching.
7. Screen grid navigation.
8. OCR/vision-assisted target selection.
9. Local intent classification.
10. Local neural TTS for a more natural female voice.
11. A GUI showing recognized speech and command status.
12. Per-command confirmation for sensitive actions.

Keep the architecture:

```text
Audio
  ↓
Offline STT
  ↓
Command Parser
  ↓
Safety / Allowlist
  ↓
Action Controller
  ↓
Optional Offline TTS
```

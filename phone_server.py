from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import tempfile
import time
import subprocess
import threading
from datetime import datetime
from functools import wraps
from pathlib import Path

import pyautogui
from flask import Flask, jsonify, request, render_template, redirect, url_for
from faster_whisper import WhisperModel

from command_parser import CommandParser
from safety import SafetyManager
from ai_brain import AIBrain


HOST = "0.0.0.0"
PORT = 5000

# Existing PIN - kept as fallback during development.
ACCESS_TOKEN = "akshaykumar"

MAX_MOVE_PIXELS = 2000
SCROLL_AMOUNT = 8

PHONE_WHISPER_MODEL = "base.en"

BASE_DIR = Path(__file__).parent

# Device authentication storage
DEVICE_FILE = BASE_DIR / "trusted_devices.json"
PENDING_FILE = BASE_DIR / "pending_devices.json"


ALLOWED_KEYS = {
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "space", "enter", "backspace", "tab", "esc", "delete",
    "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
    "shift", "ctrl", "alt", "capslock"
}


app = Flask(__name__)
log = logging.getLogger("phone_server")

_phone_whisper = None

_phone_safety = SafetyManager()
_phone_parser = CommandParser(
    safety=_phone_safety
)

_phone_ai = AIBrain()

# Live state for the exhibition UI. The dashboard runs on this PC,
# so the read endpoint is intentionally local-only.
_assistant_state_lock = threading.Lock()
_assistant_state = {
    "state": "listening",
    "text": "",
    "message": "",
    "action": "",
    "updated_at": time.time(),
}

def set_assistant_state(state, text=None, message=None, action=None):
    with _assistant_state_lock:
        _assistant_state["state"] = state
        if text is not None:
            _assistant_state["text"] = text
        if message is not None:
            _assistant_state["message"] = message
        if action is not None:
            _assistant_state["action"] = action
        _assistant_state["updated_at"] = time.time()

def get_assistant_state():
    with _assistant_state_lock:
        return dict(_assistant_state)


# ============================================================
# DEVICE STORAGE
# ============================================================

def load_json_file(path: Path) -> dict:
    try:
        if path.exists():
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(data, dict):
                return data

    except Exception:
        log.exception(
            "Could not load %s",
            path
        )

    return {}


def save_json_file(
    path: Path,
    data: dict,
) -> None:

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    temp.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temp.replace(path)


trusted_devices = load_json_file(
    DEVICE_FILE
)

pending_devices = load_json_file(
    PENDING_FILE
)


def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_device_token() -> str:
    return secrets.token_urlsafe(32)


def device_name_from_request() -> str:
    user_agent = request.headers.get(
        "User-Agent",
        "Unknown device",
    )

    # Keep only a reasonable amount of information.
    return user_agent[:200]


# ============================================================
# DEVICE AUTHENTICATION
# ============================================================

def get_authenticated_device():
    """
    Accept either:

    1. Existing development PIN
    2. Approved device token
    """

    token = request.headers.get(
        "X-Access-Token",
        ""
    ).strip()

    if not token:
        return None

    # Existing PIN fallback
    if secrets.compare_digest(
        token,
        ACCESS_TOKEN,
    ):
        return {
            "id": "legacy-pin",
            "name": "Legacy PIN",
        }

    token_hash = hash_token(token)

    for device_id, device in trusted_devices.items():

        stored_hash = str(
            device.get(
                "token_hash",
                ""
            )
        )

        if stored_hash == token_hash:
            return {
                "id": device_id,
                "name": device.get(
                    "name",
                    "Trusted device",
                ),
            }

    return None


def require_auth(fn):

    @wraps(fn)
    def wrapper(
        *args,
        **kwargs,
    ):

        device = get_authenticated_device()

        if device is None:

            return jsonify({
                "ok": False,
                "error": "Authentication required",
                "code": "AUTH_REQUIRED",
            }), 401

        request.authenticated_device = device

        return fn(
            *args,
            **kwargs,
        )

    return wrapper


# ============================================================
# LOCAL ADMIN CHECK
# ============================================================

def is_local_request() -> bool:

    remote = request.remote_addr

    return remote in {
        "127.0.0.1",
        "::1",
    }


# ============================================================
# DEVICE REGISTRATION
# ============================================================

@app.post("/api/device/register")
def register_device():

    data = request.get_json(
        silent=True
    ) or {}

    device_id = str(
        data.get(
            "device_id",
            "",
        )
    ).strip()

    if not device_id:
        return jsonify({
            "ok": False,
            "error": "Missing device ID.",
        }), 400

    if len(device_id) > 128:
        return jsonify({
            "ok": False,
            "error": "Invalid device ID.",
        }), 400

    # Already trusted
    existing = trusted_devices.get(
        device_id
    )

    if existing:

        return jsonify({
            "ok": True,
            "status": "trusted",
            "device_id": device_id,
            "message": "Device already trusted.",
        })

    # Already waiting for approval
    if device_id in pending_devices:

        return jsonify({
            "ok": True,
            "status": "pending",
            "device_id": device_id,
            "message": "Waiting for PC approval.",
        })

    pending_devices[device_id] = {
        "name": device_name_from_request(),
        "created_at": int(time.time()),
        "ip": request.remote_addr or "unknown",
    }

    save_json_file(
        PENDING_FILE,
        pending_devices,
    )

    print()
    print("=" * 50)
    print("NEW DEVICE ACCESS REQUEST")
    print("=" * 50)
    print(f"Device ID : {device_id}")
    print(
        f"Device    : "
        f"{pending_devices[device_id]['name']}"
    )
    print(
        f"IP        : "
        f"{pending_devices[device_id]['ip']}"
    )
    print("=" * 50)
    print()

    return jsonify({
        "ok": True,
        "status": "pending",
        "device_id": device_id,
        "message": "Waiting for PC approval.",
    })


# ============================================================
# DEVICE STATUS
# ============================================================

@app.get("/api/device/status/<device_id>")
def device_status(device_id):

    if device_id in trusted_devices:

        return jsonify({
            "ok": True,
            "status": "trusted",
        })

    if device_id in pending_devices:

        return jsonify({
            "ok": True,
            "status": "pending",
        })

    return jsonify({
        "ok": True,
        "status": "unknown",
    })


# ============================================================
# LOCAL ADMIN PAGE
# ============================================================

@app.get("/admin/devices")
def admin_devices():

    if not is_local_request():

        return (
            "Admin panel is available only "
            "on this Windows PC.",
            403,
        )

    return render_template(
        "device_admin.html",
        pending=pending_devices,
        trusted=trusted_devices,
    )


# ============================================================
# APPROVE DEVICE
# ============================================================

@app.post("/admin/device/<device_id>/approve")
def approve_device(device_id):

    if not is_local_request():

        return (
            jsonify({
                "ok": False,
                "error": "Local PC access required.",
            }),
            403,
        )

    device = pending_devices.get(
        device_id
    )

    if not device:

        return jsonify({
            "ok": False,
            "error": "Device request not found.",
        }), 404

    raw_token = create_device_token()

    trusted_devices[device_id] = {
        "name": device.get(
            "name",
            "Unknown device",
        ),
        "created_at": device.get(
            "created_at",
            int(time.time()),
        ),
        "approved_at": int(
            time.time()
        ),
        "token_hash": hash_token(
            raw_token
        ),
    }

    pending_devices.pop(
        device_id,
        None
    )

    save_json_file(
        DEVICE_FILE,
        trusted_devices,
    )

    save_json_file(
        PENDING_FILE,
        pending_devices,
    )

    return jsonify({
        "ok": True,
        "status": "approved",
        "device_id": device_id,

        # Returned only once.
        "device_token": raw_token,

        "message": "Device approved.",
    })


# ============================================================
# DENY DEVICE
# ============================================================

@app.post("/admin/device/<device_id>/deny")
def deny_device(device_id):

    if not is_local_request():

        return (
            jsonify({
                "ok": False,
                "error": "Local PC access required.",
            }),
            403,
        )

    if device_id not in pending_devices:

        return jsonify({
            "ok": False,
            "error": "Device request not found.",
        }), 404

    pending_devices.pop(
        device_id,
        None
    )

    save_json_file(
        PENDING_FILE,
        pending_devices,
    )

    return jsonify({
        "ok": True,
        "status": "denied",
        "message": "Device denied.",
    })


# ============================================================
# REVOKE TRUSTED DEVICE
# ============================================================

@app.post("/admin/device/<device_id>/revoke")
def revoke_device(device_id):

    if not is_local_request():

        return (
            jsonify({
                "ok": False,
                "error": "Local PC access required.",
            }),
            403,
        )

    if device_id not in trusted_devices:

        return jsonify({
            "ok": False,
            "error": "Trusted device not found.",
        }), 404

    trusted_devices.pop(
        device_id,
        None
    )

    save_json_file(
        DEVICE_FILE,
        trusted_devices,
    )

    return jsonify({
        "ok": True,
        "status": "revoked",
        "message": "Device access revoked.",
    })


# ============================================================
# MAIN PAGE
# ============================================================

@app.get("/")
def index():

    return render_template(
        "phone_control.html"
    )


@app.get("/assistant")
def assistant_ui():

    return render_template(
        "assistant_3d.html"
    )


@app.get("/api/assistant-state")
def assistant_state():
    # Exhibition dashboard is intended to run on the Windows PC itself.
    if not is_local_request():
        return jsonify({
            "ok": False,
            "error": "Assistant dashboard state is local-only.",
        }), 403

    return jsonify({
        "ok": True,
        **get_assistant_state(),
    })


# ============================================================
# WHISPER
# ============================================================

def get_phone_whisper():

    global _phone_whisper

    if _phone_whisper is None:

        print(
            "Loading phone voice Whisper model..."
        )

        _phone_whisper = WhisperModel(
            PHONE_WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
        )

        print(
            "Phone voice Whisper model loaded."
        )

    return _phone_whisper


def transcribe_phone_audio(
    audio_path: str,
) -> str:

    model = get_phone_whisper()

    segments, _ = model.transcribe(
        audio_path,
        language="en",
        beam_size=5,
        best_of=5,
        temperature=0.0,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    return " ".join(
        segment.text.strip()
        for segment in segments
        if segment.text.strip()
    ).strip().lower()


# ============================================================
# MOUSE
# ============================================================

@app.post("/api/move")
@require_auth
def move():

    data = request.get_json(
        silent=True
    ) or {}

    direction = data.get(
        "direction"
    )

    try:
        amount = int(
            data.get(
                "amount",
                35,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        amount = 35

    amount = max(
        1,
        min(
            MAX_MOVE_PIXELS,
            amount,
        ),
    )

    if direction == "left":
        dx, dy = -amount, 0

    elif direction == "right":
        dx, dy = amount, 0

    elif direction == "up":
        dx, dy = 0, -amount

    elif direction == "down":
        dx, dy = 0, amount

    else:
        return jsonify({
            "ok": False,
            "error": "Invalid direction",
        }), 400

    pyautogui.moveRel(
        dx,
        dy,
        duration=0,
    )

    return jsonify({
        "ok": True
    })


@app.post("/api/click")
@require_auth
def click():

    button = (
        request
        .get_json(
            silent=True
        )
        or {}
    ).get(
        "button",
        "left",
    )

    if button not in (
        "left",
        "right",
    ):
        return jsonify({
            "ok": False,
            "error": "Invalid button",
        }), 400

    pyautogui.click(
        button=button
    )

    return jsonify({
        "ok": True
    })


@app.post("/api/double-click")
@require_auth
def double_click():

    pyautogui.doubleClick()

    return jsonify({
        "ok": True
    })


@app.post("/api/scroll")
@require_auth
def scroll():

    data = request.get_json(
        silent=True
    ) or {}

    direction = data.get(
        "direction"
    )

    try:
        amount = int(
            data.get(
                "amount",
                SCROLL_AMOUNT,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        amount = SCROLL_AMOUNT

    amount = max(
        1,
        min(
            50,
            amount,
        ),
    )

    if direction == "up":
        pyautogui.scroll(amount)

    elif direction == "down":
        pyautogui.scroll(-amount)

    else:
        return jsonify({
            "ok": False,
            "error": "Invalid direction",
        }), 400

    return jsonify({
        "ok": True
    })


@app.post("/api/center")
@require_auth
def center():

    width, height = pyautogui.size()

    pyautogui.moveTo(
        width // 2,
        height // 2,
        duration=0,
    )

    return jsonify({
        "ok": True
    })


# ============================================================
# WINDOWS ACTIONS
# ============================================================

WINDOWS_ACTIONS = {
    "volume_up",
    "volume_down",
    "volume_mute",
    "screenshot",
    "lock_pc",
    "sleep",
    "settings",
    "downloads",
    "documents",
}


@app.post("/api/windows-action")
@require_auth
def windows_action():
    data = request.get_json(silent=True) or {}
    action = str(data.get("action", "")).strip().lower()

    if action not in WINDOWS_ACTIONS:
        return jsonify({
            "ok": False,
            "error": "Invalid Windows action",
        }), 400

    try:
        if action == "volume_up":
            pyautogui.press("volumeup")
            message = "Volume increased."

        elif action == "volume_down":
            pyautogui.press("volumedown")
            message = "Volume decreased."

        elif action == "volume_mute":
            pyautogui.press("volumemute")
            message = "Mute toggled."

        elif action == "screenshot":
            pictures = Path.home() / "Pictures" / "Screenshots"
            pictures.mkdir(parents=True, exist_ok=True)
            filename = pictures / (
                "Screenshot_" +
                datetime.now().strftime("%Y%m%d_%H%M%S") +
                ".png"
            )
            pyautogui.screenshot(str(filename))
            message = f"Screenshot saved to {filename}"

        elif action == "lock_pc":
            subprocess.Popen(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            message = "PC locked."

        elif action == "sleep":
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-Command",
                 "Start-Sleep -Milliseconds 500; Add-Type -AssemblyName System.Windows.Forms; "
                 "[System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            message = "Putting the PC to sleep."

        elif action == "settings":
            subprocess.Popen(
                ["explorer.exe", "ms-settings:"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            message = "Opening Settings."

        elif action == "downloads":
            subprocess.Popen(
                ["explorer.exe", str(Path.home() / "Downloads")],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            message = "Opening Downloads."

        else:  # documents
            subprocess.Popen(
                ["explorer.exe", str(Path.home() / "Documents")],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            message = "Opening Documents."

        log.info("Windows action executed: %s", action)
        return jsonify({
            "ok": True,
            "action": action,
            "message": message,
        })

    except Exception as exc:
        log.exception("Windows action failed: %s", action)
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 500


# ============================================================
# BACKWARD-COMPATIBLE SYSTEM ACTIONS
# ============================================================

@app.post("/api/system-action")
@require_auth
def system_action_compat():
    data = request.get_json(silent=True) or {}
    action = str(data.get("action", "")).strip().lower()

    # Old frontend names -> current Windows action names.
    aliases = {
        "lock": "lock_pc",
        "volume_up": "volume_up",
        "volume_down": "volume_down",
        "volume_mute": "volume_mute",
        "screenshot": "screenshot",
        "sleep": "sleep",
    }

    mapped = aliases.get(action)

    if mapped is None:
        return jsonify({
            "ok": False,
            "error": "Invalid system action",
        }), 400

    # Execute through the same implementation as /api/windows-action.
    # Reuse the action logic without duplicating platform code.
    data["action"] = mapped

    # Temporarily replace request JSON is not appropriate; execute directly.
    try:
        if mapped == "volume_up":
            pyautogui.press("volumeup")
            message = "Volume increased."
        elif mapped == "volume_down":
            pyautogui.press("volumedown")
            message = "Volume decreased."
        elif mapped == "volume_mute":
            pyautogui.press("volumemute")
            message = "Mute toggled."
        elif mapped == "screenshot":
            pictures = Path.home() / "Pictures" / "Screenshots"
            pictures.mkdir(parents=True, exist_ok=True)
            filename = pictures / (
                "Screenshot_" +
                datetime.now().strftime("%Y%m%d_%H%M%S") +
                ".png"
            )
            pyautogui.screenshot(str(filename))
            message = f"Screenshot saved to {filename}"
        elif mapped == "lock_pc":
            subprocess.Popen(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            message = "PC locked."
        else:  # sleep
            subprocess.Popen(
                [
                    "powershell.exe", "-NoProfile", "-Command",
                    "Start-Sleep -Milliseconds 500; "
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "[System.Windows.Forms.Application]::SetSuspendState("
                    "'Suspend', $false, $false)"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            message = "Putting the PC to sleep."

        log.info("System action executed: %s -> %s", action, mapped)
        return jsonify({
            "ok": True,
            "action": mapped,
            "message": message,
        })
    except Exception as exc:
        log.exception("System action failed: %s", mapped)
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 500


# ============================================================
# KEYBOARD
# ============================================================

@app.post("/api/key")
@require_auth
def key():

    data = request.get_json(
        silent=True
    ) or {}

    key_name = str(
        data.get(
            "key",
            "",
        )
    ).lower()

    action = str(
        data.get(
            "action",
            "press",
        )
    ).lower()

    if key_name not in ALLOWED_KEYS:

        return jsonify({
            "ok": False,
            "error": "Key not allowed",
        }), 400

    if action not in (
        "press",
        "down",
        "up",
    ):

        return jsonify({
            "ok": False,
            "error": "Invalid key action",
        }), 400

    if action == "press":
        pyautogui.press(key_name)

    elif action == "down":
        pyautogui.keyDown(key_name)

    else:
        pyautogui.keyUp(key_name)

    return jsonify({
        "ok": True
    })


# ============================================================
# PHONE VOICE
# ============================================================

@app.post("/api/voice")
@require_auth
def voice():

    uploaded = request.files.get(
        "audio"
    )

    if uploaded is None:

        return jsonify({
            "ok": False,
            "error": "No audio file received.",
        }), 400

    temp_path = None

    try:

        suffix = (
            Path(
                uploaded.filename
                or "voice.webm"
            ).suffix
            or ".webm"
        )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=str(BASE_DIR),
        ) as temp:

            uploaded.save(
                temp.name
            )

            temp_path = temp.name

        print(
            "Phone voice: transcribing..."
        )

        text = transcribe_phone_audio(
            temp_path
        )

        if not text:

            return jsonify({
                "ok": True,
                "text": "",
                "message":
                    "I could not hear a command.",
            })

        print(
            f"Phone voice: {text}"
        )
        set_assistant_state("thinking", text=text, message="")

        command = _phone_parser.parse(
            text
        )

        if command.action == "unknown":

            print(
                "Phone voice: sending to local AI..."
            )
            set_assistant_state("thinking", text=text, action="ai_conversation")

            try:
                answer = _phone_ai.ask(text)

            except Exception as exc:
                log.exception(
                    "Phone AI response failed"
                )

                return jsonify({
                    "ok": False,
                    "text": text,
                    "action": "ai_error",
                    "error": (
                        "Local AI unavailable: "
                        + str(exc)
                    ),
                }), 500

            set_assistant_state("speaking", text=text, message=answer, action="ai_conversation")
            threading.Timer(2.5, lambda: set_assistant_state("listening")).start()
            return jsonify({
                "ok": True,
                "text": text,
                "action": "ai_conversation",
                "message": answer,
            })

        if command.action == "stop":

            return jsonify({
                "ok": True,
                "text": text,
                "action": "stop",
                "message":
                    "Stop command is handled by the main assistant.",
            })

        set_assistant_state("executing", text=text, message="", action=command.action)
        result = _phone_safety.execute(
            command
        )
        set_assistant_state("speaking", text=text, message=result.message, action=command.action)
        threading.Timer(2.5, lambda: set_assistant_state("listening")).start()

        return jsonify({
            "ok": True,
            "text": text,
            "action": command.action,
            "message": result.message,
        })

    except Exception as exc:

        log.exception(
            "Phone voice command failed"
        )
        set_assistant_state("speaking", message="Something went wrong.", action="error")

        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 500

    finally:

        if temp_path:

            try:
                os.remove(
                    temp_path
                )
            except OSError:
                pass


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("==============================")
    print("PHONE PC CONTROLLER")
    print("==============================")
    print(
        f"Open https://<PC-IP>:{PORT} "
        "on your phone."
    )
    print()
    print(
        "Development PIN: akshaykumar"
    )
    print()
    print(
        "Local device approval:"
    )
    print(
        f"https://127.0.0.1:{PORT}/admin/devices"
    )
    print()
    print(
        "Phone Voice: OFFLINE WHISPER"
    )
    print(
        "Press Ctrl+C to stop."
    )
    print()

    cert_file = BASE_DIR / "192.168.1.4+2.pem"
    key_file = BASE_DIR / "192.168.1.4+2-key.pem"

    # The old build hard-coded certificate filenames. If those files are absent,
    # Flask crashes with FileNotFoundError before the phone controller starts.
    # Prefer the user's certificates when available; otherwise generate a
    # temporary development certificate automatically.
    if cert_file.exists() and key_file.exists():
        ssl_context = (str(cert_file), str(key_file))
        print("HTTPS: using local certificate files.")
    else:
        ssl_context = "adhoc"
        print("HTTPS: certificate files not found; using a temporary development certificate.")
        print("The browser may show a certificate warning on first connection.")

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        threaded=True,
        ssl_context=ssl_context,
    )

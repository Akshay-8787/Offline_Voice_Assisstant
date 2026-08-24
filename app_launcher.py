from __future__ import annotations

import ctypes
import json
import logging
import os
import shutil
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import pyautogui


class AppLauncher:
    """Open apps and control their windows safely."""

    CACHE_FILE = Path(__file__).with_name("app_cache.json")

    SEARCH_ROOTS = [
        Path(os.environ.get("APPDATA", ""))
        / r"Microsoft\Windows\Start Menu\Programs",
        Path(os.environ.get("PROGRAMDATA", ""))
        / r"Microsoft\Windows\Start Menu\Programs",
        Path(os.environ.get("USERPROFILE", ""))
        / "Desktop",
        Path(os.environ.get("PUBLIC", ""))
        / "Desktop",
    ]

    ALLOWED_SUFFIXES = {".exe", ".lnk"}

    # Windows ShowWindow constants
    SW_MINIMIZE = 6
    SW_MAXIMIZE = 3
    SW_RESTORE = 9

    # Windows message
    WM_CLOSE = 0x0010

    def __init__(self) -> None:
        self.log = logging.getLogger("app_launcher")
        self.cache = self._load_cache()

    # =========================================================
    # NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize(name: str) -> str:
        text = name.lower().strip()

        for suffix in (".exe", ".lnk"):
            if text.endswith(suffix):
                text = text[:-len(suffix)]

        return " ".join(
            text.replace("_", " ")
            .replace("-", " ")
            .split()
        )

    # =========================================================
    # CACHE
    # =========================================================

    def _load_cache(self) -> dict[str, str]:
        try:
            if self.CACHE_FILE.exists():

                data = json.loads(
                    self.CACHE_FILE.read_text(
                        encoding="utf-8"
                    )
                )

                if isinstance(data, dict):
                    return {
                        str(k): str(v)
                        for k, v in data.items()
                    }

        except Exception:
            self.log.exception(
                "Could not load app cache"
            )

        return {}

    def _save_cache(self) -> None:
        try:
            self.CACHE_FILE.write_text(
                json.dumps(
                    self.cache,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        except Exception:
            self.log.exception(
                "Could not save app cache"
            )

    # =========================================================
    # OPEN PATH
    # =========================================================

    def _open_path(self, path: str) -> bool:
        try:
            target = Path(path)

            if not target.exists():
                return False

            os.startfile(str(target))

            return True

        except (OSError, ValueError):
            self.log.exception(
                "Could not open %s",
                path,
            )

            return False

    # =========================================================
    # CACHE SEARCH
    # =========================================================

    def _cached_path(
        self,
        query: str,
    ) -> Optional[str]:

        key = self._normalize(query)

        path = self.cache.get(key)

        if path and Path(path).exists():
            return path

        if path:
            self.cache.pop(key, None)
            self._save_cache()

        return None

    # =========================================================
    # LOCAL APP SEARCH
    # =========================================================

    def _search_files(
        self,
        query: str,
    ) -> Optional[str]:

        q = self._normalize(query)

        if not q:
            return None

        candidates: list[
            tuple[float, str]
        ] = []

        for root in self.SEARCH_ROOTS:

            if not root.exists():
                continue

            try:

                for path in root.rglob("*"):

                    if (
                        not path.is_file()
                        or path.suffix.lower()
                        not in self.ALLOWED_SUFFIXES
                    ):
                        continue

                    name = self._normalize(
                        path.stem
                    )

                    if not name:
                        continue

                    if name == q:
                        score = 1.0

                    elif q in name:
                        score = 0.92

                    else:
                        score = SequenceMatcher(
                            None,
                            q,
                            name,
                        ).ratio()

                    if score >= 0.72:
                        candidates.append(
                            (
                                score,
                                str(path),
                            )
                        )

            except (
                OSError,
                PermissionError,
            ):
                continue

        exe = shutil.which(query)

        if exe:
            return exe

        if candidates:

            candidates.sort(
                key=lambda item: item[0],
                reverse=True,
            )

            best_score, best_path = (
                candidates[0]
            )

            if best_score >= 0.80:
                return best_path

        return None

    # =========================================================
    # WINDOWS SEARCH
    # =========================================================

    def _windows_search(
        self,
        app_name: str,
    ) -> bool:

        query = self._normalize(
            app_name
        )

        if not query:
            return False

        try:

            pyautogui.press("win")

            time.sleep(0.7)

            pyautogui.hotkey(
                "ctrl",
                "a",
            )

            pyautogui.write(
                query,
                interval=0.02,
            )

            time.sleep(1.5)

            pyautogui.press("enter")

            time.sleep(1.0)

            return True

        except Exception:

            self.log.exception(
                "Windows Search fallback failed"
            )

            return False

    # =========================================================
    # FIND + OPEN
    # =========================================================

    def find_and_open(
        self,
        app_name: str,
    ) -> tuple[
        bool,
        bool,
        Optional[str],
    ]:

        query = self._normalize(
            app_name
        )

        # 1. Cache
        cached = self._cached_path(
            query
        )

        if cached and self._open_path(
            cached
        ):
            return (
                True,
                True,
                cached,
            )

        # 2. Local search
        found = self._search_files(
            query
        )

        if found:

            self.cache[query] = found
            self._save_cache()

            if self._open_path(found):
                return (
                    True,
                    True,
                    found,
                )

        # 3. Windows Search
        if self._windows_search(
            query
        ):
            return (
                True,
                True,
                None,
            )

        return (
            False,
            False,
            None,
        )

    # =========================================================
    # KNOWN APPLICATIONS
    # =========================================================

    def open_known(
        self,
        app_name: str,
    ) -> tuple[bool, str]:

        key = self._normalize(
            app_name
        )

        # File Explorer
        if key in {
            "file manager",
            "file explorer",
            "explorer",
            "my files",
            "files",
        }:

            try:

                os.startfile(
                    "explorer.exe"
                )

                return (
                    True,
                    "Opening File Explorer.",
                )

            except OSError:

                return (
                    False,
                    "Unable to open File Explorer.",
                )

        # WhatsApp
        if key in {
            "whatsapp",
            "whatsapp desktop",
        }:

            try:

                os.startfile(
                    "whatsapp:"
                )

                return (
                    True,
                    "Opening WhatsApp.",
                )

            except OSError:
                pass

        # Chrome
        if key in {
            "chrome",
            "google chrome",
        }:

            chrome = shutil.which(
                "chrome.exe"
            )

            if chrome and self._open_path(
                chrome
            ):
                return (
                    True,
                    "Opening Chrome.",
                )

            for path in (
                Path(
                    os.environ.get(
                        "PROGRAMFILES",
                        "",
                    )
                )
                / r"Google\Chrome\Application\chrome.exe",

                Path(
                    os.environ.get(
                        "PROGRAMFILES(X86)",
                        "",
                    )
                )
                / r"Google\Chrome\Application\chrome.exe",

                Path(
                    os.environ.get(
                        "LOCALAPPDATA",
                        "",
                    )
                )
                / r"Google\Chrome\Application\chrome.exe",
            ):

                if (
                    path.exists()
                    and self._open_path(
                        str(path)
                    )
                ):

                    return (
                        True,
                        "Opening Chrome.",
                    )

        return (
            False,
            "",
        )

    # =========================================================
    # OPEN APPLICATION
    # =========================================================

    def open_application(
        self,
        app_name: str,
    ) -> tuple[bool, str]:

        known_ok, known_message = (
            self.open_known(app_name)
        )

        if known_ok:
            return (
                True,
                known_message,
            )

        opened, found, _ = (
            self.find_and_open(
                app_name
            )
        )

        if opened:
            return (
                True,
                f"Opening {app_name}.",
            )

        if found:
            return (
                False,
                f"I found {app_name}, "
                "but I was unable to open it.",
            )

        return (
            False,
            f"Unable to find "
            f"{app_name} on this PC.",
        )

    # =========================================================
    # WINDOW SEARCH
    # =========================================================

    def _find_windows(
        self,
        app_name: str,
    ) -> list[int]:
        """
        Find visible Windows whose title
        contains the requested application name.
        """

        query = self._normalize(
            app_name
        )

        if not query:
            return []

        user32 = ctypes.windll.user32

        results: list[int] = []

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )

        def callback(
            hwnd,
            lparam,
        ):

            try:

                if not user32.IsWindowVisible(
                    hwnd
                ):
                    return True

                length = user32.GetWindowTextLengthW(
                    hwnd
                )

                if length <= 0:
                    return True

                buffer = ctypes.create_unicode_buffer(
                    length + 1
                )

                user32.GetWindowTextW(
                    hwnd,
                    buffer,
                    length + 1,
                )

                title = self._normalize(
                    buffer.value
                )

                if not title:
                    return True

                # Exact application title
                if query == title:
                    results.append(
                        int(hwnd)
                    )
                    return True

                # Application name appears in title
                if query in title:
                    results.append(
                        int(hwnd)
                    )
                    return True

                # Fuzzy match for longer titles
                score = SequenceMatcher(
                    None,
                    query,
                    title,
                ).ratio()

                if (
                    len(query) >= 4
                    and score >= 0.72
                ):
                    results.append(
                        int(hwnd)
                    )

            except Exception:
                return True

            return True

        callback_ref = EnumWindowsProc(
            callback
        )

        user32.EnumWindows(
            callback_ref,
            0,
        )

        return results

    # =========================================================
    # SWITCH WINDOW
    # =========================================================

    def switch_window(
        self,
        app_name: str,
    ) -> tuple[bool, str]:

        windows = self._find_windows(
            app_name
        )

        if not windows:
            return (
                False,
                f"I couldn't find an open "
                f"{app_name} window.",
            )

        hwnd = windows[0]

        user32 = ctypes.windll.user32

        try:

            # Restore if minimized
            user32.ShowWindow(
                hwnd,
                self.SW_RESTORE,
            )

            # Bring window to foreground
            user32.SetForegroundWindow(
                hwnd
            )

            return (
                True,
                f"Switching to {app_name}.",
            )

        except Exception:

            self.log.exception(
                "Could not switch to %s",
                app_name,
            )

            return (
                False,
                f"I couldn't switch to "
                f"{app_name}.",
            )

    # =========================================================
    # MINIMIZE WINDOW
    # =========================================================

    def minimize_window(
        self,
        app_name: str,
    ) -> tuple[bool, str]:

        windows = self._find_windows(
            app_name
        )

        if not windows:
            return (
                False,
                f"I couldn't find an open "
                f"{app_name} window.",
            )

        user32 = ctypes.windll.user32

        try:

            user32.ShowWindow(
                windows[0],
                self.SW_MINIMIZE,
            )

            return (
                True,
                f"Minimizing {app_name}.",
            )

        except Exception:

            self.log.exception(
                "Could not minimize %s",
                app_name,
            )

            return (
                False,
                f"I couldn't minimize "
                f"{app_name}.",
            )

    # =========================================================
    # MAXIMIZE WINDOW
    # =========================================================

    def maximize_window(
        self,
        app_name: str,
    ) -> tuple[bool, str]:

        windows = self._find_windows(
            app_name
        )

        if not windows:
            return (
                False,
                f"I couldn't find an open "
                f"{app_name} window.",
            )

        user32 = ctypes.windll.user32

        try:

            user32.ShowWindow(
                windows[0],
                self.SW_MAXIMIZE,
            )

            user32.SetForegroundWindow(
                windows[0]
            )

            return (
                True,
                f"Maximizing {app_name}.",
            )

        except Exception:

            self.log.exception(
                "Could not maximize %s",
                app_name,
            )

            return (
                False,
                f"I couldn't maximize "
                f"{app_name}.",
            )

    # =========================================================
    # CLOSE WINDOW
    # =========================================================

    def close_window(
        self,
        app_name: str,
    ) -> tuple[bool, str]:

        windows = self._find_windows(
            app_name
        )

        if not windows:
            return (
                False,
                f"I couldn't find an open "
                f"{app_name} window.",
            )

        user32 = ctypes.windll.user32

        try:

            # Send normal Windows close request.
            user32.PostMessageW(
                windows[0],
                self.WM_CLOSE,
                0,
                0,
            )

            return (
                True,
                f"Closing {app_name}.",
            )

        except Exception:

            self.log.exception(
                "Could not close %s",
                app_name,
            )

            return (
                False,
                f"I couldn't close "
                f"{app_name}.",
            )
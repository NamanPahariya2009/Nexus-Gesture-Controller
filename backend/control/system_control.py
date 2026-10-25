import os
import platform
import time
import pyautogui

_PLATFORM = platform.system()


def _set_volume_windows(level: int):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, level / 100.0)), None)
    except Exception as e:
        print(f"[Volume] Windows error: {e}")


def _set_volume_mac(level: int):
    try:
        os.system(f"osascript -e 'set volume output volume {level}'")
    except Exception as e:
        print(f"[Volume] macOS error: {e}")


def _set_volume_linux(level: int):
    try:
        os.system(f"pactl set-sink-volume @DEFAULT_SINK@ {level}%")
    except Exception as e:
        print(f"[Volume] Linux error: {e}")


def set_volume(level: int):
    level = max(0, min(100, level))
    if _PLATFORM == "Windows":
        _set_volume_windows(level)
    elif _PLATFORM == "Darwin":
        _set_volume_mac(level)
    else:
        _set_volume_linux(level)


class DesktopSwitcher:
    def __init__(self):
        self.swipe_start_x = None
        self.last_swipe_time = 0.0

    def update(self, current_x: float, cooldown: float, threshold: float):
        now = time.time()
        if (now - self.last_swipe_time) < cooldown:
            return None

        if self.swipe_start_x is None:
            self.swipe_start_x = current_x
            return None

        dx = current_x - self.swipe_start_x
        if abs(dx) > threshold:
            self.last_swipe_time = now
            self.swipe_start_x = None

            if dx > 0:
                if _PLATFORM == "Darwin":
                    pyautogui.hotkey('ctrl', 'right')
                else:
                    pyautogui.hotkey('win', 'ctrl', 'right')
                return "right"
            else:
                if _PLATFORM == "Darwin":
                    pyautogui.hotkey('ctrl', 'left')
                else:
                    pyautogui.hotkey('win', 'ctrl', 'left')
                return "left"

        return None

    def reset(self):
        self.swipe_start_x = None

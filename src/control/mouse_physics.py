import math
import platform
import ctypes
import pyautogui
import config

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

_IS_WINDOWS = platform.system() == "Windows"
if _IS_WINDOWS:
    _user32 = ctypes.windll.user32


class PhysicsCursor:
    def __init__(self):
        self.prev_dx = 0.0
        self.prev_dy = 0.0
        self.remainder_x = 0.0
        self.remainder_y = 0.0

    def reset(self):
        self.prev_dx = 0.0
        self.prev_dy = 0.0
        self.remainder_x = 0.0
        self.remainder_y = 0.0

    def update_relative(self, dx, dy, dt=0.0):
        mag = math.hypot(dx, dy)

        if mag < config.DEAD_ZONE:
            self.prev_dx *= 0.5
            self.prev_dy *= 0.5
            return

        effective_mag = mag - config.DEAD_ZONE
        scale = effective_mag / mag
        dx *= scale
        dy *= scale

        if getattr(config, 'DELTA_SMOOTHING', 0.0) > 0.0:
            alpha = 1.0 - config.DELTA_SMOOTHING
            dx = alpha * dx + (1.0 - alpha) * self.prev_dx
            dy = alpha * dy + (1.0 - alpha) * self.prev_dy

        self.prev_dx = dx
        self.prev_dy = dy

        gain = config.BASE_SENSITIVITY * (1.0 + config.ACCELERATION_FACTOR * mag)
        gain = min(gain, config.MAX_SENSITIVITY)

        move_x = dx * config.WINDOW_WIDTH * gain
        move_y = dy * config.WINDOW_HEIGHT * gain

        self.remainder_x += move_x
        self.remainder_y += move_y

        int_move_x = int(self.remainder_x)
        int_move_y = int(self.remainder_y)

        if int_move_x != 0 or int_move_y != 0:
            if _IS_WINDOWS:
                _user32.mouse_event(0x0001, int_move_x, int_move_y, 0, 0)
            else:
                pyautogui.move(int_move_x, int_move_y, _pause=False)

            self.remainder_x -= int_move_x
            self.remainder_y -= int_move_y

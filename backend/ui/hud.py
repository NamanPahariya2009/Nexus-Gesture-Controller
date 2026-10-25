import cv2
import numpy as np
from collections import deque
import config

INDEX_MCP = 5
PINKY_MCP = 17
WRIST = 0

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


class CinematicHUD:
    def __init__(self):
        self.trail = deque(maxlen=20)
        self.pulse_phase = 0.0

    def _palm_center(self, hand_landmarks, w, h):
        idx = hand_landmarks[INDEX_MCP]
        pnk = hand_landmarks[PINKY_MCP]
        wrs = hand_landmarks[WRIST]
        cx = int((idx.x + pnk.x + wrs.x) / 3 * w)
        cy = int((idx.y + pnk.y + wrs.y) / 3 * h)
        return cx, cy

    def draw(self, img, hand_landmarks, state, confidence, meta=None):
        if meta is None:
            meta = {}

        h, w, _ = img.shape

        if state == "SLEEPING":
            cv2.rectangle(img, (0, 0), (w, h), config.COLOR_SLEEP, 10)
            cv2.putText(img, "SLEEPING  (Middle Finger to Wake)",
                        (w // 2 - 250, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, config.COLOR_SLEEP, 2)
            self.trail.clear()
            return

        if state == "SLEEP_TOGGLE":
            remaining = meta.get("remaining", 0)
            label = "WAKING..." if meta.get("will_activate") else "SLEEPING..."
            cv2.putText(img, f"{label} {remaining:.1f}s",
                        (w // 2 - 120, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            return

        if hand_landmarks is None:
            self.trail.clear()
            return

        cx, cy = self._palm_center(hand_landmarks, w, h)

        if getattr(config, 'SHOW_SKELETON', True):
            pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]
            for p1, p2 in HAND_CONNECTIONS:
                if p1 < len(pts) and p2 < len(pts):
                    cv2.line(img, pts[p1], pts[p2], (180, 180, 50), 1)
            for px, py in pts:
                cv2.circle(img, (px, py), 3, (0, 255, 255), -1)

        self.trail.appendleft((cx, cy))
        for i in range(1, len(self.trail)):
            thickness = int(np.sqrt(20 / i) * 2)
            cv2.line(img, self.trail[i - 1], self.trail[i],
                     config.COLOR_IDLE, thickness)

        self.pulse_phase += 0.1
        radius = int(40 + np.sin(self.pulse_phase) * 5)
        color = config.COLOR_IDLE

        if state == "MOVE":
            color = config.COLOR_MOVE
            radius = 20
        elif state == "CLICK_LEFT":
            color = config.COLOR_CLICK
            radius = 35
            cv2.circle(img, (cx, cy), radius, color, 3)
        elif state == "CLICK_RIGHT":
            color = config.COLOR_RIGHT_CLICK
            radius = 35
            cv2.putText(img, "R", (cx - 10, cy + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        elif state == "DOUBLE_CLICK":
            color = config.COLOR_DOUBLE_CLICK
            radius = 35
            cv2.putText(img, "2x", (cx - 15, cy + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        elif state == "DRAG_ACTIVE":
            color = config.COLOR_DRAG_ACTIVE
            radius = 35
            cv2.circle(img, (cx, cy), radius, color, 4)
            cv2.rectangle(img, (cx - 10, cy - 10), (cx + 10, cy + 10),
                          color, -1)
        elif state == "FIST":
            color = (0, 165, 255)
            radius = 30
            cv2.putText(img, "TOGGLE", (cx - 25, cy - 40),
                        cv2.FONT_HERSHEY_PLAIN, 1, color, 1)
        elif state == "SCROLL":
            color = config.COLOR_SCROLL
            radius = 45
            cv2.arrowedLine(img, (cx, cy - 20), (cx, cy - 60), color, 2)
            cv2.arrowedLine(img, (cx, cy + 20), (cx, cy + 60), color, 2)
        elif state == "VOLUME":
            color = config.COLOR_VOLUME
            radius = 30
            vol = meta.get("volume_pct", 0)
            bar_top, bar_bot = 150, 400
            cv2.rectangle(img, (50, bar_top), (85, bar_bot), color, 3)
            filled_y = int(np.interp(vol, [0, 100], [bar_bot, bar_top]))
            cv2.rectangle(img, (50, filled_y), (85, bar_bot), color, cv2.FILLED)
            cv2.putText(img, f"{int(vol)}%", (40, bar_bot + 30),
                        cv2.FONT_HERSHEY_PLAIN, 2, color, 2)
        elif state == "SWIPE":
            color = config.COLOR_SWIPE
            radius = 30
            direction = meta.get("swipe_dir")
            if direction == "right":
                cv2.arrowedLine(img, (cx - 40, cy), (cx + 40, cy), color, 3)
                cv2.putText(img, "NEXT DESKTOP", (cx - 80, cy - 40),
                            cv2.FONT_HERSHEY_PLAIN, 2, color, 2)
            elif direction == "left":
                cv2.arrowedLine(img, (cx + 40, cy), (cx - 40, cy), color, 3)
                cv2.putText(img, "PREV DESKTOP", (cx - 80, cy - 40),
                            cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

        cv2.ellipse(img, (cx, cy), (radius, radius),
                    self.pulse_phase * 50, 0, 270, color, 2)

        cv2.putText(img, f"STATUS: {state}", (cx + 50, cy - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

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

GUIDE_ITEMS = [
    ("Move", "Right Palm / Index"),
    ("Left Click", "Thumb + Index"),
    ("Right Click", "Thumb + Middle"),
    ("Double Click", "Thumb + Ring"),
    ("Drag / Drop", "Closed Fist"),
    ("Scroll", "Left Peace Sign"),
    ("Volume", "Left Pinky (Height)"),
    ("Zoom", "Two-Hand Spread"),
    ("Desktop", "Left 4-Finger Swipe"),
    ("Pause/Wake", "Hold Middle (1s)"),
    ("Quit / Screen", "Press Q / F"),
]


class CinematicHUD:
    def __init__(self):
        self.trail = deque(maxlen=20)
        self.pulse_phase = 0.0

    def _draw_guide(self, img):
        if not getattr(config, 'SHOW_GUIDE', True):
            return
        h, w = img.shape[:2]
        panel_w = 260
        panel_h = 335
        panel_x = w - panel_w - 20
        panel_y = 20

        overlay = img.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (25, 25, 25), -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)
        cv2.rectangle(img, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (70, 70, 70), 1)

        cv2.putText(img, "GESTURE GUIDE", (panel_x + 15, panel_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
        cv2.line(img, (panel_x + 15, panel_y + 35), (panel_x + panel_w - 15, panel_y + 35), (70, 70, 70), 1)

        y = panel_y + 58
        for action, gesture in GUIDE_ITEMS:
            cv2.putText(img, f"{action}:", (panel_x + 15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)
            cv2.putText(img, gesture, (panel_x + 110, y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
            y += 24

    def _palm_center(self, hand_landmarks, w, h):
        idx = hand_landmarks[INDEX_MCP]
        pnk = hand_landmarks[PINKY_MCP]
        wrs = hand_landmarks[WRIST]
        mid = hand_landmarks[9]
        cx = int((idx.x + pnk.x + wrs.x + mid.x * 2.0) / 5.0 * w)
        cy = int((idx.y + pnk.y + wrs.y + mid.y * 2.0) / 5.0 * h)
        return cx, cy

    def _draw_skeleton(self, img, landmarks, w, h, color):
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        for p1, p2 in HAND_CONNECTIONS:
            if p1 < len(pts) and p2 < len(pts):
                cv2.line(img, pts[p1], pts[p2], color, 1)
        for px, py in pts:
            cv2.circle(img, (px, py), 3, (0, 255, 255), -1)

    def draw(self, img, hand_landmarks, state, confidence=1.0, meta=None,
             secondary_landmarks=None, state_s=None, meta_s=None, zoom_active=False):
        if meta is None:
            meta = {}
        if meta_s is None:
            meta_s = {}

        self._draw_guide(img)
        h, w, _ = img.shape

        if state == "SLEEPING" or state_s == "SLEEPING":
            cv2.rectangle(img, (0, 0), (w, h), config.COLOR_SLEEP, 10)
            cv2.putText(img, "SLEEPING  (Middle Finger to Wake)",
                        (w // 2 - 250, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, config.COLOR_SLEEP, 2)
            self.trail.clear()
            return

        if state == "SLEEP_TOGGLE" or state_s == "SLEEP_TOGGLE":
            active_meta = meta if state == "SLEEP_TOGGLE" else meta_s
            remaining = active_meta.get("remaining", 0)
            label = "WAKING..." if active_meta.get("will_activate") else "SLEEPING..."
            cv2.putText(img, f"{label} {remaining:.1f}s",
                        (w // 2 - 120, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            return

        cx_sec, cy_sec = None, None
        if secondary_landmarks is not None:
            cx_sec, cy_sec = self._palm_center(secondary_landmarks, w, h)
            if getattr(config, 'SHOW_SKELETON', True):
                self._draw_skeleton(img, secondary_landmarks, w, h, (180, 50, 180))

            cv2.circle(img, (cx_sec, cy_sec), 25, config.COLOR_SECONDARY, 2)
            cv2.putText(img, f"SEC: {state_s or 'IDLE'}", (cx_sec - 40, cy_sec - 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, config.COLOR_SECONDARY, 1)

            if state_s == "VOLUME":
                vol = meta_s.get("volume_pct", 0)
                bar_top, bar_bot = 150, 400
                cv2.rectangle(img, (50, bar_top), (85, bar_bot), config.COLOR_VOLUME, 3)
                filled_y = int(np.interp(vol, [0, 100], [bar_bot, bar_top]))
                cv2.rectangle(img, (50, filled_y), (85, bar_bot), config.COLOR_VOLUME, cv2.FILLED)
                cv2.putText(img, f"{int(vol)}%", (40, bar_bot + 30),
                            cv2.FONT_HERSHEY_PLAIN, 2, config.COLOR_VOLUME, 2)

            elif state_s == "SCROLL":
                cv2.arrowedLine(img, (cx_sec, cy_sec - 20), (cx_sec, cy_sec - 60), config.COLOR_SCROLL, 2)
                cv2.arrowedLine(img, (cx_sec, cy_sec + 20), (cx_sec, cy_sec + 60), config.COLOR_SCROLL, 2)

            elif state_s == "SWIPE":
                direction = meta_s.get("swipe_dir")
                if direction == "right":
                    cv2.arrowedLine(img, (cx_sec - 40, cy_sec), (cx_sec + 40, cy_sec), config.COLOR_SWIPE, 3)
                    cv2.putText(img, "NEXT DESKTOP", (cx_sec - 80, cy_sec - 40),
                                cv2.FONT_HERSHEY_PLAIN, 2, config.COLOR_SWIPE, 2)
                elif direction == "left":
                    cv2.arrowedLine(img, (cx_sec + 40, cy_sec), (cx_sec - 40, cy_sec), config.COLOR_SWIPE, 3)
                    cv2.putText(img, "PREV DESKTOP", (cx_sec - 80, cy_sec - 40),
                                cv2.FONT_HERSHEY_PLAIN, 2, config.COLOR_SWIPE, 2)

        if hand_landmarks is None:
            self.trail.clear()
            return

        cx, cy = self._palm_center(hand_landmarks, w, h)

        if zoom_active and cx_sec is not None:
            mid_x = (cx + cx_sec) // 2
            mid_y = (cy + cy_sec) // 2
            cv2.line(img, (cx, cy), (cx_sec, cy_sec), config.COLOR_ZOOM, 2)
            cv2.circle(img, (mid_x, mid_y), 20, config.COLOR_ZOOM, -1)
            cv2.putText(img, "ZOOM", (mid_x - 17, mid_y + 4), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 0, 0), 2)

        if getattr(config, 'SHOW_SKELETON', True):
            self._draw_skeleton(img, hand_landmarks, w, h, (180, 180, 50))

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
        elif state == "SCROLL" and secondary_landmarks is None:
            color = config.COLOR_SCROLL
            radius = 45
            cv2.arrowedLine(img, (cx, cy - 20), (cx, cy - 60), color, 2)
            cv2.arrowedLine(img, (cx, cy + 20), (cx, cy + 60), color, 2)
        elif state == "VOLUME" and secondary_landmarks is None:
            color = config.COLOR_VOLUME
            radius = 30
            vol = meta.get("volume_pct", 0)
            bar_top, bar_bot = 150, 400
            cv2.rectangle(img, (50, bar_top), (85, bar_bot), color, 3)
            filled_y = int(np.interp(vol, [0, 100], [bar_bot, bar_top]))
            cv2.rectangle(img, (50, filled_y), (85, bar_bot), color, cv2.FILLED)
            cv2.putText(img, f"{int(vol)}%", (40, bar_bot + 30),
                        cv2.FONT_HERSHEY_PLAIN, 2, color, 2)
        elif state == "SWIPE" and secondary_landmarks is None:
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

        label_prefix = "PRI: " if secondary_landmarks is not None else "STATUS: "
        cv2.putText(img, f"{label_prefix}{state}", (cx + 50, cy - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

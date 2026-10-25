import math
import time
import config

WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_MCP = 17
PINKY_TIP = 20

INDEX_PIP = 6
MIDDLE_PIP = 10
RING_PIP = 14
PINKY_PIP = 18


class GestureClassifier:
    def __init__(self):
        self.state = "IDLE"
        self.pinch_confidence = 0.0
        self.system_active = True
        self.sleep_hold_start = 0.0
        self.last_sleep_toggle = 0.0
        self.prev_wrist = None
        self.last_update = time.time()

    @staticmethod
    def _fingers_up(landmarks):
        up = [False] * 5
        for i, (tip, pip) in enumerate([
            (INDEX_TIP, INDEX_PIP),
            (MIDDLE_TIP, MIDDLE_PIP),
            (RING_TIP, RING_PIP),
            (PINKY_TIP, PINKY_PIP),
        ]):
            up[i + 1] = landmarks[tip].y < landmarks[pip].y

        thumb_tip = landmarks[THUMB_TIP]
        index_mcp = landmarks[INDEX_MCP]
        up[0] = math.hypot(thumb_tip.x - index_mcp.x, thumb_tip.y - index_mcp.y) > 0.05
        return up

    @staticmethod
    def _pinch_dist(landmarks, tip_a, tip_b):
        a = landmarks[tip_a]
        b = landmarks[tip_b]
        return math.hypot(a.x - b.x, a.y - b.y)

    def process(self, landmarks):
        if landmarks is None:
            self.state = "IDLE"
            self.pinch_confidence = 0.0
            self.prev_wrist = None
            self.sleep_hold_start = 0.0
            return self.state, {}

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        fingers = self._fingers_up(landmarks)

        wrist = landmarks[WRIST]
        velocity = 0.0
        if self.prev_wrist is not None and dt > 0:
            dx = wrist.x - self.prev_wrist.x
            dy = wrist.y - self.prev_wrist.y
            velocity = math.hypot(dx, dy) / dt
        self.prev_wrist = wrist

        dist_index = self._pinch_dist(landmarks, THUMB_TIP, INDEX_TIP)
        dist_middle = self._pinch_dist(landmarks, THUMB_TIP, MIDDLE_TIP)
        dist_ring = self._pinch_dist(landmarks, THUMB_TIP, RING_TIP)

        middle_only = (not fingers[0] and not fingers[1] and fingers[2]
                       and not fingers[3] and not fingers[4])

        if middle_only:
            if self.sleep_hold_start == 0.0:
                self.sleep_hold_start = now
            elapsed = now - self.sleep_hold_start
            remaining = max(0, config.SLEEP_HOLD_TIME - elapsed)

            if elapsed >= config.SLEEP_HOLD_TIME:
                if (now - self.last_sleep_toggle) > config.SLEEP_TOGGLE_COOLDOWN:
                    self.system_active = not self.system_active
                    self.last_sleep_toggle = now
                    self.sleep_hold_start = 0.0

            self.state = "SLEEP_TOGGLE"
            return self.state, {
                "remaining": remaining,
                "will_activate": not self.system_active,
                "confidence": 1.0,
            }
        else:
            self.sleep_hold_start = 0.0

        if not self.system_active:
            self.state = "SLEEPING"
            return self.state, {"confidence": 0.0}

        if dist_index < config.PINCH_THRESHOLD_NORM:
            self.state = "CLICK_LEFT"
            return self.state, {"confidence": 1.0, "pinch_dist": dist_index}

        if dist_middle < config.PINCH_THRESHOLD_NORM:
            self.state = "CLICK_RIGHT"
            return self.state, {"confidence": 1.0, "pinch_dist": dist_middle}

        if dist_ring < config.PINCH_THRESHOLD_NORM:
            self.state = "DOUBLE_CLICK"
            return self.state, {"confidence": 1.0, "pinch_dist": dist_ring}

        if fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
            self.state = "SCROLL"
            return self.state, {"norm_y": landmarks[INDEX_TIP].y, "confidence": 1.0}

        if not fingers[1] and not fingers[2] and not fingers[3] and fingers[4]:
            self.state = "VOLUME"
            return self.state, {"norm_y": landmarks[PINKY_TIP].y, "confidence": 1.0}

        if fingers[1] and fingers[2] and fingers[3] and fingers[4]:
            self.state = "SWIPE"
            return self.state, {"norm_x": landmarks[MIDDLE_TIP].x, "confidence": 1.0}

        if not any(fingers[1:]):
            self.state = "FIST"
            return self.state, {"confidence": 1.0}

        if all(fingers) or (fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]):
            self.state = "MOVE"
            return self.state, {"confidence": 1.0}

        self.state = "IDLE"
        return self.state, {"confidence": 0.0}

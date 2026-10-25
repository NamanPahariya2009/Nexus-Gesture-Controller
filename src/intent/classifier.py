import math
import time
import config

WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4

INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8

MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12

RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16

PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20


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
    def _dist(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def _fingers_up(self, landmarks, hand_scale):
        up = [False] * 5
        wrist = landmarks[WRIST]

        for i, (tip, pip, mcp) in enumerate([
            (INDEX_TIP, INDEX_PIP, INDEX_MCP),
            (MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP),
            (RING_TIP, RING_PIP, RING_MCP),
            (PINKY_TIP, PINKY_PIP, PINKY_MCP),
        ]):
            d_wrist_tip = self._dist(wrist, landmarks[tip])
            d_wrist_pip = self._dist(wrist, landmarks[pip])
            d_mcp_tip = self._dist(landmarks[mcp], landmarks[tip])
            d_mcp_pip = self._dist(landmarks[mcp], landmarks[pip])

            is_extended = (d_wrist_tip > d_wrist_pip * 1.12) and (d_mcp_tip > d_mcp_pip * 1.15)
            up[i + 1] = is_extended

        d_thumb_pinky = self._dist(landmarks[THUMB_TIP], landmarks[PINKY_MCP])
        d_thumb_ip_pinky = self._dist(landmarks[THUMB_IP], landmarks[PINKY_MCP])
        d_thumb_index_mcp = self._dist(landmarks[THUMB_TIP], landmarks[INDEX_MCP])

        thumb_out = (d_thumb_pinky > d_thumb_ip_pinky * 1.1) and (d_thumb_index_mcp > hand_scale * 0.42)
        up[0] = thumb_out

        return up

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

        hand_scale = self._dist(landmarks[WRIST], landmarks[MIDDLE_MCP])
        if hand_scale < 1e-4:
            hand_scale = 0.2

        fingers = self._fingers_up(landmarks, hand_scale)

        wrist = landmarks[WRIST]
        velocity = 0.0
        if self.prev_wrist is not None and dt > 0:
            dx = wrist.x - self.prev_wrist.x
            dy = wrist.y - self.prev_wrist.y
            velocity = math.hypot(dx, dy) / dt
        self.prev_wrist = wrist

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

        if not any(fingers[1:]):
            self.state = "FIST"
            return self.state, {"confidence": 1.0}

        dist_index = self._dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP])
        dist_middle = self._dist(landmarks[THUMB_TIP], landmarks[MIDDLE_TIP])
        dist_ring = self._dist(landmarks[THUMB_TIP], landmarks[RING_TIP])

        ratio_index = dist_index / hand_scale
        ratio_middle = dist_middle / hand_scale
        ratio_ring = dist_ring / hand_scale

        pinch_thresh = getattr(config, 'PINCH_THRESHOLD_NORM', 0.05)
        pinch_ratio_thresh = getattr(config, 'PINCH_RATIO_THRESHOLD', 0.28)

        is_pinch_index = (dist_index < pinch_thresh) or (ratio_index < pinch_ratio_thresh)
        is_pinch_middle = (dist_middle < pinch_thresh) or (ratio_middle < pinch_ratio_thresh)
        is_pinch_ring = (dist_ring < pinch_thresh) or (ratio_ring < pinch_ratio_thresh)

        if is_pinch_index and not is_pinch_middle:
            self.state = "CLICK_LEFT"
            return self.state, {"confidence": 1.0, "pinch_dist": dist_index}

        if is_pinch_middle and not is_pinch_index:
            self.state = "CLICK_RIGHT"
            return self.state, {"confidence": 1.0, "pinch_dist": dist_middle}

        if is_pinch_ring:
            self.state = "DOUBLE_CLICK"
            return self.state, {"confidence": 1.0, "pinch_dist": dist_ring}

        if fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
            self.state = "SCROLL"
            return self.state, {"norm_y": landmarks[INDEX_TIP].y, "confidence": 1.0}

        if not fingers[1] and not fingers[2] and not fingers[3] and fingers[4]:
            self.state = "VOLUME"
            return self.state, {"norm_y": landmarks[PINKY_TIP].y, "confidence": 1.0}

        if fingers[1] and fingers[2] and fingers[3] and fingers[4] and not fingers[0]:
            self.state = "SWIPE"
            return self.state, {"norm_x": landmarks[MIDDLE_TIP].x, "confidence": 1.0}

        is_open_palm = fingers[1] and fingers[2] and fingers[3] and (fingers[4] or fingers[0])
        is_pointing_index = fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]

        if is_open_palm or is_pointing_index or all(fingers):
            self.state = "MOVE"
            return self.state, {"confidence": 1.0}

        self.state = "IDLE"
        return self.state, {"confidence": 0.0}

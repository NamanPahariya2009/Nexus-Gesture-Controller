import cv2
import time
import numpy as np
import pyautogui

import config
from perception.tracker import HandTracker
from perception.smoothing import OneEuroFilter
from intent.classifier import GestureClassifier
from control.mouse_physics import PhysicsCursor
from control.system_control import set_volume, DesktopSwitcher
from ui.hud import CinematicHUD
from server.websocket import WebSocketServer


class SystemController:
    def __init__(self):
        self.running = True
        self.cap = cv2.VideoCapture(config.CAMERA_ID)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)

        self.tracker = HandTracker()
        self.start_time = time.time()
        self.ws = WebSocketServer(port=config.WS_PORT)

    def run(self):
        print(f"[{config.APP_NAME}] System initialized. Press 'Q' to quit.")

        smoother = OneEuroFilter(
            time.time(), [0.5, 0.5],
            min_cutoff=config.ONE_EURO_MIN_CUTOFF,
            beta=config.ONE_EURO_BETA,
        )
        classifier = GestureClassifier()
        cursor = PhysicsCursor()
        hud = CinematicHUD()
        switcher = DesktopSwitcher()

        self.ws.start()
        print(f"[{config.APP_NAME}] WebSocket server running on ws://localhost:{config.WS_PORT}")

        last_time = time.time()
        prev_hand_x = None
        prev_hand_y = None
        drag_active = False
        last_toggle_time = 0.0
        last_click_time = 0.0
        last_scroll_y = None

        while self.running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            success, img = self.cap.read()
            if not success:
                continue

            img = cv2.flip(img, 1)
            h_img, w_img = img.shape[:2]
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            fps = int(1 / dt) if dt > 0 else 0

            if fps < config.FAILSAFE_FPS and (current_time - self.start_time) > 2.0:
                cv2.putText(img, "SAFETY PAUSE: LOW FPS",
                            (w_img // 2 - 180, h_img // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow(config.APP_NAME, img)
                if cv2.waitKey(1) == ord('q'):
                    self.running = False
                continue

            ts_ms = (current_time - self.start_time) * 1000
            detection = self.tracker.process(img_rgb, ts_ms)

            hand_landmarks = None
            delta_x, delta_y = 0.0, 0.0
            state = "IDLE"
            meta = {}

            if detection.hand_landmarks:
                hand_landmarks = detection.hand_landmarks[0]
                raw = hand_landmarks[5]
                norm_x, norm_y = raw.x, raw.y

                filtered = smoother(current_time, [norm_x, norm_y])
                curr_x, curr_y = filtered[0], filtered[1]

                if prev_hand_x is not None:
                    delta_x = curr_x - prev_hand_x
                    delta_y = curr_y - prev_hand_y
                prev_hand_x, prev_hand_y = curr_x, curr_y

                state, meta = classifier.process(hand_landmarks)
                raw_state = state
                confidence = meta.get("confidence", 0.0)

                if state in ("SLEEPING", "SLEEP_TOGGLE"):
                    pass

                elif state == "FIST":
                    if (current_time - last_toggle_time) > config.DRAG_TOGGLE_COOLDOWN:
                        drag_active = not drag_active
                        last_toggle_time = current_time
                        if drag_active:
                            pyautogui.mouseDown()
                        else:
                            pyautogui.mouseUp()

                elif drag_active:
                    state = "DRAG_ACTIVE"
                    if raw_state in ("MOVE", "IDLE"):
                        cursor.update_relative(delta_x, delta_y, dt)

                else:
                    if state == "MOVE":
                        cursor.update_relative(delta_x, delta_y, dt)

                    elif state == "CLICK_LEFT":
                        if (current_time - last_click_time) > config.CLICK_COOLDOWN:
                            pyautogui.click()
                            last_click_time = current_time

                    elif state == "CLICK_RIGHT":
                        if (current_time - last_click_time) > config.CLICK_COOLDOWN:
                            pyautogui.rightClick()
                            last_click_time = current_time

                    elif state == "DOUBLE_CLICK":
                        if (current_time - last_click_time) > config.CLICK_COOLDOWN:
                            pyautogui.doubleClick()
                            last_click_time = current_time

                    elif state == "SCROLL":
                        scroll_y = meta.get("norm_y", 0.5)
                        if last_scroll_y is not None:
                            dy = scroll_y - last_scroll_y
                            if abs(dy) > 0.005:
                                pyautogui.scroll(int(-dy * config.SCROLL_SPEED * 100))
                        last_scroll_y = scroll_y

                    elif state == "VOLUME":
                        vol_y = meta.get("norm_y", 0.5)
                        vol = int(np.interp(vol_y, [0.1, 0.9], [100, 0]))
                        vol = max(0, min(100, vol))
                        set_volume(vol)
                        meta["volume_pct"] = vol

                    elif state == "SWIPE":
                        swipe_x = meta.get("norm_x", 0.5)
                        result = switcher.update(
                            swipe_x,
                            config.SWIPE_COOLDOWN,
                            config.SWIPE_THRESHOLD,
                        )
                        if result:
                            meta["swipe_dir"] = result

                    if state != "SCROLL":
                        last_scroll_y = None

                    if state != "SWIPE":
                        switcher.reset()

                hud.draw(img, hand_landmarks, state, confidence, meta)

            else:
                if drag_active:
                    pyautogui.mouseUp()
                    drag_active = False

                prev_hand_x = None
                prev_hand_y = None
                last_scroll_y = None
                switcher.reset()
                classifier.process(None)
                hud.draw(img, None, "IDLE", 0.0)

            self.ws.update(
                mode=state,
                fps=fps,
                hand_detected=(hand_landmarks is not None),
                gesture=state,
            )

            cv2.putText(img, f"{config.APP_NAME}  |  FPS: {fps}",
                        (20, 30), cv2.FONT_HERSHEY_PLAIN, 1, (200, 255, 200), 1)

            cv2.imshow(config.APP_NAME, img)

            if cv2.waitKey(1) == ord('q'):
                self.running = False

        if drag_active:
            pyautogui.mouseUp()
        self.cap.release()
        cv2.destroyAllWindows()
        print(f"[{config.APP_NAME}] Shutdown complete.")

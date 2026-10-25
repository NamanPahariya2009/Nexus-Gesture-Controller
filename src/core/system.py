import cv2
import time
import math
import numpy as np
import pyautogui

import config
from perception.tracker import HandTracker
from perception.smoothing import OneEuroFilter
from intent.classifier import GestureClassifier
from control.mouse_physics import PhysicsCursor
from control.system_control import set_volume, DesktopSwitcher
from ui.hud import CinematicHUD


class SystemController:
    def __init__(self):
        self.running = True
        self.cap = cv2.VideoCapture(config.CAMERA_ID)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)

        self.tracker = HandTracker()
        self.start_time = time.time()
        self.last_ts_ms = 0
        self.fullscreen = getattr(config, 'FULLSCREEN', True)

    def run(self):
        print(f"[{config.APP_NAME}] System initialized. Press 'Q' to quit, 'F' for fullscreen.")

        cv2.namedWindow(config.APP_NAME, cv2.WINDOW_NORMAL)
        if self.fullscreen:
            cv2.setWindowProperty(config.APP_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        smoother = OneEuroFilter(
            time.time(), [0.5, 0.5],
            min_cutoff=config.ONE_EURO_MIN_CUTOFF,
            beta=config.ONE_EURO_BETA,
            d_cutoff=config.ONE_EURO_D_CUTOFF,
        )
        classifier_primary = GestureClassifier()
        classifier_secondary = GestureClassifier()
        cursor = PhysicsCursor()
        hud = CinematicHUD()
        switcher = DesktopSwitcher()

        last_time = time.time()
        prev_hand_x = None
        prev_hand_y = None
        drag_active = False
        last_toggle_time = 0.0
        last_click_time = 0.0
        last_scroll_y = None
        prev_zoom_dist = None

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

            raw_ts = int((current_time - self.start_time) * 1000)
            ts_ms = max(self.last_ts_ms + 1, raw_ts)
            self.last_ts_ms = ts_ms

            detection = self.tracker.process(img_rgb, ts_ms)

            landmarks_list = detection.hand_landmarks if detection.hand_landmarks else []
            primary_landmarks = None
            secondary_landmarks = None

            if len(landmarks_list) == 1:
                primary_landmarks = landmarks_list[0]
                secondary_landmarks = None
                classifier_secondary.process(None)
                prev_zoom_dist = None
            elif len(landmarks_list) >= 2:
                h0, h1 = landmarks_list[0], landmarks_list[1]
                x0 = (h0[0].x + h0[5].x + h0[17].x) / 3.0
                x1 = (h1[0].x + h1[5].x + h1[17].x) / 3.0

                if getattr(config, 'PRIMARY_HAND', 'Right') == 'Right':
                    if x0 > x1:
                        primary_landmarks, secondary_landmarks = h0, h1
                    else:
                        primary_landmarks, secondary_landmarks = h1, h0
                else:
                    if x0 < x1:
                        primary_landmarks, secondary_landmarks = h0, h1
                    else:
                        primary_landmarks, secondary_landmarks = h1, h0
            else:
                prev_zoom_dist = None

            state_p, meta_p = "IDLE", {}
            state_s, meta_s = "IDLE", {}
            zoom_active = False

            if primary_landmarks is not None:
                state_p, meta_p = classifier_primary.process(primary_landmarks)

            if secondary_landmarks is not None:
                state_s, meta_s = classifier_secondary.process(secondary_landmarks)

            if primary_landmarks is not None and secondary_landmarks is not None:
                p_cx = (primary_landmarks[0].x + primary_landmarks[5].x + primary_landmarks[17].x) / 3.0
                p_cy = (primary_landmarks[0].y + primary_landmarks[5].y + primary_landmarks[17].y) / 3.0
                s_cx = (secondary_landmarks[0].x + secondary_landmarks[5].x + secondary_landmarks[17].x) / 3.0
                s_cy = (secondary_landmarks[0].y + secondary_landmarks[5].y + secondary_landmarks[17].y) / 3.0
                current_dist = math.hypot(p_cx - s_cx, p_cy - s_cy)

                can_zoom_p = state_p in ("MOVE", "CLICK_LEFT", "IDLE")
                can_zoom_s = state_s in ("MOVE", "CLICK_LEFT", "IDLE")

                if can_zoom_p and can_zoom_s:
                    if prev_zoom_dist is not None:
                        ddist = current_dist - prev_zoom_dist
                        if abs(ddist) > config.ZOOM_DEADZONE:
                            zoom_amount = int(ddist * config.ZOOM_SPEED * 100)
                            if zoom_amount != 0:
                                pyautogui.keyDown('ctrl')
                                pyautogui.scroll(zoom_amount)
                                pyautogui.keyUp('ctrl')
                                zoom_active = True
                    prev_zoom_dist = current_dist
                else:
                    prev_zoom_dist = None
            else:
                prev_zoom_dist = None

            delta_x, delta_y = 0.0, 0.0

            if primary_landmarks is not None:
                idx = primary_landmarks[5]
                pnk = primary_landmarks[17]
                wrs = primary_landmarks[0]
                mid = primary_landmarks[9]
                norm_x = (idx.x + pnk.x + wrs.x + mid.x * 2.0) / 5.0
                norm_y = (idx.y + pnk.y + wrs.y + mid.y * 2.0) / 5.0

                filtered = smoother(current_time, [norm_x, norm_y])
                curr_x, curr_y = filtered[0], filtered[1]

                if prev_hand_x is not None:
                    delta_x = curr_x - prev_hand_x
                    delta_y = curr_y - prev_hand_y
                prev_hand_x, prev_hand_y = curr_x, curr_y

                raw_state_p = state_p

                if not zoom_active:
                    if state_p in ("SLEEPING", "SLEEP_TOGGLE"):
                        cursor.reset()

                    elif state_p == "FIST":
                        cursor.reset()
                        if (current_time - last_toggle_time) > config.DRAG_TOGGLE_COOLDOWN:
                            drag_active = not drag_active
                            last_toggle_time = current_time
                            if drag_active:
                                pyautogui.mouseDown()
                            else:
                                pyautogui.mouseUp()

                    elif drag_active:
                        state_p = "DRAG_ACTIVE"
                        if raw_state_p in ("MOVE", "IDLE"):
                            cursor.update_relative(delta_x, delta_y, dt)

                    else:
                        if state_p == "MOVE":
                            cursor.update_relative(delta_x, delta_y, dt)

                        elif state_p == "CLICK_LEFT":
                            cursor.reset()
                            if (current_time - last_click_time) > config.CLICK_COOLDOWN:
                                pyautogui.click()
                                last_click_time = current_time

                        elif state_p == "CLICK_RIGHT":
                            cursor.reset()
                            if (current_time - last_click_time) > config.CLICK_COOLDOWN:
                                pyautogui.rightClick()
                                last_click_time = current_time

                        elif state_p == "DOUBLE_CLICK":
                            cursor.reset()
                            if (current_time - last_click_time) > config.CLICK_COOLDOWN:
                                pyautogui.doubleClick()
                                last_click_time = current_time

                        if secondary_landmarks is None:
                            if state_p == "SCROLL":
                                cursor.reset()
                                scroll_y = meta_p.get("norm_y", 0.5)
                                if last_scroll_y is not None:
                                    dy = scroll_y - last_scroll_y
                                    if abs(dy) > 0.003:
                                        pyautogui.scroll(int(-dy * config.SCROLL_SPEED * 100))
                                last_scroll_y = scroll_y

                            elif state_p == "VOLUME":
                                cursor.reset()
                                vol_y = meta_p.get("norm_y", 0.5)
                                vol = int(np.interp(vol_y, [0.1, 0.9], [100, 0]))
                                vol = max(0, min(100, vol))
                                set_volume(vol)
                                meta_p["volume_pct"] = vol

                            elif state_p == "SWIPE":
                                cursor.reset()
                                swipe_x = meta_p.get("norm_x", 0.5)
                                result = switcher.update(
                                    swipe_x,
                                    config.SWIPE_COOLDOWN,
                                    config.SWIPE_THRESHOLD,
                                )
                                if result:
                                    meta_p["swipe_dir"] = result

                            if state_p != "SCROLL":
                                last_scroll_y = None
                            if state_p != "SWIPE":
                                switcher.reset()

            else:
                if drag_active:
                    pyautogui.mouseUp()
                    drag_active = False

                prev_hand_x = None
                prev_hand_y = None
                last_scroll_y = None
                smoother.reset()
                cursor.reset()
                switcher.reset()
                classifier_primary.process(None)

            if secondary_landmarks is not None and not zoom_active:
                if state_s == "VOLUME":
                    vol_y = meta_s.get("norm_y", 0.5)
                    vol = int(np.interp(vol_y, [0.1, 0.9], [100, 0]))
                    vol = max(0, min(100, vol))
                    set_volume(vol)
                    meta_s["volume_pct"] = vol

                elif state_s == "SCROLL":
                    scroll_y = meta_s.get("norm_y", 0.5)
                    if last_scroll_y is not None:
                        dy = scroll_y - last_scroll_y
                        if abs(dy) > 0.003:
                            pyautogui.scroll(int(-dy * config.SCROLL_SPEED * 100))
                    last_scroll_y = scroll_y

                elif state_s == "SWIPE":
                    swipe_x = meta_s.get("norm_x", 0.5)
                    result = switcher.update(
                        swipe_x,
                        config.SWIPE_COOLDOWN,
                        config.SWIPE_THRESHOLD,
                    )
                    if result:
                        meta_s["swipe_dir"] = result

                if state_s != "SCROLL":
                    last_scroll_y = None
                if state_s != "SWIPE":
                    switcher.reset()

            hud.draw(
                img,
                primary_landmarks,
                state_p,
                confidence=1.0,
                meta=meta_p,
                secondary_landmarks=secondary_landmarks,
                state_s=state_s,
                meta_s=meta_s,
                zoom_active=zoom_active,
            )

            cv2.putText(img, f"{config.APP_NAME}  |  FPS: {fps}",
                        (20, 30), cv2.FONT_HERSHEY_PLAIN, 1, (200, 255, 200), 1)

            cv2.imshow(config.APP_NAME, img)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
            elif key == ord('f'):
                self.fullscreen = not self.fullscreen
                prop = cv2.WINDOW_FULLSCREEN if self.fullscreen else cv2.WINDOW_NORMAL
                cv2.setWindowProperty(config.APP_NAME, cv2.WND_PROP_FULLSCREEN, prop)

        if drag_active:
            pyautogui.mouseUp()
        self.cap.release()
        cv2.destroyAllWindows()
        print(f"[{config.APP_NAME}] Shutdown complete.")

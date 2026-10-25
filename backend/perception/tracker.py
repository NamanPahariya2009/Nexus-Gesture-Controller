import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class HandTracker:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hand_landmarker.task')
        self.model_path = os.path.abspath(model_path)

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"MediaPipe model not found at {self.model_path}")

        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def process(self, image_rgb, timestamp_ms):
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        return self.landmarker.detect_for_video(mp_image, int(timestamp_ms))
